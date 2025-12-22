"""Utility script to clear all data from Neo4j instances.
This can help fix corrupted data issues with mem0."""

import sys
from neo4j import GraphDatabase

# Neo4j 인스턴스 설정
NEO4J_INSTANCES = [
    {"name": "우파 정치인", "url": "bolt://localhost:7687", "user": "neo4j", "password": "password"},
    {"name": "우파 학자", "url": "bolt://localhost:7688", "user": "neo4j", "password": "password"},
    {"name": "좌파 정치인", "url": "bolt://localhost:7689", "user": "neo4j", "password": "password"},
    {"name": "좌파 학자", "url": "bolt://localhost:7690", "user": "neo4j", "password": "password"},
]

def clear_neo4j_instance(name: str, url: str, user: str, password: str) -> bool:
    """Clear all data from a Neo4j instance."""
    try:
        print(f"🔌 [{name}] 연결 중... ({url})")
        driver = GraphDatabase.driver(url, auth=(user, password))
        
        with driver.session() as session:
            # 모든 노드와 관계 삭제
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            deleted_count = result.single()["deleted"]
            print(f"✅ [{name}] {deleted_count}개의 노드 삭제 완료")
        
        driver.close()
        return True
    except Exception as e:
        print(f"❌ [{name}] 오류 발생: {e}")
        return False

def main():
    """Clear all Neo4j instances."""
    print("=" * 70)
    print("Neo4j 데이터 초기화 유틸리티")
    print("=" * 70)
    print()
    print("⚠️  경고: 이 스크립트는 모든 Neo4j 데이터를 삭제합니다!")
    print()
    
    # 사용자 확인
    response = input("계속하시겠습니까? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("취소되었습니다.")
        return
    
    print()
    print("데이터 삭제를 시작합니다...")
    print()
    
    success_count = 0
    for instance in NEO4J_INSTANCES:
        if clear_neo4j_instance(**instance):
            success_count += 1
        print()
    
    print("=" * 70)
    print(f"완료: {success_count}/{len(NEO4J_INSTANCES)} 인스턴스 초기화 성공")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        sys.exit(0)
    except ImportError:
        print("❌ neo4j 패키지가 설치되지 않았습니다.")
        print("   다음 명령어로 설치하세요: pip install neo4j")
        sys.exit(1)

