"""Markdown 출력 포매터"""

from datetime import datetime
from typing import Union

from debate_evaluator.models.aaf import AAFResult
from debate_evaluator.models.afra import AFRAResult
from debate_evaluator.models.base import EvaluationMode, EvaluationResult
from debate_evaluator.models.dqi import DQIResult
from debate_evaluator.models.hybrid import HybridResult


class MarkdownFormatter:
    """Markdown 형식 출력 포매터

    평가 결과를 읽기 좋은 Markdown 형식으로 변환합니다.
    """

    def format(self, result: EvaluationResult) -> str:
        """평가 결과를 Markdown으로 포매팅

        Args:
            result: 평가 결과 객체

        Returns:
            Markdown 형식 문자열
        """
        # 결과 타입에 따라 적절한 포매터 호출
        if isinstance(result, DQIResult):
            return self._format_dqi(result)
        elif isinstance(result, AAFResult):
            return self._format_aaf(result)
        elif isinstance(result, HybridResult):
            return self._format_hybrid(result)
        elif isinstance(result, AFRAResult):
            return self._format_afra(result)
        else:
            return self._format_generic(result)

    def _format_header(self, mode: EvaluationMode, timestamp: datetime) -> str:
        """공통 헤더 생성"""
        mode_names = {
            EvaluationMode.DQI: "DQI (Discourse Quality Index)",
            EvaluationMode.AAF: "AAF (Argumentation, Authority, Flow)",
            EvaluationMode.HYBRID: "DQI-AAF 하이브리드",
            EvaluationMode.AFRA: "AFRA (Rhetorical Analysis)",
        }

        mode_name = mode_names.get(mode, mode.value.upper())
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        return f"""# 토론 평가 리포트

**평가 방법론**: {mode_name}
**평가 시각**: {timestamp_str}

---

"""

    def _format_dqi(self, result: DQIResult) -> str:
        """DQI 결과 포매팅"""
        output = self._format_header(result.mode, result.timestamp)

        # 토론 요약
        if result.debate_summary:
            output += f"## 토론 요약\n\n{result.debate_summary}\n\n"

        # 점수 요약 테이블
        output += "## DQI 점수 요약\n\n"
        output += "| 범주 | 코드 |\n"
        output += "|------|------|\n"

        for cs in result.category_scores:
            output += f"| {cs.category_name} | {cs.code} |\n"

        output += f"| **총점** | **{result.total_score}/21** |\n"
        output += f"| **평균** | **{result.average_score:.2f}/3** |\n\n"

        # 상세 평가
        output += "## 상세 평가\n\n"
        for cs in result.category_scores:
            output += f"### {cs.category_name}\n\n"
            output += f"- **코드**: {cs.code}\n"
            output += f"- **설명**: {cs.description}\n"
            if cs.evidence:
                output += "- **근거 발언**:\n"
                for ev in cs.evidence:
                    output += f"  > {ev}\n"
            output += "\n"

        # 종합 평가
        if result.overall_assessment:
            output += f"## 종합 평가\n\n{result.overall_assessment}\n\n"

        # 개선점
        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"

        return output

    def _format_aaf(self, result: AAFResult) -> str:
        """AAF 결과 포매팅"""
        output = self._format_header(result.mode, result.timestamp)

        # 점수 테이블
        output += "## AAF 점수 요약\n\n"
        output += "| 기준 | 점수 (1-5) |\n"
        output += "|------|------------|\n"

        for cs in result.criterion_scores:
            output += f"| {cs.criterion_name} | {cs.score} |\n"

        output += f"| **총점** | **{result.total_score}/15** |\n"
        output += f"| **평균** | **{result.average_score:.2f}/5** |\n\n"

        # 상세 평가
        output += "## 상세 평가\n\n"
        for cs in result.criterion_scores:
            output += f"### {cs.criterion_name} - {cs.score}점\n\n"

            if cs.strengths:
                output += "**강점:**\n"
                for s in cs.strengths:
                    output += f"- {s}\n"
                output += "\n"

            if cs.weaknesses:
                output += "**약점:**\n"
                for w in cs.weaknesses:
                    output += f"- {w}\n"
                output += "\n"

            if cs.feedback:
                output += f"**개선점:** {cs.feedback}\n\n"

        # 종합 분석
        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        # 개선 제안
        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"

        return output

    def _format_hybrid(self, result: HybridResult) -> str:
        """하이브리드 결과 포매팅"""
        output = self._format_header(result.mode, result.timestamp)

        # 요약 통계
        output += "## 분석 요약\n\n"
        output += f"- **총 논증 수**: {result.total_arguments}\n"
        output += f"- **평균 DQI 점수**: {result.average_dqi_score:.1f}/18\n"
        output += f"- **공격 관계 수**: {len(result.attack_relations)}\n\n"

        # 논증 노드 테이블
        output += "## 논증 강도 분석\n\n"
        output += "| 논증 ID | 발언자 | DQI 점수 | 최종 공격 수 | 강도 등급 |\n"
        output += "|---------|--------|----------|--------------|----------|\n"

        for node in result.argument_nodes:
            output += f"| {node.id} | {node.speaker or '-'} | {node.dqi_score}/18 | {node.final_attack_count} | {node.strength_rank} |\n"

        output += "\n"

        # 공격 관계
        if result.attack_relations:
            output += "## 공격 관계\n\n"
            for attacker, target in result.attack_relations:
                output += f"- {attacker} → {target}\n"
            output += "\n"

        # 충돌 해결 노트
        if result.conflict_resolution_notes:
            output += f"## 충돌 해결\n\n{result.conflict_resolution_notes}\n\n"

        # 논증 상세
        output += "## 논증 상세\n\n"
        for node in result.argument_nodes:
            output += f"### {node.id}: {node.speaker or '발언자 미상'}\n\n"
            output += f"**내용**: {node.content}\n\n"
            output += "**DQI 세부 점수**:\n"
            for key, value in node.dqi_breakdown.items():
                output += f"- {key}: {value}/3\n"
            output += "\n"

        # 종합 분석
        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        # 개선 제안
        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"

        return output

    def _format_afra(self, result: AFRAResult) -> str:
        """AFRA 결과 포매팅"""
        output = self._format_header(result.mode, result.timestamp)

        # 점수 요약 테이블
        output += "## AFRA 점수 요약\n\n"
        output += "| 영역 | 기준 | 점수 |\n"
        output += "|------|------|------|\n"

        for c in result.criteria:
            output += f"| {c.domain_name} | {c.name} | {c.score:.1f}/10 |\n"

        output += f"| **평균** | | **{result.average_score:.1f}/10** |\n\n"

        # 영역별 평균
        output += "## 영역별 평균 점수\n\n"
        output += "| 영역 | 평균 점수 |\n"
        output += "|------|----------|\n"

        for domain, score in result.domain_scores.items():
            output += f"| {domain} | {score:.1f}/10 |\n"

        output += "\n"

        # 상세 평가
        output += "## 상세 평가\n\n"
        current_domain = None
        for c in result.criteria:
            if c.domain != current_domain:
                output += f"### {c.domain_name}\n\n"
                current_domain = c.domain

            output += f"#### {c.name} - {c.score:.1f}/10\n\n"
            if c.feedback:
                output += f"{c.feedback}\n\n"

        # 시급한 개선점
        if result.urgent_improvements:
            output += "## 시급한 개선점\n\n"
            for i, imp in enumerate(result.urgent_improvements, 1):
                output += f"{i}. {imp}\n"
            output += "\n"

        # 종합 분석
        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        return output

    def _format_generic(self, result: EvaluationResult) -> str:
        """일반 결과 포매팅"""
        output = self._format_header(result.mode, result.timestamp)

        if result.summary:
            output += f"## 요약\n\n{result.summary}\n\n"

        output += "## LLM 응답\n\n"
        output += result.raw_response

        if result.recommendations:
            output += "\n\n## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"

        return output

    def format_all(self, results: dict[EvaluationMode, EvaluationResult]) -> str:
        """4가지 평가 방법론 통합 결과 포매팅

        Args:
            results: 평가 모드별 결과 딕셔너리

        Returns:
            통합 Markdown 형식 문자열
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        output = f"""# 토론 통합 평가 리포트

