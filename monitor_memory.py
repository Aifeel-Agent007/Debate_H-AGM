#!/usr/bin/env python
"""메모리 모니터링 스크립트"""
import time
import sys
from datetime import datetime
from src.shared.memory_layer import AgenticMemorySystem

print('=' * 70)
print('📊 메모리 모니터링 시작')
print('=' * 70)
print('10초마다 각 패널리스트의 메모리 수를 확인합니다.')
print('=' * 70)
sys.stdout.flush()

# 각 패널리스트별 Neo4j 포트
panelists = [
    ('right_politician', '우파정치인', 7687),
    ('right_scholar', '우파학자', 7688),
    ('left_politician', '좌파정치인', 7689),
    ('left_scholar', '좌파학자', 7690),
]

# 메모리 시스템 초기화
print('\n메모리 시스템 연결 중...')
sys.stdout.flush()

memory_systems = {}
for persona_id, name, port in panelists:
    try:
        mem = AgenticMemorySystem(
            user_id=f'panelist_{persona_id}',
            neo4j_url=f'bolt://localhost:{port}'
        )
        memory_systems[persona_id] = (name, mem)
        print(f'  ✅ {name} 연결 완료')
    except Exception as e:
        print(f'  ❌ {name} 연결 실패: {e}')
    sys.stdout.flush()

print('\n' + '=' * 70)
print(f"{'시간':^12} | {'우파정치인':^10} | {'우파학자':^10} | {'좌파정치인':^10} | {'좌파학자':^10} | {'총합':^6}")
print('=' * 70)
sys.stdout.flush()

iteration = 0
try:
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        counts = []

        for persona_id, (name, mem) in memory_systems.items():
            try:
                if mem.m:
                    result = mem.m.get_all(user_id=f'panelist_{persona_id}')
                    if isinstance(result, dict) and 'results' in result:
                        count = len(result['results'])
                    elif isinstance(result, list):
                        count = len(result)
                    else:
                        count = 0
                else:
                    count = 0
            except Exception as e:
                count = -1
            counts.append(count)

        total = sum(c for c in counts if c >= 0)
        print(f'{now:^12} | {counts[0]:^10} | {counts[1]:^10} | {counts[2]:^10} | {counts[3]:^10} | {total:^6}')
        sys.stdout.flush()

        iteration += 1
        if iteration >= 60:  # 10분 후 종료
            break
        time.sleep(10)

except KeyboardInterrupt:
    pass

print('\n' + '=' * 70)
print('모니터링 종료')
