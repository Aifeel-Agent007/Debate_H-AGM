"""DQI-AAF 하이브리드 모델 데이터 모델"""

from typing import Optional

from pydantic import BaseModel, Field

from debate_evaluator.models.base import EvaluationMode, EvaluationResult


class ArgumentNode(BaseModel):
    """논증 노드

    각 발언을 개별 논증(Argument)으로 식별합니다.
    """

    id: str = Field(..., description="논증 ID (ARG1, ARG2, ...)")
    speaker: str = Field(default="", description="발언자")
    content: str = Field(..., description="발언 내용 (요약)")
    dqi_score: int = Field(default=0, ge=0, le=18, description="DQI 총점 (0-18)")
    dqi_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="DQI 세부 점수 (6가지 지표)"
    )
    attacks: list[str] = Field(
        default_factory=list,
        description="이 논증이 공격하는 다른 논증 ID 목록"
    )
    attacked_by: list[str] = Field(
        default_factory=list,
        description="이 논증을 공격하는 다른 논증 ID 목록"
    )
    final_attack_count: int = Field(
        default=0,
        ge=0,
        description="충돌 해소 후 최종 공격 수"
    )

    @property
    def strength_rank(self) -> str:
        """강도 등급"""
        if self.dqi_score >= 15:
            return "매우 강함"
        elif self.dqi_score >= 12:
            return "강함"
        elif self.dqi_score >= 9:
            return "보통"
        elif self.dqi_score >= 6:
            return "약함"
        else:
            return "매우 약함"


class HybridResult(EvaluationResult):
    """DQI-AAF 하이브리드 평가 결과

    각 발언을 논증 노드로 식별하고, DQI 점수로 가중치를 부여하여
    논증 간 공격 관계(Attack)를 분석합니다.
    """

    mode: EvaluationMode = EvaluationMode.HYBRID
    argument_nodes: list[ArgumentNode] = Field(
        default_factory=list,
        description="논증 노드 목록"
    )
    attack_relations: list[tuple[str, str]] = Field(
        default_factory=list,
        description="공격 관계 목록 (공격자, 피공격자)"
    )
    conflict_resolution_notes: str = Field(
        default="",
        description="충돌 해결 설명"
    )
    overall_analysis: str = Field(default="", description="종합 분석")

    @property
    def total_arguments(self) -> int:
        """총 논증 수"""
        return len(self.argument_nodes)

    @property
    def average_dqi_score(self) -> float:
        """평균 DQI 점수"""
        if not self.argument_nodes:
            return 0.0
        return sum(n.dqi_score for n in self.argument_nodes) / len(self.argument_nodes)

    @property
    def strongest_argument(self) -> Optional[ArgumentNode]:
        """가장 강한 논증"""
        if not self.argument_nodes:
            return None
        return max(self.argument_nodes, key=lambda n: n.dqi_score)

    @property
    def weakest_argument(self) -> Optional[ArgumentNode]:
        """가장 약한 논증"""
        if not self.argument_nodes:
            return None
        return min(self.argument_nodes, key=lambda n: n.dqi_score)

    def get_argument_by_id(self, arg_id: str) -> Optional[ArgumentNode]:
        """ID로 논증 노드 검색"""
        for node in self.argument_nodes:
            if node.id == arg_id:
                return node
        return None
