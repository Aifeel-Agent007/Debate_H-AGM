# Test Scripts

이 디렉토리에는 프로젝트의 다양한 테스트 스크립트들이 포함되어 있습니다.

## MCP (Model Context Protocol) 테스트

### Core MCP Tests
- **`test_mcp_tools.py`** ✅ 최신
  - MCP search 도구들의 기본 기능 테스트
  - 4개 도구 로딩 확인: search_web_tool, get_quick_answer_tool, get_context_tool, verify_fact_tool
  - 실제 Tavily API 호출 테스트

- **`test_agent_mcp_usage.py`** ✅ 최신
  - 에이전트들이 실제 대화에서 MCP 도구를 사용하는지 테스트
  - Panelist와 Moderator의 MCP 도구 활용도 검증
  - 결과: Moderator는 research phase에서 적극 활용, Panelist는 선택적 사용

### Legacy MCP Tests (참고용)
- `test_mcp_integration.py` - 초기 MCP 통합 테스트
- `test_mcp_simple.py` - 간단한 MCP 연결 테스트
- `test_mcp_live.py` - 실시간 MCP 테스트
- `test_mcp_working.py` - MCP 작동 확인
- `test_mcp_v2.py` - MCP v2 버전 테스트
- `test_tavily_direct.py` - Tavily API 직접 호출 테스트
- `test_tools_direct.py` - 도구 직접 호출 테스트

## 응답 길이 및 품질 테스트

- **`test_panelist_response.py`**
  - Panelist 에이전트의 응답 생성 테스트
  - 응답 형식 및 길이 검증

- **`test_longer_response.py`**
  - 긴 응답 생성 능력 테스트
  - 목표: 6000자 (3분 분량)

- **`test_simple_response.py`**
  - 기본 응답 생성 기능 테스트

- **`test_actual_length.py`**
  - 실제 응답 길이 측정

- **`test_2000_chars.py`**
  - 2000자 기준 응답 테스트 (1분 분량)

## 토론 시스템 테스트

- **`test_subtopic_debate.py`**
  - 부주제 기반 토론 시스템 테스트
  - Subtopic 생성 및 시간 배분 검증
  - 부주제별 토론 진행 테스트

## 토론 평가 관련 스크립트

- **`convert_debate_for_evaluation.py`** ✅ 최신
  - 토론 결과 JSON 파일을 Debate Evaluator가 읽을 수 있는 전사본 형식으로 변환
  - 사용법: `python scripts/convert_debate_for_evaluation.py <debate_json_file> [output_file]`
  - 예시: `python scripts/convert_debate_for_evaluation.py debate/20241226_123456_topic.json transcript.txt`

- **`run_debate_with_evaluation.py`** ✅ 최신
  - 토론 결과 파일을 자동으로 평가하는 통합 스크립트
  - 사용법: `python scripts/run_debate_with_evaluation.py <debate_json_file> [evaluation_mode]`
  - 예시: `python scripts/run_debate_with_evaluation.py debate/20241226_123456_topic.json all`
  - 평가 모드: `dqi`, `aaf`, `dqi-aaf`, `afra`, `all` (기본값: `all`)

## 테스트 실행 방법

### 루트 디렉토리에서 실행
```bash
# scripts 디렉토리로 이동하지 않고 실행
uv run python scripts/test_mcp_tools.py
uv run python scripts/test_agent_mcp_usage.py
uv run python scripts/test_subtopic_debate.py

# 토론 평가
uv run python scripts/run_debate_with_evaluation.py debate/latest.json all
```

### 토론 평가 워크플로우

1. **토론 실행**
   ```bash
   ./run_debate.sh
   # 또는
   .\run_debate.ps1
   ```

2. **토론 결과 확인**
   - 토론 결과는 `debate/` 디렉토리에 JSON 및 텍스트 형식으로 저장됩니다.

3. **토론 평가 실행**
   ```bash
   # 최신 토론 자동 평가
   ./evaluate_debate.sh
   
   # 특정 파일 평가
   ./evaluate_debate.sh "debate/20241226_123456_topic.json" "all"
   ```

4. **평가 결과 확인**
   - 평가 결과는 `debate_results/` 디렉토리에 Markdown 형식으로 저장됩니다.
