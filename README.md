# H-AGM Multi-Agent Debate Platform (Integrated)

## 📋 프로젝트 개요

이 프로젝트는 \*\*H-AGM (Agentic Memory System)\*\*과 **A2A Protocol**을 결합한 다중 에이전트 토론 플랫폼입니다. 4명의 AI 패널리스트(좌/우파, 정치인/학자)와 1명의 AI 사회자가 실시간으로 토론을 진행하며, 각 에이전트는 독립적인 장기 기억(Memory)과 외부 도구(MCP)를 활용하여 논리적이고 사실에 기반한 토론을 수행합니다.

### 핵심 특징

  - **4인의 독립 패널리스트**: 각 패널리스트는 물리적으로 분리된 메모리 시스템을 가집니다.
  - **H-AGM 메모리 아키텍처**: Neo4j(Graph) + Qdrant(Vector)를 결합한 하이브리드 메모리 시스템.
  - **ReAct & MCP 기반 추론**: 패널리스트는 답변 전 스스로 생각하고(ReAct), Tavily 검색 도구(MCP)를 사용해 정보를 검증합니다.
  - **동적 토론 진행**: 사회자는 정해진 라운드 외에도 토론의 품질을 판단하여 조기 종료하거나 연장할 수 있습니다.

-----

## 🏗️ 시스템 아키텍처

```mermaid
graph TD
    Client[User/Client] --> Moderator
    
    subgraph "Moderator Node (Port 10000)"
        Moderator[Social Moderator Agent]
    end

    Moderator <-->|A2A Protocol| P1
    Moderator <-->|A2A Protocol| P2
    Moderator <-->|A2A Protocol| P3
    Moderator <-->|A2A Protocol| P4

    subgraph "Panelist Nodes & Memories"
        P1[우파 정치인 :10001] -->|Uses| M1[Neo4j #1 :7687]
        P2[우파 학자 :10002] -->|Uses| M2[Neo4j #2 :7688]
        P3[좌파 정치인 :10003] -->|Uses| M3[Neo4j #3 :7689]
        P4[좌파 학자 :10004] -->|Uses| M4[Neo4j #4 :7690]
    end
```

-----

## 🔧 사전 준비 및 설치

### 1\. 환경 변수 설정 (.env)

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
# 필수: LLM 및 검색 도구
OPENAI_API_KEY=sk-your-openai-api-key
TAVILY_API_KEY=tvly-your-tavily-api-key

# 선택사항: Neo4j (기본값 사용 시 생략 가능)
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 2\. 의존성 설치

`uv`를 사용하여 프로젝트 의존성을 설치합니다.

```bash
uv sync
```

-----

## 🚀 실행 가이드 (순서 중요)

시스템의 각 구성 요소는 의존성이 있으므로 **반드시 아래 순서대로 실행**해야 합니다.

### 1단계: Neo4j 인스턴스 (4개) 시작

각 패널리스트의 독립적인 메모리를 위해 4개의 Neo4j 컨테이너를 실행합니다.

**Windows PowerShell:**
```powershell
.\start_neo4j_panelists.ps1
```

**Linux/Mac:**
```bash
chmod +x start_neo4j_panelists.sh
./start_neo4j_panelists.sh
```

> **확인**: 실행 후 약 30초 대기. `docker ps`로 포트 7687~7690이 모두 떴는지 확인하세요.

### 2단계: 패널리스트 에이전트 시작

4명의 패널리스트 서버를 구동합니다. 이들은 자동으로 각자의 Neo4j 인스턴스에 연결됩니다.

**Windows PowerShell:**
```powershell
.\start_panelists.ps1
```

**Linux/Mac:**
```bash
chmod +x start_panelists.sh
./start_panelists.sh
```

> **확인**: 각 터미널 창에 "Memory system READY" 및 "server ready" 메시지가 뜰 때까지 대기하세요.

### 3단계: 모더레이터(사회자) 시작

패널리스트가 모두 준비된 후 사회자를 실행합니다.

**Windows PowerShell:**
```powershell
.\start_moderator.ps1
```

**Linux/Mac:**
```bash
chmod +x start_moderator.sh
./start_moderator.sh
```

### 4단계: 토론 클라이언트 실행

토론 주제를 입력하고 프로세스를 시작합니다.

**Windows PowerShell:**
```powershell
.\run_debate.ps1
```

**Linux/Mac:**
```bash
chmod +x run_debate.sh
./run_debate.sh
```

### Neo4j 인스턴스 중지

**Windows PowerShell:**
```powershell
.\stop_neo4j_panelists.ps1
```

