"""AFRA (Argumentation Framework for Rhetorical Analysis) 데이터 모델"""

from enum import Enum

from pydantic import BaseModel, Field

from debate_evaluator.models.base import EvaluationMode, EvaluationResult


class AFRADomain(str, Enum):
    """AFRA 4대 영역"""

    LOGOS = "logos"  # 논리적 품질
    ETHOS_PATHOS = "ethos_pathos"  # 수사적 호소
    TECHNIQUE = "technique"  # 토론 기술 및 전략
    LANGUAGE = "language"  # 언어적 품질

    @property
    def display_name(self) -> str:
        """한글 표시명"""
        names = {
            "logos": "논리적 품질 (Logos)",
            "ethos_pathos": "수사적 호소 (Ethos & Pathos)",
            "technique": "토론 기술 및 전략",
            "language": "언어적 품질",
        }
        return names.get(self.value, self.value)


class AFRACriterion(BaseModel):
    """개별 기준 점수 (10개 기준 중 하나)"""

    domain: AFRADomain = Field(..., description="소속 영역")
    name: str = Field(..., description="기준명")
    score: float = Field(..., ge=0, le=10, description="점수 (0-10)")
    feedback: str = Field(default="", description="피드백")

    @property
    def domain_name(self) -> str:
        """영역 한글명"""
        return self.domain.display_name


class AFRAResult(EvaluationResult):
    """AFRA 평가 결과

    4대 영역, 10개 세부 기준으로 수사학적 품질을 평가합니다.
    """

    mode: EvaluationMode = EvaluationMode.AFRA
    criteria: list[AFRACriterion] = Field(
        default_factory=list,
        description="10개 기준별 점수"
    )
    domain_scores: dict[str, float] = Field(
        default_factory=dict,
        description="영역별 평균 점수"
    )
    overall_analysis: str = Field(default="", description="종합 분석")
    urgent_improvements: list[str] = Field(
        default_factory=list,
        description="시급한 개선점 3가지"
    )

    @property
    def total_score(self) -> float:
        """총점 (0-100)"""
        if not self.criteria:
            return 0.0
        return sum(c.score for c in self.criteria) * 10 / len(self.criteria)

    @property
    def average_score(self) -> float:
        """평균 점수 (0-10)"""
        if not self.criteria:
            return 0.0
        return sum(c.score for c in self.criteria) / len(self.criteria)

    def get_criteria_by_domain(self, domain: AFRADomain) -> list[AFRACriterion]:
        """특정 영역의 기준들 반환"""
        return [c for c in self.criteria if c.domain == domain]

    def get_domain_average(self, domain: AFRADomain) -> float:
        """특정 영역의 평균 점수"""
        domain_criteria = self.get_criteria_by_domain(domain)
        if not domain_criteria:
            return 0.0
        return sum(c.score for c in domain_criteria) / len(domain_criteria)
