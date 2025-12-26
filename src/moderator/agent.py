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
                httpx_client=httpx.AsyncClient(timeout=600.0),
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
            statement_parts = []
            for r in last_three:
                opinion = r.get('opinion', '')
                reasoning = r.get('reasoning', '')
                statement_parts.append(
                    f"[{r.get('persona', 'Unknown')}]\n의견: {opinion}\n근거: {reasoning}"
                )
            recent_statements = "\n\n".join(statement_parts)

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
                opinion = resp.get('opinion', '')
                reasoning = resp.get('reasoning', '')
                context_parts.append(
                    f"[{resp.get('persona', 'Unknown')}]\n의견: {opinion}\n근거: {reasoning}"
                )
            previous_context = "\n\n".join(context_parts)

        # Build query message with round-specific guidance
        if round_number == 1:
            round_guide = "이번 라운드는 첫 번째 발언입니다. 당신의 핵심 주장을 명확하게 제시해주세요."
        else:
            round_guide = f"""이번 라운드는 {round_number}번째 라운드입니다.
상대 진영의 주장을 반박하거나, 같은 진영의 주장을 보완해주세요.
상대방의 구체적인 발언을 인용하며 반박하세요. (예: "앞서 ~께서 말씀하신...")"""

        query = f"""토론 주제: {topic}
현재 라운드: {round_number}
라운드 안내: {round_guide}

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
            reasoning = response_data.get("reasoning", "")

            # Format the response
            formatted_response = f"🔵 Round {round_number}\n\n{persona} ({stance}):\n\n[의견]\n{opinion}\n\n[근거]\n{reasoning}\n"

            # Log to console
            logger.info(f"\n{'─'*80}")
            logger.info(f"🔵 Round {round_number}")
            logger.info(f"{persona} ({stance})")
            logger.info(f"{'─'*80}")
            logger.info(f"[의견]\n{opinion}")
            logger.info(f"\n[근거]\n{reasoning}")
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

        Uses 2-stage LLM analysis to determine if the debate should continue:
        Stage 1: Classify each statement by type (new argument, rebuttal, elaboration, repetition)
        Stage 2: Based on classification, decide whether to continue or stop

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
            # Get all responses grouped by round for comprehensive evaluation
            all_responses_by_round = {}
            for r in panel_responses:
                rnd = r.get("round_number", 1)
                if rnd not in all_responses_by_round:
                    all_responses_by_round[rnd] = []
                all_responses_by_round[rnd].append({
                    "persona": r.get("persona", "Unknown"),
                    "opinion": r.get("opinion", ""),
                    "reasoning": r.get("reasoning", "")
                })

            # Format all responses for LLM analysis
            formatted_responses = ""
            for rnd in sorted(all_responses_by_round.keys()):
                formatted_responses += f"\n=== Round {rnd} ===\n"
                for resp in all_responses_by_round[rnd]:
                    formatted_responses += f"\n[{resp['persona']}]\n"
                    formatted_responses += f"의견: {resp['opinion']}\n"
                    formatted_responses += f"근거: {resp['reasoning']}\n"

            prompt = f"""당신은 토론 사회자입니다. 토론을 계속 진행할지 2단계로 분석해주세요.

토론 주제: {topic}
현재 라운드: {round_number}/{max_rounds}

전체 토론 내용:
{formatted_responses}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1단계] 최근 라운드(Round {round_number}) 발언 유형 분류
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

각 패널의 발언을 아래 4가지 유형으로 분류하세요:

1. 새로운 주장 (NEW): 이전에 없던 새로운 관점, 논점, 근거 제시
2. 반박 (REBUTTAL): 상대 진영의 특정 주장에 대한 직접적 반론
   - 단순히 "그건 틀렸다"가 아니라 구체적 근거로 반박해야 함
   - 반박은 토론의 핵심이므로 새로운 기여로 인정
3. 보충/심화 (ELABORATION): 자신 또는 같은 진영의 주장을 새로운 예시/근거로 확장
   - 같은 주장이라도 새로운 근거나 구체적 예시가 있으면 보충으로 인정
4. 단순 반복 (REPETITION): 이전 주장을 새로운 근거 없이 그대로 되풀이
   - 핵심 내용이 동일하고 새로운 논거가 없는 경우만 해당

※ 중요: 단순히 단어가 비슷하다고 반복이 아닙니다!
   - "경제 성장이 중요하다" → "경제 성장을 위해 규제 완화가 필요하다"는 보충(ELABORATION)
   - 상대방 주장을 언급하며 반박하면 반박(REBUTTAL)
   - 정말 같은 내용을 새 근거 없이 반복할 때만 반복(REPETITION)

