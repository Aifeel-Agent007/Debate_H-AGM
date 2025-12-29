"""
Debate Evaluator - 토론 담론 품질 평가 시스템

4가지 평가 방법론(DQI, AAF, DQI-AAF, AFRA)을 지원하는 OpenAI GPT-4o 기반 평가 도구
"""

__version__ = "0.1.0"
__author__ = "AI Thought Partner"

from debate_evaluator.models.base import EvaluationMode, EvaluationResult
from debate_evaluator.evaluators.base import EvaluatorFactory
from debate_evaluator.client import DebateEvaluatorClient

__all__ = [
    "EvaluationMode",
    "EvaluationResult",
    "EvaluatorFactory",
    "DebateEvaluatorClient",
    "__version__",
]
