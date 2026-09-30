@echo off
setlocal EnableDelayedExpansion
title "CEPA Quick Launch -- http://localhost:4173"

:: Ensure script runs from project root
cd /d "%~dp0"

echo ===============================================================================
echo     CEPA Quick Launch -- Full Stack (Backend + Frontend Web on Port 4173)
echo ===============================================================================
echo.

:: Detect Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: Detect Node / npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Node.js/npm not detected in PATH.
)

:: Check for virtualenv or conda
set "ACTIVATE_SCRIPT="
if exist "%USERPROFILE%\miniconda3\envs\cepa-ml\python.exe" (
    set "ACTIVATE_SCRIPT=call conda activate cepa-ml"
) else if exist "venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=call "%~dp0venv\Scripts\activate.bat""
) else if exist ".venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=call "%~dp0.venv\Scripts\activate.bat""
) else if exist "backend\venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=call "%~dp0backend\venv\Scripts\activate.bat""
)

:: Check if mobile dependencies are installed
if not exist "%~dp0mobile\node_modules" (
    echo [*] Mobile/Web dependencies not found. Installing via npm...
    cd /d "%~dp0mobile"
    call npm install
    cd /d "%~dp0"
    echo [*] Mobile dependencies installed.
    echo.
)

:: Ports
set "FRONTEND_PORT=4173"
set "BACKEND_PORT=8000"

:: Check if port 8000 is occupied
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>nul
if %errorlevel% equ 0 (
    echo [WARNING] Port 8000 is currently occupied by another process.
    echo [*] Automatically routing CEPA Backend to Port 8001.
    set "BACKEND_PORT=8001"
) else (
    set "BACKEND_PORT=8000"
)

echo [*] Starting Backend Server on http://localhost:!BACKEND_PORT!...
if defined ACTIVATE_SCRIPT (
    start "CEPA Backend [FastAPI:!BACKEND_PORT!]" cmd /k "%ACTIVATE_SCRIPT% && cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload"
) else (
    start "CEPA Backend [FastAPI:!BACKEND_PORT!]" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload"
)

echo [*] Starting Frontend Server on http://localhost:!FRONTEND_PORT!...
start "CEPA Frontend [Expo Web:!FRONTEND_PORT!]" cmd /k "cd /d "%~dp0mobile" && set "EXPO_PUBLIC_API_URL=http://localhost:!BACKEND_PORT!" && npx expo start --clear --port !FRONTEND_PORT! --web"

echo [*] Waiting for services to initialize...
timeout /t 5 /nobreak >nul 2>nul || ping 127.0.0.1 -n 6 >nul

echo [*] Opening Frontend Web Application in default browser...
start http://localhost:!FRONTEND_PORT!

echo.
echo ===============================================================================
echo   CEPA SERVICES ARE ACTIVE:
echo   - Frontend Web App:     http://localhost:!FRONTEND_PORT!
echo   - Backend API:          http://localhost:!BACKEND_PORT!
echo   - Swagger API Docs:     http://localhost:!BACKEND_PORT!/docs
echo   - Mandi Web Studio:     http://localhost:!BACKEND_PORT!/inspector
echo ===============================================================================
echo.
echo Press any key to exit this launcher window (services will continue running).
pause >nul
exit /b 0
