"""Moderator LangGraph agent implementation - Simple single-topic version."""

import os
import json
from typing import Any, Literal
import httpx
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from a2a.client import A2AClient
from a2a.types import SendMessageRequest

from ..shared.models import DebateState, PanelistResponse, DebateRound
from ..shared.utils import setup_logging
from ..shared.mcp_tools import get_search_tools

logger = setup_logging(__name__)


class ModeratorAgent:
    """Moderator agent for orchestrating debates - single topic version."""

    def __init__(self, panelist_urls: dict[str, str]):
        """Initialize moderator agent.

        Args:
            panelist_urls: Dictionary mapping persona types to their URLs
        """
        self.panelist_urls = panelist_urls

        # Using OpenAI GPT-4 mini
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=api_key,
            temperature=0.5,
        )

        # Get MCP search tools
        self.tools = get_search_tools()

        # Create memory saver
        self.memory = MemorySaver()

        # Initialize A2A clients for panelists
        self.panelist_clients: dict[str, A2AClient] = {}
        for persona, url in panelist_urls.items():
            self.panelist_clients[persona] = A2AClient(
                httpx_client=httpx.AsyncClient(timeout=180.0),
                url=url
            )

        # Task updater for real-time artifacts (not serialized in state)
        self.task_updater = None

        # Build graph
        self.graph = self._build_graph()

        logger.info(f"Initialized Moderator agent with {len(self.tools)} MCP tools")

    async def _research_topic(self, state: dict[str, Any]) -> dict[str, Any]:
        """Research the debate topic using MCP search tools.

        Args:
            state: Current state

        Returns:
            Updated state with research_data
        """
        topic = state["topic"]
        logger.info(f"Researching topic: {topic}")

        research_data = ""

        try:
            # Call search_web_tool
            search_tool = next((t for t in self.tools if t.name == "search_web_tool"), None)
            if search_tool:
                logger.info("Using search_web_tool...")
                search_results = await search_tool.ainvoke({
                    "query": topic,
                    "max_results": 5,
                    "search_depth": "advanced"
                })
                research_data += f"Search Results:\n{search_results}\n\n"

            # Call get_context_tool
            context_tool = next((t for t in self.tools if t.name == "get_context_tool"), None)
            if context_tool:
                logger.info("Using get_context_tool...")
                context_results = await context_tool.ainvoke({"query": topic})
                research_data += f"Context:\n{context_results}\n"

            logger.info(f"Research completed: {len(research_data)} characters")

        except Exception as e:
            logger.error(f"Error during research: {e}", exc_info=True)
            research_data = f"Research failed: {e}\nProceeding without research data."

        return {
            **state,
            "research_data": research_data,
            "round_number": 1,
            "max_rounds": 5,  # Default 5 rounds
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for moderator with simple round-based flow.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(dict)

        # Add nodes
        from functools import partial

        # Research node
        workflow.add_node("research_topic", self._research_topic)

        # Speaker and collection nodes
        workflow.add_node("decide_next_speaker", self._decide_next_speaker)
        workflow.add_node("collect_right_politician", partial(self._collect_panel_response, persona="right_politician"))
        workflow.add_node("collect_right_scholar", partial(self._collect_panel_response, persona="right_scholar"))
        workflow.add_node("collect_left_politician", partial(self._collect_panel_response, persona="left_politician"))
        workflow.add_node("collect_left_scholar", partial(self._collect_panel_response, persona="left_scholar"))

        # Round management
        workflow.add_node("check_round_complete", self._check_round_complete)
        workflow.add_node("check_debate_complete", self._check_debate_complete)

        # Finalization
        workflow.add_node("finalize_debate", self._finalize_debate)

        # Set entry point
        workflow.set_entry_point("research_topic")

        # Flow: research → decide speaker
        workflow.add_edge("research_topic", "decide_next_speaker")

        # Conditional routing to selected speaker
        workflow.add_conditional_edges(
            "decide_next_speaker",
            self._route_to_speaker,
            {
                "right_politician": "collect_right_politician",
                "right_scholar": "collect_right_scholar",
                "left_politician": "collect_left_politician",
                "left_scholar": "collect_left_scholar"
            }
        )

        # After collection, check if round is complete
        workflow.add_edge("collect_right_politician", "check_round_complete")
        workflow.add_edge("collect_right_scholar", "check_round_complete")
        workflow.add_edge("collect_left_politician", "check_round_complete")
        workflow.add_edge("collect_left_scholar", "check_round_complete")

        # From check_round_complete, either continue round or check if debate is complete
        workflow.add_conditional_edges(
            "check_round_complete",
            self._should_continue_round,
            {
                "continue_round": "decide_next_speaker",
                "next_round": "check_debate_complete"
            }
        )

        # From check_debate_complete, either start next round or finalize
        workflow.add_conditional_edges(
            "check_debate_complete",
            self._has_more_rounds,
            {
                "continue_debate": "decide_next_speaker",
                "finalize": "finalize_debate"
            }
        )

        workflow.add_edge("finalize_debate", END)

        return workflow.compile(checkpointer=self.memory)

    def _decide_next_speaker(self, state: dict[str, Any]) -> dict[str, Any]:
        """Decide which panelist should speak next using LLM.

        Args:
            state: Current state

        Returns:
            Updated state with next_speaker selected
        """
        topic = state["topic"]
        round_number = state.get("round_number", 1)
        speakers_this_round = state.get("speakers_this_round", [])

        # Available speakers who haven't spoken this round
        all_speakers = ["right_politician", "right_scholar", "left_politician", "left_scholar"]
        available_speakers = [s for s in all_speakers if s not in speakers_this_round]

        # Get recent statements for context
        panel_responses = state.get("panel_responses", [])
        recent_statements = ""
        if panel_responses:
            last_three = panel_responses[-3:]
            recent_statements = "\n".join([
                f"{r.get('persona', 'Unknown')}: {r.get('opinion', '')[:150]}..."
                for r in last_three
            ])

        # Build prompt for LLM to decide next speaker
        prompt = f"""당신은 토론 사회자입니다. 다음 발언자를 결정해야 합니다.

토론 주제: {topic}
현재 라운드: {round_number}

이번 라운드 발언 현황:
- 발언 완료: {', '.join(speakers_this_round) if speakers_this_round else '없음'}
- 발언 대기: {', '.join(available_speakers)}

최근 발언 내용:
{recent_statements if recent_statements else '아직 발언 없음'}

사용 가능한 패널:
- right_politician: 우파 정치인
- right_scholar: 우파 학자
- left_politician: 좌파 정치인
- left_scholar: 좌파 학자

토론의 균형과 흐름을 고려하여 다음 발언자를 선택하세요.
발언자 ID만 답하세요 (예: right_politician)"""

        try:
            response = self.llm.invoke(prompt)
            next_speaker = response.content.strip()

            # Validate speaker choice
            if next_speaker not in available_speakers:
                logger.warning(f"Invalid speaker choice: {next_speaker}, using first available")
                next_speaker = available_speakers[0] if available_speakers else all_speakers[0]

            logger.info(f"Next speaker: {next_speaker}")

        except Exception as e:
            logger.error(f"Error deciding next speaker: {e}")
            next_speaker = available_speakers[0] if available_speakers else all_speakers[0]

        return {
            **state,
            "next_speaker": next_speaker
        }

    def _route_to_speaker(self, state: dict[str, Any]) -> str:
        """Route to the selected speaker's collection node.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        return state["next_speaker"]

    async def _collect_panel_response(
        self,
        state: dict[str, Any],
        persona: str
    ) -> dict[str, Any]:
        """Collect response from a specific panelist.

        Args:
            state: Current state
            persona: Persona type

        Returns:
            Updated state
        """
        logger.info(f"Collecting response from {persona}")

        topic = state["topic"]
        round_number = state.get("round_number", 1)

        # Prepare previous context from all responses
        previous_context = ""
        panel_responses = state.get("panel_responses", [])
        if panel_responses:
            context_parts = []
            for resp in panel_responses[-4:]:  # Last 4 responses
                context_parts.append(
                    f"{resp.get('persona', 'Unknown')}: {resp.get('opinion', '')[:150]}..."
                )
            previous_context = "\n".join(context_parts)

        # Build query message
        query = f"""토론 주제: {topic}
현재 라운드: {round_number}

이전 발언 내용:
{previous_context if previous_context else '(첫 발언입니다)'}

위 토론 주제에 대해 당신의 관점에서 의견을 제시해주세요."""

        try:
            # Send message to panelist
            client = self.panelist_clients[persona]
            request = SendMessageRequest(
                id=f"msg_{persona}_{round_number}",
                jsonrpc="2.0",
                method="message/send",
                params={
                    "message": {
                        "kind": "message",
                        "messageId": f"msg_{persona}_{round_number}",
                        "parts": [{"kind": "text", "text": query}],
                        "role": "user"
                    }
                }
            )

            response = await client.send_message(request)

            # Extract response from artifacts
            result = response.root.result
            artifacts = result.artifacts or []

            if artifacts:
                artifact = artifacts[0]
                text_parts = [p for p in artifact.parts if p.root.kind == "text"]
                if text_parts:
                    response_data = json.loads(text_parts[0].root.text)

                    # Add to panel responses
                    panel_responses = state.get("panel_responses", [])
                    panel_responses.append(response_data)

                    # Track that this speaker has spoken
                    speakers_this_round = state.get("speakers_this_round", [])
                    speakers_this_round.append(persona)

                    # Real-time output
                    if self.task_updater:
                        await self._emit_panelist_response(
                            self.task_updater,
                            response_data,
                            round_number
                        )

                    return {
                        **state,
                        "panel_responses": panel_responses,
                        "speakers_this_round": speakers_this_round
                    }

        except Exception as e:
            logger.error(f"Error collecting response from {persona}: {e}", exc_info=True)

        return state

    async def _emit_panelist_response(
        self,
        task_updater,
        response_data: dict[str, Any],
        round_number: int
    ) -> None:
        """Emit a panelist response as an artifact in real-time.

        Args:
            task_updater: TaskUpdater for emitting artifacts
            response_data: The panelist response data
            round_number: Current round number
        """
        try:
            persona = response_data.get("persona", "Unknown")
            stance = response_data.get("stance", "")
            opinion = response_data.get("opinion", "")

            # Format the response
            formatted_response = f"🔵 Round {round_number}\n\n{persona} ({stance}):\n{opinion}\n"

            # Log to console
            logger.info(f"\n{'─'*80}")
            logger.info(f"🔵 Round {round_number}")
            logger.info(f"{persona} ({stance})")
            logger.info(f"{'─'*80}")
            logger.info(f"{opinion}")
            logger.info(f"{'─'*80}\n")

            # Emit as artifact
            await task_updater.add_artifact(
                parts=[
                    {
                        "kind": "text",
                        "text": formatted_response,
                    }
                ],
                name=f"panelist_response_r{round_number}_{persona.replace(' ', '_')}"
            )

            logger.info(f"Emitted real-time response for {persona}")

        except Exception as e:
            logger.error(f"Error emitting panelist response: {e}", exc_info=True)

    def _check_round_complete(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check if current round is complete (all 4 speakers spoke).

        Args:
            state: Current state

        Returns:
            Updated state
        """
        return state

    def _should_continue_round(self, state: dict[str, Any]) -> Literal["continue_round", "next_round"]:
        """Determine if we should continue current round or move to next.

        Args:
            state: Current state

        Returns:
            "continue_round" or "next_round"
        """
        speakers_this_round = state.get("speakers_this_round", [])

        # Check if all 4 panelists have spoken
        if len(speakers_this_round) >= 4:
            logger.info("Round complete, moving to next round check")
            return "next_round"
        else:
            logger.info(f"Round continues ({len(speakers_this_round)}/4 speakers)")
            return "continue_round"

    def _check_debate_complete(self, state: dict[str, Any]) -> dict[str, Any]:
        """Check if debate is complete and prepare for next round or finalize.

        Uses LLM to determine if the debate should continue based on:
        1. Whether new perspectives are being presented
        2. If the discussion is becoming repetitive
        3. If key points have been sufficiently covered

        Args:
            state: Current state

        Returns:
            Updated state with should_continue flag
        """
        round_number = state.get("round_number", 1)
        max_rounds = state.get("max_rounds", 5)
        topic = state.get("topic", "")
        panel_responses = state.get("panel_responses", [])

        logger.info(f"Completed round {round_number}/{max_rounds}")

        # If we've reached max rounds, don't continue
        if round_number >= max_rounds:
            logger.info(f"Reached max rounds ({max_rounds}), finalizing debate")
            return {
                **state,
                "should_continue_debate": False
            }

        # If we're at round 2 or later, ask LLM if we should continue
        if round_number >= 2:
            # Get responses from the last round
            last_round_responses = [r for r in panel_responses if r.get("round_number") == round_number]

            # Simplified responses for LLM analysis
            simplified_responses = [
                {
                    "persona": r.get("persona", "Unknown"),
                    "opinion": r.get("opinion", "")[:300]  # First 300 chars
                }
                for r in last_round_responses
            ]

            prompt = f"""당신은 토론 사회자입니다. 현재 토론을 계속 진행해야 할지 판단해주세요.

토론 주제: {topic}
현재 라운드: {round_number}/{max_rounds}
총 발언 수: {len(panel_responses)}

최근 라운드(Round {round_number}) 발언 내용:
{json.dumps(simplified_responses, ensure_ascii=False, indent=2)}

판단 기준:
1. 새로운 관점이나 논점이 계속 제시되고 있는가?
2. 토론이 심화되고 발전하고 있는가?
3. 패널들이 반복적인 주장만 하고 있지는 않은가?
4. 주제에 대한 핵심 쟁점들이 충분히 다루어졌는가?

다음 형식으로 답변하세요:

결정: CONTINUE 또는 STOP
이유: (1-2문장으로 판단 근거를 설명)

예시:
결정: CONTINUE
이유: 각 패널이 새로운 경제적 관점을 제시하고 있으며, 토론이 더 깊이 있게 발전하고 있습니다.

또는

결정: STOP
이유: 패널들이 이미 제시한 주장을 반복하고 있으며, 핵심 쟁점에 대한 논의가 충분히 이루어졌습니다."""

            try:
                response = self.llm.invoke(prompt)
                content = response.content.strip()

                # Parse decision and reason
                decision_line = ""
                reason_line = ""
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith("결정:") or line.startswith("Decision:"):
                        decision_line = line.split(":", 1)[1].strip().upper()
                    elif line.startswith("이유:") or line.startswith("Reason:"):
                        reason_line = line.split(":", 1)[1].strip()

                # If parsing failed, try to extract from full content
                if not decision_line:
                    decision_line = content.upper()

                should_continue = "CONTINUE" in decision_line

                # Log decision with reason
                logger.info(f"\n{'='*80}")
                logger.info(f"사회자 토론 계속 여부 판단 (Round {round_number})")
                logger.info(f"{'='*80}")
                logger.info(f"결정: {'CONTINUE (계속)' if should_continue else 'STOP (종료)'}")
                if reason_line:
                    logger.info(f"이유: {reason_line}")
                logger.info(f"{'='*80}\n")

                # Also print to console for real-time monitoring
                print(f"\n{'='*80}")
                print(f"🎯 사회자 판단 (Round {round_number}/{max_rounds})")
                print(f"{'='*80}")
                print(f"결정: {'✅ CONTINUE (토론 계속)' if should_continue else '🛑 STOP (토론 종료)'}")
                if reason_line:
                    print(f"이유: {reason_line}")
                print(f"{'='*80}\n")

                if not should_continue:
                    logger.info(f"LLM decided to stop debate at round {round_number}")
                    return {
                        **state,
                        "should_continue_debate": False
                    }

            except Exception as e:
                logger.error(f"Error in LLM debate continuation decision: {e}")
                # On error, default to continuing
                logger.info("Error occurred, defaulting to continue")

        # Continue to next round
        new_round_number = round_number + 1
        logger.info(f"Continuing to round {new_round_number}")

        return {
            **state,
            "round_number": new_round_number,
            "speakers_this_round": [],  # Reset for next round
            "should_continue_debate": True
        }

    def _has_more_rounds(self, state: dict[str, Any]) -> Literal["continue_debate", "finalize"]:
        """Determine if there are more rounds to conduct.

        Checks the should_continue_debate flag set by _check_debate_complete.

        Args:
            state: Current state

        Returns:
            "continue_debate" or "finalize"
        """
        should_continue = state.get("should_continue_debate", True)
        round_number = state.get("round_number", 1)
        max_rounds = state.get("max_rounds", 5)

        if not should_continue:
            logger.info(f"Debate stopped by moderator decision after round {round_number - 1}")
            return "finalize"

        if round_number <= max_rounds:
            logger.info(f"Starting round {round_number}/{max_rounds}")
            return "continue_debate"
        else:
            logger.info(f"All {max_rounds} rounds completed")
            return "finalize"

    def _finalize_debate(self, state: dict[str, Any]) -> dict[str, Any]:
        """Finalize the debate and create summary.

        Args:
            state: Current state

        Returns:
            Updated state with final summary
        """
        logger.info("Finalizing debate")

        topic = state["topic"]
        panel_responses = state.get("panel_responses", [])
        max_rounds = state.get("max_rounds", 5)

        # Calculate total time used
        total_chars = sum(
            len(r.get("opinion", "")) + len(r.get("reasoning", ""))
            for r in panel_responses
        )
        total_time = total_chars / 2000.0  # 2000 chars = 1 minute

        logger.info(f"Total debate time: {total_time:.1f} minutes")
        logger.info(f"Total responses: {len(panel_responses)}")

        # Simple summary (no LLM generation for now)
        summary = f"""토론이 완료되었습니다.

토론 주제: {topic}
총 라운드: {max_rounds}
총 발언 수: {len(panel_responses)}
총 토론 시간: {total_time:.1f}분
"""

        return {
            **state,
            "final_summary": summary,
            "debate_history": panel_responses
        }

    async def run_debate(
        self,
        topic: str,
        context_id: str,
        task_updater=None
    ) -> dict[str, Any]:
        """Run a complete debate on a topic.

        Args:
            topic: Debate topic
            context_id: Context ID for memory
            task_updater: Optional task updater for real-time output

        Returns:
            Final debate state
        """
        logger.info(f"Starting debate on topic: {topic}")

        # Store task updater
        self.task_updater = task_updater

        # Prepare input
        inputs = {
            "topic": topic
        }

        # Run graph
        config = {
            "configurable": {"thread_id": context_id},
            "recursion_limit": 200  # 5 rounds × 4 speakers × 2 nodes per speaker + overhead
        }
        result = await self.graph.ainvoke(inputs, config)

        logger.info("Debate completed")

        # Clear task updater
        self.task_updater = None

        return result
