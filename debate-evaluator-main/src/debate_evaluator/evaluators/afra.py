"""AFRA (Argumentation Framework for Rhetorical Analysis) 평가자"""

import re

from debate_evaluator.evaluators.base import BaseEvaluator, EvaluatorFactory
from debate_evaluator.models.afra import AFRACriterion, AFRADomain, AFRAResult
from debate_evaluator.models.base import EvaluationMode


@EvaluatorFactory.register(EvaluationMode.AFRA)
class AFRAEvaluator(BaseEvaluator):
    """AFRA 평가자

    수사학적 관점에서 4개 영역 10개 세부 기준을 평가합니다.
    """

    # 10개 기준 정의 (영역, 이름)
    CRITERIA_DEFINITIONS = [
        (AFRADomain.LOGOS, "주장의 명확성"),
        (AFRADomain.LOGOS, "증거의 질과 타당성"),
        (AFRADomain.LOGOS, "논리적 일관성"),
        (AFRADomain.ETHOS_PATHOS, "신뢰성"),
        (AFRADomain.ETHOS_PATHOS, "감정적 호소의 적절성"),
        (AFRADomain.TECHNIQUE, "청중 및 상황 인식"),
        (AFRADomain.TECHNIQUE, "반박의 효과성"),
        (AFRADomain.TECHNIQUE, "구성 및 흐름"),
        (AFRADomain.LANGUAGE, "언어의 명료성"),
        (AFRADomain.LANGUAGE, "어조의 균형"),
    ]

    def parse_response(self, raw_response: str) -> AFRAResult:
        """LLM 응답을 AFRAResult로 파싱

        Args:
            raw_response: LLM 원본 응답

        Returns:
            AFRAResult 객체
        """
        # 10개 기준별 점수 추출
        criteria = self._extract_criteria(raw_response)

        # 영역별 평균 점수 계산
        domain_scores = self._calculate_domain_scores(criteria)

        # 종합 분석 추출
        overall_analysis = self._extract_section(raw_response, "종합 분석")

        # 시급한 개선점 추출
        urgent_improvements = self._extract_urgent_improvements(raw_response)

        # 개선 제안 추출 (recommendations 필드용)
        recommendations = [imp for imp in urgent_improvements]

        # summary 생성
        avg_score = sum(c.score for c in criteria) / len(criteria) if criteria else 0
        summary = f"AFRA 평가 완료. 평균 점수: {avg_score:.1f}/10"

        return AFRAResult(
            raw_response=raw_response,
            criteria=criteria,
            domain_scores=domain_scores,
            overall_analysis=overall_analysis,
            urgent_improvements=urgent_improvements,
            summary=summary,
            recommendations=recommendations,
        )

    def _extract_section(self, text: str, section_name: str) -> str:
        """특정 섹션 내용 추출"""
        pattern = rf"##\s*{section_name}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_criteria(self, text: str) -> list[AFRACriterion]:
        """10개 기준별 점수 추출"""
        criteria = []

        for domain, name in self.CRITERIA_DEFINITIONS:
            score, feedback = self._extract_single_criterion(text, name)
            criteria.append(AFRACriterion(
                domain=domain,
                name=name,
                score=score,
                feedback=feedback,
            ))

        return criteria

    def _extract_single_criterion(self, text: str, criterion_name: str) -> tuple[float, str]:
        """단일 기준의 점수와 피드백 추출"""
        # 다양한 패턴으로 점수 찾기
        patterns = [
            rf"####?\s*\d*\)?\s*{re.escape(criterion_name)}.*?\n.*?\*?\*?점수\*?\*?:?\s*(\d+(?:\.\d+)?)\s*/?\s*10",
            rf"{re.escape(criterion_name)}.*?\|\s*(\d+(?:\.\d+)?)\s*/?\s*10",
            rf"\|\s*{re.escape(criterion_name)}\s*\|\s*(\d+(?:\.\d+)?)",
        ]

        score = 5.0  # 기본값
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    score = float(match.group(1))
                    break
                except ValueError:
                    pass

        # 피드백 추출 (평가 내용)
        feedback_pattern = rf"####?\s*\d*\)?\s*{re.escape(criterion_name)}.*?\n.*?\*?\*?평가\*?\*?:?\s*(.*?)(?=\n\*?\*?|\n####|\n###|\Z)"
        feedback_match = re.search(feedback_pattern, text, re.IGNORECASE | re.DOTALL)
        feedback = feedback_match.group(1).strip()[:300] if feedback_match else ""

        return score, feedback

    def _calculate_domain_scores(self, criteria: list[AFRACriterion]) -> dict[str, float]:
        """영역별 평균 점수 계산"""
        domain_scores = {}

        for domain in AFRADomain:
            domain_criteria = [c for c in criteria if c.domain == domain]
            if domain_criteria:
                avg = sum(c.score for c in domain_criteria) / len(domain_criteria)
                domain_scores[domain.value] = round(avg, 2)
            else:
                domain_scores[domain.value] = 0.0

        return domain_scores

    def _extract_urgent_improvements(self, text: str) -> list[str]:
        """시급한 개선점 3가지 추출"""
        section = self._extract_section(text, "시급한 개선점")
        if not section:
            return []

        improvements = []

        # "### 1." 또는 "1." 패턴으로 분리
        pattern = r"###?\s*\d+\.?\s*\[?([^\]\n]+)\]?"
        matches = re.finditer(pattern, section)

        for match in matches:
            title = match.group(1).strip()
            if title:
                improvements.append(title)

        return improvements[:3]  # 최대 3개
