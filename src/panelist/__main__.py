"""Panelist agent server entry point."""

import os
import click
import uvicorn
from dotenv import load_dotenv
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from ..shared.utils import setup_logging
from .agent_executor import PanelistExecutor
from .personas import get_persona, PersonaType, get_all_persona_types

# Load environment variables
load_dotenv()

logger = setup_logging(__name__)


@click.command()
@click.option(
    '--persona',
    type=click.Choice(get_all_persona_types()),
    required=True,
    help='Persona type for this panelist'
)
@click.option(
    '--port',
    type=int,
    required=True,
    help='Port to run the server on'
)
@click.option(
    '--host',
    type=str,
    default='localhost',
    help='Host to run the server on'
)
def main(persona: PersonaType, port: int, host: str) -> None:
    """Start a panelist agent server.

    Args:
        persona: Persona type
        port: Server port
        host: Server host
    """

    # Get persona configuration
    persona_config = get_persona(persona)

    logger.info(f"Starting {persona_config['name']} server on {host}:{port}")

    # Create agent executor
    agent_executor = PanelistExecutor(persona)

    # Define capabilities
    capabilities = AgentCapabilities(
        streaming=True,
        push_notifications=False
    )

    # Define skill
    skill = AgentSkill(
        id=f"debate_panelist_{persona}",
        name="Debate Panelist",
        description=persona_config['description'],
        tags=["debate", "discussion", persona_config['stance']]
    )

    # Create agent card
    agent_card = AgentCard(
        name=persona_config['name'],
        description=persona_config['description'],
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

    logger.info(f"{persona_config['name']} server ready at http://{host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
