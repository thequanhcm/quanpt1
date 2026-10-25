@echo off
REM QUAN AI BRAIN 24/7 Setup - Using schtasks
REM Run this script as your user (no admin required for user tasks)

echo ============================================================
echo QUAN AI BRAIN 24/7 Task Scheduler Setup
echo ============================================================

set BASE_DIR=E:\AI\QUAN AI BRAIN
set VENV_PYTHON=C:\Users\DELL\.venv\Scripts\python.exe
set WATCHDOG=%BASE_DIR%\tools\watchdog.py
set BACKUP=%BASE_DIR%\tools\backup_database.py

echo.
echo 1. Creating Watchdog task (runs at logon)...
schtasks /Create /TN "QUAN_AIBRAIN_Watchdog" /TR "%VENV_PYTHON% %WATCHDOG%" /SC ONLOGON /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Watchdog task created
) else (
    echo     WARNING: Could not create Watchdog task (may need to run as admin)
)

echo.
echo 2. Creating Backup task (daily at 2AM)...
schtasks /Create /TN "QUAN_AIBRAIN_Backup" /TR "cd /d %BASE_DIR% && %VENV_PYTHON% %BACKUP%" /SC DAILY /ST 02:00 /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Backup task created
) else (
    echo     WARNING: Could not create Backup task (may need to run as admin)
)

echo.
echo 3. Verifying tasks...
schtasks /Query /TN "QUAN_AIBRAIN_*" /FO LIST /V | findstr /C:"TaskName" /C:"Status" /C:"Next Run Time"

echo.
echo ============================================================
echo Setup complete!
echo.
echo Next steps:
echo   1. Open Task Scheduler: taskschd.msc
echo   2. Open Health Dashboard: http://127.0.0.1:8765/health_dashboard.html
echo   3. Check logs: %BASE_DIR%\logs\
echo ============================================================

pause