**Linux/Mac:**
```bash
chmod +x stop_neo4j_panelists.sh
./stop_neo4j_panelists.sh
```

-----

## 🧠 시스템 상세 명세

### 1\. H-AGM 메모리 시스템 (Memory Layer)

각 패널리스트는 **완전히 격리된 메모리 공간**을 가집니다. 데이터 혼재나 락(Lock) 문제를 방지하기 위해 물리적으로 분리되었습니다.

| 패널리스트 | 포트 | Neo4j 포트 | User ID | Mem0 홈 디렉토리 | 벡터 스토어 경로 |
|:---:|:---:|:---:|:---:|:---|:---|
| **우파 정치인** | 10001 | 7687 | `panelist_right_politician` | `%TEMP%\mem0_home\panelist_right_politician` | `%TEMP%\qdrant_storage\panelist_right_politician` |
| **우파 학자** | 10002 | 7688 | `panelist_right_scholar` | `%TEMP%\mem0_home\panelist_right_scholar` | `%TEMP%\qdrant_storage\panelist_right_scholar` |
| **좌파 정치인** | 10003 | 7689 | `panelist_left_politician` | `%TEMP%\mem0_home\panelist_left_politician` | `%TEMP%\qdrant_storage\panelist_left_politician` |
| **좌파 학자** | 10004 | 7690 | `panelist_left_scholar` | `%TEMP%\mem0_home\panelist_left_scholar` | `%TEMP%\qdrant_storage\panelist_left_scholar` |

> **참고**: Linux/Mac에서는 `%TEMP%` 대신 `/tmp`를 사용합니다.

#### 메모리 저장 방식 (Fallback 저장)

  * **Fallback 저장 방식**: mem0의 엔티티 추출 오류를 방지하기 위해 Neo4j에 직접 Cypher 쿼리로 저장합니다.
  * **저장되는 데이터**:
    * 메모리 내용 (`memory`, `content`, `text` 필드)
    * A-mem 분석 결과: 맥락(`amem_context`), 태그(`amem_tags`), 키워드(`amem_keywords`)
    * 메타데이터: 생성 시간, 사용자 ID 등
  * **검색 방식**: 메모리 내용, 맥락, 태그, 키워드 필드를 모두 검색하여 관련 메모리를 찾습니다.
  * **메모리 검색 타이밍**: 2번째 라운드부터만 과거 메모리를 검색합니다 (첫 번째 라운드에는 저장된 기억이 없음).

  * **검증 방법**: `uv run python test_memory_separation.py` 실행 시 각 메모리가 분리되어 작동함을 확인할 수 있습니다.

### 2\. 사회자 (Moderator) 로직 개선

복잡한 부주제(Subtopic) 방식을 제거하고 **단일 주제 중심의 동적 라운드 시스템**으로 개편되었습니다.

  * **진행 흐름**: `Research` (MCP) → `Round 1~5` → `Finalize`
  * **동적 종료 판단 (Smart Termination)**:
      * 기본 5라운드 진행.
      * **Round 3 이후**부터 매 라운드 종료 시 LLM이 토론 지속 여부(`CONTINUE` or `STOP`)를 판단.
      * 판단 기준: 새로운 관점 제시 여부, 토론 심화 정도, 주장 반복 여부.

### 3\. 패널리스트 (Panelist) 기능 강화

#### A. ReAct 패턴 및 MCP 도구 적용

패널리스트는 답변 생성 시 내부 루프(최대 5회)를 돌며 도구를 사용할지 결정합니다.

  * **사용 도구**:
      * `search_web_tool`: 웹 검색 (Tavily) 🔍
      * `verify_fact_tool`: 사실 검증 ✓
      * `get_context_tool`: 배경 지식 확보 📚
  * **로그**: 도구 사용 시 `🔍 [TOOL] search_web_tool called...`와 같이 실시간 로그가 출력됩니다.

#### B. 응답 길이 및 품질 개선

단답형 답변을 방지하고 실제 토론과 유사한 분량을 생성합니다.

  * **목표 분량**: 약 2분 발언 분량 (600\~800자).
  * **구조**:
    1.  **의견 (Opinion)**: 핵심 주장 (150\~250자)
    2.  **근거 (Reasoning)**: 논리적/사실적 뒷받침 (450\~950자)

#### C. 메모리 활용 전략

  * **메모리 검색 타이밍**: 2번째 라운드부터만 과거 메모리를 검색합니다.
    * Round 1: 저장된 기억이 없으므로 메모리 검색 없음
    * Round 2+: 과거 발언 및 검색 결과를 메모리에서 검색하여 활용
  * **메모리 검색 범위**: 메모리 내용, 키워드, 태그, 맥락 정보를 모두 검색
  * **메모리 활용**: 과거 발언 참고, 상대 진영 반박, 같은 진영 지원 등에 활용

