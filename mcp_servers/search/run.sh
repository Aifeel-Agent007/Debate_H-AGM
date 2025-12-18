#!/bin/bash

# Quick start script for the Internet Search MCP Server

set -e

# Change to project root directory
cd "$(dirname "$0")/../.."

# Load environment variables from project root .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "Loaded environment variables from .env"
fi

# Check if TAVILY_API_KEY is set
if [ -z "$TAVILY_API_KEY" ]; then
    echo "Error: TAVILY_API_KEY environment variable is not set"
    echo "Please add your Tavily API key to .env file"
    echo "Get your key from https://tavily.com"
    exit 1
fi

# Run the MCP server
echo "Starting Internet Search MCP Server..."
echo "TAVILY_API_KEY is set: ${TAVILY_API_KEY:0:10}..."
echo ""

# Use uv run to ensure dependencies are available
uv run python mcp_servers/search/server.py
