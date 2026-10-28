@echo off
REM QUAN AI BRAIN — Stop All Services (Hidden Mode)
REM Stops all Python processes running QUAN AI BRAIN

echo Stopping QUAN AI BRAIN services...

REM Kill all QUAN AI BRAIN processes
taskkill /FI "WINDOWTITLE eq QUAN AI BRAIN*" /F 2>nul

REM Also kill by process name (safe - only python.exe)
taskkill /FI "IMAGENAME eq python.exe" /F 2>nul

echo.
echo ✅ All services stopped
echo.
pause