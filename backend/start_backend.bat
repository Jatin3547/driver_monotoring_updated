@echo off
echo ========================================================
echo  FLEETGUARD - Starting Backend Server
echo ========================================================

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Found Windows Python. Starting Uvicorn on Windows...
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Found Windows py launcher. Starting Uvicorn on Windows...
    py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    goto end
)

echo [INFO] Windows Python not found in PATH.
echo [INFO] Starting FastAPI backend via WSL Ubuntu environment...
wsl -d Ubuntu -e bash -c "cd /mnt/d/fleetmanagement/backend && PYTHONPATH=. ~/.venvs/fleet/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:end
