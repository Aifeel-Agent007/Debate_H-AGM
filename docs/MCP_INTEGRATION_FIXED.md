# MCP Integration - Direct Tavily Implementation

## Overview

The debate system now uses **direct Tavily API integration** instead of the FastMCP server layer. This change resolves timeout and stability issues while maintaining all the same functionality.

## What Changed

### Previous Architecture (FastMCP - Had Issues)
```
Panelist Agent → LangChain Tools → MCP Client → FastMCP Server → Tavily API
```

**Problems:**
- `BrokenResourceError` and `ClosedResourceError` from FastMCP
- Async resource management issues
- Timeout errors during debates

### Current Architecture (Direct - Working)
```
Panelist Agent → LangChain Tools → Tavily API (Direct)
```

**Benefits:**
- ✅ No connection stability issues
- ✅ Faster response times
- ✅ Simpler architecture
- ✅ Same tool functionality

## Available Tools

All 4 search tools are still available to panelists and moderators:

### 1. `search_web_tool`
Search the web for information about debate topics.

```python
await search_web_tool.ainvoke({
    "query": "renewable energy 2024 statistics",
    "max_results": 5,
    "search_depth": "basic",  # or "advanced"
    "include_answer": False
})
```

### 2. `get_quick_answer_tool`
Get quick, concise answers to specific questions (fact-checking).

```python
await get_quick_answer_tool.ainvoke({
    "question": "What is the current renewable energy capacity globally?",
    "search_depth": "advanced"
})
```

### 3. `get_context_tool`
Get comprehensive context about topics (background research).

```python
await get_context_tool.ainvoke({
    "query": "artificial intelligence economic impact",
    "max_tokens": 4000,
    "search_depth": "advanced"
})
```

### 4. `verify_fact_tool`
Verify factual claims with evidence (fact-checking other panelists).

```python
await verify_fact_tool.ainvoke({
    "claim": "Renewable energy costs have decreased by 50% since 2020",
    "context": "renewable energy economics"
})
```

## How It Works

### Agent Integration

Both panelist and moderator agents automatically have access to these tools:

```python
from src.panelist.agent import PanelistAgent

# Tools are automatically initialized
panelist = PanelistAgent("right_scholar")
print(f"Tools available: {len(panelist.tools)}")  # 4 tools
```

### Tool Usage Logs

When agents use tools, you'll see real-time logs like:

```
================================================================================
🔧 MCP TOOL USAGE - 우파 학자
================================================================================
🔍 Tool: get_context_tool
📝 Arguments: {'query': '2024 renewable energy statistics', 'max_tokens': 4000}

⏳ Executing get_context_tool...

📚 [CONTEXT TOOL] get_context_tool
   Topic: '2024 renewable energy statistics'
   Max tokens: 4000, Depth: advanced
🌐 [TAVILY API] Getting context...
✅ [TAVILY API] Context received - 7339 characters
✅ Result received: 7339 characters
================================================================================
```

### ReAct Pattern

Agents use the ReAct (Reasoning + Acting) pattern:
1. **Think**: Decide if a tool is needed
2. **Act**: Call the tool (one at a time)
3. **Observe**: Receive tool results
4. **Continue**: Either call another tool or generate final response

Maximum 5 iterations to prevent infinite loops.

## Configuration

### Environment Variables

Required in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
TAVILY_API_KEY=tvly-dev-...
```

### Dependencies

Already installed via `pyproject.toml`:
- `tavily-python = "^0.7.13"`
- `langchain-core` (for tool wrappers)

## Testing

### Test Direct Tool Integration
```bash
uv run python -u test_tools_direct.py
```

This tests:
1. Direct tool invocation
2. Panelist agent using tools
3. End-to-end integration

Expected output:
```
✅ Direct Tool Call: PASSED
✅ Panelist with Direct Tools: PASSED
🎉 All tests passed! Direct Tavily integration is working.
```

### Test Full Debate with Tools

1. Start panelists:
```bash
./start_panelists.sh
```

2. Start moderator:
```bash
./start_moderator.sh
```

3. Run debate:
```bash
./run_debate.sh
```

Watch for tool usage logs in the panelist log files:
```bash
tail -f logs/right_scholar.log
```

## When Do Agents Use Tools?

Tools are **optional** - Claude decides autonomously when to use them based on:

- **Topic complexity**: More likely to search for recent statistics or specific data
- **Need for evidence**: When making factual claims
- **Fact-checking**: When responding to other panelists' claims
- **Knowledge gaps**: When the topic is outside training data

For general topics like "인공지능의 발전" (AI development), agents may not use tools.
For specific topics like "2024년 재생 에너지 통계" (2024 renewable energy statistics), tools are more likely.

## Implementation Details

### File: `src/shared/mcp_tools.py`

Main implementation using direct Tavily API:

```python
from tavily import AsyncTavilyClient
from langchain_core.tools import tool

def get_tavily_client() -> AsyncTavilyClient:
    """Get a Tavily client instance."""
    api_key = os.getenv("TAVILY_API_KEY")
    return AsyncTavilyClient(api_key=api_key)

@tool
async def search_web_tool(query: str, ...) -> str:
    """Search the web for information."""
    client = get_tavily_client()
    result = await client.search(query=query, ...)
    return formatted_results
```

No need for MCP client sessions or async context managers - much simpler!

## Troubleshooting

### No tool usage logs
- **Expected behavior**: Not all topics trigger tool usage
- **Solution**: Use topics requiring recent data or statistics

### Tavily API errors
- **Check**: `TAVILY_API_KEY` in `.env`
- **Verify**: API key is valid (test with `test_tavily_direct.py`)
- **Rate limits**: Free tier has usage limits

### Agent timeouts
- **Current timeout**: 180 seconds (moderator A2A client)
- **Tool timeouts**: Usually complete in 2-5 seconds
- **If still timing out**: Check network connectivity or Anthropic API status

## Migration Notes

### What Was Removed
- `mcp_servers/search/server.py` - FastMCP server (not used anymore)
- MCP client session management code
- `stdio_client` and `ClientSession` usage

### What Stayed the Same
- Tool names and signatures
- Agent integration code
- Logging format and verbosity
- ReAct pattern implementation

### Backward Compatibility
- All existing debate code works without changes
- Same 4 tools with same parameters
- Same log output format

## FastMCP Server (Optional)

The FastMCP server at `mcp_servers/search/server.py` is still available if you want to use it with other MCP clients (like Claude Desktop), but the debate agents no longer use it.

To use the FastMCP server separately:
```bash
cd mcp_servers/search
uv run python server.py
```

## References

- **Tavily API Docs**: https://docs.tavily.com/
- **LangChain Tools**: https://python.langchain.com/docs/how_to/custom_tools
- **ReAct Pattern**: https://react-lm.github.io/
