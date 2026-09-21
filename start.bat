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
    echo [WARNING] Node.js/npm not detected in PATH. Mobile app dev server will require Node.js.
)

:: Check for virtualenv
set "PY_CMD=python"
if exist "venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=%~dp0venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    set "ACTIVATE_SCRIPT=%~dp0.venv\Scripts\activate.bat"
) else (
    set "ACTIVATE_SCRIPT="
)

echo Select launch mode:
echo.
echo   [1] Full Stack -- Backend (Port 8000) + Mobile App (Expo) + Web Studio [DEFAULT]
echo   [2] Backend Only -- FastAPI Server (http://localhost:8000)
echo   [3] Mobile App Only -- Expo Dev Server (http://localhost:8081)
echo   [4] Open Mandi Web Studio in Browser (http://localhost:8000/inspector)
echo   [5] Run System Test Suite (PyTest 39 Tests + TypeScript Verification)
echo.
set "CHOICE="
set /p "CHOICE=Enter choice [1-5, default 1]: "

if "%CHOICE%"=="" set "CHOICE=1"
:: Strip any trailing whitespace
set "CHOICE=%CHOICE: =%"

if "%CHOICE%"=="1" goto launch_full_stack
if "%CHOICE%"=="2" goto launch_backend
if "%CHOICE%"=="3" goto launch_mobile
if "%CHOICE%"=="4" goto launch_studio
if "%CHOICE%"=="5" goto run_tests

echo Invalid choice. Defaulting to Full Stack...
goto launch_full_stack

:launch_full_stack
echo.
echo [*] Starting Backend Server on http://localhost:8000...
if defined ACTIVATE_SCRIPT (
    start "CEPA Backend [FastAPI:8000]" cmd /k "call "%ACTIVATE_SCRIPT%" && cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
) else (
    start "CEPA Backend [FastAPI:8000]" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
)

echo [*] Starting Mobile Expo Dev Server...
start "CEPA Mobile [Expo]" cmd /k "cd /d "%~dp0mobile" && npx expo start"

echo [*] Waiting for backend initialization...
ping 127.0.0.1 -n 4 >nul

echo [*] Opening Mandi Inspection Studio in default browser...
start http://localhost:8000/inspector

echo.
echo ===============================================================================
echo   SERVICES RUNNING CONCURRENTLY:
echo   - Backend API:         http://localhost:8000 (Docs at /docs)
echo   - Mandi Web Studio:    http://localhost:8000/inspector
echo   - Mobile App Dev:      http://localhost:8081 (Scan QR code in terminal)
echo ===============================================================================
echo.
echo Press any key to exit this launcher window (services will keep running).
pause >nul
exit /b 0

:launch_backend
echo.
echo [*] Starting Backend Server only on http://localhost:8000...
if defined ACTIVATE_SCRIPT (
    call "%ACTIVATE_SCRIPT%"
)
cd /d "%~dp0backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
exit /b 0

:launch_mobile
echo.
echo [*] Starting Mobile Expo App dev server...
cd /d "%~dp0mobile"
npx expo start
exit /b 0

:launch_studio
echo.
echo [*] Launching Mandi Web Studio in browser...
start http://localhost:8000/inspector
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
