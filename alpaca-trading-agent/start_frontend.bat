@echo off
title Alpaca Trading Agent - Frontend
echo ===================================================
echo   Iniciando Frontend (Vite + React) en Local...
echo ===================================================

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [INFO] node_modules no encontrado. Instalando dependencias con npm install...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Error al instalar dependencias de npm.
        pause
        exit /b 1
    )
)

echo [INFO] Levantando servidor Vite en http://localhost:5173 ...
call npm run dev -- --host
pause
