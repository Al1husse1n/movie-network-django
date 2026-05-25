# Starts local PostgreSQL container in background
Set-Location "$PSScriptRoot/.."
Write-Host "==> Starting local PostgreSQL 16 container..." -ForegroundColor Cyan
docker compose up -d
exit $LASTEXITCODE