[Round {round_number} 발언 분류]
- 우파 정치인: (유형) - (간략한 근거)
- 우파 학자: (유형) - (간략한 근거)
- 좌파 정치인: (유형) - (간략한 근거)
- 좌파 학자: (유형) - (간략한 근거)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2단계] 토론 계속 여부 판단
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 분류 결과를 바탕으로 판단하세요:

종료 권고 조건 (하나라도 해당되면 STOP):
✗ 4명 중 3명 이상이 "단순 반복(REPETITION)"인 경우
✗ 2라운드 연속 새로운 주장이나 의미 있는 반박이 없는 경우
✗ 핵심 쟁점에 대해 양측 입장이 충분히 개진되어 더 이상 새로운 논의가 어려운 경우

계속 권고 조건 (해당되면 CONTINUE):
✓ 새로운 주장(NEW)이나 의미 있는 반박(REBUTTAL)이 있는 경우
✓ 토론이 더 구체적/심층적으로 발전하고 있는 경우
✓ 아직 다루지 않은 중요한 측면이 남아 있는 경우

[최종 판단]
결정: CONTINUE 또는 STOP
이유: (분류 결과를 근거로 1-2문장 설명)"""

            try:
                response = self.llm.invoke(prompt)
                content = response.content.strip()

                # Parse classification results for each panelist
                classifications = {}
                classification_lines = []
                for line in content.split('\n'):
                    line = line.strip()
                    # Parse panelist classifications (e.g., "- 우파 정치인: NEW - ...")
                    if line.startswith("- 우파 정치인:") or line.startswith("- 우파 학자:") or \
                       line.startswith("- 좌파 정치인:") or line.startswith("- 좌파 학자:"):
                        classification_lines.append(line)
                        # Extract persona and type
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            persona = parts[0].replace("-", "").strip()
                            type_part = parts[1].strip()
                            # Determine type
                            if "NEW" in type_part.upper() or "새로운" in type_part:
                                classifications[persona] = "NEW"
                            elif "REBUTTAL" in type_part.upper() or "반박" in type_part:
                                classifications[persona] = "REBUTTAL"
                            elif "ELABORATION" in type_part.upper() or "보충" in type_part or "심화" in type_part:
                                classifications[persona] = "ELABORATION"
                            elif "REPETITION" in type_part.upper() or "반복" in type_part:
                                classifications[persona] = "REPETITION"

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

                # Count repetitions
                repetition_count = sum(1 for t in classifications.values() if t == "REPETITION")
                productive_count = sum(1 for t in classifications.values() if t in ["NEW", "REBUTTAL"])

                # Type emoji mapping
                type_emoji = {
                    "NEW": "🆕 새로운 주장",
                    "REBUTTAL": "⚔️ 반박",
                    "ELABORATION": "📝 보충/심화",
                    "REPETITION": "🔄 단순 반복"
                }

                # Log decision with classification details
                logger.info(f"\n{'='*80}")
                logger.info(f"사회자 토론 분석 (Round {round_number})")
                logger.info(f"{'='*80}")
                logger.info(f"[발언 유형 분류]")
                for persona, cls_type in classifications.items():
                    logger.info(f"  {persona}: {type_emoji.get(cls_type, cls_type)}")
                logger.info(f"[통계] 생산적 발언: {productive_count}/4, 단순 반복: {repetition_count}/4")
                logger.info(f"[결정] {'CONTINUE (계속)' if should_continue else 'STOP (종료)'}")
                if reason_line:
                    logger.info(f"[이유] {reason_line}")
                logger.info(f"{'='*80}\n")

                # Also print to console for real-time monitoring
                print(f"\n{'='*80}")
                print(f"🎯 사회자 토론 분석 (Round {round_number}/{max_rounds})")
                print(f"{'='*80}")
                print(f"📊 [발언 유형 분류]")
                for persona, cls_type in classifications.items():
                    print(f"   {persona}: {type_emoji.get(cls_type, cls_type)}")
                print(f"📈 [통계] 생산적 발언(NEW/REBUTTAL): {productive_count}/4, 단순 반복: {repetition_count}/4")
                print(f"{'─'*80}")
                print(f"{'✅ 결정: CONTINUE (토론 계속)' if should_continue else '🛑 결정: STOP (토론 종료)'}")
                if reason_line:
                    print(f"💬 이유: {reason_line}")
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
