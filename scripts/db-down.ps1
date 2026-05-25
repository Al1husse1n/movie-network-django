# Stops local PostgreSQL container
Set-Location "$PSScriptRoot/.."
Write-Host "==> Stopping local PostgreSQL container..." -ForegroundColor Yellow
docker compose down
exit $LASTEXITCODE
