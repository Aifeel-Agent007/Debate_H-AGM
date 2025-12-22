"""Shared utility functions for the debate system."""

import logging
from typing import Any


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging for a module.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def format_debate_history(history: list[dict[str, Any]]) -> str:
    """Format debate history for display.

    Args:
        history: List of debate rounds

    Returns:
        Formatted string
    """
    if not history:
        return "No debate history yet."

    formatted = []
    for i, round_data in enumerate(history, 1):
        formatted.append(f"\n=== Round {i} ===")
        formatted.append(f"Topic: {round_data.get('topic', 'N/A')}")

        responses = round_data.get('panelist_responses', [])
        for resp in responses:
            formatted.append(f"\n{resp.get('persona', 'Unknown')} ({resp.get('stance', 'N/A')}):")
            formatted.append(f"  {resp.get('opinion', 'No opinion')}")

        summary = round_data.get('summary')
        if summary:
            formatted.append(f"\nRound Summary: {summary}")

    return '\n'.join(formatted)


def create_debate_context(topic: str, round_num: int, previous_responses: list[dict[str, Any]] | None = None) -> str:
    """Create context string for panelists.

    Args:
        topic: Debate topic
        round_num: Current round number
        previous_responses: Previous panelist responses

    Returns:
        Context string
    """
    context = f"Debate Topic: {topic}\nRound: {round_num}"

    if previous_responses and round_num > 1:
        context += "\n\nPrevious Round Responses:"
        for resp in previous_responses:
            context += f"\n- {resp.get('persona', 'Unknown')}: {resp.get('opinion', '')[:100]}..."

    return context
