"""AAF (Argumentation, Authority, Flow) 평가자"""

import re

from debate_evaluator.evaluators.base import BaseEvaluator, EvaluatorFactory
from debate_evaluator.models.aaf import AAFCriterion, AAFCriterionScore, AAFResult
from debate_evaluator.models.base import EvaluationMode


@EvaluatorFactory.register(EvaluationMode.AAF)
class AAFEvaluator(BaseEvaluator):
    """AAF 평가자

    논증, 권위, 흐름 3가지 기준으로 토론을 평가합니다.
    """

    def parse_response(self, raw_response: str) -> AAFResult:
        """LLM 응답을 AAFResult로 파싱

        Args:
            raw_response: LLM 원본 응답

        Returns:
            AAFResult 객체
        """
        # 기준별 점수 추출
        criterion_scores = self._extract_criterion_scores(raw_response)

        # 종합 분석 추출
        overall_analysis = self._extract_section(raw_response, "종합 분석")

        # 개선 제안 추출
        recommendations = self._extract_recommendations(raw_response)

        # summary 생성
        total = sum(cs.score for cs in criterion_scores)
        summary = f"AAF 평가 완료. 총점: {total}/15" if criterion_scores else "AAF 평가 완료"

        return AAFResult(
            raw_response=raw_response,
            criterion_scores=criterion_scores,
            overall_analysis=overall_analysis,
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

    def _extract_recommendations(self, text: str) -> list[str]:
        """개선 제안 목록 추출"""
        section = self._extract_section(text, "개선 제안")
        if not section:
            return []

        recommendations = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                recommendations.append(line[1:].strip())
            elif line and not line.startswith("#"):
                recommendations.append(line)

        return recommendations

    def _extract_criterion_scores(self, text: str) -> list[AAFCriterionScore]:
        """기준별 점수 추출"""
        scores = []

        # 테이블에서 점수 추출
        table_scores = self._extract_scores_from_table(text)

        # 각 기준에 대한 상세 정보 추출
        criterion_info = {
            AAFCriterion.ARGUMENTATION: ("A", "Argumentation", "논증"),
            AAFCriterion.AUTHORITY: ("B", "Authority", "권위"),
            AAFCriterion.FLOW: ("C", "Flow", "흐름"),
        }

        for criterion, (letter, eng_name, kor_name) in criterion_info.items():
            # 테이블에서 점수 가져오기
            score = table_scores.get(criterion, 3)  # 기본값 3

            # 상세 섹션에서 정보 추출
            detail = self._extract_criterion_detail(text, letter, eng_name, kor_name)

            scores.append(AAFCriterionScore(
                criterion=criterion,
                score=score,
                strengths=detail.get("strengths", []),
                weaknesses=detail.get("weaknesses", []),
                feedback=detail.get("feedback", ""),
            ))

        return scores

    def _extract_scores_from_table(self, text: str) -> dict[AAFCriterion, int]:
        """테이블에서 점수 추출"""
        scores = {}

        # Argumentation 점수
        arg_pattern = r"Argumentation.*?\|\s*(\d)"
        arg_match = re.search(arg_pattern, text, re.IGNORECASE)
        if arg_match:
            scores[AAFCriterion.ARGUMENTATION] = int(arg_match.group(1))

        # Authority 점수
        auth_pattern = r"Authority.*?\|\s*(\d)"
        auth_match = re.search(auth_pattern, text, re.IGNORECASE)
        if auth_match:
            scores[AAFCriterion.AUTHORITY] = int(auth_match.group(1))

        # Flow 점수
        flow_pattern = r"Flow.*?\|\s*(\d)"
        flow_match = re.search(flow_pattern, text, re.IGNORECASE)
        if flow_match:
            scores[AAFCriterion.FLOW] = int(flow_match.group(1))

        return scores

    def _extract_criterion_detail(
        self,
        text: str,
        letter: str,
        eng_name: str,
        kor_name: str,
    ) -> dict:
        """개별 기준의 상세 정보 추출"""
        # 섹션 패턴
        pattern = rf"###\s*{letter}\.?\s*{eng_name}.*?\n(.*?)(?=\n###|\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not match:
            return {"strengths": [], "weaknesses": [], "feedback": ""}

        section_text = match.group(1)

        # 강점 추출
        strengths = self._extract_list_items(section_text, "강점")

        # 약점 추출
        weaknesses = self._extract_list_items(section_text, "약점")

        # 개선점을 피드백으로
        improvements = self._extract_list_items(section_text, "개선점")
        feedback = " ".join(improvements) if improvements else ""

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": feedback,
        }

    def _extract_list_items(self, text: str, section_name: str) -> list[str]:
        """리스트 항목 추출"""
        pattern = rf"\*?\*?{section_name}\*?\*?:?\s*\n(.*?)(?=\n\*?\*?[가-힣]+\*?\*?:|\n###|\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not match:
            return []

        items = []
        for line in match.group(1).split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                items.append(line[1:].strip())

        return items[:5]  # 최대 5개
