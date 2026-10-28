@echo off
REM QUAN AI BRAIN - Start All Services (Manual Mode)
REM No Admin required - runs immediately

echo ============================================
echo QUAN AI BRAIN - Starting Services...
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

echo [1/5] Starting Server (port 8765)...
start "QUAN AI BRAIN - Server" .venv\Scripts\python.exe tools\server.py
timeout /t 2 /nobreak >nul

echo [2/5] Starting Watchdog (port 17236)...
start "QUAN AI BRAIN - Watchdog" .venv\Scripts\python.exe tools\watchdog.py
timeout /t 2 /nobreak >nul

echo [3/5] Starting Learning Engine (port 7724)...
start "QUAN AI BRAIN - Learning" .venv\Scripts\python.exe tools\learning.py
timeout /t 2 /nobreak >nul

echo [4/5] Starting NetChat Responder...
start "QUAN AI BRAIN - Responder" .venv\Scripts\python.exe tools\netchat_auto_responder.py
timeout /t 2 /nobreak >nul

echo [5/5] Starting Dashboard (port 8766)...
start "QUAN AI BRAIN - Dashboard" .venv\Scripts\python.exe edge_client\main.py
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo All services started!
echo ============================================
echo.
echo Services running in separate windows.
echo Close windows to stop services.
echo.
echo Run health check:
echo   python tools\health_check.py
echo.
pause