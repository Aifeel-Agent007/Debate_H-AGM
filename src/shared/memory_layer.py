"""Agentic Memory System for Panelists - Mem0 + Neo4j integration."""

import os
import json
import uuid
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Literal, Any, Union, Tuple
from abc import ABC, abstractmethod

# Windows에서 임시 디렉토리 설정 (필요시 사용)
# Qdrant를 사용하지 않으므로 이 설정은 더 이상 필요하지 않음
# if os.name == 'nt':  # Windows
#     temp_dir = tempfile.gettempdir()
#     os.environ.setdefault('QDRANT_STORAGE_PATH', os.path.join(temp_dir, 'qdrant_storage'))

# Mem0 라이브러리
from mem0 import Memory

# LLM 관련 라이브러리
from litellm import completion
import requests

# ==============================================================================
# 1. LLM Controller Classes
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
            pass
    
    def get_completion(self, prompt: str, response_format: dict, temperature: float = 0.7) -> str:
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
        if backend == "openai":
            self.llm = OpenAIController(model, api_key)
        else:
            self.llm = OpenAIController(model, api_key)

# ==============================================================================
# 2. MemoryNote Class
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
                # 분석 실패 시 조용히 처리 (너무 많은 로그 방지)
                pass

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
# 3. AgenticMemorySystem
# ==============================================================================

class AgenticMemorySystem:
    """Agentic Memory System using Mem0 and Neo4j.
    
    Each panelist has their own isolated memory space identified by user_id.
    """
    
    def __init__(self, 
                 user_id: str = "default_user",
                 neo4j_url: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", 
                 neo4j_pass: str = "password",
                 model: str = "gpt-4o-mini",
                 **kwargs):
        """Initialize Agentic Memory System.
        
        Args:
            user_id: Unique identifier for this panelist's memory space
            neo4j_url: Neo4j connection URL
            neo4j_user: Neo4j username
            neo4j_pass: Neo4j password
            model: LLM model for analysis
        """
        self.user_id = user_id
        
        # A-mem 분석용 LLM
        api_key = kwargs.pop('api_key', None) or os.getenv('OPENAI_API_KEY')
        self.llm_controller = LLMController(model=model, api_key=api_key, **kwargs)

        # 각 패널리스트마다 고유한 Mem0 홈 디렉토리 설정 (마이그레이션 파일 잠금 방지)
        # Mem0가 ~/.mem0/migrations_qdrant/를 공유하므로, 각 user_id별로 분리된 홈 디렉토리 사용
        mem0_home = os.path.join(tempfile.gettempdir(), 'mem0_home', user_id)
        os.makedirs(mem0_home, exist_ok=True)
        
        # 환경 변수로 Mem0 홈 디렉토리 설정 (각 패널리스트마다 다름)
        # Windows에서는 USERPROFILE, Linux/Mac에서는 HOME 사용
        if os.name == 'nt':  # Windows
            original_userprofile = os.environ.get('USERPROFILE', '')
            os.environ['USERPROFILE'] = mem0_home
            # Mem0가 ~/.mem0를 찾을 수 있도록 설정
            mem0_config_dir = os.path.join(mem0_home, '.mem0')
            os.makedirs(mem0_config_dir, exist_ok=True)
        else:  # Linux/Mac
            original_home = os.environ.get('HOME', '')
            os.environ['HOME'] = mem0_home
            mem0_config_dir = os.path.join(mem0_home, '.mem0')
            os.makedirs(mem0_config_dir, exist_ok=True)
        
        # 각 패널리스트마다 고유한 Qdrant 경로 설정 (파일 잠금 방지)
        # Mem0가 기본적으로 Qdrant를 사용하므로, 각 user_id별로 분리된 경로 사용
        qdrant_path = os.path.join(tempfile.gettempdir(), 'qdrant_storage', user_id)
        os.makedirs(qdrant_path, exist_ok=True)
        
        # Mem0g 설정 (Graph Store = Neo4j, Vector Store = 각 user_id별 분리)
        config = {
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": neo4j_url,
                    "username": neo4j_user,
                    "password": neo4j_pass
                }
            },
            # 각 패널리스트마다 다른 Qdrant 경로 사용 (파일 잠금 방지)
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": qdrant_path,
                    "collection_name": f"mem0_{user_id}"
                }
            },
            "version": "v1.1"
        }
        
        # Mem0 인스턴스 초기화 (이 부분이 빠져있었습니다!)
        print(f"🔌 [Memory System] Neo4j({neo4j_url}) 연결 시도 중... (user_id: {user_id})")
        try:
            self.m = Memory.from_config(config)
            print(f"✅ [Memory System] Neo4j 연결 성공! (Mem0g Activated for user_id: {user_id})")
        except Exception as e:
            print(f"❌ [Memory System] Neo4j 연결 실패: {e}")
            print("   -> Docker 실행 여부와 비밀번호를 확인해주세요.")
            raise  # 초기화 실패 시 예외를 다시 발생시켜 패널리스트가 메모리 없이 계속 진행하지 않도록


    def add_note(self, content: str, time: str = None, **kwargs) -> str:
        """Save memory: A-mem analysis -> Mem0g(Neo4j) storage.
        
        Args:
            content: Content to save
            time: Optional timestamp
            
        Returns:
            Saved memory ID or error status
        """
        # 1. A-mem 분석
        try:
            note = MemoryNote(content, self.llm_controller, timestamp=time)
        except Exception as e:
            # 분석 실패 시 기본값 사용
            note = type('obj', (object,), {
                'context': '', 'tags': [], 'keywords': [], 
                'timestamp': time or str(datetime.now())
            })

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
            return "save_error"
        
        if result and 'results' in result and len(result['results']) > 0:
            return result['results'][0]['id']
        
        return "skipped"

    def find_related_memories(self, query: str, k: int = 5) -> Tuple[str, List[str]]:
        """Search memories: Mem0 search results in A-mem format.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            Tuple of (formatted_text, memory_ids)
        """
        results = self.m.search(query, user_id=self.user_id, limit=k)
        
        if isinstance(results, dict):
            if "results" in results:
                results = results["results"]
            else:
                results = []
        
        formatted_text = ""
        ids = []
        
        for item in results:
            mem_id = item.get("id", "unknown")
            text = item.get("memory", "")
            meta = item.get("metadata", {})
            
            context = meta.get("amem_context", "")
            tags = meta.get("amem_tags", [])
            
            ids.append(mem_id)
            formatted_text += (
                f"- [내용]: {text}\n"
                f"  [맥락]: {context} | [태그]: {tags}\n"
            )
            
        return formatted_text, ids

    def find_related_memories_raw(self, query: str, k: int = 5) -> str:
        """Search memories and return formatted text only.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            Formatted text of search results
        """
        text, _ = self.find_related_memories(query, k)
        return text

