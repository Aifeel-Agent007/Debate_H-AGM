"""프롬프트 기본 클래스 및 레지스트리"""

from abc import ABC, abstractmethod
from string import Template
from typing import ClassVar, Type

from debate_evaluator.models.base import EvaluationMode


class BasePrompt(ABC):
    """프롬프트 추상 기본 클래스

    각 평가 모드는 이 클래스를 상속하여 시스템 프롬프트를 정의합니다.
    """

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """시스템 프롬프트 반환

        평가 방법론에 대한 상세 지침을 포함합니다.
        """
        pass

    @property
    def user_prompt_template(self) -> str:
        """사용자 프롬프트 템플릿

        기본 템플릿을 제공하며, 필요 시 서브클래스에서 오버라이드 가능합니다.
        """
        return """다음 토론 스크립트를 분석해주세요:

---
$transcript
---

위 지침에 따라 상세한 평가를 제공해주세요."""

    def format_user_prompt(self, transcript: str) -> str:
        """사용자 프롬프트 생성

        Args:
            transcript: 토론 스크립트

        Returns:
            포매팅된 사용자 프롬프트
        """
        template = Template(self.user_prompt_template)
        return template.substitute(transcript=transcript)


class PromptRegistry:
    """프롬프트 레지스트리

    각 평가 모드에 해당하는 프롬프트 클래스를 등록하고 관리합니다.

    사용 예시:
        @PromptRegistry.register(EvaluationMode.DQI)
        class DQIPrompt(BasePrompt):
            ...

        prompt = PromptRegistry.get(EvaluationMode.DQI)
    """

    _registry: ClassVar[dict[EvaluationMode, Type[BasePrompt]]] = {}

    @classmethod
    def register(cls, mode: EvaluationMode):
        """프롬프트 클래스 등록 데코레이터

        Args:
            mode: 평가 모드

        Returns:
            데코레이터 함수
        """
        def decorator(prompt_class: Type[BasePrompt]) -> Type[BasePrompt]:
            cls._registry[mode] = prompt_class
            return prompt_class
        return decorator

    @classmethod
    def get(cls, mode: EvaluationMode) -> BasePrompt:
        """모드에 해당하는 프롬프트 인스턴스 반환

        Args:
            mode: 평가 모드

        Returns:
            프롬프트 인스턴스

        Raises:
            ValueError: 등록되지 않은 모드
        """
        if mode not in cls._registry:
            registered = list(cls._registry.keys())
            raise ValueError(
                f"등록되지 않은 평가 모드: {mode}. "
                f"등록된 모드: {registered}"
            )
        return cls._registry[mode]()

    @classmethod
    def available_modes(cls) -> list[EvaluationMode]:
        """등록된 모든 평가 모드 반환"""
        return list(cls._registry.keys())
