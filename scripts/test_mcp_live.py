"""
Live test of MCP tool usage with real output.

This script tests that MCP tools are actually invoked and logs are displayed.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()


async def test_panelist_with_mcp():
    """Test panelist generating response with potential MCP tool usage."""
    print("\n" + "=" * 80)
    print("LIVE TEST: Panelist with MCP Tools")
    print("=" * 80)
    print("\nThis test will:")
    print("1. Create a panelist agent with MCP tools")
    print("2. Give it a topic that might trigger tool usage")
    print("3. Watch for MCP tool invocation logs")
    print("=" * 80)

    try:
        from src.panelist.agent import PanelistAgent

        # Create a panelist
        print("\n📝 Creating right_scholar agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"✓ Created: {panelist.persona_config['name']}")
        print(f"✓ Tools available: {len(panelist.tools)}")

        # Create a topic that is likely to trigger MCP tool usage
        topic = "2024년 재생 에너지의 최신 통계와 발전 현황"
        print(f"\n🎯 Test topic: {topic}")
        print("\n⏳ Generating response (this may take 30-60 seconds)...")
        print("   Watch for MCP tool usage logs below:")
        print("-" * 80)

        # Invoke the agent
        result = await panelist.graph.ainvoke(
            {
                "topic": topic,
                "round_number": 1,
                "previous_context": "",
            },
            config={"configurable": {"thread_id": "test-mcp-live"}},
        )

        print("-" * 80)
        print("\n✅ Response generated!")
        print("\nResponse content:")
        print(f"  Opinion: {result.get('response', {}).get('opinion', 'N/A')[:200]}...")
        print(f"  Reasoning: {result.get('response', {}).get('reasoning', 'N/A')[:200]}...")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the live test."""
    print("\n" + "=" * 80)
    print("MCP Live Integration Test")
    print("=" * 80)
    print("\nThis test demonstrates real MCP tool usage.")
    print("If tools are used, you'll see logs like:")
    print("  🔧 MCP TOOL USAGE - 우파 학자")
    print("  🔍 Tool: search_web_tool")
    print("  🌐 [MCP SERVER] Calling search_web")
    print("  ✅ [MCP SERVER] search_web completed")
    print("=" * 80)

    result = await test_panelist_with_mcp()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

    if result:
        print("\n✅ Test passed!")
        print("\nNote: If you didn't see MCP tool logs above,")
        print("it means the LLM decided it didn't need to use tools")
        print("for this particular topic. This is normal behavior.")
    else:
        print("\n❌ Test failed - see errors above")


if __name__ == "__main__":
    # Run with unbuffered output
    asyncio.run(main())
