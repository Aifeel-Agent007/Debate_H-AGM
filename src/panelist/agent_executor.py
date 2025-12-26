"""Panelist A2A executor implementation."""

import json
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState

from ..shared.utils import setup_logging
from .agent import PanelistAgent
from .personas import PersonaType

logger = setup_logging(__name__)


class PanelistExecutor(AgentExecutor):
    """Executor for panelist agent."""

    def __init__(self, persona_type: PersonaType):
        """Initialize panelist executor.

        Args:
            persona_type: Type of persona for this panelist
        """
        super().__init__()
        self.persona_type = persona_type
        self.agent = PanelistAgent(persona_type)
        logger.info(f"Initialized PanelistExecutor for {persona_type}")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute panelist agent.

        Args:
            context: Request context
            event_queue: Event queue for streaming updates
        """
        try:
            # Extract information from context
            query = context.get_user_input()
            task_id = context.task_id
            context_id = context.context_id

            logger.info(f"Processing request: {query[:100]}...")

            # Create task updater
            updater = TaskUpdater(event_queue, task_id, context_id)

            # Start work
            await updater.start_work()

            # Parse debate information from query
            # Expected format: "Topic: <topic>\nRound: <round_number>\nContext: <context>"
            debate_info = self._parse_debate_query(query)

            # Get opinion from agent
            response = await self.agent.get_opinion(
                topic=debate_info["topic"],
                round_number=debate_info["round_number"],
                context_id=context_id,
                previous_context=debate_info.get("previous_context"),
            )

            # Format response as JSON for structured data
            response_data = {
                "persona": response.persona,
                "stance": response.stance,
                "opinion": response.opinion,
                "reasoning": response.reasoning,
                "round_number": response.round_number,
            }

            # Create artifact with the response
            await updater.add_artifact(
                parts=[
                    {
                        "kind": "text",
                        "text": json.dumps(response_data, ensure_ascii=False, indent=2),
                    }
                ],
                name=f"{self.persona_type}_opinion"
            )

            # Mark as complete
            await updater.complete()

            logger.info(f"Completed processing for {self.persona_type}")

        except Exception as e:
            logger.error(f"Error in panelist executor: {e}", exc_info=True)
            await updater.failed()

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel execution.

        Args:
            context: Request context
            event_queue: Event queue
        """
        logger.info(f"Cancel requested for {self.persona_type}")
        task_id = context.task_id
        context_id = context.context_id
        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel()

    def _parse_debate_query(self, query: str) -> dict[str, any]:
        """Parse debate query to extract information.

        모더레이터가 보내는 형식:
        ```
        토론 주제: {topic}
        현재 라운드: {round_number}

        이전 발언 내용:
        {previous_context - 여러 줄로 구성}

        위 토론 주제에 대해 당신의 관점에서 의견을 제시해주세요.
        ```

        Args:
            query: Query string

        Returns:
            Dictionary with debate information
        """
        lines = query.strip().split('\n')
        info = {
            "topic": "",
            "round_number": 1,
            "previous_context": None,
        }

        # 이전 발언 내용을 수집하기 위한 상태 플래그
        collecting_context = False
        context_lines = []

        for line in lines:
            stripped_line = line.strip()

            # 토론 주제 파싱 (한글/영어 둘 다 지원)
            if stripped_line.startswith("토론 주제:") or stripped_line.startswith("Topic:"):
                info["topic"] = stripped_line.split(":", 1)[1].strip()
                collecting_context = False

            # 현재 라운드 파싱 (한글/영어 둘 다 지원)
            elif stripped_line.startswith("현재 라운드:") or stripped_line.startswith("Round:"):
                try:
                    round_str = stripped_line.split(":", 1)[1].strip()
                    info["round_number"] = int(round_str)
                except (ValueError, IndexError):
                    pass
                collecting_context = False

            # 이전 발언 내용 시작 감지 (한글/영어 둘 다 지원)
            elif stripped_line.startswith("이전 발언 내용:") or stripped_line.startswith("Context:"):
                collecting_context = True
                # 같은 줄에 내용이 있는 경우 처리
                remaining = stripped_line.split(":", 1)[1].strip() if ":" in stripped_line else ""
                if remaining and remaining != "(첫 발언입니다)":
                    context_lines.append(remaining)

            # 마지막 안내 문구 감지 - 컨텍스트 수집 종료
            elif "위 토론 주제에 대해" in stripped_line or "의견을 제시해주세요" in stripped_line:
                collecting_context = False

            # 이전 발언 내용 수집 중인 경우
            elif collecting_context:
                # 빈 줄이 아니고 첫 발언 표시가 아닌 경우에만 추가
                if stripped_line and stripped_line != "(첫 발언입니다)":
                    context_lines.append(stripped_line)

        # 수집된 이전 발언 내용 병합
        if context_lines:
            info["previous_context"] = "\n".join(context_lines)

        # If topic is still empty, use the entire query as topic
        if not info["topic"]:
            info["topic"] = query

        return info
