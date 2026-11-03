@echo off
REM QUAN AI BRAIN — Setup Hidden Tasks (Admin Required)
REM Creates Task Scheduler tasks that run completely hidden

echo ============================================
echo QUAN AI BRAIN — Setup Hidden Tasks
echo ============================================
echo.

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Please run as Administrator!
    echo Right-click → Run as administrator
    pause
    exit /b 1
)

echo ✅ Running as Administrator
echo.

echo Creating hidden tasks...
.venv\Scripts\python.exe tools\setup_hidden_tasks.py

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo All services will run HIDDEN (no windows)
echo.
echo Next: Reboot to test auto-start
echo.
pause