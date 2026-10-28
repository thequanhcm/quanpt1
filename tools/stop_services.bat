@echo off
REM Stop QUAN AI BRAIN Production Services

echo ========================================
echo QUAN AI BRAIN - Stopping Production Services
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

echo Stopping all QUAN AI BRAIN processes...
echo.

REM Stop by process name
taskkill /F /IM python.exe /FI "WINDOWTITLE eq QUAN*" 2>nul

REM Wait for processes to stop
echo Waiting for processes to terminate...
timeout /t 5 /nobreak >nul

REM Force kill if still running
echo Checking for remaining processes...
tasklist | findstr python.exe | findstr /I "server.py responder.py learning.py watchdog.py" >nul 2>&1
if %errorLevel% equ 0 (
    echo Force killing remaining processes...
    taskkill /F /IM python.exe
    timeout /t 2 /nobreak >nul
)

echo.
echo Verifying all services stopped...
echo.

set ALL_STOPPED=1

curl -s -m 3 http://127.0.0.1:8216/api/health >nul 2>&1
if %errorLevel% equ 0 (
    echo [WARN] Server still running on port 8216
    set ALL_STOPPED=0
)

curl -s -m 3 http://127.0.0.1:8765/api/health >nul 2>&1
if %errorLevel% equ 0 (
    echo [WARN] Dashboard still running on port 8765
    set ALL_STOPPED=0
)

curl -s -m 3 http://127.0.0.1:18036/api/health >nul 2>&1
if %errorLevel% equ 0 (
    echo [WARN] Responder still running on port 18036
    set ALL_STOPPED=0
)

echo.
echo ========================================

if %ALL_STOPPED% equ 1 (
    echo ALL SERVICES STOPPED SUCCESSFULLY
) else (
    echo SOME SERVICES MAY STILL BE RUNNING
    echo Check Task Manager for python.exe
)

echo ========================================
echo.
pause