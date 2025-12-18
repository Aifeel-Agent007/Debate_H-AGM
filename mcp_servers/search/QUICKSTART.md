# Internet Search MCP - Quick Start

## Setup (5 minutes)

### 1. Get API Key
Visit [tavily.com](https://tavily.com) and sign up to get your API key.

### 2. Configure
Add to your `.env` file in project root:
```bash
TAVILY_API_KEY=tvly-your_key_here
```

### 3. Test
```bash
# Quick test
fastmcp dev mcp/search/server.py

# Or run examples
python mcp/search/example_usage.py
```

## Available Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `search_web` | General web search | Gather information about topics |
| `get_quick_answer` | Q&A style search | Fact-check specific claims |
| `get_context` | RAG-style context | Get comprehensive background |
| `verify_fact` | Fact verification | Check accuracy of statements |

## Quick Usage Examples

### Search for Information
```python
search_web(
    query="renewable energy benefits",
    max_results=5,
    include_answer=True
)
```

### Fact-Check a Claim
```python
verify_fact(
    claim="Solar panels last 25-30 years",
    context="debate about renewable energy"
)
```

### Get Quick Answer
```python
get_quick_answer(
    question="What is the efficiency of modern solar panels?"
)
```

### Get Comprehensive Context
```python
get_context(
    query="climate change mitigation strategies",
    max_tokens=4000
)
```

## Integration with Debate Agents

Add this to your agent's tool configuration:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["mcp/search/server.py"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # Use the tools
        result = await session.call_tool(
            "search_web",
            arguments={"query": "your search query"}
        )
```

## Troubleshooting

**Problem:** "TAVILY_API_KEY environment variable is required"
**Solution:** Add your API key to `.env` file

**Problem:** Rate limit errors
**Solution:** Check your Tavily dashboard for usage limits

**Problem:** No results returned
**Solution:** Try different search_depth: "basic" vs "advanced"

## More Information

- Full documentation: [README.md](README.md)
- Examples: [example_usage.py](example_usage.py)
- Tavily docs: https://docs.tavily.com
- FastMCP docs: https://gofastmcp.com
