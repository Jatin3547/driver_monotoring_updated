@echo off
echo ========================================================
echo  FLEETGUARD - Starting Backend Server
echo ========================================================

cd /d "%~dp0\backend"

if exist "venv313\Scripts\python.exe" (
    echo [INFO] Found backend venv313 virtual environment.
    .\venv313\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto end
)

if exist "venv\Scripts\python.exe" (
    echo [INFO] Found backend venv virtual environment.
    .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Starting Uvicorn using system Python...
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Starting Uvicorn using py launcher...
    py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto end
)

echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
pause

:end
