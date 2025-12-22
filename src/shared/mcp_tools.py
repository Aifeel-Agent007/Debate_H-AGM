"""MCP tools integration for debate agents - Version 2 with stable connections.

This version uses a single, long-lived MCP client connection that is shared
across all tool calls, avoiding the resource management issues.
"""

import os
import asyncio
from typing import Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool
from dotenv import load_dotenv

from .utils import setup_logging

# Load environment variables
load_dotenv()

logger = setup_logging(__name__)


class MCPSearchManager:
    """Singleton manager for MCP search client with connection pooling."""

    _instance: Optional['MCPSearchManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize MCP search manager."""
        self.server_params = StdioServerParameters(
            command="python",
            args=["mcp_servers/search/server.py"],
            env={
                **os.environ,
                "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
            },
        )
        self._session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._stdio_context = None
        self._session_context = None

    @classmethod
    async def get_instance(cls) -> 'MCPSearchManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = MCPSearchManager()
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize MCP connection."""
        try:
            logger.info("🔌 Initializing MCP Search connection...")

            # Start stdio client
            self._stdio_context = stdio_client(self.server_params)
            self._read, self._write = await self._stdio_context.__aenter__()

            # Create session
            self._session_context = ClientSession(self._read, self._write)
            self._session = await self._session_context.__aenter__()

            # Initialize session
            await self._session.initialize()

            logger.info("✅ MCP Search connection established")
            print("✅ [MCP MANAGER] Connection established", flush=True)

        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP connection: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool using the persistent connection.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as string
        """
        if not self._session:
            raise RuntimeError("MCP connection not initialized")

        try:
            # Log tool call
            print(f"\n🌐 [MCP SERVER] Calling {tool_name}", flush=True)
            print(f"   📝 Arguments: {arguments}", flush=True)
            logger.info(f"🌐 MCP Server: Calling {tool_name}")
            logger.info(f"   📝 Arguments: {arguments}")

            result = await self._session.call_tool(tool_name, arguments=arguments)

            # Extract text from result
            if hasattr(result, 'content') and result.content:
                text_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        text_parts.append(item.text)
                result_text = "\n".join(text_parts)
            else:
                result_text = str(result)

            print(f"✅ [MCP SERVER] {tool_name} completed", flush=True)
            print(f"   📄 Result length: {len(result_text)} characters", flush=True)
            logger.info(f"✅ MCP Server: {tool_name} completed")
            logger.info(f"   📄 Result preview: {result_text[:150]}...")

            return result_text

        except Exception as e:
            print(f"❌ [MCP SERVER] Error: {e}", flush=True)
            logger.error(f"❌ MCP Server: Error calling {tool_name}: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def close(self):
        """Close MCP connection."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
        logger.info("🔌 MCP connection closed")


# LangChain tool wrappers for MCP functions
@tool
async def search_web_tool(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = False,
) -> str:
    """Search the web for information about a topic.

    Use this tool to gather general information about debate topics,
    find supporting evidence for arguments, or explore different perspectives.

    Args:
        query: The search query or topic to search for
        max_results: Maximum number of search results to return (default: 5)
        search_depth: Search depth - "basic" for quick results, "advanced" for comprehensive (default: "basic")
        include_answer: Whether to include an AI-generated answer summarizing the results (default: False)

    Returns:
        Search results as formatted text
    """
    print(f"\n🔍 [MCP TOOL] search_web_tool", flush=True)
    print(f"   Query: '{query}'", flush=True)
    print(f"   Max results: {max_results}, Depth: {search_depth}", flush=True)
    logger.info(f"🔍 [TOOL] search_web_tool called with query: '{query}'")

    manager = await MCPSearchManager.get_instance()
    result = await manager.call_tool(
        "search_web",
        arguments={
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
        },
    )
    return result


@tool
async def get_quick_answer_tool(
    question: str,
    search_depth: str = "advanced",
) -> str:
    """Get a quick, concise answer to a specific question.

    Use this tool for fact-checking claims made during debates,
    verifying specific details, or getting direct answers to questions.

    Args:
        question: The question to answer
        search_depth: Search depth - "advanced" recommended for accuracy (default: "advanced")

    Returns:
        A concise answer to the question
    """
    print(f"\n❓ [MCP TOOL] get_quick_answer_tool", flush=True)
    print(f"   Question: '{question}'", flush=True)
    print(f"   Search depth: {search_depth}", flush=True)
    logger.info(f"❓ [TOOL] get_quick_answer_tool called with question: '{question}'")

    manager = await MCPSearchManager.get_instance()
    result = await manager.call_tool(
        "get_quick_answer",
        arguments={
            "question": question,
            "search_depth": search_depth,
        },
    )
    return result


@tool
async def get_context_tool(
    query: str,
    max_tokens: int = 4000,
    search_depth: str = "advanced",
) -> str:
    """Get comprehensive context about a topic for RAG applications.

    Use this tool to gather detailed background information about debate topics,
    get well-rounded context including multiple perspectives, or prepare
    for in-depth discussion.

    Args:
        query: The topic to get context about
        max_tokens: Maximum number of tokens in the returned context (default: 4000)
        search_depth: Search depth - "advanced" recommended for comprehensive context (default: "advanced")

    Returns:
        A formatted context string
    """
    print(f"\n📚 [MCP TOOL] get_context_tool", flush=True)
    print(f"   Topic: '{query}'", flush=True)
    print(f"   Max tokens: {max_tokens}, Depth: {search_depth}", flush=True)
    logger.info(f"📚 [TOOL] get_context_tool called for topic: '{query}'")

    manager = await MCPSearchManager.get_instance()
    result = await manager.call_tool(
        "get_context",
        arguments={
            "query": query,
            "max_tokens": max_tokens,
            "search_depth": search_depth,
        },
    )
    return result


@tool
async def verify_fact_tool(
    claim: str,
    context: str = "",
) -> str:
    """Verify a factual claim by searching for supporting or contradicting evidence.

    Use this tool to fact-check statements made by other debate participants,
    validate claims with evidence, or check the accuracy of arguments.

    Args:
        claim: The factual claim to verify
        context: Optional context about the debate topic for more relevant results

    Returns:
        Verification result with evidence
    """
    print(f"\n✓ [MCP TOOL] verify_fact_tool", flush=True)
    print(f"   Claim: '{claim}'", flush=True)
    if context:
        print(f"   Context: '{context[:100]}...'", flush=True)
    logger.info(f"✓ [TOOL] verify_fact_tool called for claim: '{claim}'")

    manager = await MCPSearchManager.get_instance()
    result = await manager.call_tool(
        "verify_fact",
        arguments={
            "claim": claim,
            "context": context,
        },
    )
    return result


def get_search_tools() -> list:
    """Get all MCP search tools for LangGraph agents.

    Returns:
        List of LangChain tools
    """
    return [
        search_web_tool,
        get_quick_answer_tool,
        get_context_tool,
        verify_fact_tool,
    ]
