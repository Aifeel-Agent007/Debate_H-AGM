"""기본 데이터 모델"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class EvaluationMode(str, Enum):
    """평가 모드 열거형

    지원되는 4가지 평가 방법론:
    - DQI: Discourse Quality Index (담론 품질 지수)
    - AAF: Argumentation, Authority, Flow (논증, 권위, 흐름)
    - HYBRID: DQI-AAF 통합 모델
    - AFRA: Argumentation Framework for Rhetorical Analysis (수사학적 분석)
    """
    DQI = "dqi"
    AAF = "aaf"
    HYBRID = "dqi-aaf"
    AFRA = "afra"

    @classmethod
    def from_string(cls, value: str) -> "EvaluationMode":
        """문자열로부터 EvaluationMode 생성

        Args:
            value: 모드 문자열 (대소문자 무관)

        Returns:
            해당하는 EvaluationMode

        Raises:
            ValueError: 유효하지 않은 모드 문자열
        """
        value_lower = value.lower().strip()
        for mode in cls:
            if mode.value == value_lower:
                return mode
        valid_modes = [m.value for m in cls]
        raise ValueError(f"유효하지 않은 평가 모드: {value}. 가능한 값: {valid_modes}")


class EvaluationResult(BaseModel):
    """평가 결과 기본 모델

    모든 평가 결과의 공통 필드를 정의합니다.
    각 평가 모드는 이 클래스를 상속하여 추가 필드를 정의합니다.
    """

    mode: EvaluationMode = Field(..., description="평가 모드")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="평가 시각"
    )
    raw_response: str = Field(..., description="LLM 원본 응답")
    summary: str = Field(default="", description="평가 요약")
    recommendations: list[str] = Field(
        default_factory=list,
        description="개선 제안 목록"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터"
    )

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()


class EvaluationRequest(BaseModel):
    """평가 요청 모델"""

    transcript: str = Field(
        ...,
        min_length=10,
        description="토론 스크립트 (최소 10자)"
    )
    mode: EvaluationMode = Field(
        default=EvaluationMode.DQI,
        description="평가 모드"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터"
    )
