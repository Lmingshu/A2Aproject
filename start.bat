@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installing dependencies...
python -m pip install -q fastapi "uvicorn[standard]" pydantic httpx python-dotenv
echo Starting server at http://localhost:8080 ...
python -m uvicorn backend.server:app --host 0.0.0.0 --port 8080
pause