**평가 방법론**: 전체 (DQI, AAF, DQI-AAF, AFRA)
**평가 시각**: {timestamp_str}

---

## 평가 점수 종합

"""
        # 종합 점수 테이블
        output += "| 방법론 | 점수 | 비고 |\n"
        output += "|--------|------|------|\n"

        if EvaluationMode.DQI in results:
            dqi_result = results[EvaluationMode.DQI]
            output += f"| DQI | {dqi_result.total_score}/21 (평균 {dqi_result.average_score:.2f}/3) | 담론 품질 지수 |\n"

        if EvaluationMode.AAF in results:
            aaf_result = results[EvaluationMode.AAF]
            output += f"| AAF | {aaf_result.total_score}/15 (평균 {aaf_result.average_score:.2f}/5) | 논증/권위/흐름 |\n"

        if EvaluationMode.HYBRID in results:
            hybrid_result = results[EvaluationMode.HYBRID]
            output += f"| DQI-AAF | 평균 {hybrid_result.average_dqi_score:.1f}/18 | {hybrid_result.total_arguments}개 논증 분석 |\n"

        if EvaluationMode.AFRA in results:
            afra_result = results[EvaluationMode.AFRA]
            output += f"| AFRA | 평균 {afra_result.average_score:.1f}/10 | 수사학적 분석 |\n"

        # output += "\n---\n\n"

        # # 각 방법론별 상세 결과
        # for mode, result in results.items():
        #     mode_names = {
        #         EvaluationMode.DQI: "DQI (Discourse Quality Index)",
        #         EvaluationMode.AAF: "AAF (Argumentation, Authority, Flow)",
        #         EvaluationMode.HYBRID: "DQI-AAF 하이브리드",
        #         EvaluationMode.AFRA: "AFRA (Rhetorical Analysis)",
        #     }
        #     mode_name = mode_names.get(mode, mode.value.upper())

        #     output += f"# {mode_name}\n\n"

        #     # 각 모드별 상세 포맷 적용 (헤더 제외)
        #     if isinstance(result, DQIResult):
        #         output += self._format_dqi_body(result)
        #     elif isinstance(result, AAFResult):
        #         output += self._format_aaf_body(result)
        #     elif isinstance(result, HybridResult):
        #         output += self._format_hybrid_body(result)
        #     elif isinstance(result, AFRAResult):
        #         output += self._format_afra_body(result)
        #     else:
        #         output += result.raw_response

        #     output += "\n---\n\n"

        return output

    def _format_dqi_body(self, result: DQIResult) -> str:
        """DQI 결과 본문 포매팅 (헤더 제외)"""
        output = ""

        if result.debate_summary:
            output += f"## 토론 요약\n\n{result.debate_summary}\n\n"

        output += "## DQI 점수 요약\n\n"
        output += "| 범주 | 코드 |\n"
        output += "|------|------|\n"

        for cs in result.category_scores:
            output += f"| {cs.category_name} | {cs.code} |\n"

        output += f"| **총점** | **{result.total_score}/21** |\n"
        output += f"| **평균** | **{result.average_score:.2f}/3** |\n\n"

        output += "## 상세 평가\n\n"
        for cs in result.category_scores:
            output += f"### {cs.category_name}\n\n"
            output += f"- **코드**: {cs.code}\n"
            output += f"- **설명**: {cs.description}\n"
            if cs.evidence:
                output += "- **근거 발언**:\n"
                for ev in cs.evidence:
                    output += f"  > {ev}\n"
            output += "\n"

        if result.overall_assessment:
            output += f"## 종합 평가\n\n{result.overall_assessment}\n\n"

        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"
            output += "\n"

        return output

    def _format_aaf_body(self, result: AAFResult) -> str:
        """AAF 결과 본문 포매팅 (헤더 제외)"""
        output = ""

        output += "## AAF 점수 요약\n\n"
        output += "| 기준 | 점수 (1-5) |\n"
        output += "|------|------------|\n"

        for cs in result.criterion_scores:
            output += f"| {cs.criterion_name} | {cs.score} |\n"

        output += f"| **총점** | **{result.total_score}/15** |\n"
        output += f"| **평균** | **{result.average_score:.2f}/5** |\n\n"

        output += "## 상세 평가\n\n"
        for cs in result.criterion_scores:
            output += f"### {cs.criterion_name} - {cs.score}점\n\n"

            if cs.strengths:
                output += "**강점:**\n"
                for s in cs.strengths:
                    output += f"- {s}\n"
                output += "\n"

            if cs.weaknesses:
                output += "**약점:**\n"
                for w in cs.weaknesses:
                    output += f"- {w}\n"
                output += "\n"

            if cs.feedback:
                output += f"**개선점:** {cs.feedback}\n\n"

        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"
            output += "\n"

        return output

    def _format_hybrid_body(self, result: HybridResult) -> str:
        """하이브리드 결과 본문 포매팅 (헤더 제외)"""
        output = ""

        output += "## 분석 요약\n\n"
        output += f"- **총 논증 수**: {result.total_arguments}\n"
        output += f"- **평균 DQI 점수**: {result.average_dqi_score:.1f}/18\n"
        output += f"- **공격 관계 수**: {len(result.attack_relations)}\n\n"

        output += "## 논증 강도 분석\n\n"
        output += "| 논증 ID | 발언자 | DQI 점수 | 최종 공격 수 | 강도 등급 |\n"
        output += "|---------|--------|----------|--------------|----------|\n"

        for node in result.argument_nodes:
            output += f"| {node.id} | {node.speaker or '-'} | {node.dqi_score}/18 | {node.final_attack_count} | {node.strength_rank} |\n"

        output += "\n"

        if result.attack_relations:
            output += "## 공격 관계\n\n"
            for attacker, target in result.attack_relations:
                output += f"- {attacker} → {target}\n"
            output += "\n"

        if result.conflict_resolution_notes:
            output += f"## 충돌 해결\n\n{result.conflict_resolution_notes}\n\n"

        output += "## 논증 상세\n\n"
        for node in result.argument_nodes:
            output += f"### {node.id}: {node.speaker or '발언자 미상'}\n\n"
            output += f"**내용**: {node.content}\n\n"
            output += "**DQI 세부 점수**:\n"
            for key, value in node.dqi_breakdown.items():
                output += f"- {key}: {value}/3\n"
            output += "\n"

        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        if result.recommendations:
            output += "## 개선 제안\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"
            output += "\n"

        return output

    def _format_afra_body(self, result: AFRAResult) -> str:
        """AFRA 결과 본문 포매팅 (헤더 제외)"""
        output = ""

        output += "## AFRA 점수 요약\n\n"
        output += "| 영역 | 기준 | 점수 |\n"
        output += "|------|------|------|\n"

        for c in result.criteria:
            output += f"| {c.domain_name} | {c.name} | {c.score:.1f}/10 |\n"

        output += f"| **평균** | | **{result.average_score:.1f}/10** |\n\n"

        output += "## 영역별 평균 점수\n\n"
        output += "| 영역 | 평균 점수 |\n"
        output += "|------|----------|\n"

        for domain, score in result.domain_scores.items():
            output += f"| {domain} | {score:.1f}/10 |\n"

        output += "\n"

        output += "## 상세 평가\n\n"
        current_domain = None
        for c in result.criteria:
            if c.domain != current_domain:
                output += f"### {c.domain_name}\n\n"
                current_domain = c.domain

            output += f"#### {c.name} - {c.score:.1f}/10\n\n"
            if c.feedback:
                output += f"{c.feedback}\n\n"

        if result.urgent_improvements:
            output += "## 시급한 개선점\n\n"
            for i, imp in enumerate(result.urgent_improvements, 1):
                output += f"{i}. {imp}\n"
            output += "\n"

        if result.overall_analysis:
            output += f"## 종합 분석\n\n{result.overall_analysis}\n\n"

        return output
