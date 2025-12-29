"""pytest 공통 픽스처"""

import pytest

from debate_evaluator.models.base import EvaluationMode


@pytest.fixture
def sample_transcript():
    """샘플 토론 스크립트"""
    return """[토론 주제: AI 규제에 대한 찬반 토론]

[찬성 측 - 홍길동]
저는 AI 규제에 찬성합니다. 첫째, AI의 윤리적 사용을 보장해야 합니다.
둘째, 개인정보 보호를 위해 필요합니다. EU의 AI Act가 좋은 사례입니다.

[반대 측 - 김철수]
저는 AI 규제에 반대합니다. 규제는 혁신을 저해합니다.
미국의 AI 산업이 발전한 것은 자유로운 환경 덕분입니다.

[찬성 측 재반박 - 홍길동]
김철수 님의 의견을 존중하지만, 규제와 혁신은 양립 가능합니다.
적절한 가이드라인이 오히려 신뢰를 높여 시장을 확대할 수 있습니다.

[반대 측 재반박 - 김철수]
홍길동 님의 우려를 이해합니다. 하지만 자율 규제가 더 효과적입니다.
산업계의 자발적 윤리 기준 수립을 지지합니다.
"""


@pytest.fixture
def sample_dqi_response():
    """샘플 DQI LLM 응답"""
    return """## 토론 요약

AI 규제의 필요성에 대한 찬반 토론입니다.

## DQI 기준별 평가

### 1. 참여 평등 (Participation Equality)
- **코드**: 1
- **근거**: 양측 모두 발언 기회를 동등하게 가졌습니다.

### 2. 정당화 수준 (Level of Justification)
- **코드**: 2
- **근거**: EU AI Act, 미국 사례 등 구체적 근거를 제시했습니다.

### 3. 정당화 내용 (Content of Justification)
- **코드**: 2
- **근거**: 공익과 산업 발전 모두를 고려했습니다.

### 4. 집단에 대한 존중 (Respect toward Groups)
- **코드**: 2
- **근거**: 상대방을 존중하는 표현을 사용했습니다.

### 5. 요구에 대한 존중 (Respect toward Demands)
- **코드**: 2
- **근거**: "의견을 존중합니다", "우려를 이해합니다" 등 표현 사용.

### 6. 반론에 대한 존중 (Respect toward Counterarguments)
- **코드**: 2
- **근거**: 상대방 주장을 인정하면서 반박했습니다.

### 7. 건설적인 정치 (Constructive Politics)
- **코드**: 1
- **근거**: 타협안 제시보다는 각자 입장 고수.

## 종합 평가

전반적으로 양질의 토론이었습니다.

## 개선점 제안
- 더 구체적인 통계 자료 활용
- 타협점 모색 노력 필요
"""


@pytest.fixture
def evaluation_modes():
    """모든 평가 모드"""
    return list(EvaluationMode)
