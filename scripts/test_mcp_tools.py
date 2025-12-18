"""Test MCP tools integration."""

import asyncio
from src.shared.mcp_tools import get_search_tools

async def test_mcp_tools():
    """Test if MCP tools are properly loaded."""
    print("Testing MCP tools...")

    # Get tools
    tools = get_search_tools()

    print(f"\n✅ Loaded {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:80]}...")

    # Test search_web_tool
    print("\n" + "="*80)
    print("Testing search_web_tool...")
    print("="*80)

    search_tool = next((t for t in tools if t.name == "search_web_tool"), None)
    if search_tool:
        print(f"✓ Found search_web_tool")
        try:
            result = await search_tool.ainvoke({
                "query": "AI and jobs",
                "max_results": 2,
                "search_depth": "basic"
            })
            print(f"✓ Search completed: {len(result)} characters")
            print(f"  Preview: {result[:200]}...")
        except Exception as e:
            print(f"✗ Search failed: {e}")
    else:
        print("✗ search_web_tool not found!")

    # Test get_context_tool
    print("\n" + "="*80)
    print("Testing get_context_tool...")
    print("="*80)

    context_tool = next((t for t in tools if t.name == "get_context_tool"), None)
    if context_tool:
        print(f"✓ Found get_context_tool")
        try:
            result = await context_tool.ainvoke({
                "query": "AI impact on employment",
                "max_tokens": 500
            })
            print(f"✓ Context retrieved: {len(result)} characters")
            print(f"  Preview: {result[:200]}...")
        except Exception as e:
            print(f"✗ Context retrieval failed: {e}")
    else:
        print("✗ get_context_tool not found!")

    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
