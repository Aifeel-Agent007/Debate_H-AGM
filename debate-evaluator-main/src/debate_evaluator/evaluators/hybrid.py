"""DQI-AAF 하이브리드 평가자"""

import re
from typing import Optional

from debate_evaluator.evaluators.base import BaseEvaluator, EvaluatorFactory
from debate_evaluator.models.base import EvaluationMode
from debate_evaluator.models.hybrid import ArgumentNode, HybridResult


@EvaluatorFactory.register(EvaluationMode.HYBRID)
class HybridEvaluator(BaseEvaluator):
    """DQI-AAF 하이브리드 평가자

    논증 노드 식별, DQI 점수 부여, 공격 관계 분석을 수행합니다.
    """

    def parse_response(self, raw_response: str) -> HybridResult:
        """LLM 응답을 HybridResult로 파싱

        Args:
            raw_response: LLM 원본 응답

        Returns:
            HybridResult 객체
        """
        # 논증 노드 추출
        argument_nodes = self._extract_argument_nodes(raw_response)

        # 공격 관계 추출
        attack_relations = self._extract_attack_relations(raw_response)

        # 충돌 해결 노트 추출
        conflict_notes = self._extract_section(raw_response, "충돌 해결")

        # 종합 분석 추출
        overall_analysis = self._extract_section(raw_response, "종합 분석")

        # 개선 제안 추출
        recommendations = self._extract_recommendations(raw_response)

        # summary 생성
        avg_score = sum(n.dqi_score for n in argument_nodes) / len(argument_nodes) if argument_nodes else 0
        summary = f"하이브리드 분석 완료. {len(argument_nodes)}개 논증, 평균 DQI: {avg_score:.1f}/18"

        return HybridResult(
            raw_response=raw_response,
            argument_nodes=argument_nodes,
            attack_relations=attack_relations,
            conflict_resolution_notes=conflict_notes,
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

        return recommendations

    def _extract_argument_nodes(self, text: str) -> list[ArgumentNode]:
        """논증 노드 추출"""
        nodes = []

        # ARG 패턴 찾기
        arg_pattern = r"###\s*(ARG\d+):?\s*\[?([^\]\n]*)\]?\s*\n(.*?)(?=\n###|\n##|\Z)"
        matches = re.finditer(arg_pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            arg_id = match.group(1).upper()
            speaker = match.group(2).strip() if match.group(2) else ""
            section_text = match.group(3)

            # 발언 요약 추출
            content = self._extract_content_summary(section_text)

            # DQI 점수 추출
            dqi_breakdown = self._extract_dqi_breakdown(section_text)
            dqi_score = sum(dqi_breakdown.values())

            nodes.append(ArgumentNode(
                id=arg_id,
                speaker=speaker,
                content=content,
                dqi_score=dqi_score,
                dqi_breakdown=dqi_breakdown,
            ))

        # 최종 강도 테이블에서 추가 정보 업데이트
        self._update_from_final_table(text, nodes)

        return nodes

    def _extract_content_summary(self, section_text: str) -> str:
        """발언 요약 추출"""
        pattern = r"\*?\*?발언\s*요약\*?\*?:?\s*(.*?)(?=\n\*?\*?|\n\||\Z)"
        match = re.search(pattern, section_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]
        return ""

    def _extract_dqi_breakdown(self, section_text: str) -> dict[str, int]:
        """DQI 세부 점수 추출"""
        breakdown = {}

        # 테이블에서 점수 추출
        indicators = [
            ("participation", "참여"),
            ("justification_level", "정당화 수준"),
            ("justification_content", "정당화 내용"),
            ("respect", "존중"),
            ("counterargument", "반론"),
            ("constructive", "건설적"),
        ]

        for key, korean in indicators:
            pattern = rf"\|\s*{korean}.*?\|\s*(\d)"
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                breakdown[key] = int(match.group(1))
            else:
                breakdown[key] = 0

        return breakdown

    def _extract_attack_relations(self, text: str) -> list[tuple[str, str]]:
        """공격 관계 추출"""
        relations = []

        # "ARG1 → ARG2" 또는 "ARG1 -> ARG2" 패턴
        pattern = r"(ARG\d+)\s*(?:→|->)+\s*(ARG\d+)"
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            attacker = match.group(1).upper()
            target = match.group(2).upper()
            if (attacker, target) not in relations:
                relations.append((attacker, target))

        return relations

    def _update_from_final_table(self, text: str, nodes: list[ArgumentNode]) -> None:
        """최종 강도 테이블에서 정보 업데이트"""
        # 테이블 행 패턴
        pattern = r"\|\s*(ARG\d+)\s*\|.*?\|\s*(\d+)/18\s*\|\s*(\d+)"
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            arg_id = match.group(1).upper()
            dqi_score = int(match.group(2))
            attack_count = int(match.group(3))

            # 해당 노드 찾아서 업데이트
            for node in nodes:
                if node.id == arg_id:
                    node.dqi_score = dqi_score
                    node.final_attack_count = attack_count
                    break
