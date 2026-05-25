# Destroys database volume and starts fresh container
Set-Location "$PSScriptRoot/.."
Write-Host "==> Resetting database: removing volume and recreating container..." -ForegroundColor Magenta
docker compose down -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose up -d
exit $LASTEXITCODE
