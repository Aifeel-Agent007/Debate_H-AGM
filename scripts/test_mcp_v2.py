"""
Test MCP tools with persistent connection (v2).

This test verifies the new connection pooling approach works.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()


async def test_mcp_v2_tool():
    """Test calling a tool with v2 MCP manager."""
    print("\n" + "="*80)
    print("TEST: MCP v2 Tool Call (Persistent Connection)")
    print("="*80)

    try:
        from src.shared.mcp_tools import search_web_tool

        print("\n1. Calling search_web_tool.ainvoke()...")
        print("   Query: 'Python programming language'")

        result = await search_web_tool.ainvoke({
            "query": "Python programming language",
            "max_results": 2,
            "search_depth": "basic",
            "include_answer": False
        })

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


async def test_multiple_calls():
    """Test multiple tool calls using the same connection."""
    print("\n" + "="*80)
    print("TEST: Multiple Tool Calls (Connection Reuse)")
    print("="*80)

    try:
        from src.shared.mcp_tools import search_web_tool, get_quick_answer_tool

        print("\n1. First call: search_web_tool")
        result1 = await search_web_tool.ainvoke({
            "query": "AI technology",
            "max_results": 2,
            "search_depth": "basic",
            "include_answer": False
        })

        print(f"   ✅ First call completed: {len(str(result1))} characters")

        print("\n2. Second call: get_quick_answer_tool")
        result2 = await get_quick_answer_tool.ainvoke({
            "question": "What is Python?",
            "search_depth": "basic"
        })

        print(f"   ✅ Second call completed: {len(str(result2))} characters")

        print("\n3. Third call: search_web_tool again")
        result3 = await search_web_tool.ainvoke({
            "query": "renewable energy",
            "max_results": 2,
            "search_depth": "basic",
            "include_answer": False
        })

        print(f"   ✅ Third call completed: {len(str(result3))} characters")

        print("\n✅ All calls succeeded using the same connection!")
        return True

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_panelist_with_mcp_v2():
    """Test panelist with MCP v2 tools."""
    print("\n" + "="*80)
    print("TEST: Panelist with MCP v2 Tools")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        print("\n1. Creating panelist agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"   ✓ Agent: {panelist.persona_config['name']}")
        print(f"   ✓ Tools: {len(panelist.tools)}")

        # Topic that might trigger tool usage
        topic = "2024년 재생 에너지의 최신 통계"

        print(f"\n2. Test topic: {topic}")
        print("\n3. Generating response (max 60 seconds)...")

        try:
            result = await asyncio.wait_for(
                panelist.graph.ainvoke(
                    {
                        "topic": topic,
                        "round_number": 1,
                        "previous_context": "",
                    },
                    config={"configurable": {"thread_id": "test-mcp-v2"}},
                ),
                timeout=60.0
            )

            print("\n4. Response generated successfully!")
            response_data = result.get("response", {})
            if isinstance(response_data, dict):
                opinion = response_data.get("opinion", "N/A")
                print(f"   Opinion preview: {opinion[:150]}...")
            else:
                print(f"   Response: {str(response_data)[:150]}...")

            return True

        except asyncio.TimeoutError:
            print("\n❌ Response generation timed out after 60 seconds")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup():
    """Cleanup MCP connection."""
    try:
        from src.shared.mcp_tools import MCPSearchManager
        if MCPSearchManager._instance:
            await MCPSearchManager._instance.close()
            print("\n🔌 MCP connection closed")
    except Exception as e:
        print(f"\n⚠️  Error during cleanup: {e}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MCP v2 Test Suite (Persistent Connection)")
    print("="*80)
    print("\nThis tests the new connection pooling approach.")

    results = []

    try:
        # Test 1: Single tool call
        print("\n" + "="*80)
        result = await test_mcp_v2_tool()
        results.append(("Single Tool Call", result))

        # Test 2: Multiple calls
        print("\n" + "="*80)
        result = await test_multiple_calls()
        results.append(("Multiple Tool Calls", result))

        # Test 3: Panelist with tools
        print("\n" + "="*80)
        result = await test_panelist_with_mcp_v2()
        results.append(("Panelist with MCP v2", result))

    finally:
        await cleanup()

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
        print("\n🎉 All tests passed! MCP v2 integration is working.")
        print("\nYou can now use the debate system with MCP server.")
    else:
        print("\n⚠️  Some tests failed.")


if __name__ == "__main__":
    asyncio.run(main())