-----

## ⚠️ 문제 해결 (Troubleshooting)

**Q1. Neo4j 연결 실패**

  * Docker 컨테이너 상태를 확인하세요:
    - Windows: `docker ps | findstr neo4j`
    - Linux/Mac: `docker ps | grep neo4j`
  * 4개의 컨테이너가 모두 실행 중이어야 합니다. 하나라도 죽어있다면:
    - Windows: `.\start_neo4j_panelists.ps1`을 다시 실행
    - Linux/Mac: `./start_neo4j_panelists.sh`를 다시 실행

**Q2. 패널리스트가 계속 로딩 중일 때**

  * 메모리 초기화에 시간이 걸릴 수 있습니다. 특히 최초 실행 시 Qdrant 및 Neo4j 데이터 생성에 30초~1분 정도 소요됩니다.

**Q3. 파일 잠금 오류 (WinError 32 또는 "파일을 사용 중")**

  * 각 패널리스트가 독립적인 Mem0 홈 디렉토리와 Qdrant 경로를 사용하도록 설정되어 있습니다.
  * 문제가 계속되면:
    1. 모든 패널리스트 프로세스를 종료
    2. 임시 디렉토리 정리:
       - Windows: `Remove-Item -Recurse -Force "$env:TEMP\mem0_home" -ErrorAction SilentlyContinue`
       - Linux/Mac: `rm -rf /tmp/mem0_home`
    3. 패널리스트를 다시 시작

**Q4. 토론이 3라운드에서 갑자기 끝납니다.**

  * 오류가 아닙니다. 사회자의 **동적 종료 로직**이 토론이 충분하다고 판단(STOP)했기 때문입니다.

**Q5. mem0 엔티티 추출 오류 (`entity_type` 관련 오류)**

  * ✅ **해결됨**: 현재 시스템은 **Fallback 저장 방식**을 사용하여 mem0의 엔티티 추출 기능을 우회합니다.
  * **Fallback 저장 방식**:
    * mem0 라이브러리를 거치지 않고 Neo4j에 직접 Cypher 쿼리로 저장
    * 엔티티 추출 오류 없이 안정적으로 메모리 저장
    * A-mem 분석 결과(키워드, 태그, 맥락)를 모두 보존
  * **장점**:
    * mem0의 엔티티 추출 오류 완전 방지
    * Neo4j 직접 저장으로 빠른 성능
    * 안정적인 메모리 저장 및 검색
  * **참고**: 검색은 mem0의 벡터 검색 기능을 사용하되, 저장은 Fallback 방식으로 처리됩니다.

-----

## 📁 주요 파일 구조

```
.
├── src/
│   ├── shared/
│   │   ├── memory_layer.py      # H-AGM 메모리 코어 (A-mem/Mem0g)
│   │   ├── mcp_tools.py         # Tavily 검색 도구 및 MCP 클라이언트
│   │   └── models.py            # 공통 데이터 모델
│   ├── panelist/
│   │   ├── agent.py             # 패널리스트 로직 (ReAct Loop 포함)
│   │   └── personas.py          # 4인 페르소나 정의
│   ├── moderator/
│   │   ├── agent.py             # 사회자 로직 (동적 라운드 판단)
│   │   └── agent_executor.py    # 실행 및 아티팩트 생성
│   └── client/                  # 테스트 클라이언트
├── start_neo4j_panelists.ps1    # Neo4j 4개 시작 (Windows)
├── start_neo4j_panelists.sh     # Neo4j 4개 시작 (Linux/Mac)
├── stop_neo4j_panelists.ps1     # Neo4j 4개 중지 (Windows)
├── stop_neo4j_panelists.sh      # Neo4j 4개 중지 (Linux/Mac)
├── start_panelists.ps1          # 패널리스트 시작 (Windows)
├── start_panelists.sh           # 패널리스트 시작 (Linux/Mac)
├── start_moderator.ps1          # 모더레이터 시작 (Windows)
├── start_moderator.sh           # 모더레이터 시작 (Linux/Mac)
├── run_debate.ps1               # 토론 클라이언트 실행 (Windows)
├── run_debate.sh                # 토론 클라이언트 실행 (Linux/Mac)
├── initialize_hagm_memories.py  # 메모리 시스템 초기화 테스트
├── test_memory_separation.py    # 메모리 분리 테스트
└── README.md                    # 이 파일
```