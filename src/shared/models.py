"""Shared data models for the debate system."""

from typing import TypedDict, Literal
from pydantic import BaseModel


class PanelistResponse(BaseModel):
    """Structured response from a panelist agent."""

    persona: str
    stance: Literal["pro", "con", "neutral", "conditional"]
    opinion: str
    reasoning: str
    round_number: int


class DebateRound(BaseModel):
    """Information about a single debate round."""

    round_number: int
    topic: str
    panelist_responses: list[PanelistResponse]
    summary: str | None = None


class DebateState(TypedDict):
    """State for the moderator's LangGraph - Simple single-topic version."""

    # Main topic
    topic: str

    # Research phase
    research_data: str

    # Round management
    round_number: int
    max_rounds: int

    # Current round speakers
    speakers_this_round: list[str]
    next_speaker: str | None
    panel_responses: list[dict]

    # History
    debate_history: list[dict]

    # Control
    should_continue_debate: bool
    final_summary: str | None
