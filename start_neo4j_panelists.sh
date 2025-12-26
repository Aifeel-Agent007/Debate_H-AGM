#!/bin/bash

# Shell script to start 4 Neo4j instances for 4 panelists

echo "========================================"
echo "Neo4j 인스턴스 4개 시작"
echo "========================================"
echo ""

# 기존 컨테이너가 있으면 중지 및 제거
echo "기존 Neo4j 컨테이너 정리 중..."
docker stop neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>/dev/null
docker rm neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>/dev/null

echo ""
echo "4개의 Neo4j 인스턴스를 시작합니다..."
echo ""

# Neo4j 인스턴스 1: 우파 정치인 (포트 7687, 7474)
echo "[1/4] Neo4j #1 시작 중 (우파 정치인용)..."
echo "   - Bolt 포트: 7687"
echo "   - HTTP 포트: 7474"
docker run -d \
  --name neo4j-panelist-1 \
  -p 7687:7687 \
  -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

sleep 3

# Neo4j 인스턴스 2: 우파 학자 (포트 7688, 7475)
echo "[2/4] Neo4j #2 시작 중 (우파 학자용)..."
echo "   - Bolt 포트: 7688"
echo "   - HTTP 포트: 7475"
docker run -d \
  --name neo4j-panelist-2 \
  -p 7688:7687 \
  -p 7475:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

sleep 3

# Neo4j 인스턴스 3: 좌파 정치인 (포트 7689, 7476)
echo "[3/4] Neo4j #3 시작 중 (좌파 정치인용)..."
echo "   - Bolt 포트: 7689"
echo "   - HTTP 포트: 7476"
docker run -d \
  --name neo4j-panelist-3 \
  -p 7689:7687 \
  -p 7476:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

sleep 3

# Neo4j 인스턴스 4: 좌파 학자 (포트 7690, 7477)
echo "[4/4] Neo4j #4 시작 중 (좌파 학자용)..."
echo "   - Bolt 포트: 7690"
echo "   - HTTP 포트: 7477"
docker run -d \
  --name neo4j-panelist-4 \
  -p 7690:7687 \
  -p 7477:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

echo ""
echo "========================================"
echo "✅ 4개의 Neo4j 인스턴스가 시작되었습니다!"
echo "========================================"
echo ""
echo "각 패널리스트별 Neo4j 접속 정보:"
echo ""
echo "  [1] 우파 정치인:"
echo "      Bolt:  bolt://localhost:7687"
echo "      HTTP:  http://localhost:7474"
echo ""
echo "  [2] 우파 학자:"
echo "      Bolt:  bolt://localhost:7688"
echo "      HTTP:  http://localhost:7475"
echo ""
echo "  [3] 좌파 정치인:"
echo "      Bolt:  bolt://localhost:7689"
echo "      HTTP:  http://localhost:7476"
echo ""
echo "  [4] 좌파 학자:"
echo "      Bolt:  bolt://localhost:7690"
echo "      HTTP:  http://localhost:7477"
echo ""
echo "사용자명: neo4j"
echo "비밀번호: password"
echo ""
echo "Neo4j 초기화에 약 30초 정도 걸릴 수 있습니다."
echo "준비되면 패널리스트를 시작하세요: ./start_panelists.sh"
echo ""

