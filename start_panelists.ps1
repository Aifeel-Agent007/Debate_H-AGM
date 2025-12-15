# PowerShell script to start all panelist servers in background

Write-Host "Starting panelist servers..." -ForegroundColor Green
Write-Host ""

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# 각 패널리스트마다 다른 Mem0 홈 디렉토리 설정 (마이그레이션 파일 잠금 방지)
$tempDir = $env:TEMP
$mem0Home1 = Join-Path $tempDir "mem0_home\panelist_right_politician"
$mem0Home2 = Join-Path $tempDir "mem0_home\panelist_right_scholar"
$mem0Home3 = Join-Path $tempDir "mem0_home\panelist_left_politician"
$mem0Home4 = Join-Path $tempDir "mem0_home\panelist_left_scholar"

# 디렉토리 생성
New-Item -ItemType Directory -Force -Path $mem0Home1 | Out-Null
New-Item -ItemType Directory -Force -Path $mem0Home2 | Out-Null
New-Item -ItemType Directory -Force -Path $mem0Home3 | Out-Null
New-Item -ItemType Directory -Force -Path $mem0Home4 | Out-Null

# Start right_politician
Write-Host "Starting Right Politician on port 10001..." -ForegroundColor Yellow
Write-Host "   Mem0 home: $mem0Home1" -ForegroundColor Gray
$env:USERPROFILE = $mem0Home1
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:USERPROFILE='$mem0Home1'; uv run python -u -m src.panelist --persona right_politician --port 10001" -WindowStyle Normal

# Wait longer to avoid file locking issues
Write-Host "Waiting 5 seconds before starting next panelist..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start right_scholar
Write-Host "Starting Right Scholar on port 10002..." -ForegroundColor Yellow
Write-Host "   Mem0 home: $mem0Home2" -ForegroundColor Gray
$env:USERPROFILE = $mem0Home2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:USERPROFILE='$mem0Home2'; uv run python -u -m src.panelist --persona right_scholar --port 10002" -WindowStyle Normal

# Wait longer to avoid file locking issues
Write-Host "Waiting 5 seconds before starting next panelist..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start left_politician
Write-Host "Starting Left Politician on port 10003..." -ForegroundColor Yellow
Write-Host "   Mem0 home: $mem0Home3" -ForegroundColor Gray
$env:USERPROFILE = $mem0Home3
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:USERPROFILE='$mem0Home3'; uv run python -u -m src.panelist --persona left_politician --port 10003" -WindowStyle Normal

# Wait longer to avoid file locking issues
Write-Host "Waiting 5 seconds before starting next panelist..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start left_scholar
Write-Host "Starting Left Scholar on port 10004..." -ForegroundColor Yellow
Write-Host "   Mem0 home: $mem0Home4" -ForegroundColor Gray
$env:USERPROFILE = $mem0Home4
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:USERPROFILE='$mem0Home4'; uv run python -u -m src.panelist --persona left_scholar --port 10004" -WindowStyle Normal

Write-Host ""
Write-Host "All panelist servers are starting in separate windows." -ForegroundColor Green
Write-Host "Wait for all servers to show 'ready' messages before starting the moderator." -ForegroundColor Yellow
Write-Host ""
Write-Host "To start moderator, run:" -ForegroundColor Cyan
Write-Host "  .\start_moderator.ps1" -ForegroundColor White
Write-Host ""

