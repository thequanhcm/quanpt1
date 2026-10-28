@echo off
REM QUAN AI BRAIN — Start Services (Hidden Windows)
REM Runs all services without visible console windows

set WORKSPACE=E:\AI\QUAN AI BRAIN
cd /d "%WORKSPACE%"

echo Starting QUAN AI BRAIN services (hidden mode)...

REM Start Server (hidden)
start /MIN "QUAN AI BRAIN - Server" .venv\Scripts\python.exe tools\server.py

REM Wait 1 second
timeout /t 1 /nobreak >nul

REM Start Watchdog (hidden)
start /MIN "QUAN AI BRAIN - Watchdog" .venv\Scripts\python.exe tools\watchdog.py

REM Wait 1 second
timeout /t 1 /nobreak >nul

REM Start Learning (hidden)
start /MIN "QUAN AI BRAIN - Learning" .venv\Scripts\python.exe tools\learning.py

REM Wait 1 second
timeout /t 1 /nobreak >nul

REM Start Responder (hidden)
start /MIN "QUAN AI BRAIN - Responder" .venv\Scripts\python.exe tools\netchat_auto_responder.py

REM Wait 1 second
timeout /t 1 /nobreak >nul

REM Start Dashboard (hidden)
start /MIN "QUAN AI BRAIN - Dashboard" .venv\Scripts\python.exe edge_client\main.py

echo.
echo ✅ All services started (hidden mode)
echo.
echo Services running in background.
echo Dashboard: http://127.0.0.1:8766/
echo.
echo Run 'stop_services_hidden.bat' to stop all services.
echo.
pause