@echo off
title APEX Trading Dashboard - Launcher
echo ===================================================
echo   Iniciando APEX Trading Agent (Backend + Frontend)
echo ===================================================

cd /d "%~dp0"

echo [1/2] Levantando Backend (FastAPI en http://localhost:8000)...
start "APEX Backend (FastAPI)" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m uvicorn backend.server:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Levantando Frontend (Vite en http://localhost:5173)...
start "APEX Frontend (Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo ===================================================
echo Listo! La app estara accesible en:
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo ===================================================
