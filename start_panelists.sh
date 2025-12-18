#!/bin/bash

# Shell script to start all panelist servers in background

echo "Starting panelist servers..."
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# 각 패널리스트마다 다른 Mem0 홈 디렉토리 설정 (마이그레이션 파일 잠금 방지)
TEMP_DIR="${TMPDIR:-/tmp}"
MEM0_HOME1="${TEMP_DIR}/mem0_home/panelist_right_politician"
MEM0_HOME2="${TEMP_DIR}/mem0_home/panelist_right_scholar"
MEM0_HOME3="${TEMP_DIR}/mem0_home/panelist_left_politician"
MEM0_HOME4="${TEMP_DIR}/mem0_home/panelist_left_scholar"

# 디렉토리 생성
mkdir -p "$MEM0_HOME1"
mkdir -p "$MEM0_HOME2"
mkdir -p "$MEM0_HOME3"
mkdir -p "$MEM0_HOME4"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start right_politician
echo "Starting Right Politician on port 10001..."
echo "   Mem0 home: $MEM0_HOME1"
gnome-terminal -- bash -c "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME1'; uv run python -u -m src.panelist --persona right_politician --port 10001; exec bash" 2>/dev/null || \
xterm -e "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME1'; uv run python -u -m src.panelist --persona right_politician --port 10001; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME1'; uv run python -u -m src.panelist --persona right_politician --port 10001\"" 2>/dev/null || \
(cd "$SCRIPT_DIR" && export HOME="$MEM0_HOME1" && uv run python -u -m src.panelist --persona right_politician --port 10001 &)

# Wait longer to avoid file locking issues
echo "Waiting 5 seconds before starting next panelist..."
sleep 5

# Start right_scholar
echo "Starting Right Scholar on port 10002..."
echo "   Mem0 home: $MEM0_HOME2"
gnome-terminal -- bash -c "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME2'; uv run python -u -m src.panelist --persona right_scholar --port 10002; exec bash" 2>/dev/null || \
xterm -e "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME2'; uv run python -u -m src.panelist --persona right_scholar --port 10002; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME2'; uv run python -u -m src.panelist --persona right_scholar --port 10002\"" 2>/dev/null || \
(cd "$SCRIPT_DIR" && export HOME="$MEM0_HOME2" && uv run python -u -m src.panelist --persona right_scholar --port 10002 &)

# Wait longer to avoid file locking issues
echo "Waiting 5 seconds before starting next panelist..."
sleep 5

# Start left_politician
echo "Starting Left Politician on port 10003..."
echo "   Mem0 home: $MEM0_HOME3"
gnome-terminal -- bash -c "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME3'; uv run python -u -m src.panelist --persona left_politician --port 10003; exec bash" 2>/dev/null || \
xterm -e "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME3'; uv run python -u -m src.panelist --persona left_politician --port 10003; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME3'; uv run python -u -m src.panelist --persona left_politician --port 10003\"" 2>/dev/null || \
(cd "$SCRIPT_DIR" && export HOME="$MEM0_HOME3" && uv run python -u -m src.panelist --persona left_politician --port 10003 &)

# Wait longer to avoid file locking issues
echo "Waiting 5 seconds before starting next panelist..."
sleep 5

# Start left_scholar
echo "Starting Left Scholar on port 10004..."
echo "   Mem0 home: $MEM0_HOME4"
gnome-terminal -- bash -c "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME4'; uv run python -u -m src.panelist --persona left_scholar --port 10004; exec bash" 2>/dev/null || \
xterm -e "cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME4'; uv run python -u -m src.panelist --persona left_scholar --port 10004; exec bash" 2>/dev/null || \
osascript -e "tell app \"Terminal\" to do script \"cd '$SCRIPT_DIR'; export HOME='$MEM0_HOME4'; uv run python -u -m src.panelist --persona left_scholar --port 10004\"" 2>/dev/null || \
(cd "$SCRIPT_DIR" && export HOME="$MEM0_HOME4" && uv run python -u -m src.panelist --persona left_scholar --port 10004 &)

echo ""
echo "All panelist servers are starting in separate windows."
echo "Wait for all servers to show 'ready' messages before starting the moderator."
echo ""
echo "To start moderator, run:"
echo "  ./start_moderator.sh"
echo ""

