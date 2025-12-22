#!/bin/bash
./run_debate.sh 2>&1 | tee debate_output.log
echo ""
echo "토론 결과가 debate_output.log 파일에 저장되었습니다."
