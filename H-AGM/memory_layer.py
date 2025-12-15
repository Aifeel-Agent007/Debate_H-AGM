import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Literal, Any, Union, Tuple
from abc import ABC, abstractmethod

# ------------------------------------------------------------------
# [핵심] Mem0 라이브러리 (기존 Retriever들을 대체함)
# ------------------------------------------------------------------
from mem0 import Memory

# LLM 관련 라이브러리 (A-mem 분석용)
from litellm import completion
import requests

# ==============================================================================
# 1. LLM Controller Classes (기존 A-mem 코드 유지)
#    : A-mem의 지능형 분석(Context/Tag 추출)을 위해 필요합니다.
# ==============================================================================

class BaseLLMController(ABC):
    @abstractmethod
    def get_completion(self, prompt: str) -> str:
        pass

class OpenAIController(BaseLLMController):
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        try:
            from openai import OpenAI
            self.model = model
            if api_key is None:
                api_key = os.getenv('OPENAI_API_KEY')
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            pass # openai 라이브러리가 없어도 실행되도록 (Mem0가 처리 가능)
    
    def get_completion(self, prompt: str, response_format: dict, temperature: float = 0.7) -> str:
        # OpenAI 클라이언트가 없으면 에러 처리
        if not hasattr(self, 'client'):
            raise ImportError("OpenAI client not initialized. pip install openai")
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You must respond with a JSON object."},
                {"role": "user", "content": prompt}
            ],
            response_format=response_format,
            temperature=temperature,
        )
        return response.choices[0].message.content

class LiteLLMController(BaseLLMController):
    def __init__(self, model: str, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key or "EMPTY"

    def get_completion(self, prompt: str, response_format: dict, temperature: float = 0.7) -> str:
        try:
            completion_args = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": response_format,
                "temperature": temperature
            }
            if self.api_base: completion_args["api_base"] = self.api_base
            if self.api_key: completion_args["api_key"] = self.api_key
            
            response = completion(**completion_args)
            return response.choices[0].message.content
        except Exception as e:
            print(f"LiteLLM Error: {e}")
            return "{}"

class LLMController:
    """LLM 컨트롤러 통합 클래스"""
    def __init__(self, backend: str = "openai", model: str = "gpt-4o", api_key: str = None, **kwargs):
        # 복잡성을 줄이기 위해 OpenAI를 기본으로, 나머지는 필요시 확장
        if backend == "openai":
            self.llm = OpenAIController(model, api_key)
        else:
            # 기본값 (Ollama 등 사용 시 수정 가능)
            self.llm = OpenAIController(model, api_key)

# ==============================================================================
# 2. MemoryNote Class (기존 A-mem 코드 유지)
#    : 텍스트를 분석해서 메타데이터(태그, 문맥)를 만드는 역할
# ==============================================================================

