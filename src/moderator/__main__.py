"""Moderator agent server entry point."""

import os
import click
import uvicorn
from dotenv import load_dotenv
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from ..shared.utils import setup_logging
from .agent_executor import ModeratorExecutor

# Load environment variables
load_dotenv()

logger = setup_logging(__name__)


@click.command()
@click.option(
    '--port',
    type=int,
    default=10000,
    help='Port to run the moderator server on'
)
@click.option(
    '--host',
    type=str,
    default='localhost',
    help='Host to run the server on'
)
@click.option(
    '--panelist-host',
    type=str,
    default='localhost',
    help='Host where panelist servers are running'
)
@click.option(
    '--right-politician-port',
    type=int,
    default=10001,
    help='Port for right politician panelist'
)
@click.option(
    '--right-scholar-port',
    type=int,
    default=10002,
    help='Port for right scholar panelist'
)
@click.option(
    '--left-politician-port',
    type=int,
    default=10003,
    help='Port for left politician panelist'
)
@click.option(
    '--left-scholar-port',
    type=int,
    default=10004,
    help='Port for left scholar panelist'
)
def main(
    port: int,
    host: str,
    panelist_host: str,
    right_politician_port: int,
    right_scholar_port: int,
    left_politician_port: int,
    left_scholar_port: int,
) -> None:
    """Start the moderator agent server.

    Args:
        port: Moderator server port
        host: Moderator server host
        panelist_host: Host where panelists are running
        right_politician_port: Right politician panelist port
        right_scholar_port: Right scholar panelist port
        left_politician_port: Left politician panelist port
        left_scholar_port: Left scholar panelist port
    """
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise click.ClickException(
            "ANTHROPIC_API_KEY environment variable must be set"
        )

    logger.info(f"Starting Moderator server on {host}:{port}")

    # Build panelist URLs
    panelist_urls = {
        "right_politician": f"http://{panelist_host}:{right_politician_port}",
        "right_scholar": f"http://{panelist_host}:{right_scholar_port}",
        "left_politician": f"http://{panelist_host}:{left_politician_port}",
        "left_scholar": f"http://{panelist_host}:{left_scholar_port}",
    }

    logger.info("Panelist URLs:")
    for persona, url in panelist_urls.items():
        logger.info(f"  {persona}: {url}")

    # Create agent executor
    agent_executor = ModeratorExecutor(panelist_urls)

    # Define capabilities
    capabilities = AgentCapabilities(
        streaming=True,
        push_notifications=False
    )

    # Define skill
    skill = AgentSkill(
        id="debate_orchestration",
        name="Debate Orchestration",
        description="토론을 주관하고 4명의 패널리스트(우파 정치인, 우파 학자, 좌파 정치인, 좌파 학자)의 의견을 수집하여 구조화된 토론을 진행합니다.",
        tags=["debate", "orchestration", "moderation"]
    )

    # Create agent card
    agent_card = AgentCard(
        name="토론 사회자",
        description="AI 에이전트들 간의 토론을 주관하는 사회자입니다. 4명의 패널리스트(우파 정치인, 우파 학자, 좌파 정치인, 좌파 학자)와 함께 다양한 관점에서 주제를 논의합니다.",
        url=f"http://{host}:{port}",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill]
    )

    # Create task store
    task_store = InMemoryTaskStore()

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store
    )

    # Create A2A server
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )

    # Build and run
    app = server.build()

    logger.info(f"Moderator server ready at http://{host}:{port}")
    logger.info("Ensure all panelist servers are running before sending debate requests")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
