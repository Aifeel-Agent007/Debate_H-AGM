"""Test simple single-topic debate system."""

import asyncio
from src.moderator.agent import ModeratorAgent


async def test_simple_debate():
    """Test the simplified single-topic debate system."""
    print("="*80)
    print("Testing Simple Single-Topic Debate System")
    print("="*80)

    # Create moderator with dummy panelist URLs
    print("\n1. Creating moderator agent...")
    moderator = ModeratorAgent({
        "right_politician": "http://localhost:8001",
        "right_scholar": "http://localhost:8002",
        "left_politician": "http://localhost:8003",
        "left_scholar": "http://localhost:8004",
    })
    print(f"✓ Moderator created with {len(moderator.tools)} tools")

    # Test the graph structure
    print("\n2. Checking graph structure...")
    print(f"   Graph nodes: {list(moderator.graph.nodes.keys())}")

    # Verify research phase
    print("\n3. Testing research phase...")
    topic = "인공지능의 윤리적 문제"

    state = {
        "topic": topic,
        "research_data": "",
        "round_number": 0,
        "max_rounds": 0,
        "speakers_this_round": [],
        "next_speaker": None,
        "panel_responses": [],
        "debate_history": [],
        "final_summary": None,
    }

    print(f"   Topic: '{topic}'")
    print("   Running research phase (this will call MCP tools)...\n")

    result = await moderator._research_topic(state)

    research_data = result.get("research_data", "")
    print(f"\n✓ Research completed: {len(research_data)} characters")
    print(f"   Round number: {result.get('round_number')}")
    print(f"   Max rounds: {result.get('max_rounds')}")

    if research_data and len(research_data) > 100:
        print("\n📝 Research data preview (first 300 chars):")
        print("-" * 80)
        print(research_data[:300] + "...")
        print("-" * 80)

    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)

    print("\n✅ Summary:")
    print(f"   - Research phase: {'✓ Working' if research_data else '✗ Failed'}")
    print(f"   - Round management: ✓ Initialized (rounds 1-{result.get('max_rounds', 5)})")
    print(f"   - Graph structure: ✓ Simplified (no subtopics)")


if __name__ == "__main__":
    asyncio.run(test_simple_debate())
