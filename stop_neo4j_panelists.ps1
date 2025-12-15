# PowerShell script to stop all 4 Neo4j instances

Write-Host "Neo4j 인스턴스 4개 중지 중..." -ForegroundColor Yellow
Write-Host ""

docker stop neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 모든 Neo4j 인스턴스가 중지되었습니다." -ForegroundColor Green
} else {
    Write-Host "⚠️  일부 컨테이너가 실행 중이지 않을 수 있습니다." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "컨테이너를 완전히 제거하려면:" -ForegroundColor Cyan
Write-Host "  docker rm neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4" -ForegroundColor White
Write-Host ""

