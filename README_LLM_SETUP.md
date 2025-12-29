# Multi-LLM 설정 가이드

이 프로젝트는 5개의 LLM 제공자(Grok, GPT, Gemini, Claude, Qwen)를 지원합니다.

## 환경 변수 설정

### 토론 시스템 LLM 설정

`.env` 파일에 다음 환경 변수를 추가하세요:

```env
# 기본 LLM 제공자 (모든 에이전트에 적용)
DEBATE_LLM_PROVIDER=gpt  # gpt, grok, gemini, claude, qwen

# 패널리스트별 LLM 설정 (선택사항, 기본값은 DEBATE_LLM_PROVIDER 사용)
PANELIST_LLM_PROVIDER=gpt
PANELIST_LLM_MODEL=gpt-4o-mini
PANELIST_LLM_TEMPERATURE=0.7

# 사회자 LLM 설정 (선택사항)
MODERATOR_LLM_PROVIDER=gpt
MODERATOR_LLM_MODEL=gpt-4o-mini
MODERATOR_LLM_TEMPERATURE=0.5

# 메모리 시스템 LLM 설정 (선택사항, 기본값: gpt-4o-mini)
MEMORY_LLM_MODEL=gpt-4o-mini
```

### 평가 시스템 LLM 설정

```env
# 평가 시스템 LLM 제공자
EVAL_LLM_PROVIDER=gpt  # gpt, grok, gemini, claude, qwen
EVAL_LLM_MODEL=gpt-4o
EVAL_LLM_TEMPERATURE=0.3
EVAL_LLM_MAX_TOKENS=4096
EVAL_LLM_TIMEOUT=120.0
```

### 각 LLM별 API 키 설정

```env
# OpenAI (GPT)
OPENAI_API_KEY=sk-your-openai-api-key

# Grok (via Groq)
GROQ_API_KEY=gsk-your-groq-api-key

# Google (Gemini)
GOOGLE_API_KEY=your-google-api-key

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# Alibaba Cloud (Qwen via DashScope)
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
```

## 지원하는 LLM 제공자

### 1. GPT (OpenAI)
- **기본 모델**: `gpt-4o-mini`
- **API 키**: `OPENAI_API_KEY`
- **사용 가능한 모델**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`

### 2. Grok (via Groq)
- **기본 모델**: `mixtral-8x7b-32768`
- **API 키**: `GROQ_API_KEY`
- **사용 가능한 모델**: `mixtral-8x7b-32768`, `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`

### 3. Gemini (Google)
- **기본 모델**: `gemini-pro`
- **API 키**: `GOOGLE_API_KEY`
- **사용 가능한 모델**: `gemini-pro`, `gemini-pro-vision`, `gemini-1.5-pro`

### 4. Claude (Anthropic)
- **기본 모델**: `claude-3-5-sonnet-20241022`
- **API 키**: `ANTHROPIC_API_KEY`
- **사용 가능한 모델**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229`

### 5. Qwen (Alibaba Cloud DashScope)
- **기본 모델**: `qwen-turbo`
- **API 키**: `DASHSCOPE_API_KEY`
- **사용 가능한 모델**: `qwen-turbo`, `qwen-plus`, `qwen-max`

## 사용 예시

### 예시 1: 모든 에이전트를 GPT로 설정
```env
DEBATE_LLM_PROVIDER=gpt
OPENAI_API_KEY=sk-xxx
```

### 예시 2: 패널리스트는 Claude, 사회자는 GPT로 설정
```env
PANELIST_LLM_PROVIDER=claude
MODERATOR_LLM_PROVIDER=gpt
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
```

### 예시 3: 평가 시스템을 Grok으로 설정
```env
EVAL_LLM_PROVIDER=grok
GROQ_API_KEY=gsk-xxx
```

### 예시 4: 각 패널리스트를 다른 LLM으로 설정
각 패널리스트는 독립적인 프로세스이므로, 환경 변수를 다르게 설정하여 실행할 수 있습니다:

```bash
# 우파 정치인 - GPT
PANELIST_LLM_PROVIDER=gpt OPENAI_API_KEY=sk-xxx uv run python -m src.panelist --persona right_politician --port 10001

# 우파 학자 - Claude
PANELIST_LLM_PROVIDER=claude ANTHROPIC_API_KEY=sk-ant-xxx uv run python -m src.panelist --persona right_scholar --port 10002

# 좌파 정치인 - Gemini
PANELIST_LLM_PROVIDER=gemini GOOGLE_API_KEY=xxx uv run python -m src.panelist --persona left_politician --port 10003

# 좌파 학자 - Qwen
PANELIST_LLM_PROVIDER=qwen DASHSCOPE_API_KEY=sk-xxx uv run python -m src.panelist --persona left_scholar --port 10004
```

## 평가 시스템에서 여러 LLM 사용

평가 시스템은 각 평가 방법론별로 다른 LLM을 사용할 수 있습니다:

```bash
# GPT로 평가
EVAL_LLM_PROVIDER=gpt uv run debate-eval transcript.txt -m dqi

# Claude로 평가
EVAL_LLM_PROVIDER=claude uv run debate-eval transcript.txt -m aaf

# Grok으로 평가
EVAL_LLM_PROVIDER=grok uv run debate-eval transcript.txt -m afra
```

## 주의사항

1. **API 키 보안**: `.env` 파일을 `.gitignore`에 추가하여 API 키가 커밋되지 않도록 하세요.

2. **모델 호환성**: 일부 모델은 특정 기능(예: 함수 호출, 스트리밍)을 지원하지 않을 수 있습니다.

3. **비용**: 각 LLM 제공자의 가격 정책이 다르므로, 사용량에 주의하세요.

4. **메모리 시스템**: 메모리 분석은 기본적으로 GPT를 사용합니다. 다른 LLM을 사용하려면 `MEMORY_LLM_MODEL` 환경 변수를 설정하세요.

