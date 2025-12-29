# PowerShell script to run batch debates from a topic file

param(
    [Parameter(Mandatory=$true)]
    [string]$TopicFile,
    
    [Parameter(Mandatory=$false)]
    [string]$ModeratorUrl = "http://localhost:10000",
    
    [Parameter(Mandatory=$false)]
    [double]$Delay = 5.0,
    
    [Parameter(Mandatory=$false)]
    [int]$StartFrom = 1
)

Write-Host "일괄 토론 실행 스크립트" -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if topic file exists
if (-not (Test-Path $TopicFile)) {
    Write-Host "❌ 오류: 파일을 찾을 수 없습니다: $TopicFile" -ForegroundColor Red
    exit 1
}

Write-Host "주제 파일: $TopicFile" -ForegroundColor Cyan
Write-Host "Moderator URL: $ModeratorUrl" -ForegroundColor Cyan
Write-Host "주제 간 대기 시간: $Delay 초" -ForegroundColor Cyan
Write-Host "시작 위치: $StartFrom" -ForegroundColor Cyan
Write-Host ""

# Run batch debates
uv run python src/client/run_batch_debates.py "$TopicFile" --moderator-url "$ModeratorUrl" --delay $Delay --start-from $StartFrom

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 일괄 토론 실행 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 일괄 토론 완료!" -ForegroundColor Green
Write-Host "요약 파일: debate_batch_summary.json" -ForegroundColor Cyan

