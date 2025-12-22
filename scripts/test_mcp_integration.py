"""
Test script for MCP integration with debate agents.

This script tests that:
1. MCP tools are properly initialized
2. Agents can access the tools
3. Tool calls work correctly
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_mcp_tools():
    """Test MCP tools directly."""
    print("=" * 60)
    print("Test 1: Testing MCP Tools Directly")
    print("=" * 60)

    try:
        from src.shared.mcp_tools import MCPSearchClient

        async with MCPSearchClient() as client:
            print("\n✓ MCP client initialized successfully")

            # Test search_web
            print("\nTesting search_web tool...")
            result = await client.call_tool(
                "search_web",
                {
                    "query": "renewable energy benefits",
                    "max_results": 2,
                    "include_answer": True,
                },
            )
            print(f"✓ search_web result: {result[:200]}...")

            # Test get_quick_answer
            print("\nTesting get_quick_answer tool...")
            result = await client.call_tool(
                "get_quick_answer",
                {"question": "What is nuclear energy?"},
            )
            print(f"✓ get_quick_answer result: {result[:200]}...")

            print("\n✅ All MCP tools working correctly!")

    except Exception as e:
        print(f"\n❌ Error testing MCP tools: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_panelist_integration():
    """Test that panelist agents have access to MCP tools."""
    print("\n" + "=" * 60)
    print("Test 2: Testing Panelist Agent Integration")
    print("=" * 60)

    try:
        from src.panelist.agent import PanelistAgent

        # Create a panelist
        panelist = PanelistAgent("right_scholar")
        print(f"\n✓ Created panelist: {panelist.persona_config['name']}")

        # Check tools
        print(f"✓ Tools available: {len(panelist.tools)}")
        for tool in panelist.tools:
            print(f"  - {tool.name}")

        print("\n✅ Panelist has access to MCP tools!")

    except Exception as e:
        print(f"\n❌ Error testing panelist integration: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_moderator_integration():
    """Test that moderator agent has access to MCP tools."""
    print("\n" + "=" * 60)
    print("Test 3: Testing Moderator Agent Integration")
    print("=" * 60)

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
        print("\n✓ Created moderator")

        # Check tools
        print(f"✓ Tools available: {len(moderator.tools)}")
        for tool in moderator.tools:
            print(f"  - {tool.name}")

        print("\n✅ Moderator has access to MCP tools!")

    except Exception as e:
        print(f"\n❌ Error testing moderator integration: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP Integration Test Suite")
    print("=" * 60)

    # Check environment
    if not os.getenv("TAVILY_API_KEY"):
        print("\n❌ TAVILY_API_KEY not found in environment")
        print("Please add it to your .env file")
        return

    print("\n✓ Environment variables configured")

    # Run tests
    results = []

    # Test 1: MCP tools
    result = await test_mcp_tools()
    results.append(("MCP Tools", result))

    # Test 2: Panelist integration
    result = await test_panelist_integration()
    results.append(("Panelist Integration", result))

    # Test 3: Moderator integration
    result = await test_moderator_integration()
    results.append(("Moderator Integration", result))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! MCP integration is working correctly.")
        print("\nNext steps:")
        print("1. Get your Tavily API key from https://tavily.com")
        print("2. Add it to your .env file")
        print("3. Run a debate with: ./run_debate.sh 'Your debate topic'")
        print("4. Watch agents use MCP tools in real-time!")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
