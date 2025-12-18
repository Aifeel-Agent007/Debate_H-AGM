"""
Example usage of the Internet Search MCP Server

This script demonstrates how to connect to and use the search MCP server
from a debate agent or any other client.
"""

import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def example_search_usage():
    """Example of using the search MCP server"""

    # Configure server connection
    server_params = StdioServerParameters(
        command="python",
        args=["mcp/search/server.py"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        },
    )

    print("🔍 Connecting to Internet Search MCP Server...\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List available tools
            tools_result = await session.list_tools()
            print(f"📚 Available tools: {len(tools_result.tools)}")
            for tool in tools_result.tools:
                print(f"   - {tool.name}: {tool.description[:60]}...")
            print()

            # Example 1: Search for information
            print("=" * 60)
            print("Example 1: Searching for information")
            print("=" * 60)
            result = await session.call_tool(
                "search_web",
                arguments={
                    "query": "benefits of renewable energy",
                    "max_results": 3,
                    "include_answer": True,
                },
            )
            print(f"\nQuery: benefits of renewable energy")
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"\nResults:\n{item.text[:500]}...")
            print()

            # Example 2: Get a quick answer
            print("=" * 60)
            print("Example 2: Getting a quick answer")
            print("=" * 60)
            result = await session.call_tool(
                "get_quick_answer",
                arguments={
                    "question": "What percentage of global energy comes from renewables?",
                },
            )
            print(f"\nQuestion: What percentage of global energy comes from renewables?")
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"Answer: {item.text}")
            print()

            # Example 3: Get context for RAG
            print("=" * 60)
            print("Example 3: Getting context for RAG")
            print("=" * 60)
            result = await session.call_tool(
                "get_context",
                arguments={
                    "query": "solar energy efficiency improvements",
                    "max_tokens": 1000,
                },
            )
            print(f"\nTopic: solar energy efficiency improvements")
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"\nContext:\n{item.text[:400]}...")
            print()

            # Example 4: Verify a fact
            print("=" * 60)
            print("Example 4: Verifying a factual claim")
            print("=" * 60)
            result = await session.call_tool(
                "verify_fact",
                arguments={
                    "claim": "Solar panels have become 90% cheaper in the last decade",
                    "context": "debate about renewable energy costs",
                },
            )
            print(f"\nClaim: Solar panels have become 90% cheaper in the last decade")
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"\nVerification:\n{item.text[:400]}...")
            print()

    print("\n✅ Examples completed successfully!")


async def debate_scenario_example():
    """Example of how a debate agent might use the search server"""

    print("\n" + "=" * 60)
    print("Debate Scenario: Using Search During a Debate")
    print("=" * 60 + "\n")

    server_params = StdioServerParameters(
        command="python",
        args=["mcp/search/server.py"],
        env={**os.environ, "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Scenario: Moderator introduces debate topic
            print("🎙️  Moderator: 'Today's debate topic is: Should nuclear energy be part of the clean energy transition?'\n")

            # Panelist 1 searches for information
            print("👤 Panelist 1: Let me search for nuclear energy benefits...")
            result = await session.call_tool(
                "search_web",
                arguments={
                    "query": "nuclear energy advantages clean energy",
                    "max_results": 3,
                },
            )
            print("   ✓ Found supporting information\n")

            # Panelist 2 makes a claim
            print("👤 Panelist 2: 'Nuclear power plants take 20 years to build!'\n")

            # Moderator fact-checks the claim
            print("🎙️  Moderator: Let me verify that claim...")
            result = await session.call_tool(
                "verify_fact",
                arguments={
                    "claim": "Nuclear power plants take 20 years to build",
                },
            )
            print("   ✓ Fact-check complete\n")

            # Panelist 1 needs context for a rebuttal
            print("👤 Panelist 1: Let me get more context about modern nuclear technology...")
            result = await session.call_tool(
                "get_context",
                arguments={
                    "query": "small modular reactors construction time",
                    "max_tokens": 2000,
                },
            )
            print("   ✓ Retrieved comprehensive context\n")

            print("This demonstrates how agents can use the search MCP during live debates!")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  Error: TAVILY_API_KEY not found in environment")
        print("Please add your Tavily API key to the .env file")
        print("Get your key from: https://tavily.com")
        exit(1)

    # Run examples
    print("\n" + "=" * 60)
    print("Internet Search MCP Server - Usage Examples")
    print("=" * 60 + "\n")

    # Run basic examples
    asyncio.run(example_search_usage())

    # Run debate scenario
    asyncio.run(debate_scenario_example())

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")
