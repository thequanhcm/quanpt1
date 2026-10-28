@echo off
REM QUAN AI BRAIN — One-Click Start All Services
REM Starts all 5 services automatically

echo ============================================
echo 🚀 QUAN AI BRAIN — Starting All Services
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

echo [1/5] Starting Server (port 8765)...
start "QUAN AI BRAIN - Server" .venv\Scripts\python.exe tools\server.py
timeout /t 2 /nobreak >nul
echo ✅ Server started

echo [2/5] Starting Watchdog (port 17236)...
start "QUAN AI BRAIN - Watchdog" .venv\Scripts\python.exe tools\watchdog.py
timeout /t 2 /nobreak >nul
echo ✅ Watchdog started

echo [3/5] Starting Learning Engine (port 7724)...
start "QUAN AI BRAIN - Learning" .venv\Scripts\python.exe tools\learning.py
timeout /t 2 /nobreak >nul
echo ✅ Learning started

echo [4/5] Starting NetChat Responder...
start "QUAN AI BRAIN - Responder" .venv\Scripts\python.exe tools\netchat_auto_responder.py
timeout /t 2 /nobreak >nul
echo ✅ Responder started

echo [5/5] Starting Dashboard (port 8766)...
start "QUAN AI BRAIN - Dashboard" .venv\Scripts\python.exe edge_client\main.py
timeout /t 2 /nobreak >nul
echo ✅ Dashboard started

echo.
echo ============================================
echo ⏳ Waiting for services to initialize...
echo ============================================
echo.
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo 📊 Checking Service Status...
echo ============================================
echo.

REM Check ports
netstat -ano | findstr ":8765" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Server: ONLINE (port 8765)
) else (
    echo ❌ Server: OFFLINE
)

netstat -ano | findstr ":8766" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Dashboard: ONLINE (port 8766)
) else (
    echo ❌ Dashboard: OFFLINE
)

netstat -ano | findstr ":17236" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Watchdog: ONLINE (port 17236)
) else (
    echo ⚠️  Watchdog: Not listening (may be running)
)

netstat -ano | findstr ":7724" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Learning: ONLINE (port 7724)
) else (
    echo ⚠️  Learning: Not listening (may be running)
)

echo.
echo ============================================
echo 🎉 ALL SERVICES STARTED!
echo ============================================
echo.
echo Dashboard: http://127.0.0.1:8766/
echo Server: http://127.0.0.1:8765/
echo.
echo To stop all services:
echo   STOP_ALL_ONECLICK.bat
echo.
echo To setup auto-start on boot:
echo   Run tools\setup_hidden_tasks.bat as Administrator
echo.
pause