class MemoryNote:
    def __init__(self, content: str, llm_controller: LLMController = None, timestamp: str = None, **kwargs):
        self.content = content
        self.id = str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.keywords = []
        self.tags = []
        self.context = "General"

        # LLM으로 내용 분석 시도
        if llm_controller:
            try:
                analysis = self.analyze_content(content, llm_controller)
                self.keywords = analysis.get("keywords", [])
                self.tags = analysis.get("tags", [])
                self.context = analysis.get("context", "General")
            except Exception as e:
                print(f"⚠️ 분석 건너뜀: {e}")

    @staticmethod
    def analyze_content(content: str, llm_controller: LLMController) -> Dict:
        """LLM에게 분석을 요청하는 프롬프트"""
        prompt = f"""
        Analyze content and return JSON:
        {{
            "keywords": ["keyword1", "keyword2"],
            "context": "summary sentence",
            "tags": ["tag1", "tag2"]
        }}
        Content: {content}
        """
        # 간단한 스키마 정의
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "analysis",
                "schema": {
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "context": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["keywords", "context", "tags"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
        response_str = llm_controller.llm.get_completion(prompt, response_format=schema)
        return json.loads(response_str)

# ==============================================================================
# 3. AgenticMemorySystem (New! Mem0g 통합 버전)
#    : Neo4j와 연결되어 그래프 저장을 담당하는 새로운 클래스
# ==============================================================================

class AgenticMemorySystem:
    def __init__(self, 
                 user_id="default_user",
                 # Neo4j 접속 정보 (Docker 설정과 일치해야 함)
                 neo4j_url="bolt://localhost:7687", 
                 neo4j_user="neo4j", 
                 neo4j_pass="password",
                 **kwargs):
        
        self.user_id = user_id
        
        # A-mem 분석용 두뇌
        self.llm_controller = LLMController(model="gpt-4o-mini", **kwargs)

        # Mem0g 설정 (Graph Store = Neo4j)
        config = {
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": neo4j_url,
                    "username": neo4j_user,
                    "password": neo4j_pass
                }
            },
            "version": "v1.1"
        }
        
        print(f"🔌 [System] Neo4j({neo4j_url}) 연결 시도 중...")
        try:
            self.m = Memory.from_config(config)
            print("✅ [System] Neo4j 연결 성공! (Mem0g Activated)")
        except Exception as e:
            print(f"❌ [System] 연결 실패: {e}")
            print("   -> Docker 실행 여부와 비밀번호를 확인해주세요.")

    def add_note(self, content: str, time: str = None, **kwargs) -> str:
        """기억 저장: A-mem 분석 -> Mem0g(Neo4j) 저장"""
        
        # 1. A-mem 분석
        print("\n🧠 [A-mem] 내용 분석 중...")
        # 분석 실패 시 에러 방지 처리
        try:
            note = MemoryNote(content, self.llm_controller, timestamp=time)
        except Exception as e:
            print(f"⚠️ 분석 오류 (기본값 사용): {e}")
            note = type('obj', (object,), {
                'context': '', 'tags': [], 'keywords': [], 
                'timestamp': str(datetime.now())
            })
            
        print(f"   -> 맥락: {note.context}")
        print(f"   -> 태그: {note.tags}")

        # 2. Mem0g 저장
        try:
            result = self.m.add(
                content, 
                user_id=self.user_id, 
                metadata={
                    "amem_context": note.context,
                    "amem_tags": note.tags,
                    "amem_keywords": note.keywords,
                    "created_at": note.timestamp
                }
            )
        except Exception as e:
            print(f"❌ Mem0 저장 중 에러 발생: {e}")
            return "save_error"
        
        # [수정된 부분] 리스트가 비어있지 않은지 확인!
        if result and 'results' in result and len(result['results']) > 0:
            saved_id = result['results'][0]['id']
            print(f"💾 [DB] 저장 완료 (ID: {saved_id})")
            return saved_id
        
        # 저장된 결과가 없는 경우 (중복 등)
        print(f"⚠️ [DB] 저장 결과 없음 (건너뜀). Result: {result}")
        return "skipped"

    def find_related_memories(self, query: str, k: int = 5) -> Tuple[str, List[str]]:
        """검색: Mem0 검색 결과를 A-mem 형식으로 변환"""
        
        print(f"\n🔍 [Search] 검색어: '{query}'")
        results = self.m.search(query, user_id=self.user_id, limit=k)
        
        # [수정된 부분] 결과가 딕셔너리로 오면 리스트를 꺼내도록 처리
        if isinstance(results, dict):
            if "results" in results:
                results = results["results"]
            else:
                # results 키가 없으면 빈 리스트 처리 (에러 방지)
                print(f"⚠️ [Search] 예상치 못한 반환 형식: {results}")
                results = []
        
        formatted_text = ""
        ids = []
        
        for item in results:
            # 안전하게 데이터 추출
            mem_id = item.get("id", "unknown")
            text = item.get("memory", "")
            meta = item.get("metadata", {})
            
            # 메타데이터 추출
            context = meta.get("amem_context", "")
            tags = meta.get("amem_tags", [])
            
            ids.append(mem_id)
            formatted_text += (
                f"- [내용]: {text}\n"
                f"  [맥락]: {context} | [태그]: {tags}\n"
            )
            
        return formatted_text, ids

    def find_related_memories_raw(self, query: str, k: int = 5) -> str:
        text, _ = self.find_related_memories(query, k)
        return text
    
    # 통합 과정이므로 별도 진화 로직 불필요
    def process_memory(self, note):
        return False, note

# ==============================================================================
# 4. 테스트 실행 (Run Tests)
# ==============================================================================

def run_tests():
    print("=== Mem0g + A-mem 통합 테스트 시작 ===")
    
    # 1. 시스템 초기화 (Neo4j 비밀번호 확인!)
    try:
        system = AgenticMemorySystem(neo4j_pass="password")
    except:
        return

    # 2. 기억 저장 테스트
    print("\n[Step 1] 기억 저장")
    system.add_note("인공지능 신경망은 인간의 뇌 구조를 모방하여 만든 모델이다.")
    system.add_note("데이터 전처리는 모델 학습 전에 데이터를 깨끗하게 만드는 과정이다.")

    # 3. 기억 검색 테스트
    print("\n[Step 2] 기억 검색")
    query = "신경망이 뭐야?"
    result_text = system.find_related_memories_raw(query)
    
    print(f"\n[검색 결과]:\n{result_text}")

if __name__ == "__main__":
    run_tests()