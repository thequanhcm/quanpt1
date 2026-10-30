@echo off
REM ============================================
REM 🧹 FINAL CLEANUP - Remove unnecessary files
REM ============================================
REM Chỉ giữ lại TONY_START & TONY_STOP
REM Xóa các file duplicate, test, archive cũ
REM ============================================

echo.
echo ============================================
echo 🧹 FINAL CLEANUP - TONY Assistant
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

echo Files to be REMOVED:
echo   ❌ Duplicate start/stop scripts
echo   ❌ Old test scripts
echo   ❌ Archive files (ZIP)
echo   ❌ Old documentation (redundant)
echo   ❌ Development scripts (not needed for runtime)
echo.
echo Files to be KEPT:
echo   ✅ TONY_START.bat (main start)
echo   ✅ TONY_STOP.bat (main stop)
echo   ✅ src/, tests/, tools/ (core code)
echo   ✅ .env.production, pyproject.toml (config)
echo   ✅ AGENTS.md, README*.md (docs)
echo   ✅ Dockerfile, docker-compose.yml (deploy)
echo.
echo This will delete ~15-20 redundant files.
echo.
set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo ❌ Cancelled.
    pause
    exit /b 0
)

echo.
echo ============================================
echo Removing redundant files...
echo ============================================
echo.

REM Remove duplicate start/stop scripts
echo [1/5] Removing duplicate scripts...
del /f "START_ALL_ONECLICK.bat" 2>nul && echo ✅ Deleted START_ALL_ONECLICK.bat
del /f "STOP_ALL_ONECLICK.bat" 2>nul && echo ✅ Deleted STOP_ALL_ONECLICK.bat
del /f "STOP_ALL_ONECLICK.ps1" 2>nul && echo ✅ Deleted STOP_ALL_ONECLICK.ps1
del /f "KHOI_DONG_24_7.bat" 2>nul && echo ✅ Deleted KHOI_DONG_24_7.bat
del /f "KHOI_DONG_QUAN_AI_BRAIN.bat" 2>nul && echo ✅ Deleted KHOI_DONG_QUAN_AI_BRAIN.bat
del /f "start_server_with_policy.bat" 2>nul && echo ✅ Deleted start_server_with_policy.bat
del /f "setup_24_7_full.bat" 2>nul && echo ✅ Deleted setup_24_7_full.bat
echo.

REM Remove test scripts
echo [2/5] Removing test scripts...
del /f "logs\test_*.bat" 2>nul && echo ✅ Deleted test scripts
echo.

REM Remove archive files
echo [3/5] Removing archive files...
del /f "QUAN_AI_BRAIN_SPRINT1_STARTER.zip" 2>nul && echo ✅ Deleted SPRINT1 archive
del /f "*.zip" 2>nul && echo ✅ Deleted other ZIP files
echo.

REM Remove old/unused documentation
echo [4/5] Removing redundant docs...
del /f "START_STOP_GUIDE.md" 2>nul && echo ✅ Deleted START_STOP_GUIDE.md
del /f "HIDDEN_MODE_GUIDE.md" 2>nul && echo ✅ Deleted HIDDEN_MODE_GUIDE.md
del /f "EMERGENCY_STOP_GUIDE.md" 2>nul && echo ✅ Deleted EMERGENCY_STOP_GUIDE.md
del /f "DEPLOYMENT_INSTRUCTIONS.md" 2>nul && echo ✅ Deleted DEPLOYMENT_INSTRUCTIONS.md
del /f "INSTALLATION_GUIDE.md" 2>nul && echo ✅ Deleted INSTALLATION_GUIDE.md
del /f "PR_DESCRIPTION.md" 2>nul && echo ✅ Deleted PR_DESCRIPTION.md
echo.

REM Remove development scripts (not needed for runtime)
echo [5/5] Removing dev scripts...
del /f "create_desktop_shortcuts.ps1" 2>nul && echo ✅ Deleted create_desktop_shortcuts.ps1
del /f "create_tony_shortcuts.ps1" 2>nul && echo ✅ Deleted create_tony_shortcuts.ps1
del /f "CLEANUP_REDUNDANT.bat" 2>nul && echo ✅ Deleted CLEANUP_REDUNDANT.bat
del /f "run_executive_desk.py" 2>nul && echo ✅ Deleted run_executive_desk.py
del /f "run_web_ui.py" 2>nul && echo ✅ Deleted run_web_ui.py
del /f "start_dual_servers.py" 2>nul && echo ✅ Deleted start_dual_servers.py
del /f "start_server_fixed.py" 2>nul && echo ✅ Deleted start_server_fixed.py
echo.

REM Remove old audit files (already committed)
echo Removing old audit files...
del /f "AUDIT_V30_BASELINE.json" 2>nul && echo ✅ Deleted AUDIT_V30_BASELINE.json
del /f "AUDIT_EXECUTIVE_SUMMARY.md" 2>nul && echo ✅ Deleted AUDIT_EXECUTIVE_SUMMARY.md
echo.

echo ============================================
echo ✅ CLEANUP COMPLETE!
echo ============================================
echo.
echo Files remaining:
echo   🚀 TONY_START.bat (START TONY)
echo   🛑 TONY_STOP.bat (STOP TONY)
echo   📁 src/, tests/, tools/ (core code)
echo   📄 Config files (.env, pyproject, etc.)
echo   📚 Essential docs (AGENTS, README)
echo   🐳 Docker files (Dockerfile, docker-compose)
echo.
echo Total files removed: ~20 files
echo.
echo To start TONY: Double-click 🚀 TONY_START.bat
echo To stop TONY: Double-click 🛑 TONY_STOP.bat
echo.
echo ============================================
pause