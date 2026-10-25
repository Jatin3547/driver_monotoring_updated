@echo off
setlocal enabledelayedexpansion
echo ========================================================
echo  FLEETGUARD - Starting AI Backend Server
echo ========================================================

cd /d "%~dp0"

:: 1. Ensure backend/.env exists out-of-the-box
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Auto-creating backend\.env from template...
        copy ".env.example" ".env" >nul
    )
)

:: 2. Ensure frontend root .env exists out-of-the-box
if not exist "..\.env" (
    if exist "..\.env.example" (
        echo [INFO] Auto-creating root .env from template...
        copy "..\.env.example" "..\.env" >nul
    )
)

:: 3. Locate Python with OpenCV + MediaPipe + Ultralytics support
set "PY_EXE="

:: Check local venv313
if exist "venv313\Scripts\python.exe" (
    set "PY_EXE=venv313\Scripts\python.exe"
    echo [INFO] Using local backend venv313 virtual environment.
    goto launch
)

:: Check local venv
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    echo [INFO] Using local backend venv virtual environment.
    goto launch
)

:: Check sibling folder on the same machine (e.g. freshly pulled clone)
if exist "..\..\driver_monotoring_updated\backend\venv313\Scripts\python.exe" (
    set "PY_EXE=..\..\driver_monotoring_updated\backend\venv313\Scripts\python.exe"
    echo [INFO] Reusing AI virtual environment from sibling folder: driver_monotoring_updated
    goto launch
)

if exist "%USERPROFILE%\OneDrive\Desktop\driver\driver_monotoring_updated\backend\venv313\Scripts\python.exe" (
    set "PY_EXE=%USERPROFILE%\OneDrive\Desktop\driver\driver_monotoring_updated\backend\venv313\Scripts\python.exe"
    echo [INFO] Reusing AI virtual environment from %USERPROFILE%\OneDrive\Desktop\driver\driver_monotoring_updated\backend\venv313
    goto launch
)

:: Check system python
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Checking system Python for AI dependencies...
    python -c "import cv2, mediapipe, fastapi" >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set "PY_EXE=python"
        echo [INFO] System Python has all required AI libraries.
        goto launch
    ) else (
        echo [WARNING] System Python is missing OpenCV/MediaPipe/FastAPI.
        echo [INFO] Automatically creating local virtual environment 'venv313'...
        python -m venv venv313
        if exist "venv313\Scripts\pip.exe" (
            call venv313\Scripts\python.exe -m pip install --upgrade pip
            call venv313\Scripts\pip.exe install -r requirements.txt
            set "PY_EXE=venv313\Scripts\python.exe"
            goto launch
        )
    )
)

:: Check py launcher
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Checking py launcher for AI dependencies...
    py -c "import cv2, mediapipe, fastapi" >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set "PY_EXE=py"
        echo [INFO] Python via py launcher has all required AI libraries.
        goto launch
    ) else (
        echo [WARNING] Missing AI libraries. Automatically creating local virtual environment 'venv313'...
        py -m venv venv313
        if exist "venv313\Scripts\pip.exe" (
            call venv313\Scripts\python.exe -m pip install --upgrade pip
            call venv313\Scripts\pip.exe install -r requirements.txt
            set "PY_EXE=venv313\Scripts\python.exe"
            goto launch
        )
    )
)

:launch
if defined PY_EXE (
    echo [INFO] Launching FastAPI Uvicorn on http://127.0.0.1:8000
    "%PY_EXE%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto end
)

echo [ERROR] No suitable Python interpreter found.
echo Please install Python 3.10+ (64-bit) and add it to PATH.
pause

:end
