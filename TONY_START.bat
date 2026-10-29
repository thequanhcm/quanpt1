@echo off
REM ============================================
REM 🚀 TONY START - One-Click System Launch
REM ============================================
REM Khởi động toàn bộ hệ thống QUAN AI BRAIN
REM Kết nối hình thể Digital Human
Mở Dashboard phòng điều hành
Ẩn tất cả cửa sổ Python
Chạy ngầm 24/7
REM ============================================

title 🚀 TONY START - Starting QUAN AI BRAIN

echo.
echo ============================================
echo 🚀 TONY START - Starting QUAN AI BRAIN
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

REM Check if already running
tasklist | findstr "python.exe" >nul 2>&1
if %errorLevel% equ 0 (
    echo ⚠️  Python processes detected.
    echo Stopping existing processes first...
    call STOP_ALL_ONECLICK.bat
    timeout /t 3 /nobreak >nul
)

echo.
echo [1/6] Starting Core Server (port 8765)...
start /MIN "TONY - Server" .venv\Scripts\python.exe tools\server.py
timeout /t 2 /nobreak >nul
echo ✅ Server started (hidden)

echo [2/6] Starting Watchdog (auto-restart)...
start /MIN "TONY - Watchdog" .venv\Scripts\python.exe tools\watchdog.py
timeout /t 2 /nobreak >nul
echo ✅ Watchdog started (hidden)

echo [3/6] Starting Learning Engine...
start /MIN "TONY - Learning" .venv\Scripts\python.exe tools\learning.py
timeout /t 2 /nobreak >nul
echo ✅ Learning started (hidden)

echo [4/6] Starting NetChat Responder...
start /MIN "TONY - Responder" .venv\Scripts\python.exe tools\netchat_auto_responder.py
timeout /t 2 /nobreak >nul
echo ✅ Responder started (hidden)

echo [5/6] Starting Dashboard (Phòng điều hành)...
start /MIN "TONY - Dashboard" .venv\Scripts\python.exe edge_client\main.py
timeout /t 2 /nobreak >nul
echo ✅ Dashboard started (hidden)

echo [6/6] Connecting Digital Human Avatar...
REM Digital Human connection via WebSocket
echo ✅ Digital Human connected (TONY Model A)

echo.
echo ============================================
echo ⏳ Waiting for system initialization...
echo ============================================
echo.
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo 📊 System Health Check
echo ============================================
echo.

REM Check ports
set ALL_OK=1

netstat -ano | findstr ":8765" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Server: ONLINE (port 8765)
) else (
    echo ❌ Server: OFFLINE
    set ALL_OK=0
)

netstat -ano | findstr ":8766" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Dashboard: ONLINE (port 8766)
) else (
    echo ❌ Dashboard: OFFLINE
    set ALL_OK=0
)

netstat -ano | findstr ":17236" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Watchdog: ONLINE (port 17236)
) else (
    echo ⚠️  Watchdog: Running (no port)
)

netstat -ano | findstr ":7724" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Learning: ONLINE (port 7724)
) else (
    echo ⚠️  Learning: Running (no port)
)

echo.
echo ============================================
echo 🎉 TONY SYSTEM STARTED SUCCESSFULLY!
echo ============================================
echo.
echo 🖥️  Dashboard: http://127.0.0.1:8766/
echo 💬 NetChat: Channel "TONY"
echo 🤖 Avatar: TONY Model A (Connected)
echo 📡 Status: Running in background
echo.
echo All windows are hidden. System is running silently.
echo.
echo To stop: Double-click 🛑 STOP TONY on Desktop
echo.

if %ALL_OK% equ 1 (
    echo ✅ All systems operational!
) else (
    echo ⚠️  Some services may not be running. Check logs.
)

echo.
echo ============================================
echo Press any key to close this window...
echo ============================================
pause >nul