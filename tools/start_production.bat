@echo off
REM Start QUAN AI BRAIN Production Services
REM Run as Administrator

echo ========================================
echo QUAN AI BRAIN - Starting Production Services
echo ========================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Must run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/5] Stopping existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq QUAN*" 2>nul
timeout /t 3 /nobreak >nul

echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/5] Starting Server (port 8216)...
start /b "QUAN AI BRAIN - Server" python tools/server.py --env=production

echo [4/5] Starting Responder (port 18036)...
start /b "QUAN AI BRAIN - Responder" python tools/netchat_auto_responder.py --env=production

echo [5/5] Starting Learning Daemon (port 7724)...
start /b "QUAN AI BRAIN - Learning" python tools/learning_daemon.py --env=production

echo.
echo Starting Watchdog (port 17236)...
start /b "QUAN AI BRAIN - Watchdog" python tools/watchdog.py --env=production

echo.
echo Starting Dashboard (port 8765)...
start /b "QUAN AI BRAIN - Dashboard" python tools/dashboard.py --env=production

echo.
echo ========================================
echo Services starting...
echo ========================================
echo.
echo Waiting for services to initialize...
timeout /t 15 /nobreak >nul

echo.
echo Verifying services...
echo.

REM Check health endpoints
set SERVICES_OK=1

echo Checking Server (8216)...
curl -s -m 5 http://127.0.0.1:8216/api/health >nul 2>&1
if %errorLevel% neq 0 (
    echo   [FAIL] Server not responding
    set SERVICES_OK=0
) else (
    echo   [OK] Server healthy
)

echo Checking Dashboard (8765)...
curl -s -m 5 http://127.0.0.1:8765/api/health >nul 2>&1
if %errorLevel% neq 0 (
    echo   [FAIL] Dashboard not responding
    set SERVICES_OK=0
) else (
    echo   [OK] Dashboard healthy
)

echo Checking Responder (18036)...
curl -s -m 5 http://127.0.0.1:18036/api/health >nul 2>&1
if %errorLevel% neq 0 (
    echo   [FAIL] Responder not responding
    set SERVICES_OK=0
) else (
    echo   [OK] Responder healthy
)

echo.
echo ========================================

if %SERVICES_OK% equ 1 (
    echo ALL SERVICES STARTED SUCCESSFULLY
    echo.
    echo Access points:
    echo   - API Server:    http://localhost:8216
    echo   - Dashboard:     http://localhost:8765
    echo   - Responder:     http://localhost:18036
    echo   - Watchdog:      http://localhost:17236
    echo.
    echo Logs: C:\AI\QUAN AI BRAIN\logs\
    echo ========================================
) else (
    echo SOME SERVICES FAILED TO START
    echo Check logs for details
    echo ========================================
)

echo.
echo Press any key to exit...
pause >nul