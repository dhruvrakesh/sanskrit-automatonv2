@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

cd /d "%~dp0"

echo.
echo  ============================================================
echo    Sanskrit Automaton v2  --  Local Pipeline
echo  ============================================================
echo.

rem -- Ensure folders exist -----------------------------------------
if not exist inbox       mkdir inbox
if not exist data\raw    mkdir data\raw
if not exist exports     mkdir exports

rem -- Launch Dashboard (Flask, port 5057) --------------------------
echo [1/2] Starting Dashboard on http://127.0.0.1:5057/
start "Sanskrit Dashboard" cmd /k "chcp 65001 & cd /d ""%~dp0"" & python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057"

rem -- Small delay so Flask starts first ----------------------------
timeout /t 3 /nobreak > nul

rem -- Launch Export API (FastAPI, port 8000) -----------------------
echo [2/2] Starting Export API on http://127.0.0.1:8000/
start "Sanskrit Export API" cmd /k "chcp 65001 & cd /d ""%~dp0"" & python -m uvicorn api:app --reload --port 8000"

rem -- Open browser -------------------------------------------------
timeout /t 3 /nobreak > nul
start http://127.0.0.1:5057/

echo.
echo  Both servers are running:
echo    Dashboard  --  http://127.0.0.1:5057/
echo    Export API --  http://127.0.0.1:8000/
echo.
echo  Close the dashboard and export-api terminal windows to stop.
echo.
