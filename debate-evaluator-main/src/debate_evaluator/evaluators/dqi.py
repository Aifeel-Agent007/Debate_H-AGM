"""DQI (Discourse Quality Index) 평가자"""

import re
from typing import Optional

from debate_evaluator.evaluators.base import BaseEvaluator, EvaluatorFactory
from debate_evaluator.models.base import EvaluationMode
from debate_evaluator.models.dqi import DQICategory, DQICategoryScore, DQIResult


@EvaluatorFactory.register(EvaluationMode.DQI)
class DQIEvaluator(BaseEvaluator):
    """DQI 평가자

    토론의 담론 품질을 7가지 범주로 평가합니다.
    """

    def parse_response(self, raw_response: str) -> DQIResult:
        """LLM 응답을 DQIResult로 파싱

        Args:
            raw_response: LLM 원본 응답

        Returns:
            DQIResult 객체
        """
        # 토론 요약 추출
        debate_summary = self._extract_section(raw_response, "토론 요약")

        # 종합 평가 추출
        overall_assessment = self._extract_section(raw_response, "종합 평가")

        # 개선점 추출
        recommendations = self._extract_recommendations(raw_response)

        # 범주별 점수 추출
        category_scores = self._extract_category_scores(raw_response)

        # summary 생성
        summary = f"DQI 평가 완료. 평균 점수: {sum(cs.code for cs in category_scores) / len(category_scores):.2f}/3" if category_scores else "DQI 평가 완료"

        return DQIResult(
            raw_response=raw_response,
            debate_summary=debate_summary,
            category_scores=category_scores,
            overall_assessment=overall_assessment,
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
        """개선점 목록 추출"""
        section = self._extract_section(text, "개선점 제안")
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

    def _extract_category_scores(self, text: str) -> list[DQICategoryScore]:
        """범주별 점수 추출"""
        scores = []

        # 범주 매핑
        category_mapping = {
            "참여 평등": DQICategory.PARTICIPATION,
            "participation equality": DQICategory.PARTICIPATION,
            "정당화 수준": DQICategory.JUSTIFICATION_LEVEL,
            "level of justification": DQICategory.JUSTIFICATION_LEVEL,
            "정당화 내용": DQICategory.JUSTIFICATION_CONTENT,
            "content of justification": DQICategory.JUSTIFICATION_CONTENT,
            "집단에 대한 존중": DQICategory.RESPECT_GROUPS,
            "respect toward groups": DQICategory.RESPECT_GROUPS,
            "요구에 대한 존중": DQICategory.RESPECT_DEMANDS,
            "respect toward demands": DQICategory.RESPECT_DEMANDS,
            "반론에 대한 존중": DQICategory.RESPECT_COUNTERARGS,
            "respect toward counterarguments": DQICategory.RESPECT_COUNTERARGS,
            "건설적인 정치": DQICategory.CONSTRUCTIVE_POLITICS,
            "constructive politics": DQICategory.CONSTRUCTIVE_POLITICS,
        }

        # 각 범주 섹션에서 점수 추출
        for name, category in category_mapping.items():
            score = self._extract_single_category_score(text, name, category)
            if score and not any(s.category == category for s in scores):
                scores.append(score)

        return scores

    def _extract_single_category_score(
        self,
        text: str,
        section_name: str,
        category: DQICategory,
    ) -> Optional[DQICategoryScore]:
        """단일 범주 점수 추출"""
        # 섹션 찾기
        pattern = rf"###\s*\d*\.?\s*{re.escape(section_name)}.*?\n(.*?)(?=\n###|\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not match:
            return None

        section_text = match.group(1)

        # 코드 추출
        code_pattern = r"\*?\*?코드\*?\*?:?\s*(\d+|2a|2b)"
        code_match = re.search(code_pattern, section_text, re.IGNORECASE)

        if not code_match:
            return None

        code_str = code_match.group(1)
        # 2a, 2b는 2로 변환
        code = 2 if code_str in ("2a", "2b") else int(code_str)

        # 근거 추출
        evidence_pattern = r"\*?\*?근거\*?\*?:?\s*(.*?)(?=\n\*?\*?|\Z)"
        evidence_match = re.search(evidence_pattern, section_text, re.DOTALL | re.IGNORECASE)
        evidence_text = evidence_match.group(1).strip() if evidence_match else ""

        # 근거를 리스트로 분리
        evidence_list = []
        if evidence_text:
            # 인용문이나 문장 단위로 분리
            for line in evidence_text.split("\n"):
                line = line.strip()
                if line and not line.startswith("-"):
                    evidence_list.append(line)
                elif line.startswith("-"):
                    evidence_list.append(line[1:].strip())

        return DQICategoryScore(
            category=category,
            code=code,
            description=evidence_text[:200] if evidence_text else f"{category.display_name} 평가",
            evidence=evidence_list[:5],  # 최대 5개
        )
