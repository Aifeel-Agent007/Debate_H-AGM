"""Test if agents actually use MCP search tools during debate."""

import asyncio
import os
from dotenv import load_dotenv
from src.panelist.agent import PanelistAgent

load_dotenv()


async def test_panelist_mcp_usage():
    """Test if panelist uses MCP tools when generating responses."""
    print("="*80)
    print("Testing Panelist MCP Tool Usage During Debate")
    print("="*80)

    # Create a panelist
    print("\n1. Creating right_politician agent...")
    agent = PanelistAgent("right_politician")
    print(f"✓ Agent created with {len(agent.tools)} tools")

    # Test topic that would benefit from search
    topic = "AI가 일자리에 미치는 영향"
    context_id = "test_mcp_usage"

    print(f"\n2. Testing with topic: '{topic}'")
    print("   This topic should trigger MCP tool usage for factual information\n")

    # Get opinion (this should trigger MCP tool usage internally)
    print("3. Generating response (watch for MCP tool calls)...\n")
    print("-" * 80)

    response = await agent.get_opinion(
        topic=topic,
        round_number=1,
        context_id=context_id,
        previous_context=None
    )

    print("-" * 80)
    print("\n4. Response received:")
    print(f"   Persona: {response.persona}")
    print(f"   Stance: {response.stance}")
    print(f"   Opinion length: {len(response.opinion)} chars")
    print(f"   Reasoning length: {len(response.reasoning)} chars")

    # Check if response seems to contain factual information
    has_numbers = any(char.isdigit() for char in response.reasoning)
    has_sources = any(word in response.reasoning.lower() for word in ['연구', '조사', '통계', '보고'])

    print("\n5. Response analysis:")
    print(f"   Contains numbers: {has_numbers}")
    print(f"   Contains source references: {has_sources}")

    if has_numbers or has_sources:
        print("   ✓ Response appears to contain researched information")
    else:
        print("   ⚠ Response may not have used MCP search tools")

    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)

    # Show preview of reasoning
    print("\n📝 Reasoning preview (first 500 chars):")
    print("-" * 80)
    print(response.reasoning[:500] + "...")
    print("-" * 80)


async def test_moderator_research():
    """Test if moderator uses MCP tools during research phase."""
    print("\n\n")
    print("="*80)
    print("Testing Moderator MCP Tool Usage During Research")
    print("="*80)

    from src.moderator.agent import ModeratorAgent

    # Create moderator (with dummy panelist URLs since we're just testing research)
    print("\n1. Creating moderator agent...")
    moderator = ModeratorAgent({
        "right_politician": "http://localhost:8001",
        "right_scholar": "http://localhost:8002",
        "left_politician": "http://localhost:8003",
        "left_scholar": "http://localhost:8004",
    })
    print(f"✓ Moderator created with {len(moderator.tools)} tools")

    # Test research phase only
    topic = "인공지능의 윤리적 문제"
    print(f"\n2. Testing research phase with topic: '{topic}'")
    print("   This should trigger MCP search tools for background research\n")

    # Create initial state
    state = {
        "topic": topic,
        "research_data": "",
        "subtopics": [],
        "current_subtopic_index": 0,
        "total_allocated_minutes": 0,
        "speakers_this_round": [],
        "next_speaker": None,
        "panel_responses": [],
        "debate_history": [],
        "should_continue": True,
        "final_summary": None,
    }

    print("3. Running research phase (watch for MCP tool calls)...\n")
    print("-" * 80)

    # Call research_topic directly
    result = await moderator._research_topic(state)

    print("-" * 80)

    research_data = result.get("research_data", "")

    print("\n4. Research results:")
    print(f"   Research data length: {len(research_data)} chars")

    if research_data and len(research_data) > 100:
        print("   ✓ Research data collected successfully")
        print("\n📝 Research data preview (first 500 chars):")
        print("-" * 80)
        print(research_data[:500] + "...")
        print("-" * 80)
    else:
        print("   ✗ Research data seems empty or failed")

    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)


async def main():
    """Run all tests."""
    # Test panelist MCP usage
    await test_panelist_mcp_usage()

    # Test moderator research
    await test_moderator_research()


if __name__ == "__main__":
    asyncio.run(main())
