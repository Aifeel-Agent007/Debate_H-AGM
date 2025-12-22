"""H-AGM 메모리 시스템 초기화 스크립트

4개의 패널리스트를 위한 독립적인 H-AGM 메모리 시스템을 생성합니다.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.shared.memory_layer import AgenticMemorySystem
from src.panelist.personas import PERSONAS

# 4개의 패널리스트 정의
PANELISTS = [
    ("right_politician", "우파 정치인"),
    ("right_scholar", "우파 학자"),
    ("left_politician", "좌파 정치인"),
    ("left_scholar", "좌파 학자"),
]


def initialize_all_memories():
    """4개의 패널리스트를 위한 H-AGM 메모리 시스템을 초기화합니다."""
    print("="*70)
    print("🧠 H-AGM 메모리 시스템 초기화")
    print("="*70)
    print()
    print("4개의 독립적인 H-AGM 메모리 시스템을 생성합니다:")
    print()
    
    # 환경 변수 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 추가하세요.")
        return False
    
    print(f"✅ OpenAI API 키 확인됨 (길이: {len(api_key)})")
    print()
    
    # 각 패널리스트의 메모리 시스템 초기화
    memory_systems = {}
    success_count = 0
    
    # 각 패널리스트마다 다른 Neo4j 포트 사용
    neo4j_ports = {
        "right_politician": 7687,  # Neo4j #1
        "right_scholar": 7688,      # Neo4j #2
        "left_politician": 7689,    # Neo4j #3
        "left_scholar": 7690,       # Neo4j #4
    }
    
    for idx, (persona_type, persona_name) in enumerate(PANELISTS, 1):
        user_id = f"panelist_{persona_type}"
        neo4j_port = neo4j_ports[persona_type]
        neo4j_url = f"bolt://localhost:{neo4j_port}"
        
        print(f"[{idx}/4] {persona_name} (user_id: {user_id})")
        print("-" * 70)
        
        try:
            print(f"   🔌 Neo4j #{idx} 연결 중... (포트: {neo4j_port})")
            print(f"   📁 벡터 스토어 경로 생성 중...")
            
            memory_system = AgenticMemorySystem(
                user_id=user_id,
                neo4j_url=neo4j_url,
                model="gpt-4o-mini",
                api_key=api_key
            )
            
            memory_systems[persona_type] = memory_system
            success_count += 1
            
            print(f"   ✅ H-AGM 메모리 시스템 #{idx} 생성 완료!")
            print(f"      - User ID: {user_id}")
            print(f"      - Persona: {persona_name}")
            print()
            
        except Exception as e:
            print(f"   ❌ 메모리 시스템 생성 실패: {e}")
            print()
            return False
    
    print("="*70)
    print(f"✅ 총 {success_count}/4개의 H-AGM 메모리 시스템이 성공적으로 생성되었습니다!")
    print("="*70)
    print()
    print("생성된 메모리 시스템:")
    for idx, (persona_type, persona_name) in enumerate(PANELISTS, 1):
        user_id = f"panelist_{persona_type}"
        print(f"  [{idx}] {persona_name}")
        print(f"      User ID: {user_id}")
        print(f"      Vector Store: %TEMP%\\qdrant_storage\\{user_id}\\")
        print(f"      Collection: mem0_{user_id}")
        print()
    
    print("이제 각 패널리스트가 독립적인 메모리 시스템을 사용할 수 있습니다.")
    print()
    
    return True


if __name__ == "__main__":
    print()
    success = initialize_all_memories()
    sys.exit(0 if success else 1)

