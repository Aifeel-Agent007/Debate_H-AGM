# PowerShell script to run debates with all 5 LLMs

param(
    [Parameter(Mandatory=$false)]
    [string]$TopicFile = "topics.txt",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpt", "grok", "gemini", "claude", "qwen")]
    [string[]]$LLMProviders = @("gpt", "grok", "gemini", "claude", "qwen"),
    
    [Parameter(Mandatory=$false)]
    [string]$ModeratorUrl = "http://localhost:10000",
    
    [Parameter(Mandatory=$false)]
    [double]$Delay = 5.0,
    
    [Parameter(Mandatory=$false)]
    [double]$DelayLLMs = 10.0,
    
    [Parameter(Mandatory=$false)]
    [int]$StartFromLLM = 1,
    
    [Parameter(Mandatory=$false)]
    [int]$StartFromTopic = 1
)

Write-Host "다중 LLM 토론 실행 스크립트" -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if topic file exists
if (-not (Test-Path $TopicFile)) {
    Write-Host "❌ 오류: 파일을 찾을 수 없습니다: $TopicFile" -ForegroundColor Red
    exit 1
}

Write-Host "주제 파일: $TopicFile" -ForegroundColor Cyan
Write-Host "사용할 LLM: $($LLMProviders -join ', ')" -ForegroundColor Cyan
Write-Host "Moderator URL: $ModeratorUrl" -ForegroundColor Cyan
Write-Host "주제 간 대기 시간: $Delay 초" -ForegroundColor Cyan
Write-Host "LLM 간 대기 시간: $DelayLLMs 초" -ForegroundColor Cyan
Write-Host "시작 LLM: $StartFromLLM" -ForegroundColor Cyan
Write-Host "시작 주제: $StartFromTopic" -ForegroundColor Cyan
Write-Host ""

# Build LLM providers argument
$llmProvidersArg = $LLMProviders -join " "

# Run multi-LLM debates
uv run python src/client/run_multi_llm_debates.py "$TopicFile" --llm-providers $llmProvidersArg --moderator-url "$ModeratorUrl" --delay $Delay --delay-llms $DelayLLMs --start-from-llm $StartFromLLM --start-from-topic $StartFromTopic

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 다중 LLM 토론 실행 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 다중 LLM 토론 완료!" -ForegroundColor Green
Write-Host "전체 요약: debate_multi_llm_summary.json" -ForegroundColor Cyan
Write-Host "LLM별 요약: debate_batch_summary_<llm>.json" -ForegroundColor Cyan
Write-Host "토론 결과: debate/<llm>/ 디렉토리" -ForegroundColor Cyan

