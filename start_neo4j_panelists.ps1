# PowerShell script to start 4 Neo4j instances for 4 panelists

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Neo4j 인스턴스 4개 시작" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 기존 컨테이너가 있으면 중지 및 제거
Write-Host "기존 Neo4j 컨테이너 정리 중..." -ForegroundColor Yellow
docker stop neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>$null
docker rm neo4j-panelist-1 neo4j-panelist-2 neo4j-panelist-3 neo4j-panelist-4 2>$null

Write-Host ""
Write-Host "4개의 Neo4j 인스턴스를 시작합니다..." -ForegroundColor Green
Write-Host ""

# Neo4j 인스턴스 1: 우파 정치인 (포트 7687, 7474)
Write-Host "[1/4] Neo4j #1 시작 중 (우파 정치인용)..." -ForegroundColor Yellow
Write-Host "   - Bolt 포트: 7687" -ForegroundColor Gray
Write-Host "   - HTTP 포트: 7474" -ForegroundColor Gray
docker run -d `
  --name neo4j-panelist-1 `
  -p 7687:7687 `
  -p 7474:7474 `
  -e NEO4J_AUTH=neo4j/password `
  neo4j:latest

Start-Sleep -Seconds 3

# Neo4j 인스턴스 2: 우파 학자 (포트 7688, 7475)
Write-Host "[2/4] Neo4j #2 시작 중 (우파 학자용)..." -ForegroundColor Yellow
Write-Host "   - Bolt 포트: 7688" -ForegroundColor Gray
Write-Host "   - HTTP 포트: 7475" -ForegroundColor Gray
docker run -d `
  --name neo4j-panelist-2 `
  -p 7688:7687 `
  -p 7475:7474 `
  -e NEO4J_AUTH=neo4j/password `
  neo4j:latest

Start-Sleep -Seconds 3

# Neo4j 인스턴스 3: 좌파 정치인 (포트 7689, 7476)
Write-Host "[3/4] Neo4j #3 시작 중 (좌파 정치인용)..." -ForegroundColor Yellow
Write-Host "   - Bolt 포트: 7689" -ForegroundColor Gray
Write-Host "   - HTTP 포트: 7476" -ForegroundColor Gray
docker run -d `
  --name neo4j-panelist-3 `
  -p 7689:7687 `
  -p 7476:7474 `
  -e NEO4J_AUTH=neo4j/password `
  neo4j:latest

Start-Sleep -Seconds 3

# Neo4j 인스턴스 4: 좌파 학자 (포트 7690, 7477)
Write-Host "[4/4] Neo4j #4 시작 중 (좌파 학자용)..." -ForegroundColor Yellow
Write-Host "   - Bolt 포트: 7690" -ForegroundColor Gray
Write-Host "   - HTTP 포트: 7477" -ForegroundColor Gray
docker run -d `
  --name neo4j-panelist-4 `
  -p 7690:7687 `
  -p 7477:7474 `
  -e NEO4J_AUTH=neo4j/password `
  neo4j:latest

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 4개의 Neo4j 인스턴스가 시작되었습니다!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "각 패널리스트별 Neo4j 접속 정보:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  [1] 우파 정치인:" -ForegroundColor White
Write-Host "      Bolt:  bolt://localhost:7687" -ForegroundColor Gray
Write-Host "      HTTP:  http://localhost:7474" -ForegroundColor Gray
Write-Host ""
Write-Host "  [2] 우파 학자:" -ForegroundColor White
Write-Host "      Bolt:  bolt://localhost:7688" -ForegroundColor Gray
Write-Host "      HTTP:  http://localhost:7475" -ForegroundColor Gray
Write-Host ""
Write-Host "  [3] 좌파 정치인:" -ForegroundColor White
Write-Host "      Bolt:  bolt://localhost:7689" -ForegroundColor Gray
Write-Host "      HTTP:  http://localhost:7476" -ForegroundColor Gray
Write-Host ""
Write-Host "  [4] 좌파 학자:" -ForegroundColor White
Write-Host "      Bolt:  bolt://localhost:7690" -ForegroundColor Gray
Write-Host "      HTTP:  http://localhost:7477" -ForegroundColor Gray
Write-Host ""
Write-Host "사용자명: neo4j" -ForegroundColor Cyan
Write-Host "비밀번호: password" -ForegroundColor Cyan
Write-Host ""
Write-Host "Neo4j 초기화에 약 30초 정도 걸릴 수 있습니다." -ForegroundColor Yellow
Write-Host "준비되면 패널리스트를 시작하세요: .\start_panelists.ps1" -ForegroundColor Green
Write-Host ""

