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

        # Using OpenAI GPT-4 mini
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=api_key,
            temperature=0.7,
        )

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
            self.memory_system = AgenticMemorySystem(
                user_id=user_id,
                neo4j_url=neo4j_url,
                model="gpt-4o-mini",
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

        # Save previous context to memory if available (opponent's arguments)
        if previous_context and self.memory_system:
            try:
                memory_content = f"[상대방 주장 - Round {round_number-1}] {previous_context}"
                self.memory_system.add_note(memory_content)
                logger.info(f"💾 Saved opponent's argument to memory for {self.persona_config['name']}")
            except Exception as e:
                logger.warning(f"Failed to save previous context to memory: {e}")

        # Retrieve relevant memories before generating response
        memory_context = ""
        if self.memory_system:
            try:
                # Search for relevant memories about the topic
                memory_results = self.memory_system.find_related_memories_raw(topic, k=5)
                if memory_results:
                    memory_context = f"\n\n[과거 메모리에서 검색된 관련 정보]:\n{memory_results}"
                    logger.info(f"🔍 Retrieved {len(memory_results.split('['))-1} relevant memories for {self.persona_config['name']}")
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")

        # Build prompt
        context_info = ""
        if previous_context and round_number > 1:
            context_info = f"\n\n이전 라운드 정보:\n{previous_context}"
        
        # Add memory context
        context_info += memory_context

        # First round: mandatory background research
        tool_instruction = ""
        if round_number == 1:
            tool_instruction = f"""
[첫 라운드 필수 작업]
토론을 시작하기 전에 반드시 다음 작업을 수행하세요:

1. get_context_tool을 사용하여 "{topic}"에 대한 배경 정보를 수집하세요
   - 이 단계는 필수이며, 반드시 실행해야 합니다
   - 수집한 정보를 바탕으로 당신의 관점에서 의견을 구성하세요

2. 배경 정보 수집 후, 당신의 페르소나({self.persona_config['name']}, {self.persona_config['stance']})에 맞게 의견을 제시하세요

사용 가능한 도구:
- get_context_tool: 종합적인 배경 정보 (첫 라운드에서 필수 사용)
- search_web_tool: 추가 웹 검색이 필요한 경우
- get_quick_answer_tool: 빠른 답변 얻기
- verify_fact_tool: 팩트 검증

중요: 한 번에 하나의 도구만 호출하세요."""
        else:
            tool_instruction = """
필요하다면 다음 도구 중 하나를 사용할 수 있습니다 (한 번에 하나만):
- search_web_tool: 웹에서 정보 검색
- get_quick_answer_tool: 빠른 답변 얻기
- get_context_tool: 종합적인 배경 정보
- verify_fact_tool: 팩트 검증

중요: 도구는 정말 필요한 경우에만 사용하고, 반드시 한 번에 하나의 도구만 호출하세요."""

        system_prompt = f"""{self.persona_config['system_prompt']}

토론 주제: {topic}
현재 라운드: {round_number}{context_info}

위 토론 주제에 대해 당신의 관점에서 의견을 제시해주세요.
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
   - 상대 관점에 대한 예상 반박과 재반박 포함
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

        return PanelistResponse(
            persona=self.persona_config["name"],
            stance=self.persona_config["stance"],  # type: ignore
            opinion=opinion,
            reasoning=reasoning,
            round_number=round_number,
        )
