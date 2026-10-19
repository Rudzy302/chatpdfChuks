@echo off
title Document Studio - Iniciar Backend y Frontend
echo ============================================================
echo           INICIANDO DOCUMENT STUDIO (FASTAPI + REACT)
echo ============================================================

REM 1. Iniciar Backend FastAPI en segundo plano en una nueva ventana
echo [1/2] Iniciando Backend en http://localhost:8000 ...
start "Backend - FastAPI" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Iniciar Frontend Vite en segundo plano en una nueva ventana
echo [2/2] Iniciando Frontend en http://localhost:3000 ...
start "Frontend - React Vite" cmd /k "cd frontend && npm run dev -- --port 3000"

echo ============================================================
echo  Ambos servicios se estan ejecutando:
echo    - Frontend: http://localhost:3000
echo    - Backend API: http://localhost:8000/docs
echo ============================================================
timeout /t 3 >nul
start http://localhost:3000
