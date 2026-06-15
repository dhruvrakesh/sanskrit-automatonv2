@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

cd /d "%~dp0"

echo.
echo  ============================================================
echo    Sanskrit Automaton v2  --  Local Pipeline
echo    Engine : Gemini 2.5 Flash (default)
echo    Budget : $8.00 ceiling  (edit .env to change)
echo  ============================================================
echo.

rem -- Load .env into the current environment ----------------------
rem    (Python scripts load it themselves via env_loader.py, but
rem     this makes the vars visible in the cmd windows too)
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "line=%%A"
        if not "!line:~0,1!"=="#" (
            if not "%%B"=="" set "%%A=%%B"
        )
    )
)

rem -- Ensure folders exist ----------------------------------------
if not exist inbox       mkdir inbox
if not exist data\raw    mkdir data\raw
if not exist exports     mkdir exports

rem -- Launch Dashboard (Flask, port 5057) -------------------------
echo [1/2] Starting Dashboard on http://127.0.0.1:5057/
start "Sanskrit Dashboard" cmd /k "chcp 65001 & cd /d ""%~dp0"" & python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057"

rem -- Small delay so Flask starts first ---------------------------
timeout /t 3 /nobreak > nul

rem -- Launch Export API (FastAPI, port 8000) ----------------------
rem    --workers 1 is 