@echo off
echo ========================================================
echo  FLEETGUARD - Starting Frontend & AI Backend
echo ========================================================

cd /d "%~dp0"

:: Start backend in a separate dedicated window
echo [INFO] Starting Backend Server in new window...
start "FLEETGUARD AI Backend" cmd /c "call start_backend.bat"

:: Start frontend Vite dev server in current window
echo [INFO] Starting Frontend Dev Server on http://localhost:3000...
npm run dev
