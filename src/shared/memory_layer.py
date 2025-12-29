"""Agentic Memory System for Panelists - Mem0 + Neo4j integration."""

import os
import json
import uuid
import tempfile
import math
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
                self.keywords = analysis.get("keywords", []) or []
                self.tags = analysis.get("tags", []) or []
                self.context = analysis.get("context", "General") or "General"
            except Exception as e:
                # 분석 실패 시 로그 출력 및 기본값 사용
                print(f"⚠️ [A-mem] 분석 실패, 기본값 사용: {str(e)[:100]}")
                # 기본값은 이미 초기화되어 있음 (keywords=[], tags=[], context="General")

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
        
        # Neo4j 연결 정보 저장 (나중에 사용)
        self.neo4j_url = neo4j_url
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        
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
        
        # Mem0 인스턴스 초기화 (Fallback 모드로 사용 - mem0 엔티티 추출 오류 방지)
        print(f"🔌 [Memory System] Neo4j({neo4j_url}) 연결 시도 중... (user_id: {user_id})")
        print(f"ℹ️ [Memory System] Fallback 모드 활성화 - Neo4j 직접 저장 방식 사용")
        try:
            # mem0 인스턴스는 검색용으로만 사용 (저장은 fallback 사용)
            self.m = Memory.from_config(config)
            print(f"✅ [Memory System] Neo4j 연결 성공! (Fallback 저장 모드, user_id: {user_id})")
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
            print(f"✅ [A-mem] 분석 완료 - 키워드: {len(note.keywords)}개, 태그: {len(note.tags)}개, 맥락: {note.context[:50] if note.context else 'None'}...")
        except Exception as e:
            # 분석 실패 시 기본값 사용
            print(f"⚠️ [A-mem] MemoryNote 생성 실패, 기본값 사용: {str(e)[:100]}")
            note = type('obj', (object,), {
                'context': 'General', 'tags': [], 'keywords': [], 
                'timestamp': time or str(datetime.now())
            })

        # 2. Mem0g 저장 - 메타데이터 안전 처리
        def safe_str(value, default=""):
            """안전하게 문자열로 변환 (None 방지)"""
            if value is None:
                return default
            if isinstance(value, list):
                return ", ".join(str(v) for v in value) if value else default
            return str(value)
        
        # 메타데이터를 안전하게 변환 (None 방지 및 문자열 변환)
        safe_metadata = {
            "amem_context": safe_str(note.context, "General"),
            "amem_tags": safe_str(note.tags, ""),
            "amem_keywords": safe_str(note.keywords, ""),
            "created_at": safe_str(note.timestamp, str(datetime.now()))
        }
        
        # Fallback 저장 방식 직접 사용 (mem0 엔티티 추출 오류 방지)
        print(f"💾 [Memory System] Fallback 저장 방식으로 메모리 저장 중...")
        return self._fallback_save(content, safe_metadata)

    def find_related_memories(self, query: str, k: int = 5) -> Tuple[str, List[str]]:
        """Search memories: Hybrid search (vector + graph expansion).
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            Tuple of (formatted_text, memory_ids)
        """
        # 하이브리드 검색 사용 (기본 파라미터)
        return self.find_related_memories_hybrid(query, k=k, alpha=0.7, max_distance=2)
    
    def _fallback_search(self, query: str, k: int = 5) -> Tuple[str, List[str]]:
        """Fallback: 직접 Neo4j에서 메모리 검색 (mem0 실패 시 사용)
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            Tuple of (formatted_text, memory_ids)
        """
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            with driver.session() as session:
                # Neo4j에서 직접 검색 (Cypher 쿼리)
                # 메모리 내용에 쿼리 키워드가 포함된 노드 검색
                # 여러 필드를 확인하여 검색 범위 확대
                cypher_query = """
                MATCH (n)
                WHERE (
                    (n.user_id = $user_id OR n.user_id IS NULL)
                    AND (
                        (n.memory IS NOT NULL AND toLower(n.memory) CONTAINS toLower($query))
                        OR (n.content IS NOT NULL AND toLower(n.content) CONTAINS toLower($query))
                        OR (n.text IS NOT NULL AND toLower(n.text) CONTAINS toLower($query))
                        OR (n.amem_context IS NOT NULL AND toLower(n.amem_context) CONTAINS toLower($query))
                        OR (n.amem_tags IS NOT NULL AND toLower(n.amem_tags) CONTAINS toLower($query))
                        OR (n.amem_keywords IS NOT NULL AND toLower(n.amem_keywords) CONTAINS toLower($query))
                        OR (n.metadata IS NOT NULL AND n.metadata.amem_context IS NOT NULL 
                            AND toLower(n.metadata.amem_context) CONTAINS toLower($query))
                    )
                )
                RETURN n, n.id as mem_id, n.memory as memory, n.content as content, 
                       n.text as text, n.amem_context as amem_context, 
                       n.amem_tags as amem_tags, n.amem_keywords as amem_keywords,
                       n.metadata as metadata, n.created_at as created_at, n.timestamp as timestamp
                ORDER BY COALESCE(n.timestamp, n.created_at) DESC
                LIMIT $limit
                """
                
                # Neo4j session.run()은 파라미터를 딕셔너리로 전달해야 함
                result = session.run(
                    cypher_query,
                    {
                        "user_id": self.user_id,
                        "query": query,
                        "limit": k
                    }
                )
                
                formatted_text = ""
                ids = []
                
                for record in result:
                    mem_id = record.get("mem_id") or record.get("n", {}).get("id", "unknown")
                    memory = record.get("memory") or ""
                    content = record.get("content") or ""
                    text = record.get("text") or ""
                    
                    # 메모리 텍스트 추출 (우선순위: memory > content > text)
                    mem_text = memory or content or text or ""
                    
                    # Fallback 저장 시 사용한 개별 필드에서 메타데이터 추출
                    context = record.get("amem_context") or ""
                    tags_str = record.get("amem_tags") or ""
                    # tags는 문자열로 저장되었으므로 쉼표로 분리
                    tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
                    
                    if mem_text:  # 텍스트가 있는 경우만 추가
                        ids.append(str(mem_id))
                        formatted_text += (
                            f"- [내용]: {mem_text[:500]}{'...' if len(mem_text) > 500 else ''}\n"
                            f"  [맥락]: {context} | [태그]: {tags}\n"
                        )
                
                driver.close()
                
                if formatted_text:
                    print(f"✅ [Memory System] Fallback 검색 성공: {len(ids)}개 결과 발견")
                    return formatted_text, ids
                else:
                    print(f"⚠️ [Memory System] Fallback 검색 결과 없음 (쿼리: '{query}')")
                    return "", []
                    
        except ImportError:
            print(f"⚠️ [Memory System] neo4j 패키지 없음. Fallback 검색 불가 (pip install neo4j)")
            return "", []
        except Exception as e:
            print(f"❌ [Memory System] Fallback 검색 실패: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()[:200]}")
            return "", []

    def find_related_memories_raw(self, query: str, k: int = 5) -> str:
        """Search memories and return formatted text only.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            Formatted text of search results
        """
        print(f"🔍 [Memory System] 메모리 검색 시작 (쿼리: '{query}', user_id: {self.user_id})")
        text, ids = self.find_related_memories(query, k)
        if text:
            print(f"✅ [Memory System] 검색 완료: {len(ids)}개 메모리 발견")
        else:
            print(f"⚠️ [Memory System] 검색 결과 없음 (쿼리: '{query}')")
        return text
    
    def _fallback_save(self, content: str, metadata: dict) -> str:
        """Fallback: 직접 Neo4j에 메모리 저장 (mem0 엔티티 추출 오류 방지)
        
        이 메서드는 mem0의 엔티티 추출 기능에서 발생하는 오류를 방지하기 위해
        Neo4j에 직접 Cypher 쿼리를 사용하여 메모리를 저장합니다.
        
        [Fallback 저장 방법 설명]
        
        1. 저장 방식:
           - mem0 라이브러리를 거치지 않고 Neo4j에 직접 저장
           - Cypher 쿼리 사용: CREATE (n:Memory { ... })
        
        2. 저장되는 데이터:
           - id: 고유 메모리 ID (UUID)
           - user_id: 패널리스트별 고유 식별자
           - memory/content/text: 메모리 내용 (3개 필드에 동일하게 저장)
           - amem_context: A-mem 분석 결과 - 맥락 정보
           - amem_tags: A-mem 분석 결과 - 태그 (쉼표로 구분된 문자열)
           - amem_keywords: A-mem 분석 결과 - 키워드 (쉼표로 구분된 문자열)
           - created_at: 생성 시간
           - timestamp: Neo4j datetime() 함수로 생성된 타임스탬프
           - metadata_json: 전체 메타데이터의 JSON 문자열 버전
        
        3. 검색 방법:
           - Fallback 검색 (_fallback_search)에서 다음 필드들을 검색:
             * memory, content, text: 메모리 내용
             * amem_context: 맥락 정보
             * amem_tags: 태그
             * amem_keywords: 키워드
           - 대소문자 구분 없이 CONTAINS 검색 사용
        
        4. 장점:
           - mem0의 엔티티 추출 오류 없이 안정적으로 저장
           - Neo4j에 직접 저장하여 빠른 성능
           - A-mem 메타데이터(키워드, 태그, 맥락) 보존
        
        5. 단점:
           - mem0의 그래프 관계 자동 생성 기능 미사용
           - 엔티티 간 관계는 수동으로 관리해야 함
        
        Args:
            content: 저장할 메모리 내용
            metadata: 메타데이터 딕셔너리 (amem_context, amem_tags, amem_keywords 포함)
            
        Returns:
            저장된 메모리 ID 또는 "save_error"
        """
        try:
            from neo4j import GraphDatabase
            import uuid
            import json
            
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            mem_id = str(uuid.uuid4())
            
            with driver.session() as session:
                # Neo4j에 직접 노드 생성
                # metadata를 JSON 문자열로 변환하여 저장 (Neo4j는 중첩 Map을 지원하지 않음)
                # 또는 각 필드를 개별 속성으로 저장
                metadata_json = json.dumps(metadata, ensure_ascii=False)
                
                cypher_query = """
                CREATE (n:Memory {
                    id: $id,
                    user_id: $user_id,
                    memory: $content,
                    content: $content,
                    text: $content,
                    metadata_json: $metadata_json,
                    amem_context: $amem_context,
                    amem_tags: $amem_tags,
                    amem_keywords: $amem_keywords,
                    created_at: $created_at,
                    timestamp: datetime()
                })
                RETURN n.id as id
                """
                
                result = session.run(
                    cypher_query,
                    id=mem_id,
                    user_id=self.user_id,
                    content=content,
                    metadata_json=metadata_json,
                    amem_context=metadata.get("amem_context", ""),
                    amem_tags=metadata.get("amem_tags", ""),
                    amem_keywords=metadata.get("amem_keywords", ""),
                    created_at=metadata.get("created_at", str(datetime.now()))
                )
                
                record = result.single()
                if record:
                    saved_id = record["id"]
                    driver.close()
                    print(f"✅ [Memory System] Fallback 저장 성공 (ID: {saved_id}, user_id: {self.user_id})")
                    # 관계 생성 추가
                    self._create_relationships(saved_id, content, metadata)
                    return str(saved_id)
            
            driver.close()
            print(f"⚠️ [Memory System] Fallback 저장 결과 없음")
            return "skipped"
            
        except ImportError:
            print(f"⚠️ [Memory System] neo4j 패키지 없음. Fallback 저장 불가 (pip install neo4j)")
            return "save_error"
        except Exception as e:
            print(f"❌ [Memory System] Fallback 저장 실패: {e}")
            import traceback
            print(f"   -> 상세 오류: {traceback.format_exc()[:300]}")
            return "save_error"
    
    def _create_relationships(self, new_mem_id: str, content: str, metadata: dict):
        """새 메모리와 기존 메모리 간 관계 생성
        
        Args:
            new_mem_id: 새로 저장된 메모리 ID
            content: 메모리 내용
            metadata: 메타데이터 (tags, keywords 포함)
        """
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            with driver.session() as session:
                # 키워드나 태그가 겹치는 기존 메모리 찾기
                keywords_str = metadata.get("amem_keywords", "")
                tags_str = metadata.get("amem_tags", "")
                
                keywords = [k.strip() for k in keywords_str.split(",")] if keywords_str else []
                tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
                
                # 관련 메모리 찾기 (키워드/태그 기반)
                if keywords or tags:
                    cypher_query = """
                    MATCH (new:Memory {id: $new_id, user_id: $user_id})
                    MATCH (existing:Memory)
                    WHERE existing.id <> $new_id 
                      AND existing.user_id = $user_id
                      AND (
                        ANY(kw IN $keywords WHERE 
                          (existing.amem_keywords IS NOT NULL AND existing.amem_keywords CONTAINS kw)
                          OR (existing.amem_tags IS NOT NULL AND existing.amem_tags CONTAINS kw)
                        )
                        OR ANY(tag IN $tags WHERE 
                          existing.amem_tags IS NOT NULL AND existing.amem_tags CONTAINS tag
                        )
                        OR (existing.amem_context IS NOT NULL AND existing.amem_context = $context)
                      )
                    MERGE (new)-[r:RELATED_TO {
                        weight: 1.0,
                        created_at: datetime()
                    }]->(existing)
                    RETURN count(r) as rel_count
                    """
                    
                    result = session.run(
                        cypher_query,
                        {
                            "new_id": new_mem_id,
                            "user_id": self.user_id,
                            "keywords": keywords,
                            "tags": tags,
                            "context": metadata.get("amem_context", "")
                        }
                    )
                    
                    record = result.single()
                    if record:
                        rel_count = record["rel_count"]
                        if rel_count > 0:
                            print(f"🔗 [Graph] {rel_count}개의 관계 생성됨")
            
            driver.close()
        except Exception as e:
            print(f"⚠️ [Graph] 관계 생성 실패: {e}")

    def _graph_expansion(self, node_ids: List[str], max_distance: int = 2, max_nodes: int = 20) -> Dict[str, float]:
        """그래프 확장: 주어진 노드들에서 distance d 내의 관련 노드 찾기
        
        Args:
            node_ids: 시작 노드 ID 리스트
            max_distance: 최대 탐색 거리 (d)
            max_nodes: 최대 반환 노드 수
            
        Returns:
            {node_id: centrality_score} 딕셔너리
        """
        try:
            from neo4j import GraphDatabase
            
            if not node_ids:
                return {}
            
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            with driver.session() as session:
                # 그래프 확장 쿼리: distance d 내의 모든 노드 찾기
                cypher_query = """
                MATCH path = (start:Memory)-[*1..$max_distance]-(related:Memory)
                WHERE start.id IN $node_ids 
                  AND start.user_id = $user_id
                  AND related.user_id = $user_id
                WITH related, 
                     min(length(path)) as min_distance,
                     count(path) as path_count
                RETURN related.id as node_id, 
                       min_distance,
                       path_count,
                       // 간단한 centrality: 연결된 경로 수와 거리 역수
                       1.0 / (min_distance + 1) * log(path_count + 1) as centrality
                ORDER BY centrality DESC
                LIMIT $max_nodes
                """
                
                result = session.run(
                    cypher_query,
                    {
                        "node_ids": node_ids,
                        "user_id": self.user_id,
                        "max_distance": max_distance,
                        "max_nodes": max_nodes
                    }
                )
                
                expanded_nodes = {}
                for record in result:
                    node_id = record["node_id"]
                    centrality = record["centrality"]
                    expanded_nodes[node_id] = float(centrality) if centrality else 0.0
            
            driver.close()
            return expanded_nodes
            
        except Exception as e:
            print(f"⚠️ [Graph] 그래프 확장 실패: {e}")
            import traceback
            print(f"   상세: {traceback.format_exc()[:200]}")
            return {}

    def _calculate_node_centrality(self, node_id: str) -> float:
        """특정 노드의 centrality 계산 (간단한 버전)
        
        Args:
            node_id: 노드 ID
            
        Returns:
            Centrality 점수
        """
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            with driver.session() as session:
                # 연결된 노드 수와 경로 수를 기반으로 centrality 계산
                cypher_query = """
                MATCH (n:Memory {id: $node_id, user_id: $user_id})
                OPTIONAL MATCH (n)-[r:RELATED_TO]-(connected:Memory)
                WITH n, count(DISTINCT connected) as degree, count(r) as edge_count
                RETURN 
                    CASE 
                        WHEN degree > 0 THEN log(degree + 1) * (edge_count / (degree + 1.0))
                        ELSE 0.0
                    END as centrality
                """
                
                result = session.run(
                    cypher_query,
                    {
                        "node_id": node_id,
                        "user_id": self.user_id
                    }
                )
                
                record = result.single()
                driver.close()
                
                if record:
                    centrality = record["centrality"]
                    return float(centrality) if centrality else 0.0
            return 0.0
            
        except Exception as e:
            print(f"⚠️ [Graph] Centrality 계산 실패: {e}")
            return 0.0

    def find_related_memories_hybrid(
        self, 
        query: str, 
        k: int = 5, 
        alpha: float = 0.7, 
        max_distance: int = 2
    ) -> Tuple[str, List[str]]:
        """하이브리드 검색: 벡터 검색 + 그래프 확장 + 점수 통합
        
        Args:
            query: 검색 쿼리
            k: 벡터 검색 결과 수
            alpha: 유사도 가중치 (0~1, 1-alpha는 centrality 가중치)
            max_distance: 그래프 확장 최대 거리
        
        Returns:
            (formatted_text, memory_ids) 튜플
        """
        print(f"\n🔍 [Hybrid Search] 쿼리: '{query}' (α={alpha}, d={max_distance})")
        
        # Stage 1: Vector Retrieval
        vector_results = {}
        vector_ids = []
        
        try:
            results = self.m.search(query, user_id=self.user_id, limit=k)
            
            if isinstance(results, dict):
                if "results" in results:
                    results = results["results"]
                else:
                    results = []
            
            # 벡터 검색 결과와 유사도 점수 저장
            for idx, item in enumerate(results):
                mem_id = item.get("id", "unknown")
                # score가 있으면 사용, 없으면 순위 기반 유사도 추정
                similarity = item.get("score", 1.0 - (idx * 0.1))
                vector_results[mem_id] = similarity
                vector_ids.append(mem_id)
                
        except Exception as e:
            print(f"⚠️ [Hybrid] 벡터 검색 실패, fallback 사용: {e}")
            return self._fallback_search(query, k)
        
        if not vector_ids:
            print(f"⚠️ [Hybrid] 벡터 검색 결과 없음, fallback 사용")
            return self._fallback_search(query, k)
        
        print(f"✅ [Hybrid] Stage 1 완료: {len(vector_ids)}개 벡터 결과")
        
        # Stage 2: Graph Expansion
        expanded_nodes = self._graph_expansion(vector_ids, max_distance=max_distance)
        print(f"✅ [Hybrid] Stage 2 완료: {len(expanded_nodes)}개 확장 노드")
        
        # Stage 3: Integration - 점수 통합
        all_nodes = set(vector_ids) | set(expanded_nodes.keys())
        scored_nodes = {}
        
        for node_id in all_nodes:
            # 벡터 유사도 (없으면 0)
            sim_score = vector_results.get(node_id, 0.0)
            
            # Centrality 점수
            if node_id in expanded_nodes:
                centrality_score = expanded_nodes[node_id]
            else:
                # 벡터 결과지만 그래프에 없는 경우 centrality 계산
                centrality_score = self._calculate_node_centrality(node_id)
            
            # 정규화 (0~1 범위로)
            normalized_sim = sim_score if sim_score <= 1.0 else 1.0 / (1.0 + sim_score)
            normalized_centrality = min(centrality_score / 10.0, 1.0)  # 최대 10으로 정규화
            
            # 통합 점수: score(a_i) = α · sim(q, a_i) + (1-α) · centrality(a_i)
            final_score = alpha * normalized_sim + (1 - alpha) * normalized_centrality
            scored_nodes[node_id] = {
                'score': final_score,
                'sim': normalized_sim,
                'centrality': normalized_centrality
            }
        
        # 점수 순으로 정렬
        sorted_nodes = sorted(
            scored_nodes.items(), 
            key=lambda x: x[1]['score'], 
            reverse=True
        )[:k * 2]  # 최대 k*2개까지 반환 (확장 포함)
        
        # 결과 포맷팅
        formatted_text = ""
        result_ids = []
        
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            
            with driver.session() as session:
                for node_id, scores in sorted_nodes:
                    # Neo4j에서 노드 정보 가져오기
                    cypher_query = """
                    MATCH (n:Memory {id: $node_id, user_id: $user_id})
                    RETURN n.memory as memory, n.content as content, n.text as text,
                           n.amem_context as context, n.amem_tags as tags
                    """
                    
                    result = session.run(cypher_query, {"node_id": node_id, "user_id": self.user_id})
                    record = result.single()
                    
                    if record:
                        mem_text = record.get("memory") or record.get("content") or record.get("text") or ""
                        context = record.get("context") or ""
                        tags_str = record.get("tags") or ""
                        tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
                        
                        if mem_text:
                            result_ids.append(node_id)
                            formatted_text += (
                                f"- [내용]: {mem_text[:500]}{'...' if len(mem_text) > 500 else ''}\n"
                                f"  [맥락]: {context} | [태그]: {tags}\n"
                                f"  [점수]: sim={scores['sim']:.3f}, centrality={scores['centrality']:.3f}, "
                                f"final={scores['score']:.3f}\n"
                            )
            
            driver.close()
            
        except Exception as e:
            print(f"⚠️ [Hybrid] 결과 포맷팅 실패: {e}")
            import traceback
            print(f"   상세: {traceback.format_exc()[:200]}")
            return self._fallback_search(query, k)
        
        print(f"✅ [Hybrid] Stage 3 완료: {len(result_ids)}개 최종 결과")
        return formatted_text, result_ids

    def clear_all_memories(self) -> bool:
        """Clear all memories for this user from Neo4j.
        
        This can be used to fix corrupted data issues.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # 직접 Neo4j 연결하여 모든 노드 삭제
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            with driver.session() as session:
                # 모든 노드와 관계 삭제 (주의: 이는 모든 데이터를 삭제합니다)
                session.run("MATCH (n) DETACH DELETE n")
            driver.close()
            print(f"✅ [Memory System] Neo4j 데이터 초기화 완료 (user_id: {self.user_id})")
            return True
        except ImportError:
            print(f"⚠️ [Memory System] neo4j 패키지가 설치되지 않았습니다. pip install neo4j")
            return False
        except Exception as e:
            print(f"❌ [Memory System] 메모리 삭제 실패: {e}")
            return False

