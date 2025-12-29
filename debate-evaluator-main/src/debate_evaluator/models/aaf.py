"""AAF (Argumentation, Authority, Flow) 데이터 모델"""

from enum import Enum

from pydantic import BaseModel, Field

from debate_evaluator.models.base import EvaluationMode, EvaluationResult


class AAFCriterion(str, Enum):
    """AAF 3가지 평가 기준"""

    ARGUMENTATION = "argumentation"  # 논증
    AUTHORITY = "authority"  # 권위 및 신뢰성
    FLOW = "flow"  # 흐름 및 구조

    @property
    def display_name(self) -> str:
        """한글 표시명"""
        names = {
            "argumentation": "논증 (Argumentation)",
            "authority": "권위 및 신뢰성 (Authority)",
            "flow": "흐름 및 구조 (Flow)",
        }
        return names.get(self.value, self.value)


class AAFCriterionScore(BaseModel):
    """개별 기준 점수"""

    criterion: AAFCriterion = Field(..., description="평가 기준")
    score: int = Field(..., ge=1, le=5, description="점수 (1-5)")
    strengths: list[str] = Field(default_factory=list, description="강점")
    weaknesses: list[str] = Field(default_factory=list, description="약점")
    feedback: str = Field(default="", description="상세 피드백")

    @property
    def criterion_name(self) -> str:
        """기준 한글명"""
        return self.criterion.display_name


class AAFResult(EvaluationResult):
    """AAF 평가 결과

    3가지 기준별 5점 척도 점수와 피드백을 포함합니다.
    """

    mode: EvaluationMode = EvaluationMode.AAF
    criterion_scores: list[AAFCriterionScore] = Field(
        default_factory=list,
        description="기준별 점수"
    )
    overall_analysis: str = Field(default="", description="종합 분석")

    @property
    def total_score(self) -> int:
        """총점 (3-15)"""
        return sum(cs.score for cs in self.criterion_scores)

    @property
    def average_score(self) -> float:
        """평균 점수"""
        if not self.criterion_scores:
            return 0.0
        return self.total_score / len(self.criterion_scores)

    @property
    def score_table(self) -> dict[str, int]:
        """점수 테이블"""
        return {cs.criterion.value: cs.score for cs in self.criterion_scores}
