#!/bin/bash

# Start moderator server

echo "Starting Moderator server on port 10000..."
echo "Make sure all panelist servers are running first!"
echo ""

# Use uv run to ensure proper environment (with unbuffered output)
cd "$(dirname "$0")"
uv run python -u -m src.moderator
