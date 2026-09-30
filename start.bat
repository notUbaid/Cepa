@echo off
setlocal EnableDelayedExpansion
title "CEPA -- SIH26031 Onion Mandi Inspection & Grading System"

:: Ensure script runs from project root
cd /d "%~dp0"

cls
echo ===============================================================================
echo     CEPA (SIH26031) -- AI Onion Mandi Inspection ^& Grading System
echo     NAFED / APMC Precision Computer Vision System (BIS IS 17912:2022)
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
    echo [WARNING] Node.js/npm not detected in PATH. Mobile/Web app dev server requires Node.js.
)

:: Check for virtualenv
set "PY_CMD=python"
set "ACTIVATE_SCRIPT="
if exist "venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=%~dp0venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=%~dp0.venv\Scripts\activate.bat"
) else if exist "backend\venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=%~dp0backend\venv\Scripts\activate.bat"
)

:: Check if mobile dependencies are installed
if not exist "%~dp0mobile\node_modules" (
    echo [*] Mobile/Web dependencies not found. Installing via npm...
    cd /d "%~dp0mobile"
    call npm install
    cd /d "%~dp0"
    echo [*] Mobile dependencies installed successfully.
    echo.
)

:: Configure default ports
set "FRONTEND_PORT=4173"
set "BACKEND_PORT=8000"

:: Detect if port 8000 is already in use
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>nul
if %errorlevel% equ 0 (
    echo [WARNING] Port 8000 is currently occupied by another process.
    echo [*] Automatically routing CEPA Backend to Port 8001 to prevent conflicts.
    set "BACKEND_PORT=8001"
) else (
    set "BACKEND_PORT=8000"
)

echo Port Configuration:
echo   - Backend Server:   http://localhost:!BACKEND_PORT!
echo   - Frontend (Web):   http://localhost:!FRONTEND_PORT!
echo.
echo Select launch mode:
echo.
echo   [1] Full Stack -- Backend + Frontend Web (Port 4173) [DEFAULT]
echo   [2] Full Stack (Production Build) -- Backend + Static Web (Port 4173)
echo   [3] Backend Only -- FastAPI Server (http://localhost:!BACKEND_PORT!)
echo   [4] Frontend Only -- Expo Web Server (http://localhost:!FRONTEND_PORT!)
echo   [5] Open Mandi Web Studio in Browser (http://localhost:!BACKEND_PORT!/inspector)
echo   [6] Run System Test Suite (PyTest + TypeScript Verification)
echo.
set "CHOICE="
set /p "CHOICE=Enter choice [1-6, default 1]: "

if "%CHOICE%"=="" set "CHOICE=1"
set "CHOICE=%CHOICE: =%"

if "%CHOICE%"=="1" goto launch_full_stack
if "%CHOICE%"=="2" goto launch_prod_stack
if "%CHOICE%"=="3" goto launch_backend
if "%CHOICE%"=="4" goto launch_frontend
if "%CHOICE%"=="5" goto launch_studio
if "%CHOICE%"=="6" goto run_tests

echo Invalid choice. Defaulting to Full Stack...
goto launch_full_stack

:launch_full_stack
echo.
echo [*] Starting Backend Server on http://localhost:!BACKEND_PORT!...
if defined ACTIVATE_SCRIPT (
    start "CEPA Backend [FastAPI:!BACKEND_PORT!]" cmd /k "call "%ACTIVATE_SCRIPT%" && cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload"
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
echo   CEPA SERVICES RUNNING:
echo   - Frontend Web App:     http://localhost:!FRONTEND_PORT!
echo   - Backend API:          http://localhost:!BACKEND_PORT!
echo   - Swagger API Docs:     http://localhost:!BACKEND_PORT!/docs
echo   - Mandi Web Studio:     http://localhost:!BACKEND_PORT!/inspector
echo ===============================================================================
echo.
echo Press any key to exit this launcher window (services will continue running).
pause >nul
exit /b 0

:launch_prod_stack
echo.
echo [*] Starting Backend Server on http://localhost:!BACKEND_PORT!...
if defined ACTIVATE_SCRIPT (
    start "CEPA Backend [FastAPI:!BACKEND_PORT!]" cmd /k "call "%ACTIVATE_SCRIPT%" && cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload"
) else (
    start "CEPA Backend [FastAPI:!BACKEND_PORT!]" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload"
)

if not exist "%~dp0mobile\dist\index.html" (
    echo [*] Building production web export...
    cd /d "%~dp0mobile"
    call npx expo export -p web
    cd /d "%~dp0"
)

echo [*] Serving static web client on http://localhost:!FRONTEND_PORT!...
start "CEPA Static Web [Port !FRONTEND_PORT!]" cmd /k "python -m http.server !FRONTEND_PORT! --directory "%~dp0mobile\dist""

echo [*] Waiting for services to initialize...
timeout /t 4 /nobreak >nul 2>nul || ping 127.0.0.1 -n 5 >nul

echo [*] Opening Frontend Web Application in default browser...
start http://localhost:!FRONTEND_PORT!

echo.
echo ===============================================================================
echo   CEPA SERVICES RUNNING (PRODUCTION BUILD):
echo   - Frontend Web App:     http://localhost:!FRONTEND_PORT!
echo   - Backend API:          http://localhost:!BACKEND_PORT!
echo   - Swagger API Docs:     http://localhost:!BACKEND_PORT!/docs
echo   - Mandi Web Studio:     http://localhost:!BACKEND_PORT!/inspector
echo ===============================================================================
echo.
echo Press any key to exit this launcher window (services will continue running).
pause >nul
exit /b 0

:launch_backend
echo.
echo [*] Starting Backend Server on http://localhost:!BACKEND_PORT!...
if defined ACTIVATE_SCRIPT (
    call "%ACTIVATE_SCRIPT%"
)
cd /d "%~dp0backend"
python -m uvicorn main:app --host 0.0.0.0 --port !BACKEND_PORT! --reload
exit /b 0

:launch_frontend
echo.
echo [*] Starting Frontend on http://localhost:!FRONTEND_PORT!...
cd /d "%~dp0mobile"
set "EXPO_PUBLIC_API_URL=http://localhost:!BACKEND_PORT!"
npx expo start --clear --port !FRONTEND_PORT! --web
exit /b 0

:launch_studio
echo.
echo [*] Launching Mandi Web Studio in browser...
start http://localhost:!BACKEND_PORT!/inspector
exit /b 0

:run_tests
echo.
echo [*] Running PyTest Backend Test Suite...
if defined ACTIVATE_SCRIPT (
    call "%ACTIVATE_SCRIPT%"
)
python -m pytest backend/tests -v
echo.
echo [*] Running Mobile TypeScript Typecheck...
cd /d "%~dp0mobile"
call npx tsc --noEmit
if %errorlevel% equ 0 (
    echo [PASS] Mobile TypeScript: 0 errors.
) else (
    echo [FAIL] Mobile TypeScript errors detected.
)
echo.
pause
exit /b 0
