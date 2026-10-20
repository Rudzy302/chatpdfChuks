@echo off
title Document Studio - Iniciar Backend y Frontend
echo ============================================================
echo           INICIANDO DOCUMENT STUDIO (FASTAPI + REACT)
echo ============================================================

REM 1. Iniciar Backend FastAPI en segundo plano en una nueva ventana
echo [1/2] Iniciando Backend en http://127.0.0.1:8008 ...
start "Backend - FastAPI" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8008 --reload"

REM 2. Iniciar Frontend Vite en segundo plano en una nueva ventana
echo [2/2] Iniciando Frontend en http://127.0.0.1:4173 ...
start "Frontend - React Vite" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 4173"

echo ============================================================
echo  Ambos servicios se estan ejecutando:
echo    - Frontend: http://127.0.0.1:4173
echo    - Backend API: http://127.0.0.1:8008/docs
echo ============================================================
timeout /t 3 >nul
start http://127.0.0.1:4173
