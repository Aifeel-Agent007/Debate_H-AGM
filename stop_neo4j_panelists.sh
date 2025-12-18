#!/bin/bash

# Shell script to stop all 4 Neo4j instances

echo "Neo4j 인스턴스 4개 중지 중..."
echo ""

docker stop neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 모든 Neo4j 인스턴스가 중지되었습니다."
else
    echo "⚠️  일부 컨테이너가 실행 중이지 않을 수 있습니다."
fi

echo ""
echo "컨테이너를 완전히 제거하려면:"
echo "  docker rm neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4"
echo ""

