"""
Direct test of Tavily API without MCP layer.

This test verifies that Tavily API works correctly,
helping us determine if the issue is with FastMCP or Tavily.
"""

import asyncio
import os
from dotenv import load_dotenv
from tavily import AsyncTavilyClient

# Load environment variables
load_dotenv()


async def test_tavily_search():
    """Test Tavily search API directly."""
    print("\n" + "="*80)
    print("TEST: Direct Tavily API Search")
    print("="*80)

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("❌ TAVILY_API_KEY not found in environment")
            return False

        print(f"\n✓ API Key found: {api_key[:10]}...")

        print("\n1. Creating Tavily client...")
        client = AsyncTavilyClient(api_key=api_key)
        print("   ✓ Client created")

        print("\n2. Performing search...")
        print("   Query: 'Python programming language'")

        result = await client.search(
            query="Python programming language",
            max_results=2,
            search_depth="basic",
            include_answer=False
        )

        print("\n3. Search completed!")
        print(f"   Results: {len(result.get('results', []))} items")

        if result.get('results'):
            first_result = result['results'][0]
            print(f"   First result: {first_result.get('title', 'N/A')}")
            print(f"   URL: {first_result.get('url', 'N/A')}")

        print("\n✅ Tavily API works correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tavily_context():
    """Test Tavily get_search_context API directly."""
    print("\n" + "="*80)
    print("TEST: Direct Tavily Context API")
    print("="*80)

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        client = AsyncTavilyClient(api_key=api_key)

        print("\n1. Getting context...")
        print("   Query: 'artificial intelligence impact'")

        context = await client.get_search_context(
            query="artificial intelligence impact",
            max_tokens=1000,
            search_depth="basic"
        )

        print("\n2. Context retrieved!")
        print(f"   Length: {len(context)} characters")
        print(f"   Preview: {context[:200]}...")

        print("\n✅ Tavily Context API works correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all direct Tavily tests."""
    print("\n" + "="*80)
    print("Direct Tavily API Test Suite")
    print("="*80)
    print("\nThis test bypasses FastMCP to verify Tavily API works.")

    results = []

    # Test 1: Search
    result = await test_tavily_search()
    results.append(("Tavily Search", result))

    # Test 2: Context
    result = await test_tavily_context()
    results.append(("Tavily Context", result))

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
        print("\n🎉 All tests passed! Tavily API is working.")
        print("\nConclusion: The issue is with FastMCP, not Tavily.")
    else:
        print("\n⚠️  Some tests failed.")
        print("\nPossible issues:")
        print("1. Tavily API key invalid")
        print("2. Network connectivity issues")
        print("3. Tavily API rate limiting")


if __name__ == "__main__":
    asyncio.run(main())
