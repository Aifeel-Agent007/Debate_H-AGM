"""프롬프트 패키지"""

from debate_evaluator.prompts.base import BasePrompt, PromptRegistry

# 프롬프트 모듈 import (데코레이터로 자동 등록됨)
from debate_evaluator.prompts import dqi, aaf, hybrid, afra  # noqa: F401

__all__ = ["BasePrompt", "PromptRegistry"]
