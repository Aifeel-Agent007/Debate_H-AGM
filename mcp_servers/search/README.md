# Internet Search MCP Server

A FastMCP server that provides web search capabilities for debate agents using the Tavily API.

## Overview

This MCP server enables panelists and moderators in the debate system to:
- Search for information about debate topics
- Get quick answers to specific questions
- Verify facts and claims made during debates
- Retrieve contextual information for knowledge-grounded responses

## Features

The server provides 4 powerful tools:

### 1. `search_web`
General web search with configurable parameters.

**Use Cases:**
- Gather information about debate topics
- Find supporting evidence for arguments
- Explore different perspectives on an issue

**Parameters:**
- `query` (required): The search query or topic
- `max_results` (optional): Maximum results to return (default: 5)
- `search_depth` (optional): "basic" or "advanced" (default: "basic")
- `include_answer` (optional): Include AI-generated summary (default: false)

**Example:**
```python
search_web("advantages of renewable energy", max_results=3, include_answer=True)
```

### 2. `get_quick_answer`
Get concise answers to specific questions.

**Use Cases:**
- Fact-check claims made during debates
- Verify specific details quickly
- Get direct answers without full search results

**Parameters:**
- `question` (required): The question to answer
- `search_depth` (optional): "basic" or "advanced" (default: "advanced")

**Example:**
```python
get_quick_answer("What is the current global temperature increase?")
```

### 3. `get_context`
Retrieve comprehensive contextual information.

**Use Cases:**
- Gather detailed background on debate topics
- Get well-rounded context with multiple perspectives
- Prepare for in-depth discussion

**Parameters:**
- `query` (required): The topic to get context about
- `max_tokens` (optional): Maximum tokens in response (default: 4000)
- `search_depth` (optional): "basic" or "advanced" (default: "advanced")

**Example:**
```python
get_context("climate change mitigation strategies", max_tokens=3000)
```

### 4. `verify_fact`
Verify factual claims with evidence.

**Use Cases:**
- Fact-check statements from other participants
- Validate claims with supporting evidence
- Check accuracy of arguments

**Parameters:**
- `claim` (required): The factual claim to verify
- `context` (optional): Additional context about the debate topic

**Example:**
```python
verify_fact("Solar energy is now cheaper than coal in most countries")
```

## Setup

### 1. Install Dependencies

The dependencies are already installed in the project via `uv`:

```bash
uv add fastmcp tavily-python
```

### 2. Get Tavily API Key

1. Visit [https://tavily.com](https://tavily.com)
2. Sign up for an account
3. Get your API key from the dashboard

### 3. Configure Environment

Add your Tavily API key to `.env`:

```bash
TAVILY_API_KEY=your_tavily_api_key_here
```

## Running the Server

### Development Mode

Run the server in development mode with auto-reload:

```bash
fastmcp dev mcp/search/server.py
```

### Production Mode

Run the server in production mode:

```bash
fastmcp run mcp/search/server.py
```

### Using with Stdio Transport

For integration with LangGraph agents:

```bash
python mcp/search/server.py
```

## Integration with Debate Agents

### Adding to Panelist Agent

To enable panelists to use the search tools, add the MCP server as a tool provider:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to the search MCP server
server_params = StdioServerParameters(
    command="python",
    args=["mcp/search/server.py"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List available tools
        tools = await session.list_tools()

        # Call a tool
        result = await session.call_tool(
            "search_web",
            arguments={"query": "benefits of solar energy"}
        )
```

### Adding to Moderator Agent

The moderator can use the MCP server to verify facts and gather context:

```python
# Verify a claim made by a panelist
verification = await session.call_tool(
    "verify_fact",
    arguments={
        "claim": "Renewable energy creates more jobs than fossil fuels",
        "context": "debate about energy transition"
    }
)
```

## Testing

### Manual Testing

You can test the server using the FastMCP CLI:

```bash
# Start the server
fastmcp dev mcp/search/server.py

# In another terminal, use the MCP inspector
fastmcp inspect mcp/search/server.py
```

### Testing Individual Tools

```python
# Test search_web
result = await search_web(
    query="climate change statistics",
    max_results=3,
    include_answer=True
)
print(result)

# Test get_quick_answer
answer = await get_quick_answer("What percentage of energy comes from renewables?")
print(answer)

# Test get_context
context = await get_context("renewable energy adoption worldwide")
print(context)

# Test verify_fact
verification = await verify_fact("Electric cars have zero emissions")
print(verification)
```

## Response Formats

### search_web Response
```json
{
  "query": "renewable energy",
  "answer": "AI-generated summary (if requested)",
  "results": [
    {
      "title": "Article title",
      "url": "https://example.com",
      "content": "Relevant content snippet",
      "score": 0.95
    }
  ],
  "images": ["https://example.com/image.jpg"]
}
```

### get_quick_answer Response
```text
"A concise answer to the question as plain text"
```

### get_context Response
```text
"Comprehensive formatted context suitable for RAG applications"
```

### verify_fact Response
```json
{
  "claim": "Original claim",
  "answer": "Summary of verification",
  "evidence": [
    {
      "title": "Supporting article",
      "url": "https://example.com",
      "content": "Evidence snippet",
      "score": 0.92
    }
  ]
}
```

## Error Handling

All tools include error handling and will return structured error responses:

```json
{
  "error": "Error description",
  "query": "Original query",
  "results": []
}
```

## Rate Limits

Tavily API has rate limits based on your plan:
- Free tier: 1,000 requests/month
- Pro tier: Higher limits available

The server will return appropriate error messages if rate limits are exceeded.

## Best Practices

1. **Use appropriate search depth:**
   - Use "basic" for quick searches during debates
   - Use "advanced" for fact-checking and important claims

2. **Optimize max_results:**
   - Use fewer results (3-5) for quick lookups
   - Use more results (5-10) for comprehensive research

3. **Cache results:**
   - Consider caching search results to avoid redundant API calls
   - Store frequently used context for debate topics

4. **Error handling:**
   - Always check for error fields in responses
   - Implement retry logic for transient failures

## Troubleshooting

### "TAVILY_API_KEY environment variable is required"
- Make sure you've added your API key to the `.env` file
- Verify the `.env` file is in the project root
- Check that `python-dotenv` is loading the environment variables

### Rate limit errors
- Check your Tavily API usage in the dashboard
- Consider upgrading your plan if you need more requests
- Implement caching to reduce API calls

### No results returned
- Verify your internet connection
- Check if the query is too specific or too broad
- Try different search depth settings

## License

This MCP server is part of the a2a-agents-debate project.
