# MCP Integration Guide

> **⚠️ IMPORTANT UPDATE**: This document describes the original FastMCP-based implementation.
> The system now uses **direct Tavily API integration** instead, which is more stable and faster.
> See [MCP_INTEGRATION_FIXED.md](./MCP_INTEGRATION_FIXED.md) for the current implementation.

## Overview

The debate system integrates with Tavily API for internet search, allowing all agents (panelists and moderator) to access real-time web information during debates.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Debate System                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Panelist 1  │  │  Panelist 2  │  │  Moderator   │      │
│  │              │  │              │  │              │      │
│  │ - search_web │  │ - search_web │  │ - search_web │      │
│  │ - get_answer │  │ - get_answer │  │ - verify_fact│      │
│  │ - verify_fact│  │ - verify_fact│  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │   MCP Search Server  │
                │                      │
                │  - search_web        │
                │  - get_quick_answer  │
                │  - get_context       │
                │  - verify_fact       │
                └──────────┬───────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  Tavily API   │
                   └───────────────┘
```

## Components

### 1. MCP Search Server
**Location:** `mcp/search/server.py`

Provides 4 tools for web search and fact-checking:
- `search_web` - General web search
- `get_quick_answer` - Q&A for specific questions
- `get_context` - RAG-style context generation
- `verify_fact` - Fact verification with evidence

### 2. MCP Tool Wrapper
**Location:** `src/shared/mcp_tools.py`

Converts MCP tools into LangChain tools that can be used by LangGraph agents:
- `MCPSearchClient` - Async client for MCP server
- `search_web_tool` - LangChain wrapper for search_web
- `get_quick_answer_tool` - LangChain wrapper for get_quick_answer
- `get_context_tool` - LangChain wrapper for get_context
- `verify_fact_tool` - LangChain wrapper for verify_fact

### 3. Agent Integration
**Locations:**
- `src/panelist/agent.py`
- `src/moderator/agent.py`

Both agents now:
1. Initialize MCP tools during `__init__`
2. Bind tools to their LLM instances
3. Include tool descriptions in prompts
4. Can invoke tools during response generation

## How It Works

### Panelist Agent Flow

```
1. Panelist receives debate topic
   ↓
2. Panelist LLM decides if it needs information
   ↓
3. If yes: Call search_web_tool or verify_fact_tool
   ↓
4. MCP client forwards request to MCP server
   ↓
5. MCP server calls Tavily API
   ↓
6. Results return through chain
   ↓
7. Panelist uses information in response
```

### Example: Panelist Using Tools

```python
Topic: "Should nuclear energy be part of clean energy transition?"

Panelist (thinking):
- I need current information about nuclear energy
- Let me search for recent developments

Panelist → search_web_tool("nuclear energy advantages 2024")
         → Returns: Recent articles about SMRs, safety improvements

Panelist: "Based on recent developments in Small Modular Reactors (SMRs),
          nuclear energy can play a crucial role..."
```

### Example: Moderator Fact-Checking

```python
Panelist A: "Nuclear plants take 20 years to build"

Moderator (thinking):
- This claim needs verification
- Let me fact-check it

Moderator → verify_fact_tool("Nuclear plants take 20 years to build")
          → Returns: Evidence showing 5-10 years for modern plants

Moderator: Decides whether to challenge the claim or move on
```

## Tool Usage Patterns

### For Panelists

**When to use `search_web_tool`:**
- Initial research on debate topic
- Finding supporting evidence
- Exploring different perspectives

**When to use `get_quick_answer_tool`:**
- Checking specific statistics
- Verifying dates or numbers
- Quick fact lookups

**When to use `get_context_tool`:**
- Deep research on complex topics
- Understanding background information
- Preparing comprehensive arguments

**When to use `verify_fact_tool`:**
- Checking opponent's claims
- Validating your own statements
- Ensuring accuracy

### For Moderator

**When to use tools:**
- Fact-checking dubious claims
- Understanding technical topics
- Ensuring debate accuracy
- Providing context when needed

## Configuration

### Environment Variables

Required in `.env`:
```bash
# Anthropic API for Claude
ANTHROPIC_API_KEY=your_anthropic_key

# Tavily API for web search
TAVILY_API_KEY=your_tavily_key
```

### Tool Binding

Tools are automatically bound to LLM instances:

```python
# In PanelistAgent.__init__
self.tools = get_search_tools()

