#!/bin/bash

# Shell script to run debates with all 5 LLMs

TOPIC_FILE="${1:-topics.txt}"
LLM_PROVIDERS="${2:-gpt grok gemini claude qwen}"
MODERATOR_URL="${3:-http://localhost:10000}"
DELAY="${4:-5.0}"
DELAY_LLMS="${5:-10.0}"
START_FROM_LLM="${6:-1}"
START_FROM_TOPIC="${7:-1}"

echo "다중 LLM 토론 실행 스크립트"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if topic file exists
if [ ! -f "$TOPIC_FILE" ]; then
    echo "❌ 오류: 파일을 찾을 수 없습니다: $TOPIC_FILE"
    exit 1
fi

echo "주제 파일: $TOPIC_FILE"
echo "사용할 LLM: $LLM_PROVIDERS"
echo "Moderator URL: $MODERATOR_URL"
echo "주제 간 대기 시간: $DELAY 초"
echo "LLM 간 대기 시간: $DELAY_LLMS 초"
echo "시작 LLM: $START_FROM_LLM"
echo "시작 주제: $START_FROM_TOPIC"
echo ""

# Run multi-LLM debates
uv run python src/client/run_multi_llm_debates.py "$TOPIC_FILE" --llm-providers $LLM_PROVIDERS --moderator-url "$MODERATOR_URL" --delay "$DELAY" --delay-llms "$DELAY_LLMS" --start-from-llm "$START_FROM_LLM" --start-from-topic "$START_FROM_TOPIC"

if [ $? -ne 0 ]; then
    echo "❌ 다중 LLM 토론 실행 실패"
    exit 1
fi

echo ""
echo "✅ 다중 LLM 토론 완료!"
echo "전체 요약: debate_multi_llm_summary.json"
echo "LLM별 요약: debate_batch_summary_<llm>.json"
echo "토론 결과: debate/<llm>/ 디렉토리"

