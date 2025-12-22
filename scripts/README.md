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

## 테스트 실행 방법

### 루트 디렉토리에서 실행
```bash
# scripts 디렉토리로 이동하지 않고 실행
uv run python scripts/test_mcp_tools.py
uv run python scripts/test_agent_mcp_usage.py
uv run python scripts/test_subtopic_debate.py
```

### scripts 디렉토리에서 실행
```bash
cd scripts
uv run python test_mcp_tools.py
uv run python test_agent_mcp_usage.py
uv run python test_subtopic_debate.py
```

## 주요 테스트 결과

### MCP 도구 통합 (2025-12-02)
✅ **성공**: MCP search 도구들이 정상 작동
- Tavily API 연동 완료
- 4개 도구 모두 로드 및 실행 성공
- Moderator의 research phase에서 적극 활용

### 에이전트 모델 변경 (2025-12-02)
✅ **완료**: Anthropic Claude → OpenAI GPT-4o-mini
- Moderator: `gpt-4o-mini` (temperature: 0.5)
- Panelist: `gpt-4o-mini` (temperature: 0.7)
- 기존 Anthropic 코드는 주석 처리하여 보존

### 부주제 기반 토론 (2025-12-02)
✅ **구현**: Round 기반 → Subtopic 기반으로 전환
- 4-6개 부주제 자동 생성
- 중요도 기반 시간 배분 (총 100분)
- 부주제별 토론 진행 및 전환 로직

## 환경 변수 요구사항

테스트 실행 전 `.env` 파일에 다음 API 키가 필요합니다:

```bash
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

## 참고사항

- 일부 legacy 테스트는 이전 시스템 구조를 기준으로 작성되어 현재는 실행되지 않을 수 있습니다
- 최신 테스트는 ✅ 표시로 구분됩니다
- 테스트 실행 시 MCP 서버가 자동으로 시작됩니다 (별도 실행 불필요)
