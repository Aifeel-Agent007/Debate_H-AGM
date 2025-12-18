import os
import sys

# utils.py를 불러오지 않도록 주의! (거기서 torch를 찾음)
# 바로 memory_layer만 불러옵니다.
try:
    from memory_layer import AgenticMemorySystem
except ImportError as e:
    print(f"❌ 임포트 에러: {e}")
    print("   (memory_layer.py 파일이 같은 폴더에 있는지 확인해주세요)")
    sys.exit(1)

def run_simple_test():
    print("=== [Torch 없는 가벼운 테스트 시작] ===")
    
    # 1. 시스템 초기화
    # (Neo4j가 켜져 있어야 합니다!)
    print("\n1. 시스템 초기화 중...")
    try:
        # OpenAI API 키가 환경변수에 없으면 여기서 직접 넣어도 됩니다.
        # api_key="sk-..." 
        system = AgenticMemorySystem(neo4j_pass="password") 
        print("✅ 초기화 성공!")
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        print("   -> Docker로 Neo4j를 실행했는지 확인해주세요.")
        return

    # 2. 기억 저장 테스트
    print("\n2. 기억 저장 테스트 (A-mem 분석 -> Mem0g 저장)")
    
    notes = [
        "나는 요즘 파이썬으로 AI 에이전트를 만드는 공부를 하고 있어.",
        "Neo4j는 그래프 데이터베이스인데, 관계를 저장하기 좋아.",
        "베이스 환경에서는 Torch 설치가 까다로워서 뺐어."
    ]
    
    for note in notes:
        print(f"   📝 저장 중: '{note[:15]}...'")
        system.add_note(note)
    
    print("✅ 저장 완료!")

    # 3. 기억 검색 테스트
    print("\n3. 기억 검색 테스트")
    queries = [
        "내가 요즘 뭐 공부하고 있지?",
        "그래프 데이터베이스가 뭐야?",
        "Torch는 왜 안 깔았어?"
    ]
    
    for q in queries:
        print(f"\n   🔍 질문: '{q}'")
        # find_related_memories_raw 함수는 문자열을 반환합니다.
        result = system.find_related_memories_raw(q)
        print(f"   📄 답변:\n{result}")
        print("   " + "-"*30)

if __name__ == "__main__":
    run_simple_test()