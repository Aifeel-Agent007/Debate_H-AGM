"""
Test if MCP tools actually work end-to-end.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()


async def test_single_tool():
    """Test a single MCP tool directly."""
    print("\n" + "="*80)
    print("TEST: Single MCP Tool Call")
    print("="*80)

    try:
        from src.shared.mcp_tools import search_web_tool

        print("\n1. Calling search_web_tool...")
        print("   Query: 'Python programming language'")

        result = await search_web_tool(
            query="Python programming language",
            max_results=2,
            search_depth="basic",
            include_answer=False
        )

        print(f"\n2. Result received:")
        print(f"   Length: {len(str(result))} characters")
        print(f"   Preview: {str(result)[:300]}...")

        if "Error:" in str(result):
            print("\n❌ Tool returned an error")
            return False
        else:
            print("\n✅ Tool worked successfully!")
            return True

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_panelist_short_timeout():
    """Test panelist with a simple topic and shorter timeout."""
    print("\n" + "="*80)
    print("TEST: Panelist with MCP Tools (Short Timeout)")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        print("\n1. Creating panelist agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"   ✓ Agent: {panelist.persona_config['name']}")
        print(f"   ✓ Tools: {len(panelist.tools)}")

        # Simple topic that doesn't necessarily require tools
        topic = "인공지능의 발전"

        print(f"\n2. Test topic: {topic}")
        print("   Note: LLM may or may not use tools based on its judgment")
        print("\n3. Generating response (max 60 seconds)...")

        # Use asyncio.wait_for to add timeout
        try:
            result = await asyncio.wait_for(
                panelist.graph.ainvoke(
                    {
                        "topic": topic,
                        "round_number": 1,
                        "previous_context": "",
                    },
                    config={"configurable": {"thread_id": "test-mcp-working"}},
                ),
                timeout=60.0  # 60 second timeout for this test
            )

            print("\n4. Response generated successfully!")
            response_data = result.get("response", {})
            if isinstance(response_data, dict):
                opinion = response_data.get("opinion", "N/A")
                print(f"   Opinion: {opinion[:100]}...")
            else:
                print(f"   Response: {str(response_data)[:100]}...")

            return True

        except asyncio.TimeoutError:
            print("\n❌ Response generation timed out after 60 seconds")
            print("   This suggests MCP tools are hanging")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MCP Working Test Suite")
    print("="*80)
    print("\nThis test verifies that MCP tools actually work.")

    results = []

    # Test 1: Direct tool call
    print("\n" + "="*80)
    result = await test_single_tool()
    results.append(("Single Tool Call", result))

    # Test 2: Panelist with tools
    print("\n" + "="*80)
    result = await test_panelist_short_timeout()
    results.append(("Panelist with Tools", result))

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! MCP integration is working.")
    else:
        print("\n⚠️  Some tests failed.")
        print("\nPossible issues:")
        print("1. MCP server connection problems")
        print("2. Tavily API key invalid or rate limited")
        print("3. Network connectivity issues")


if __name__ == "__main__":
    asyncio.run(main())
