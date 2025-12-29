# PowerShell script to evaluate all debates from multiple LLMs

param(
    [Parameter(Mandatory=$false)]
    [string]$DebateDir = "debate",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpt", "grok", "gemini", "claude", "qwen")]
    [string[]]$EvalLLMProviders = @("gpt", "grok", "gemini", "claude", "qwen"),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpt", "grok", "gemini", "claude", "qwen")]
    [string[]]$DebateLLMProviders = @(),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dqi", "aaf", "dqi-aaf", "afra", "all")]
    [string]$EvaluationMode = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "debate_results",
    
    [Parameter(Mandatory=$false)]
    [double]$Delay = 2.0
)

Write-Host "다중 LLM 토론 평가 스크립트" -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

Write-Host "토론 디렉토리: $DebateDir" -ForegroundColor Cyan
Write-Host "평가 LLM: $($EvalLLMProviders -join ', ')" -ForegroundColor Cyan
if ($DebateLLMProviders.Count -gt 0) {
    Write-Host "토론 LLM: $($DebateLLMProviders -join ', ')" -ForegroundColor Cyan
} else {
    Write-Host "토론 LLM: 자동 감지 (모든 LLM)" -ForegroundColor Cyan
}
Write-Host "평가 모드: $EvaluationMode" -ForegroundColor Cyan
Write-Host "출력 디렉토리: $OutputDir" -ForegroundColor Cyan
Write-Host "평가 간 대기 시간: $Delay 초" -ForegroundColor Cyan
Write-Host ""

# Build arguments
$argsList = @(
    "--debate-dir", $DebateDir,
    "--evaluation-mode", $EvaluationMode,
    "--output-dir", $OutputDir,
    "--delay", $Delay
)

if ($EvalLLMProviders.Count -gt 0) {
    $argsList += "--eval-llm-providers"
    $argsList += $EvalLLMProviders
}

if ($DebateLLMProviders.Count -gt 0) {
    $argsList += "--debate-llm-providers"
    $argsList += $DebateLLMProviders
}

# Run evaluation
uv run python scripts/run_multi_llm_evaluation.py @argsList

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 평가 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 다중 LLM 평가 완료!" -ForegroundColor Green
Write-Host "전체 요약: $OutputDir/evaluation_multi_llm_summary.json" -ForegroundColor Cyan
Write-Host "평가 결과: $OutputDir/<debate_llm>/<eval_llm>/ 디렉토리" -ForegroundColor Cyan

