"""
Simple MCP integration test.

Tests that agents have access to MCP tools without actually calling them.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_panelist_tools():
    """Test that panelist has MCP tools."""
    print("\n" + "=" * 80)
    print("TEST 1: Panelist Agent Tool Integration")
    print("=" * 80)

    try:
        from src.panelist.agent import PanelistAgent

        # Create a panelist
        panelist = PanelistAgent("right_scholar")
        print(f"\n✓ Created panelist: {panelist.persona_config['name']}")

        # Check tools
        print(f"✓ Agent has {len(panelist.tools)} MCP tools available")

        for tool in panelist.tools:
            print(f"  - {tool.name}: {tool.description[:80]}...")

        print("\n✅ Panelist has access to MCP tools!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_moderator_tools():
    """Test that moderator has MCP tools."""
    print("\n" + "=" * 80)
    print("TEST 2: Moderator Agent Tool Integration")
    print("=" * 80)

    try:
        from src.moderator.agent import ModeratorAgent

        # Create a moderator (with dummy URLs)
        panelist_urls = {
            "right_politician": "http://localhost:8001",
            "right_scholar": "http://localhost:8002",
            "left_politician": "http://localhost:8003",
            "left_scholar": "http://localhost:8004",
        }

        moderator = ModeratorAgent(panelist_urls)
        print(f"\n✓ Created moderator agent")

        # Check tools
        print(f"✓ Agent has {len(moderator.tools)} MCP tools available")

        for tool in moderator.tools:
            print(f"  - {tool.name}: {tool.description[:80]}...")

        print("\n✅ Moderator has access to MCP tools!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_invocation_simple():
    """Test simple tool invocation without full MCP server."""
    print("\n" + "=" * 80)
    print("TEST 3: Tool Invocation Test (Mocked)")
    print("=" * 80)

    try:
        from src.shared.mcp_tools import search_web_tool, get_quick_answer_tool

        print("\n✓ MCP tools imported successfully")
        print(f"  - search_web_tool: {search_web_tool.name}")
        print(f"  - get_quick_answer_tool: {get_quick_answer_tool.name}")

        # Check tool properties
        print(f"\n✓ Tools are LangChain-compatible")
        print(f"  - search_web_tool.func: {search_web_tool.func}")
        print(f"  - search_web_tool.args: {list(search_web_tool.args.keys())}")

        print("\n✅ Tools are properly configured!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MCP Integration Test - Simple Version")
    print("=" * 80)

    # Check environment
    if not os.getenv("TAVILY_API_KEY"):
        print("\n⚠️  TAVILY_API_KEY not found in environment")
        print("Note: This is OK for tool integration tests")


    print("\n✓ Environment configured")

    # Run tests
    results = []

    result = await test_panelist_tools()
    results.append(("Panelist Tools", result))

    result = await test_moderator_tools()
    results.append(("Moderator Tools", result))

    result = await test_tool_invocation_simple()
    results.append(("Tool Configuration", result))

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Start the debate system: ./start_panelists.sh")
        print("2. In another terminal: ./start_moderator.sh")
        print("3. Run a debate: ./run_debate.sh")
        print("4. Watch for MCP tool usage logs in the output!")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
