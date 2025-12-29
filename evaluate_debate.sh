#!/bin/bash

# Shell script to evaluate a debate file

DEBATE_FILE="${1:-}"
MODE="${2:-all}"

echo "토론 평가 스크립트"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# If no file specified, find the latest debate file
if [ -z "$DEBATE_FILE" ]; then
    DEBATE_DIR="debate"
    if [ ! -d "$DEBATE_DIR" ]; then
        echo "❌ 오류: debate 디렉토리를 찾을 수 없습니다."
        echo "   토론을 먼저 실행하거나 파일 경로를 지정하세요."
        exit 1
    fi
    
    LATEST_FILE=$(ls -t "$DEBATE_DIR"/*.json 2>/dev/null | head -n 1)
    if [ -z "$LATEST_FILE" ]; then
        echo "❌ 오류: 토론 결과 파일을 찾을 수 없습니다."
        exit 1
    fi
    
    DEBATE_FILE="$LATEST_FILE"
    echo "📁 최신 토론 파일 사용: $DEBATE_FILE"
    echo ""
fi

if [ ! -f "$DEBATE_FILE" ]; then
    echo "❌ 오류: 파일을 찾을 수 없습니다: $DEBATE_FILE"
    exit 1
fi

echo "토론 파일: $DEBATE_FILE"
echo "평가 모드: $MODE"
echo ""

# Run evaluation script
uv run python scripts/run_debate_with_evaluation.py "$DEBATE_FILE" "$MODE"

if [ $? -ne 0 ]; then
    echo "❌ 평가 실패"
    exit 1
fi

echo ""
echo "✅ 평가 완료!"

