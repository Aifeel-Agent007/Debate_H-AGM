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
        
        # 재시도 로직 추가 (파일 잠금 문제 해결)
        import time
        import random
        max_retries = 5
        retry_delay = 1.0  # 초기 지연 시간 (초)
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"   ⚠️ Retry attempt {attempt + 1}/{max_retries}...")
                
                print(f"🔌 [Memory] Initializing H-AGM memory system")
                print(f"   - User ID: {user_id}")
                print(f"   - Neo4j URL: {neo4j_url}")
                print(f"   - Mem0 home: {mem0_home} (isolated per panelist)")
                print(f"   - Qdrant path: {qdrant_path} (isolated per panelist)")
                print(f"   - Collection: mem0_{user_id}")
            
            self.m = Memory.from_config(config)
                
                print(f"✅ [Memory] H-AGM memory system initialized successfully")
                print(f"   - User ID: {user_id}")
                print(f"   - This is an independent memory space isolated from other panelists")
                print(f"   - All memories stored in Neo4j graph database")
                break  # 성공하면 루프 종료
                
        except Exception as e:
            error_msg = str(e)
                is_file_lock_error = (
                    'WinError 32' in error_msg or 
                    '파일을 사용 중' in error_msg or
                    'file is locked' in error_msg.lower() or
                    'permission denied' in error_msg.lower() or
                    'storage.sqlite' in error_msg
                )
                
                if is_file_lock_error and attempt < max_retries - 1:
                    # 파일 잠금 오류인 경우 재시도
                    wait_time = retry_delay * (2 ** attempt) + random.uniform(0, 0.5)  # 지수 백오프 + 랜덤 지터
                    print(f"   ⚠️ File lock detected, waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    # 최대 재시도 횟수 초과 또는 다른 오류
                    if is_file_lock_error:
                raise RuntimeError(
                            f"Mem0 vector store initialization failed for user_id={user_id} after {attempt + 1} attempts: {e}. "
                            f"This is a file locking issue. Try:\n"
                            f"1. Closing all panelist processes and restarting\n"
                            f"2. Deleting the Qdrant storage directory: {qdrant_path}\n"
                            f"3. Starting panelists one at a time with delays"
                )
                    raise RuntimeError(
                        f"Failed to connect to Neo4j for user_id={user_id}: {e}. "
                        f"Please ensure Neo4j is running at {neo4j_url}."
                    )

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

