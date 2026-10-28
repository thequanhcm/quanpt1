@echo off
REM QUAN AI BRAIN — Emergency Stop (One-Click)
REM Stops ALL services and processes immediately

echo ============================================
echo 🛑 QUAN AI BRAIN — EMERGENCY STOP
echo ============================================
echo.

echo ⚠️  This will stop ALL services immediately!
echo.
pause

echo.
echo ============================================
echo Step 1: Stopping Task Scheduler Tasks
echo ============================================
echo.

schtasks /End /TN "QUAN-AI-BRAIN-Server" 2>nul
echo ✅ Server task stopped

schtasks /End /TN "QUAN-AI-BRAIN-Watchdog" 2>nul
echo ✅ Watchdog task stopped

schtasks /End /TN "QUAN-AI-BRAIN-Learning" 2>nul
echo ✅ Learning task stopped

schtasks /End /TN "QUAN-AI-BRAIN-Responder" 2>nul
echo ✅ Responder task stopped

schtasks /End /TN "QUAN-AI-BRAIN-Dashboard" 2>nul
echo ✅ Dashboard task stopped

echo.
echo ============================================
echo Step 2: Killing All Python Processes
echo ============================================
echo.

REM Kill by window title first
taskkill /FI "WINDOWTITLE eq QUAN AI BRAIN*" /F 2>nul
echo ✅ Killed processes by window title

REM Kill all python.exe (safe - only QUAN AI BRAIN running)
taskkill /FI "IMAGENAME eq python.exe" /F 2>nul
echo ✅ Killed all Python processes

echo.
echo ============================================
echo Step 3: Verifying Stop
echo ============================================
echo.

REM Wait 2 seconds for processes to terminate
timeout /t 2 /nobreak >nul

REM Check if any python processes remain
tasklist | findstr "python.exe" >nul 2>&1
if %errorLevel% equ 0 (
    echo ⚠️  Some Python processes still running...
    taskkill /FI "IMAGENAME eq python.exe" /F
    echo ✅ Force killed remaining processes
) else (
    echo ✅ All Python processes stopped
)

echo.
echo ============================================
echo Step 4: Final Status
echo ============================================
echo.

REM Run health check to verify
python tools\health_check.py

echo.
echo ============================================
echo 🛑 EMERGENCY STOP COMPLETE
echo ============================================
echo.
echo All services have been stopped.
echo.
echo To restart:
echo   tools\start_services.bat
echo   OR
echo   tools\start_services_hidden.bat
echo.
echo ============================================
echo.
pause