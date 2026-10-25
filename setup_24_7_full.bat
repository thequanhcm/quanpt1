@echo off
REM QUAN AI BRAIN 24/7 FULL SETUP — One-click deployment
REM Run as Administrator for best results

echo ============================================================
echo QUAN AI BRAIN 24/7 FULL SETUP
echo ============================================================
echo.

set BASE_DIR=E:\AI\QUAN AI BRAIN
set VENV_PYTHON=C:\Users\DELL\.venv\Scripts\python.exe
set WATCHDOG=%BASE_DIR%\tools\watchdog.py
set BACKUP=%BASE_DIR%\tools\backup_database.py
set LEARNING=%BASE_DIR%\tools\learning_daemon.py
set RESOURCE=%BASE_DIR%\tools\resource_monitor.py

echo [1/5] Creating Watchdog Task (auto-restart on crash)...
schtasks /Create /TN "QUAN_AIBRAIN_Watchdog" /TR "%VENV_PYTHON% %WATCHDOG%" /SC ONLOGON /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Watchdog task created
) else (
    echo     WARNING: Could not create Watchdog task
)

echo.
echo [2/5] Creating Backup Task (daily at 2AM)...
schtasks /Create /TN "QUAN_AIBRAIN_Backup" /TR "cd /d %BASE_DIR% && %VENV_PYTHON% %BACKUP%" /SC DAILY /ST 02:00 /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Backup task created
) else (
    echo     WARNING: Could not create Backup task
)

echo.
echo [3/5] Creating Learning Daemon Task (24/7 learning)...
schtasks /Create /TN "QUAN_AIBRAIN_Learning" /TR "%VENV_PYTHON% %LEARNING%" /SC ONLOGON /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Learning task created
) else (
    echo     WARNING: Could not create Learning task
)

echo.
echo [4/5] Creating Resource Monitor Task (every 5 minutes)...
schtasks /Create /TN "QUAN_AIBRAIN_ResourceMonitor" /TR "%VENV_PYTHON% %RESOURCE%" /SC MINUTE /MO 5 /RL HIGHEST /F /RU "%USERNAME%"
if %errorlevel% equ 0 (
    echo     SUCCESS: Resource Monitor task created
) else (
    echo     WARNING: Could not create Resource Monitor task
)

echo.
echo [5/5] Verifying tasks...
schtasks /Query /TN "QUAN_AIBRAIN_*" /FO LIST /V | findstr /C:"TaskName" /C:"Status" /C:"Next Run Time"

echo.
echo ============================================================
echo SETUP COMPLETE!
echo ============================================================
echo.
echo Created tasks:
echo   1. QUAN_AIBRAIN_Watchdog — Auto-restart on crash (at logon)
echo   2. QUAN_AIBRAIN_Backup — Daily backup at 2AM
echo   3. QUAN_AIBRAIN_Learning — Continuous learning 24/7 (at logon)
echo   4. QUAN_AIBRAIN_ResourceMonitor — Monitor every 5 minutes
echo.
echo Next steps:
echo   1. Restart your computer (tasks will auto-start)
echo   2. Open browser: http://127.0.0.1:8765/health_dashboard.html
echo   3. Check logs: E:\AI\QUAN AI BRAIN\logs\
echo.
echo To manage tasks: taskschd.msc
echo ============================================================

pause