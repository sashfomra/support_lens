@echo off
echo SupportLens - Starting all services
echo =====================================

echo.
echo [1] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo    Ollama is running OK
) else (
    echo    Starting Ollama...
    start "" /B ollama serve
    timeout /t 3 /nobreak >nul
)

echo.
echo [2] Starting Backend (FastAPI on port 8000)...
start "SupportLens Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8000"

echo.
echo [3] Waiting 8 seconds for backend to start...
timeout /t 8 /nobreak >nul

echo.
echo [4] Starting Frontend (Vite on port 5173)...
start "SupportLens Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
timeout /t 4 /nobreak >nul

echo.
echo ========================================
echo  SupportLens is RUNNING!
echo.
echo  Open:  http://localhost:5173
echo  Docs:  http://localhost:8000/docs
echo ========================================

start http://localhost:5173
