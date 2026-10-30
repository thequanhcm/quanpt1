@echo off
REM QUAN AI BRAIN — Windows Service Setup
REM Creates Task Scheduler entries for auto-start on boot

echo ============================================
echo QUAN AI BRAIN — Windows Service Setup
echo ============================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Please run this script as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/5] Creating Task Scheduler tasks...
echo.

REM Define workspace
set WORKSPACE=E:\AI\QUAN AI BRAIN
set PYTHON=%WORKSPACE%\.venv\Scripts\python.exe

REM Task 1: QUAN AI BRAIN Server
echo Creating task: QUAN-AI-BRAIN-Server
schtasks /Create /TN "QUAN-AI-BRAIN-Server" /TR "\"%PYTHON%\" \"%WORKSPACE%\tools\server.py\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if %errorLevel% equ 0 (
    echo ✅ Server task created
) else (
    echo ❌ Failed to create Server task
)

REM Task 2: QUAN AI BRAIN Watchdog
echo Creating task: QUAN-AI-BRAIN-Watchdog
schtasks /Create /TN "QUAN-AI-BRAIN-Watchdog" /TR "\"%PYTHON%\" \"%WORKSPACE%\tools\watchdog.py\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if %errorLevel% equ 0 (
    echo ✅ Watchdog task created
) else (
    echo ❌ Failed to create Watchdog task
)

REM Task 3: QUAN AI BRAIN Learning Daemon
echo Creating task: QUAN-AI-BRAIN-Learning
schtasks /Create /TN "QUAN-AI-BRAIN-Learning" /TR "\"%PYTHON%\" \"%WORKSPACE%\tools\learning_daemon.py\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if %errorLevel% equ 0 (
    echo ✅ Learning task created
) else (
    echo ❌ Failed to create Learning task
)

REM Task 4: QUAN AI BRAIN NetChat Responder
echo Creating task: QUAN-AI-BRAIN-Responder
schtasks /Create /TN "QUAN-AI-BRAIN-Responder" /TR "\"%PYTHON%\" \"%WORKSPACE%\tools\netchat_auto_responder.py\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if %errorLevel% equ 0 (
    echo ✅ Responder task created
) else (
    echo ❌ Failed to create Responder task
)

REM Task 5: QUAN AI BRAIN Dashboard
echo Creating task: QUAN-AI-BRAIN-Dashboard
schtasks /Create /TN "QUAN-AI-BRAIN-Dashboard" /TR "\"%PYTHON%\" \"%WORKSPACE%\edge_client\main.py\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if %errorLevel% equ 0 (
    echo ✅ Dashboard task created
) else (
    echo ❌ Failed to create Dashboard task
)

echo.
echo [2/5] Configuring task settings...

REM Configure tasks to run with highest privileges
schtasks /Change /TN "QUAN-AI-BRAIN-Server" /RU SYSTEM /RL HIGHEST
schtasks /Change /TN "QUAN-AI-BRAIN-Watchdog" /RU SYSTEM /RL HIGHEST
schtasks /Change /TN "QUAN-AI-BRAIN-Learning" /RU SYSTEM /RL HIGHEST
schtasks /Change /TN "QUAN-AI-BRAIN-Responder" /RU SYSTEM /RL HIGHEST
schtasks /Change /TN "QUAN-AI-BRAIN-Dashboard" /RU SYSTEM /RL HIGHEST

echo [3/5] Setting up recovery options...

REM Configure restart on failure
schtasks /Change /TN "QUAN-AI-BRAIN-Server" /RC 1 /R 1 /RP 60
schtasks /Change /TN "QUAN-AI-BRAIN-Watchdog" /RC 1 /R 1 /RP 60
schtasks /Change /TN "QUAN-AI-BRAIN-Learning" /RC 1 /R 1 /RP 60
schtasks /Change /TN "QUAN-AI-BRAIN-Responder" /RC 1 /R 1 /RP 60
schtasks /Change /TN "QUAN-AI-BRAIN-Dashboard" /RC 1 /R 1 /RP 60

echo [4/5] Verifying tasks...
echo.

schtasks /Query /TN "QUAN-AI-BRAIN-*" /V /FO TABLE | findstr "QUAN-AI-BRAIN"

echo.
echo [5/5] Testing tasks...
echo.

echo Starting tasks manually to verify...
schtasks /Run /TN "QUAN-AI-BRAIN-Server"
echo ✅ Server task triggered
timeout /t 2 /nobreak >nul

schtasks /Run /TN "QUAN-AI-BRAIN-Watchdog"
echo ✅ Watchdog task triggered
timeout /t 2 /nobreak >nul

schtasks /Run /TN "QUAN-AI-BRAIN-Learning"
echo ✅ Learning task triggered
timeout /t 2 /nobreak >nul

schtasks /Run /TN "QUAN-AI-BRAIN-Responder"
echo ✅ Responder task triggered
timeout /t 2 /nobreak >nul

schtasks /Run /TN "QUAN-AI-BRAIN-Dashboard"
echo ✅ Dashboard task triggered

echo.
echo ============================================
echo ✅ WINDOWS SERVICE SETUP COMPLETE
echo ============================================
echo.
echo Created 5 tasks:
echo   • QUAN-AI-BRAIN-Server
echo   • QUAN-AI-BRAIN-Watchdog
echo   • QUAN-AI-BRAIN-Learning
echo   • QUAN-AI-BRAIN-Responder
echo   • QUAN-AI-BRAIN-Dashboard
echo.
echo All tasks will auto-start on Windows boot.
echo.
echo Management commands:
echo   List:     schtasks /Query /TN "QUAN-AI-BRAIN-*"
echo   Stop:     run tools\stop_services.bat
echo   Start:    run tools\start_services.bat
echo   Remove:   run tools\remove_services.bat
echo.
echo ============================================
pause