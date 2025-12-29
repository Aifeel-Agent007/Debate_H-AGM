# PowerShell script to evaluate a debate file

param(
    [Parameter(Mandatory=$false)]
    [string]$DebateFile = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dqi", "aaf", "dqi-aaf", "afra", "all")]
    [string]$Mode = "all"
)

Write-Host "토론 평가 스크립트" -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# If no file specified, find the latest debate file
if ([string]::IsNullOrEmpty($DebateFile)) {
    $debateDir = Join-Path $PSScriptRoot "debate"
    if (-not (Test-Path $debateDir)) {
        Write-Host "❌ 오류: debate 디렉토리를 찾을 수 없습니다." -ForegroundColor Red
        Write-Host "   토론을 먼저 실행하거나 파일 경로를 지정하세요." -ForegroundColor Yellow
        exit 1
    }
    
    $debateFiles = Get-ChildItem -Path $debateDir -Filter "*.json" | Sort-Object LastWriteTime -Descending
    if ($debateFiles.Count -eq 0) {
        Write-Host "❌ 오류: 토론 결과 파일을 찾을 수 없습니다." -ForegroundColor Red
        exit 1
    }
    
    $DebateFile = $debateFiles[0].FullName
    Write-Host "📁 최신 토론 파일 사용: $DebateFile" -ForegroundColor Cyan
    Write-Host ""
}

if (-not (Test-Path $DebateFile)) {
    Write-Host "❌ 오류: 파일을 찾을 수 없습니다: $DebateFile" -ForegroundColor Red
    exit 1
}

Write-Host "토론 파일: $DebateFile" -ForegroundColor Cyan
Write-Host "평가 모드: $Mode" -ForegroundColor Cyan
Write-Host ""

# Run evaluation script
uv run python scripts/run_debate_with_evaluation.py "$DebateFile" "$Mode"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 평가 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 평가 완료!" -ForegroundColor Green

