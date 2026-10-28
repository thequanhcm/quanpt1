@echo off
REM QUAN AI BRAIN — One-Click Installation
REM Complete setup for new computers
REM Run this script as Administrator

echo ============================================
echo QUAN AI BRAIN — One-Click Installation
echo ============================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Please run this script as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo ✅ Running as Administrator
echo.

REM Set workspace
set WORKSPACE=E:\AI\QUAN AI BRAIN

echo ============================================
echo Step 1: Checking Python & Dependencies
echo ============================================
echo.

REM Check Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

echo ✅ Python found
echo.

echo ============================================
echo Step 2: Setting up Virtual Environment
echo ============================================
echo.

cd /d "%WORKSPACE%"

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment exists
)

echo.
echo ============================================
echo Step 3: Installing Dependencies
echo ============================================
echo.

echo Installing core dependencies...
.venv\Scripts\pip.exe install -q -e ".[all]"
echo ✅ Dependencies installed
echo.

echo ============================================
echo Step 4: Initializing Databases
echo ============================================
echo.

echo Creating data directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist data\uat_logs mkdir data\uat_logs

echo Initializing brain.db...
.venv\Scripts\python.exe -c "from quan_ai_brain.memory.models import *; print('✅ brain.db ready')" 2>nul || echo ⚠️ brain.db initialization skipped

echo Initializing vector_db...
if not exist data\vector_db (
    .venv\Scripts\python.exe tools\init_vector_memory.py 2>nul || echo ⚠️ vector_db initialization skipped
) else (
    echo ✅ vector_db exists
)

echo.
echo ============================================
echo Step 5: Creating Task Scheduler Tasks
echo ============================================
echo.

echo Creating 5 service tasks...
.venv\Scripts\python.exe tools\setup_windows_services.py 2>nul || (
    echo Using batch script...
    call tools\setup_windows_services.bat
)

echo.
echo ============================================
echo Step 6: Verifying Installation
echo ============================================
echo.

echo Running health check...
.venv\Scripts\python.exe tools\health_check.py

echo.
echo ============================================
echo Installation Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Reboot your computer
echo 2. After reboot, services will auto-start
echo 3. Run: python tools\health_check.py
echo 4. Open Dashboard: http://127.0.0.1:8766/
echo.
echo For help, see: HDSD\trợ lý số\
echo.
pause