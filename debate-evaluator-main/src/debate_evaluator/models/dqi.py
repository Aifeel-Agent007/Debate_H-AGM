"""DQI (Discourse Quality Index) 데이터 모델"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from debate_evaluator.models.base import EvaluationMode, EvaluationResult


class DQICategory(str, Enum):
    """DQI 7가지 평가 범주"""

    PARTICIPATION = "participation"  # 참여 평등
    JUSTIFICATION_LEVEL = "justification_level"  # 정당화 수준
    JUSTIFICATION_CONTENT = "justification_content"  # 정당화 내용
    RESPECT_GROUPS = "respect_groups"  # 집단에 대한 존중
    RESPECT_DEMANDS = "respect_demands"  # 요구에 대한 존중
    RESPECT_COUNTERARGS = "respect_counterargs"  # 반론에 대한 존중
    CONSTRUCTIVE_POLITICS = "constructive_politics"  # 건설적인 정치

    @property
    def display_name(self) -> str:
        """한글 표시명"""
        names = {
            "participation": "참여 평등",
            "justification_level": "정당화 수준",
            "justification_content": "정당화 내용",
            "respect_groups": "집단에 대한 존중",
            "respect_demands": "요구에 대한 존중",
            "respect_counterargs": "반론에 대한 존중",
            "constructive_politics": "건설적인 정치",
        }
        return names.get(self.value, self.value)


class DQICategoryScore(BaseModel):
    """개별 범주 점수"""

    category: DQICategory = Field(..., description="평가 범주")
    code: int = Field(..., ge=0, le=3, description="코딩 레벨 (0-3)")
    description: str = Field(..., description="점수 부여 근거")
    evidence: list[str] = Field(
        default_factory=list,
        description="스크립트 내 근거 발언"
    )

    @property
    def category_name(self) -> str:
        """범주 한글명"""
        return self.category.display_name


class DQIResult(EvaluationResult):
    """DQI 평가 결과

    7가지 범주별 코딩 레벨(0-3)과 근거를 포함합니다.
    """

    mode: EvaluationMode = EvaluationMode.DQI
    debate_summary: str = Field(default="", description="토론 요약")
    category_scores: list[DQICategoryScore] = Field(
        default_factory=list,
        description="범주별 점수"
    )
    overall_assessment: str = Field(default="", description="종합 평가")

    @property
    def total_score(self) -> int:
        """총점 (0-21)"""
        return sum(cs.code for cs in self.category_scores)

    @property
    def average_score(self) -> float:
        """평균 점수"""
        if not self.category_scores:
            return 0.0
        return self.total_score / len(self.category_scores)

    @property
    def score_summary(self) -> dict[str, int]:
        """범주별 점수 요약"""
        return {cs.category.value: cs.code for cs in self.category_scores}

    def get_category_score(self, category: DQICategory) -> Optional[DQICategoryScore]:
        """특정 범주의 점수 반환"""
        for cs in self.category_scores:
            if cs.category == category:
                return cs
        return None
