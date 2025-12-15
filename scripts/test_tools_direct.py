"""
Test MCP tools with direct Tavily integration.

This test verifies that the tools work correctly after bypassing FastMCP.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()


async def test_direct_tool():
    """Test calling a tool directly."""
    print("\n" + "="*80)
    print("TEST: Direct Tool Call (Bypassing FastMCP)")
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


async def test_panelist_with_direct_tools():
    """Test panelist with direct Tavily tools."""
    print("\n" + "="*80)
    print("TEST: Panelist with Direct Tools")
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
        print("   Note: LLM may or may not use tools")
        print("\n3. Generating response (max 60 seconds)...")

        try:
            result = await asyncio.wait_for(
                panelist.graph.ainvoke(
                    {
                        "topic": topic,
                        "round_number": 1,
                        "previous_context": "",
                    },
                    config={"configurable": {"thread_id": "test-direct-tools"}},
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


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Direct Tavily Integration Test Suite")
    print("="*80)
    print("\nThese tests verify tools work after bypassing FastMCP.")

    results = []

    # Test 1: Direct tool call
    print("\n" + "="*80)
    result = await test_direct_tool()
    results.append(("Direct Tool Call", result))

    # Test 2: Panelist with tools
    print("\n" + "="*80)
    result = await test_panelist_with_direct_tools()
    results.append(("Panelist with Direct Tools", result))

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
        print("\n🎉 All tests passed! Direct Tavily integration is working.")
        print("\nYou can now use the debate system with search tools.")
    else:
        print("\n⚠️  Some tests failed.")


if __name__ == "__main__":
    asyncio.run(main())
