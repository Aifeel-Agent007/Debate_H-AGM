"""Panelist LangGraph agent implementation."""

import os
from typing import Any
# from langchain_anthropic import ChatAnthropic  # Commented out - using OpenAI instead
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from ..shared.models import PanelistResponse
from ..shared.utils import setup_logging
from ..shared.mcp_tools import get_search_tools
from ..shared.memory_layer import AgenticMemorySystem
from .personas import get_persona, PersonaType

logger = setup_logging(__name__)

# 진영별 패널리스트 분류
FACTION_MAP = {
    "right": ["right_politician", "right_scholar"],
    "left": ["left_politician", "left_scholar"]
}

PERSONA_DISPLAY_NAMES = {
    "right_politician": "우파 정치인",
    "right_scholar": "우파 학자",
    "left_politician": "좌파 정치인",
    "left_scholar": "좌파 학자"
}


def get_faction(persona_type: str) -> str:
    """패널리스트의 진영을 반환"""
    for faction, members in FACTION_MAP.items():
        if persona_type in members:
            return faction
    return "unknown"


def get_ally(persona_type: str) -> str | None:
    """같은 진영의 다른 패널리스트를 반환"""
    faction = get_faction(persona_type)
    for member in FACTION_MAP.get(faction, []):
        if member != persona_type:
            return member
    return None


def get_opponents(persona_type: str) -> list[str]:
    """상대 진영의 패널리스트들을 반환"""
    my_faction = get_faction(persona_type)
    for faction, members in FACTION_MAP.items():
        if faction != my_faction:
            return members
    return []


class PanelistState(BaseModel):
    """State for panelist agent."""

    topic: str
    round_number: int
    previous_context: str | None = None
    response: str | None = None
    reasoning: str | None = None