# In _generate_response
llm_with_tools = self.llm.bind_tools(self.tools)
response = llm_with_tools.invoke(prompt)
```

## Prompts

### Panelist Prompt (with tools)

```
당신은 다음 도구들을 사용할 수 있습니다:
- search_web_tool: 토론 주제에 대한 정보 검색
- get_quick_answer_tool: 특정 질문에 대한 빠른 답변
- get_context_tool: 주제에 대한 종합적인 배경 정보
- verify_fact_tool: 다른 패널리스트의 주장이나 팩트 검증

필요하다면 도구를 사용하여 정보를 수집하고,
그 정보를 바탕으로 의견을 제시하세요.
```

### Moderator Prompt (with tools)

```
당신은 다음 도구들을 사용할 수 있습니다 (필요시):
- verify_fact_tool: 패널리스트의 주장이 사실인지 검증
- search_web_tool: 토론 주제에 대한 추가 정보 검색
```

## Implementation Details

### Async Context Management

The MCP client uses async context managers for proper resource management:

```python
async with MCPSearchClient() as client:
    result = await client.call_tool("search_web", {"query": "..."})
```

### Error Handling

All tool calls include error handling:

```python
try:
    result = await client.call_tool(tool_name, arguments)
    return result
except Exception as e:
    logger.error(f"Error calling MCP tool: {e}")
    return f"Error: {str(e)}"
```

### Result Formatting

MCP results are formatted as strings for easy consumption by LLMs:

```python
# Raw MCP result
result = {
    "query": "renewable energy",
    "results": [{"title": "...", "content": "..."}],
    "answer": "..."
}

# Formatted for LLM
"Search Results:
Title: ...
Content: ...

Summary: ..."
```

## Testing

### Manual Testing

1. Start the MCP server:
```bash
python mcp/search/server.py
```

2. Test tool calls:
```python
from src.shared.mcp_tools import get_mcp_client

async with get_mcp_client() as client:
    result = await client.call_tool(
        "search_web",
        {"query": "test query", "max_results": 3}
    )
    print(result)
```

3. Run debate with tools:
```bash
./run_debate.sh "Should AI be regulated?"
```

### Integration Testing

The agents will automatically use tools when appropriate based on:
- Prompt instructions
- Debate context
- Information needs
- Claude's tool use capabilities

## Troubleshooting

### Tools Not Available

**Problem:** Agents can't access MCP tools

**Solution:**
1. Check TAVILY_API_KEY is set in .env
2. Verify MCP server is running
3. Check logs for initialization errors

### Tool Calls Failing

**Problem:** Tool calls return errors

**Solution:**
1. Check MCP server logs: `tail -f logs/*.log`
2. Verify Tavily API key is valid
3. Check internet connectivity
4. Review rate limits on Tavily dashboard

### Agents Not Using Tools

**Problem:** Agents generate responses without using tools

**Solution:**
1. This is expected - tools are optional
2. Agents use tools only when needed
3. Claude decides autonomously when to use tools
4. Check prompt includes tool descriptions

## Best Practices

### For Development

1. **Always initialize MCP client in async context**
   ```python
   async with get_mcp_client() as client:
       # Use client here
   ```

2. **Handle tool errors gracefully**
   - Don't let tool failures stop debate
   - Provide fallback responses
   - Log errors for debugging

3. **Test with real debates**
   - Use topics that benefit from research
   - Monitor when tools are actually used
   - Adjust prompts based on usage patterns

### For Deployment

1. **Set proper timeouts**
   - MCP calls can take 5-10 seconds
   - Adjust httpx client timeout accordingly

2. **Monitor API usage**
   - Tavily has rate limits
   - Track tool call frequency
   - Implement caching if needed

3. **Log tool usage**
   - Track which tools are used
   - Monitor success/failure rates
   - Analyze usage patterns

## Future Enhancements

### Planned Features

1. **Tool usage analytics**
   - Track frequency of each tool
   - Measure impact on debate quality
   - Optimize based on data

2. **Caching layer**
   - Cache common searches
   - Reduce API calls
   - Improve response time

3. **Additional MCP servers**
   - Academic paper search
   - Expert database
   - Fact-checking database

4. **Tool orchestration**
   - Combine multiple tool results
   - Chain tool calls
   - Smart tool selection

## References

- [MCP Search Server README](../mcp/search/README.md)
- [MCP Search Quickstart](../mcp/search/QUICKSTART.md)
- [FastMCP Documentation](https://gofastmcp.com)
- [Tavily API Documentation](https://docs.tavily.com)
- [LangChain Tools](https://python.langchain.com/docs/modules/tools/)
