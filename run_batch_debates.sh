#!/bin/bash

# Shell script to run batch debates from a topic file

TOPIC_FILE="${1:-}"
MODERATOR_URL="${2:-http://localhost:10000}"
DELAY="${3:-5.0}"
START_FROM="${4:-1}"

if [ -z "$TOPIC_FILE" ]; then
    echo "사용법: $0 <topic_file> [moderator_url] [delay] [start_from]"
    echo "예시: $0 topics.txt http://localhost:10000 5.0 1"
    exit 1
fi

echo "일괄 토론 실행 스크립트"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if topic file exists
if [ ! -f "$TOPIC_FILE" ]; then
    echo "❌ 오류: 파일을 찾을 수 없습니다: $TOPIC_FILE"
    exit 1
fi

echo "주제 파일: $TOPIC_FILE"
echo "Moderator URL: $MODERATOR_URL"
echo "주제 간 대기 시간: $DELAY 초"
echo "시작 위치: $START_FROM"
echo ""

# Run batch debates
uv run python src/client/run_batch_debates.py "$TOPIC_FILE" --moderator-url "$MODERATOR_URL" --delay "$DELAY" --start-from "$START_FROM"

if [ $? -ne 0 ]; then
    echo "❌ 일괄 토론 실행 실패"
    exit 1
fi

echo ""
echo "✅ 일괄 토론 완료!"
echo "요약 파일: debate_batch_summary.json"