class PanelistAgent:
    """Panelist agent using LangGraph."""

    def __init__(self, persona_type: PersonaType):
        """Initialize panelist agent.

        Args:
            persona_type: Type of persona for this panelist
        """
        self.persona_type = persona_type
        self.persona_config = get_persona(persona_type)

        # Initialize LLM
        # api_key = os.getenv("ANTHROPIC_API_KEY")  # Commented out - using OpenAI instead
        # if not api_key:
        #     raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        # self.llm = ChatAnthropic(  # Commented out - using OpenAI instead
        #     model="claude-sonnet-4-5-20250929",
        #     anthropic_api_key=api_key,
        #     temperature=0.7,
        # )

        # Initialize LLM from configuration
        from ..shared.llm_factory import get_llm_from_config
        
        # Get LLM provider from environment (default: gpt)
        llm_provider = os.getenv("PANELIST_LLM_PROVIDER", os.getenv("DEBATE_LLM_PROVIDER", "gpt")).lower()
        llm_model = os.getenv("PANELIST_LLM_MODEL")
        llm_temperature = float(os.getenv("PANELIST_LLM_TEMPERATURE", "0.7"))
        
        self.llm = get_llm_from_config(
            config_key="PANELIST_LLM_PROVIDER",
            default_provider=llm_provider,
            model=llm_model,
            temperature=llm_temperature,
        )
        
        # Get API key for memory system (use OpenAI key as default for memory analysis)
        from ..shared.llm_factory import API_KEY_ENV_VARS
        api_key_env = API_KEY_ENV_VARS.get(llm_provider, "OPENAI_API_KEY")
        api_key = os.getenv(api_key_env)
        if not api_key:
            # Fallback to OpenAI key
            api_key = os.getenv("OPENAI_API_KEY")
        
        # Get MCP search tools
        self.tools = get_search_tools()

        # Initialize Agentic Memory System with unique user_id for this panelist
        # Each panelist has their own isolated memory space in Neo4j
        # 총 4개의 독립적인 H-AGM 메모리 시스템이 생성됩니다:
        #   1. panelist_right_politician (우파 정치인)
        #   2. panelist_right_scholar (우파 학자)
        #   3. panelist_left_politician (좌파 정치인)
        #   4. panelist_left_scholar (좌파 학자)
        user_id = f"panelist_{persona_type}"
        
        # 패널리스트별 메모리 시스템 번호 결정
        memory_numbers = {
            "right_politician": 1,
            "right_scholar": 2,
            "left_politician": 3,
            "left_scholar": 4,
        }
        memory_number = memory_numbers.get(persona_type, 0)
        
        # 각 패널리스트마다 다른 Neo4j 포트 사용
        neo4j_ports = {
            "right_politician": 7687,  # Neo4j #1
            "right_scholar": 7688,      # Neo4j #2
            "left_politician": 7689,    # Neo4j #3
            "left_scholar": 7690,       # Neo4j #4
        }
        neo4j_port = neo4j_ports.get(persona_type, 7687)
        neo4j_url = f"bolt://localhost:{neo4j_port}"
        
        print(f"\n{'='*70}")
        print(f"🧠 [H-AGM #{memory_number}] Creating memory system for {self.persona_config['name']}")
        print(f"{'='*70}")
        print(f"   Memory System #: {memory_number}/4")
        print(f"   User ID: {user_id}")
        print(f"   Persona: {persona_type}")
        print(f"   Name: {self.persona_config['name']}")
        print(f"   Neo4j URL: {neo4j_url} (독립 인스턴스 #{memory_number})")
        print(f"{'='*70}\n")
        
        try:
            # Use LLM model for memory system (default to gpt-4o-mini for compatibility)
            memory_model = os.getenv("MEMORY_LLM_MODEL", "gpt-4o-mini")
            self.memory_system = AgenticMemorySystem(
                user_id=user_id,
                neo4j_url=neo4j_url,
                model=memory_model,
                api_key=api_key
            )
            logger.info(f"✅ H-AGM Memory System #{memory_number} initialized for {self.persona_config['name']} (user_id: {user_id})")
            print(f"\n{'='*70}")
            print(f"✅ [H-AGM #{memory_number}] Memory system READY for {self.persona_config['name']}")
            print(f"{'='*70}")
            print(f"   ✅ Memory System #{memory_number}/4 created successfully")
            print(f"   ✅ User ID: {user_id}")
            print(f"   ✅ This is an independent, isolated memory space")
            print(f"   ✅ No memory sharing with other panelists")
            print(f"{'='*70}\n")
        except Exception as e:
            logger.error(f"❌ H-AGM Memory System #{memory_number} initialization failed for {self.persona_config['name']}: {e}")
            print(f"\n{'='*70}")
            print(f"❌ [H-AGM #{memory_number}] Memory system initialization FAILED")
            print(f"{'='*70}")
            print(f"   Panelist: {self.persona_config['name']}")
            print(f"   User ID: {user_id}")
            print(f"   Error: {e}")
            print(f"   Continuing without memory system...")
            print(f"{'='*70}\n")
            self.memory_system = None

        # Create memory saver (LangGraph checkpoint)
        self.memory = MemorySaver()

        # Build graph
        self.graph = self._build_graph()

        logger.info(f"Initialized {self.persona_config['name']} agent with {len(self.tools)} MCP tools")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for panelist.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(dict)

        # Add nodes
        workflow.add_node("generate_response", self._generate_response)

        # Set entry point
        workflow.set_entry_point("generate_response")

        # Add edge to end
        workflow.add_edge("generate_response", END)

        return workflow.compile(checkpointer=self.memory)

    def _build_round1_instruction(self) -> str:
        """라운드 1: 핵심 의견 주장 프롬프트"""
        return """
[1라운드 - 핵심 의견 주장]

이번 라운드는 첫 번째 발언입니다. 당신의 핵심 주장을 명확하게 제시하세요.

발언 목표:
1. 당신의 정치적/학문적 관점에서 주제에 대한 명확한 입장을 밝히세요
2. 핵심 논거 2-3개를 제시하고, 각각에 대해 상세히 설명하세요
3. 구체적인 데이터, 사례, 전문가 의견을 인용하여 신뢰성을 높이세요
4. 향후 반박에 대비하여 논리적 근거를 탄탄하게 구축하세요

이 라운드에서는 상대 진영을 반박하지 않습니다. 오직 당신의 주장에 집중하세요.
"""

    def _build_round2_plus_instruction(self, ally: str | None, opponents: list[str]) -> str:
        """라운드 2+: 반박 및 보완 프롬프트"""
        ally_display = PERSONA_DISPLAY_NAMES.get(ally, ally) if ally else "없음"
        opponent_displays = [PERSONA_DISPLAY_NAMES.get(o, o) for o in opponents]

        return f"""
[2라운드 이상 - 반박 및 보완]

⚠️ 중요: 주장 반복 금지!
아래 [나의 과거 주장 - 반복 금지 목록]에 있는 내용을 다시 주장하지 마세요:
- 같은 핵심 논리 반복 금지
- 같은 통계/데이터 재인용 금지
- 같은 사례 반복 금지
- 반드시 새로운 관점, 새로운 근거, 새로운 논점을 제시하세요
- 이미 사용한 근거가 있다면 "앞서 제가 언급한 바와 같이"로 간략히 언급만 하세요

당신의 동맹: {ally_display}
상대 진영: {', '.join(opponent_displays)}

발언 전략 (권장 비중):

1. 상대 진영 반박 (70%)
   - 상대방이 제시한 논거의 논리적 허점을 지적하세요
   - "앞서 {opponent_displays[0]}께서 말씀하신 ~는..." 형식으로 정중하게 인용
   - verify_fact_tool을 사용하여 상대방 주장의 사실 여부를 검증하세요 (강력 권고)
   - 반박 시 구체적인 증거와 데이터를 제시하세요

2. 재반박 (20%)
   - 이전 라운드에서 상대방이 당신의 주장을 반박했다면 대응하세요
   - "저의 이전 발언에 대해 ~라는 반박이 있었는데..." 형식
   - 새로운 근거를 추가하여 원래 주장을 강화하세요

3. 같은 진영 보완 (10%)
   - {ally_display}의 주장을 보충하고 강화하세요
   - "같은 진영의 {ally_display}께서 언급하신 바와 같이..." 형식

인용 스타일 (필수):
- "앞서 우파 정치인께서 '시장 자율에 맡겨야 한다'고 말씀하셨는데, 이는..."
- "좌파 학자께서 언급하신 OECD 통계에 대해 제가 확인해본 결과..."
- "같은 진영의 우파 학자께서 제시하신 이론적 근거에 더하여..."

주의사항:
- 상대방의 구체적인 발언을 인용하여 반박하세요 (막연한 반박 금지)
- 감정적 표현보다 논리적, 사실적 반박을 우선하세요
"""

    def _extract_opinions_only(self, memories: str) -> str:
        """과거 발언에서 의견 부분만 추출 (근거 제외)"""
        import re

        # 패턴: [패널리스트 - Round X]\n의견: ...\n근거: ...
        pattern = r'\[([^\]]+)\]\n의견:\s*(.*?)(?=\n근거:|$)'
        matches = re.findall(pattern, memories, re.DOTALL)

        if not matches:
            return memories  # 패턴 매칭 실패 시 원본 반환

        result = []
        for header, opinion in matches:
            opinion_clean = opinion.strip()[:500]  # 최대 500자로 제한
            result.append(f"[{header}]\n의견: {opinion_clean}")

        return "\n\n".join(result)

    async def _search_memories_by_faction(self, topic: str, round_number: int) -> dict[str, str]:
        """진영별 메모리 검색"""
        results = {"ally_memories": "", "opponent_memories": "", "my_previous": ""}

        if not self.memory_system or round_number < 2:
            return results

        ally = get_ally(self.persona_type)
        opponents = get_opponents(self.persona_type)

        # 1. 상대 진영 주장 검색 (반박용)
        for opponent in opponents:
            opponent_name = PERSONA_DISPLAY_NAMES.get(opponent, opponent)
            query = f"[{opponent_name}]"
            memories = self.memory_system.find_related_memories_raw(query, k=3)
            if memories:
                results["opponent_memories"] += f"\n--- {opponent_name} ---\n{memories}"

        # 2. 같은 진영 주장 검색 (보완용)
        if ally:
            ally_name = PERSONA_DISPLAY_NAMES.get(ally, ally)
            memories = self.memory_system.find_related_memories_raw(f"[{ally_name}]", k=2)
            if memories:
                results["ally_memories"] = memories

        # 3. 내 이전 발언 검색 (반복 방지용) - 더 많이 검색
        my_name = self.persona_config["name"]
        memories = self.memory_system.find_related_memories_raw(f"[{my_name}]", k=5)  # k=2 → k=5
        if memories:
            # 의견 + 근거 전체를 가져옴 (반복 방지를 위해 전체 내용 필요)
            results["my_previous"] = memories

        return results

    def _build_tool_instruction(self, round_number: int) -> str:
        """라운드별 도구 사용 지침"""
        base_tools = """
사용 가능한 도구:
- search_web_tool: 웹에서 최신 정보, 뉴스, 통계 검색
- get_context_tool: 주제에 대한 종합적인 배경 정보 수집
- get_quick_answer_tool: 특정 질문에 대한 빠른 답변
- verify_fact_tool: 주장이나 통계의 사실 여부 검증
"""

        if round_number == 1:
            return f"""
[검색 도구 활용 지침 - 1라운드]
{base_tools}
1라운드 권장:
- get_context_tool: 주제 배경 정보 수집 (필수)
- search_web_tool: 최신 통계/데이터 검색

당신의 페르소나: {self.persona_config['name']} ({self.persona_config['stance']})
"""
        else:
            return f"""
[검색 도구 활용 지침 - {round_number}라운드]
{base_tools}
2라운드+ 권장:
- verify_fact_tool: 상대방 주장 검증 (강력 권고!)
  예시: verify_fact_tool(claim="상대방이 주장한 내용")
- search_web_tool: 반박 근거 검색

당신의 페르소나: {self.persona_config['name']} ({self.persona_config['stance']})
"""

    async def _generate_response(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate response based on persona with ReAct pattern.

        Args:
            state: Current state

        Returns:
            Updated state with response
        """
        topic = state.get("topic", "")
        round_number = state.get("round_number", 1)
        previous_context = state.get("previous_context", "")

        # Save previous context to memory if available (발언자별로 분리하여 저장)
        if previous_context and self.memory_system:
            try:
                import re
                # previous_context에서 발언자별로 분리하여 저장
                pattern = r'\[([^\]]+)\]\n의견: (.*?)\n근거: (.*?)(?=\n\n\[|\Z)'
                matches = re.findall(pattern, previous_context, re.DOTALL)

                if matches:
                    for speaker, opinion, reasoning in matches:
                        memory_content = f"[{speaker} - Round {round_number-1}]\n의견: {opinion.strip()}\n근거: {reasoning.strip()}"
                        self.memory_system.add_note(memory_content)
                        logger.info(f"💾 Saved {speaker}'s argument to memory")
                else:
                    # Fallback: 기존 방식
                    memory_content = f"[상대방 주장 - Round {round_number-1}] {previous_context}"
                    self.memory_system.add_note(memory_content)
                    logger.info(f"💾 Saved opponent's argument to memory for {self.persona_config['name']}")
            except Exception as e:
                logger.warning(f"Failed to save previous context to memory: {e}")

        # 진영별 메모리 검색 (2번째 라운드부터)
        memory_context = ""
        ally = get_ally(self.persona_type)
        opponents = get_opponents(self.persona_type)

        if self.memory_system and round_number >= 2:
            try:
                faction_memories = await self._search_memories_by_faction(topic, round_number)

                # 메모리 검색 결과 터미널 출력
                print("\n" + "="*80)
                print(f"🧠 FACTION-BASED MEMORY RETRIEVAL - {self.persona_config['name']} (Round {round_number})")
                print("="*80)
                print(f"📍 Topic: {topic}")
                print(f"🤝 Ally: {PERSONA_DISPLAY_NAMES.get(ally, ally) if ally else 'None'}")
                print(f"⚔️ Opponents: {[PERSONA_DISPLAY_NAMES.get(o, o) for o in opponents]}")
                print("-"*80)

                if faction_memories["opponent_memories"]:
                    memory_context += f"\n\n[반박 대상 - 상대 진영 주장]{faction_memories['opponent_memories']}"
                    print(f"📛 Opponent memories found")
                if faction_memories["ally_memories"]:
                    memory_context += f"\n\n[보완 참고 - 같은 진영 주장]\n{faction_memories['ally_memories']}"
                    print(f"🤝 Ally memories found")
                if faction_memories["my_previous"]:
                    memory_context += f"\n\n[나의 과거 주장 - 반복 금지 목록]\n{faction_memories['my_previous']}"
                    print(f"⚠️ My previous claims found (DO NOT REPEAT)")

                if not memory_context:
                    print(f"No relevant faction memories found")
                print("="*80 + "\n")
            except Exception as e:
                logger.warning(f"Failed to retrieve faction memories: {e}")
        elif round_number == 1:
            print(f"\n🧠 [{self.persona_config['name']}] Round 1 - No previous memories to retrieve.\n")

        # Build prompt - 이전 발언 컨텍스트
        context_info = ""
        if previous_context and round_number > 1:
            context_info = f"\n\n[이번 라운드 이전 발언들]\n{previous_context}"

        # Add memory context (진영별 메모리)
        context_info += memory_context

        # 라운드별 프롬프트 구성
        if round_number == 1:
            round_instruction = self._build_round1_instruction()
        else:
            round_instruction = self._build_round2_plus_instruction(ally, opponents)

        # 도구 사용 지침 (라운드별 차별화)
        tool_instruction = self._build_tool_instruction(round_number)

        system_prompt = f"""{self.persona_config['system_prompt']}

토론 주제: {topic}
현재 라운드: {round_number}
{context_info}

{round_instruction}

{tool_instruction}

최종 응답은 반드시 다음 형식과 길이로 작성해주세요:

[발언 길이 가이드라인]
- 기본 목표: 3분 분량 (약 6000자)
- 최소 길이: 2분 분량 (약 4000자)
- 최대 길이: 5분 분량 (약 10000자)

한국어로 1분에 약 2000자를 말할 수 있습니다. 매우 구체적이고 상세하며 설득력 있는 내용을 담아주세요.

[응답 형식]
1. 의견 (Opinion): 당신의 핵심 주장을 명확하고 강력하게 제시 (10~15문장, 약 1000~1500자)
2. 근거 (Reasoning): 당신의 의견을 뒷받침하는 논리적 근거를 매우 상세히 작성 (30~60문장, 약 4000~8500자)
   - 최소 3~5개의 구체적인 예시와 최신 데이터를 포함
   - 각 논점을 충분히 전개하고 깊이 있게 분석
   - 라운드 2+에서는 반드시 상대방 발언을 인용하며 반박
   - 역사적 사례, 통계, 전문가 의견 등 다양한 근거 활용
   - 논리적 연결고리를 명확히 하고 단계적으로 전개
   - 각 근거마다 충분한 설명과 분석 제공
   - 강력한 결론과 요약으로 마무리"""

        # Generate response directly (MCP tools disabled)
        messages = [{"role": "user", "content": system_prompt}]

        # If tools are enabled, use ReAct loop
        if self.tools:
            llm_with_tools = self.llm.bind_tools(self.tools)
            max_iterations = 5
            for iteration in range(max_iterations):
                response = await llm_with_tools.ainvoke(messages)

                # Check if LLM wants to use tools
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # Log tool usage with clear visual separator
                    print("\n" + "="*80)
                    print(f"🔧 MCP TOOL USAGE - {self.persona_config['name']}")
                    print("="*80)

                    for tool_call in response.tool_calls:
                        print(f"🔍 Tool: {tool_call['name']}")
                        print(f"📝 Arguments: {tool_call['args']}")
                        logger.info(f"🔍 {self.persona_config['name']} using tool: {tool_call['name']}")
                        logger.info(f"   Arguments: {tool_call['args']}")

                    # Add assistant message with tool calls
                    messages.append(response)

                    # Execute tools and get results
                    from langchain_core.messages import ToolMessage
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']

                        # Find and execute the tool
                        tool_result = None
                        tool_error = None
                        for tool in self.tools:
                            if tool.name == tool_name:
                                try:
                                    print(f"\n⏳ Executing {tool_name}...")
                                    tool_result = await tool.ainvoke(tool_args)
                                    print(f"✅ Result received: {len(str(tool_result))} characters")
                                    print(f"📄 Preview: {str(tool_result)[:300]}...")
                                    logger.info(f"✅ Tool result: {tool_result[:200]}...")
                                    
                                    # Save search results to memory
                                    if self.memory_system and tool_result and not (isinstance(tool_result, str) and tool_result.startswith("Error:")):
                                        try:
                                            # Create a memory entry for the search result
                                            search_query = tool_args.get('query', tool_args.get('question', tool_args.get('claim', '')))
                                            memory_content = f"[검색 결과 - {tool_name}] 쿼리: {search_query}\n결과: {str(tool_result)[:1000]}"  # Limit to 1000 chars
                                            self.memory_system.add_note(memory_content)
                                            logger.info(f"💾 Saved search result to memory for {self.persona_config['name']}")
                                        except Exception as mem_e:
                                            logger.warning(f"Failed to save search result to memory: {mem_e}")
                                    
                                except Exception as e:
                                    tool_error = e
                                    tool_result = f"Error: {str(e)}"
                                    print(f"❌ Tool error: {e}")
                                    logger.error(f"❌ Tool error: {e}")
                                break

                        # Add tool result to messages
                        messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call['id']
                        ))

                    print("="*80 + "\n")

                    # Continue loop to let LLM process tool results
                    continue
                else:
                    # No more tool calls, this is the final response
                    response_text = response.content
                    break
            else:
                # Max iterations reached, use last response
                response_text = response.content if hasattr(response, 'content') else str(response)
        else:
            # No tools, generate response directly
            response = await self.llm.ainvoke(messages)
            response_text = response.content

        # Parse response (simple split for now)
        lines = response_text.split('\n')
        opinion_lines = []
        reasoning_lines = []
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '의견' in line or 'Opinion' in line or line.startswith('1.'):
                current_section = 'opinion'
                # Extract text after the label
                if ':' in line:
                    opinion_lines.append(line.split(':', 1)[1].strip())
            elif '근거' in line or 'Reasoning' in line or line.startswith('2.'):
                current_section = 'reasoning'
                # Extract text after the label
                if ':' in line:
                    reasoning_lines.append(line.split(':', 1)[1].strip())
            elif current_section == 'opinion':
                opinion_lines.append(line)
            elif current_section == 'reasoning':
                reasoning_lines.append(line)

        opinion = ' '.join(opinion_lines) if opinion_lines else response_text[:200]
        reasoning = ' '.join(reasoning_lines) if reasoning_lines else response_text

        return {
            **state,
            "response": {
                "opinion": opinion,
                "reasoning": reasoning,
            },
        }

    async def get_opinion(
        self,
        topic: str,
        round_number: int,
        context_id: str,
        previous_context: str | None = None,
    ) -> PanelistResponse:
        """Get opinion on a debate topic.

        Args:
            topic: Debate topic
            round_number: Current round number
            context_id: Context ID for memory
            previous_context: Previous round context

        Returns:
            Structured panelist response
        """
        # Prepare input
        inputs = {
            "topic": topic,
            "round_number": round_number,
            "previous_context": previous_context,
        }

        # Run graph
        config = {"configurable": {"thread_id": context_id}}
        result = await self.graph.ainvoke(inputs, config)

        # Create response
        response_data = result.get("response", {})
        if isinstance(response_data, dict):
            opinion = response_data.get("opinion", "No opinion generated")
            reasoning = response_data.get("reasoning", "No reasoning provided")
        else:
            # Fallback for old format
            opinion = str(response_data)
            reasoning = result.get("reasoning", "No reasoning provided")

        # 패널리스트 자신의 발언을 메모리에 저장 (페르소나 이름 명시)
        if self.memory_system:
            try:
                persona_name = self.persona_config["name"]
                full_response = f"[{persona_name} - Round {round_number}]\n의견: {opinion}\n근거: {reasoning}"
                memory_id = self.memory_system.add_note(full_response)
                logger.info(f"💾 Saved own response to memory for {self.persona_config['name']} (memory_id: {memory_id})")
            except Exception as e:
                logger.warning(f"Failed to save own response to memory: {e}")

        return PanelistResponse(
            persona=self.persona_config["name"],
            stance=self.persona_config["stance"],  # type: ignore
            opinion=opinion,
            reasoning=reasoning,
            round_number=round_number,
        )
