#!/bin/bash

# Shell script to run test debate client

echo "Starting debate test client..."
echo "Make sure moderator server is running first!"
echo ""

cd "$(dirname "$0")"
uv run python src/client/test_debate.py

