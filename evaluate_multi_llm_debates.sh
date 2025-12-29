#!/bin/bash

# Shell script to evaluate all debates from multiple LLMs

DEBATE_DIR="${1:-debate}"
EVAL_LLM_PROVIDERS="${2:-gpt grok gemini claude qwen}"
DEBATE_LLM_PROVIDERS="${3:-}"
EVALUATION_MODE="${4:-all}"
OUTPUT_DIR="${5:-debate_results}"
DELAY="${6:-2.0}"

echo "다중 LLM 토론 평가 스크립트"
echo ""

# Change to script directory
cd "$(dirname "$0")"

echo "토론 디렉토리: $DEBATE_DIR"
echo "평가 LLM: $EVAL_LLM_PROVIDERS"
if [ -n "$DEBATE_LLM_PROVIDERS" ]; then
    echo "토론 LLM: $DEBATE_LLM_PROVIDERS"
else
    echo "토론 LLM: 자동 감지 (모든 LLM)"
fi
echo "평가 모드: $EVALUATION_MODE"
echo "출력 디렉토리: $OUTPUT_DIR"
echo "평가 간 대기 시간: $DELAY 초"
echo ""

# Build arguments
ARGS=(
    "--debate-dir" "$DEBATE_DIR"
    "--evaluation-mode" "$EVALUATION_MODE"
    "--output-dir" "$OUTPUT_DIR"
    "--delay" "$DELAY"
)

if [ -n "$EVAL_LLM_PROVIDERS" ]; then
    ARGS+=("--eval-llm-providers")
    ARGS+=($EVAL_LLM_PROVIDERS)
fi

if [ -n "$DEBATE_LLM_PROVIDERS" ]; then
    ARGS+=("--debate-llm-providers")
    ARGS+=($DEBATE_LLM_PROVIDERS)
fi

# Run evaluation
uv run python scripts/run_multi_llm_evaluation.py "${ARGS[@]}"

if [ $? -ne 0 ]; then
    echo "❌ 평가 실패"
    exit 1
fi

echo ""
echo "✅ 다중 LLM 평가 완료!"
echo "전체 요약: $OUTPUT_DIR/evaluation_multi_llm_summary.json"
echo "평가 결과: $OUTPUT_DIR/<debate_llm>/<eval_llm>/ 디렉토리"

