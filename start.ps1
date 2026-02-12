# A2A start server
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "Installing dependencies..."
python -m pip install -q fastapi "uvicorn[standard]" pydantic httpx python-dotenv
Write-Host "Starting server at http://localhost:8080 ..."
python -m uvicorn backend.server:app --host 0.0.0.0 --port 8080
