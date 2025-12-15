# PowerShell script to start moderator server

Write-Host "Starting Moderator server on port 10000..." -ForegroundColor Green
Write-Host "Make sure all panelist servers are running first!" -ForegroundColor Yellow
Write-Host ""

uv run python -u -m src.moderator

