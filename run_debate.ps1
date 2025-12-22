# PowerShell script to run test debate client

Write-Host "Starting debate test client..." -ForegroundColor Green
Write-Host "Make sure moderator server is running first!" -ForegroundColor Yellow
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Run the debate client
uv run python src/client/test_debate.py

