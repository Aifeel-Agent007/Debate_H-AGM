"""
Internet Search MCP Server for Debate Agents

This MCP server provides web search capabilities using the Tavily API.
It enables debate agents (panelists and moderator) to:
- Search for information about debate topics
- Get quick answers to specific questions
- Verify facts and claims made during debates
- Retrieve contextual information for RAG applications
"""

import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastmcp import FastMCP
from tavily import AsyncTavilyClient


# Load environment variables from project root .env file
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

# Initialize FastMCP server
mcp = FastMCP("debate-search", dependencies=["tavily-python"])

# Initialize Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError(
        "TAVILY_API_KEY environment variable is not set\n"
        "Please add your Tavily API key to .env file\n"
        "Get your key from https://tavily.com"
    )

tavily = AsyncTavilyClient(api_key=tavily_api_key)


@mcp.tool()
async def search_web(
    query: str,
    max_results: int = 5,
    search_depth: Literal["basic", "advanced"] = "basic",
    include_answer: bool = False,
) -> dict[str, Any]:
    """
    Search the web for information about a topic.

    Use this tool to gather general information about debate topics,
    find supporting evidence for arguments, or explore different perspectives.

    Args:
        query: The search query or topic to search for
        max_results: Maximum number of search results to return (default: 5)
        search_depth: Search depth - "basic" for quick results, "advanced" for comprehensive (default: "basic")
        include_answer: Whether to include an AI-generated answer summarizing the results (default: False)

    Returns:
        A dictionary containing:
        - query: The original search query
        - answer: AI-generated summary (if include_answer=True)
        - results: List of search results with title, url, content, and score
        - images: List of relevant image URLs

    Example:
        search_web("advantages of renewable energy", max_results=3, include_answer=True)
    """
    try:
        response = await tavily.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
            include_images=True,
        )
        return response
    except Exception as e:
        return {
            "error": str(e),
            "query": query,
            "results": [],
        }


@mcp.tool()
async def get_quick_answer(
    question: str,
    search_depth: Literal["basic", "advanced"] = "advanced",
) -> str:
    """
    Get a quick, concise answer to a specific question.

    Use this tool for fact-checking claims made during debates,
    verifying specific details, or getting direct answers to questions.

    Args:
        question: The question to answer
        search_depth: Search depth - "advanced" recommended for accuracy (default: "advanced")

    Returns:
        A concise answer to the question as a string

    Example:
        get_quick_answer("What is the current global temperature increase?")
    """
    try:
        answer = await tavily.qna_search(
            query=question,
            search_depth=search_depth,
        )
        return answer or "No answer found for this question."
    except Exception as e:
        return f"Error getting answer: {str(e)}"


@mcp.tool()
async def get_context(
    query: str,
    max_tokens: int = 4000,
    search_depth: Literal["basic", "advanced"] = "advanced",
) -> str:
    """
    Get comprehensive context about a topic for RAG applications.

    Use this tool to gather detailed background information about debate topics,
    get well-rounded context including multiple perspectives, or prepare
    for in-depth discussion.

    Args:
        query: The topic to get context about
        max_tokens: Maximum number of tokens in the returned context (default: 4000)
        search_depth: Search depth - "advanced" recommended for comprehensive context (default: "advanced")

    Returns:
        A formatted context string suitable for RAG applications

    Example:
        get_context("climate change mitigation strategies", max_tokens=3000)
    """
    try:
        context = await tavily.get_search_context(
            query=query,
            max_tokens=max_tokens,
            search_depth=search_depth,
        )
        return context or "No context found for this query."
    except Exception as e:
        return f"Error getting context: {str(e)}"


@mcp.tool()
async def verify_fact(
    claim: str,
    context: str = "",
) -> dict[str, Any]:
    """
    Verify a factual claim by searching for supporting or contradicting evidence.

    Use this tool to fact-check statements made by other debate participants,
    validate claims with evidence, or check the accuracy of arguments.

    Args:
        claim: The factual claim to verify
        context: Optional context about the debate topic for more relevant results

    Returns:
        A dictionary containing:
        - claim: The original claim
        - answer: A summary addressing the claim's accuracy
        - evidence: Search results with supporting or contradicting information

    Example:
        verify_fact("Solar energy is now cheaper than coal in most countries")
    """
    try:
        # Construct a verification query
        query = f"Is this claim true: {claim}"
        if context:
            query += f" (Context: {context})"

        # Get comprehensive search results
        search_response = await tavily.search(
            query=query,
            max_results=5,
            search_depth="advanced",
            include_answer=True,
        )

        return {
            "claim": claim,
            "answer": search_response.get("answer", "Unable to verify claim"),
            "evidence": search_response.get("results", []),
        }
    except Exception as e:
        return {
            "claim": claim,
            "error": str(e),
            "evidence": [],
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
