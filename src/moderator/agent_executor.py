"""Moderator A2A executor implementation."""

import json
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState

from ..shared.utils import setup_logging, format_debate_history
from .agent import ModeratorAgent

logger = setup_logging(__name__)


class ModeratorExecutor(AgentExecutor):
    """Executor for moderator agent."""

    def __init__(self, panelist_urls: dict[str, str]):
        """Initialize moderator executor.

        Args:
            panelist_urls: Dictionary mapping persona types to their URLs
        """
        super().__init__()
        self.agent = ModeratorAgent(panelist_urls)
        logger.info("Initialized ModeratorExecutor")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute moderator agent.

        Args:
            context: Request context
            event_queue: Event queue for streaming updates
        """
        try:
            # Extract information from context
            query = context.get_user_input()
            task_id = context.task_id
            context_id = context.context_id

            logger.info(f"Starting debate on topic: {query[:100]}...")

            # Create task updater
            updater = TaskUpdater(event_queue, task_id, context_id)

            # Start work
            await updater.start_work()

            # Extract topic from query
            # Expected format could be just the topic, or "Topic: <topic>"
            topic = query
            if query.lower().startswith("topic:"):
                topic = query.split(":", 1)[1].strip()

            # Run debate with task updater for real-time output
            result = await self.agent.run_debate(topic, context_id, task_updater=updater)

            # Extract results
            debate_history = result.get("debate_history", [])
            panel_responses = result.get("panel_responses", [])
            research_data = result.get("research_data", "")
            final_summary = result.get("final_summary", "요약을 생성할 수 없습니다.")
            max_rounds = result.get("max_rounds", 5)

            # Create research data artifact (if exists)
            if research_data:
                await updater.add_artifact(
                    parts=[
                        {
                            "kind": "text",
                            "text": f"# Background Research\n\n{research_data[:1000]}...",  # Limit to 1000 chars
                        }
                    ],
                    name="background_research"
                )

            # Create debate history artifact (by rounds)
            history_text = "# Debate History\n\n"

            # Group responses by round
            for round_num in range(1, max_rounds + 1):
                round_responses = [r for r in panel_responses if r.get("round_number") == round_num]
                if not round_responses:
                    break

                history_text += f"## Round {round_num}\n\n"

                for resp in round_responses:
                    persona = resp.get("persona", "Unknown")
                    stance = resp.get("stance", "")
                    opinion = resp.get("opinion", "")
                    history_text += f"### {persona} ({stance})\n{opinion}\n\n"

                history_text += "---\n\n"

            await updater.add_artifact(
                parts=[
                    {
                        "kind": "text",
                        "text": history_text,
                    }
                ],
                name="debate_history"
            )

            # Create summary artifact
            await updater.add_artifact(
                parts=[
                    {
                        "kind": "text",
                        "text": final_summary,
                    }
                ],
                name="debate_summary"
            )

            # Calculate total time
            total_chars = sum(
                len(r.get("opinion", "")) + len(r.get("reasoning", ""))
                for r in panel_responses
            )
            total_time = total_chars / 2000.0

            # Create detailed JSON artifact
            await updater.add_artifact(
                parts=[
                    {
                        "kind": "text",
                        "text": json.dumps(
                            {
                                "topic": topic,
                                "total_rounds": max_rounds,
                                "total_responses": len(panel_responses),
                                "total_time_minutes": total_time,
                                "panel_responses": panel_responses,
                                "final_summary": final_summary,
                            },
                            ensure_ascii=False,
                            indent=2
                        ),
                    }
                ],
                name="debate_data"
            )

            # Mark as complete
            await updater.complete()

            logger.info("Debate completed successfully")

        except Exception as e:
            logger.error(f"Error in moderator executor: {e}", exc_info=True)
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
        logger.info("Cancel requested for moderator")
        task_id = context.task_id
        context_id = context.context_id
        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel()
