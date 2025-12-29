"""평가자 기본 클래스 및 팩토리"""

from abc import ABC, abstractmethod
from typing import ClassVar, Type

from debate_evaluator.client import DebateEvaluatorClient
from debate_evaluator.models.base import EvaluationMode, EvaluationResult
from debate_evaluator.prompts.base import BasePrompt, PromptRegistry


class BaseEvaluator(ABC):
    """평가자 추상 기본 클래스

    각 평가 모드는 이 클래스를 상속하여 평가 로직을 구현합니다.

    사용 예시:
        evaluator = EvaluatorFactory.create(EvaluationMode.DQI, client)
        result = evaluator.evaluate(transcript)
    """

    mode: ClassVar[EvaluationMode]  # 서브클래스에서 정의

    def __init__(self, client: DebateEvaluatorClient, prompt: BasePrompt):
        """평가자 초기화

        Args:
            client: OpenAI API 클라이언트
            prompt: 해당 모드의 프롬프트
        """
        self.client = client
        self.prompt = prompt

    def evaluate(self, transcript: str) -> EvaluationResult:
        """토론 스크립트 평가 실행

        Args:
            transcript: 토론 스크립트 텍스트

        Returns:
            평가 결과 객체
        """
        # API 호출
        raw_response = self.client.chat_completion(
            system_prompt=self.prompt.system_prompt,
            user_message=self.prompt.format_user_prompt(transcript),
        )

        # 응답 파싱 및 결과 생성
        return self.parse_response(raw_response)

    @abstractmethod
    def parse_response(self, raw_response: str) -> EvaluationResult:
        """API 응답을 결과 모델로 파싱

        Args:
            raw_response: LLM 원본 응답 텍스트

        Returns:
            파싱된 평가 결과 객체
        """
        pass


class EvaluatorFactory:
    """평가자 팩토리

    평가 모드에 따라 적절한 평가자 인스턴스를 생성합니다.

    사용 예시:
        # 데코레이터로 등록
        @EvaluatorFactory.register(EvaluationMode.DQI)
        class DQIEvaluator(BaseEvaluator):
            ...

        # 팩토리로 생성
        evaluator = EvaluatorFactory.create(EvaluationMode.DQI, client)
    """

    _registry: ClassVar[dict[EvaluationMode, Type[BaseEvaluator]]] = {}

    @classmethod
    def register(cls, mode: EvaluationMode):
        """평가자 클래스 등록 데코레이터

        Args:
            mode: 평가 모드

        Returns:
            데코레이터 함수
        """
        def decorator(evaluator_class: Type[BaseEvaluator]) -> Type[BaseEvaluator]:
            cls._registry[mode] = evaluator_class
            evaluator_class.mode = mode
            return evaluator_class
        return decorator

    @classmethod
    def create(
        cls,
        mode: EvaluationMode,
        client: DebateEvaluatorClient,
    ) -> BaseEvaluator:
        """모드에 맞는 평가자 인스턴스 생성

        Args:
            mode: 평가 모드
            client: OpenAI API 클라이언트

        Returns:
            평가자 인스턴스

        Raises:
            ValueError: 등록되지 않은 모드
        """
        if mode not in cls._registry:
            registered = list(cls._registry.keys())
            raise ValueError(
                f"등록되지 않은 평가 모드: {mode}. "
                f"등록된 모드: {registered}"
            )

        # 프롬프트 가져오기
        prompt = PromptRegistry.get(mode)

        # 평가자 인스턴스 생성
        return cls._registry[mode](client, prompt)

    @classmethod
    def available_modes(cls) -> list[EvaluationMode]:
        """등록된 모든 평가 모드 반환"""
        return list(cls._registry.keys())
