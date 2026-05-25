# Connects to PostgreSQL container via interactive psql
Set-Location "$PSScriptRoot/.."
Write-Host "==> Connecting to movie_network database inside container..." -ForegroundColor Green
docker compose exec db psql -U movie_network -d movie_network
exit $LASTEXITCODE
