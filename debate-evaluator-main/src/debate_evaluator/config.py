"""설정 관리 모듈"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정

    환경변수 또는 .env 파일에서 설정을 로드합니다.
    모든 환경변수는 DEBATE_EVAL_ 접두사를 사용합니다.

    예시:
        DEBATE_EVAL_OPENAI_API_KEY=sk-xxx
        DEBATE_EVAL_OPENAI_MODEL=gpt-4o
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DEBATE_EVAL_",
        case_sensitive=False,
    )

    # OpenAI API 설정
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.3

    # 타임아웃 설정 (초)
    openai_timeout: float = 120.0
    openai_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    """설정 인스턴스 반환 (캐시됨)"""
    return Settings()
