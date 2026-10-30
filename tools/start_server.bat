@echo off
REM ============================================
REM 🚀 START SERVER - QUAN AI BRAIN API Server
REM ============================================

echo.
echo ============================================
echo 🚀 QUAN AI BRAIN - Starting API Server
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ❌ Error: Virtual environment not found!
    echo Please run INSTALL_ONE_CLICK.bat first.
    pause
    exit /b 1
)

echo Starting server on port 8765...
echo Press Ctrl+C to stop

echo.
REM Start server (hidden window if called from hidden mode)
start /MIN "" ".venv\Scripts\python.exe" -m quan_ai_brain.server --host 0.0.0.0 --port 8765

echo.
echo ✅ Server started in background!
echo    URL: http://127.0.0.1:8765/
echo    Health: http://127.0.0.1:8765/api/health
echo.
echo Server will run in background.
echo To stop: Use STOP TONY or run tools/stop_services.bat
echo.
pause