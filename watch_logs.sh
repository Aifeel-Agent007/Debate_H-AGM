#!/bin/bash

# Watch all panelist logs in real-time

echo "==================================================================="
echo "Watching all panelist logs in real-time"
echo "==================================================================="
echo "Press Ctrl+C to stop"
echo ""

# Use tail -f to follow all log files simultaneously
tail -f logs/right_politician.log logs/right_scholar.log logs/left_politician.log logs/left_scholar.log 2>/dev/null | grep --line-buffered -E "TOOL|TAVILY|MCP|Tool:|Arguments:|Executing|completed|Result received"
