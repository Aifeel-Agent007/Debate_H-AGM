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

        for line in lines:
            line = line.strip()
            if line.startswith("Topic:"):
                info["topic"] = line.replace("Topic:", "").strip()
            elif line.startswith("Round:"):
                try:
                    info["round_number"] = int(line.replace("Round:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("Context:"):
                context = line.replace("Context:", "").strip()
                if context and context != "None":
                    info["previous_context"] = context

        # If topic is still empty, use the entire query as topic
        if not info["topic"]:
            info["topic"] = query

        return info
