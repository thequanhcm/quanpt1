@echo off
REM ============================================
REM 🧹 CLEANUP - Remove redundant one-click files
REM ============================================

echo.
echo ============================================
echo 🧹 TONY Cleanup - Removing redundant files
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

echo This script will remove redundant one-click files.
echo Keeping only:
echo   - TONY_START.bat (NEW main start)
echo   - TONY_STOP.bat (NEW main stop)
echo   - INSTALL_ONE_CLICK.bat (Installation)
echo   - Setup scripts (tools/)
echo   - Backup & maintenance scripts
echo.
pause

echo.
echo Removing redundant files...
echo.

REM Remove duplicate start scripts
echo [1/10] Removing duplicate start scripts...
del /f "KHOI_DONG_24_7.bat" 2>nul && echo ✅ Deleted KHOI_DONG_24_7.bat
del /f "KHOI_DONG_QUAN_AI_BRAIN.bat" 2>nul && echo ✅ Deleted KHOI_DONG_QUAN_AI_BRAIN.bat
del /f "start_server_with_policy.bat" 2>nul && echo ✅ Deleted start_server_with_policy.bat
del /f "setup_24_7_full.bat" 2>nul && echo ✅ Deleted setup_24_7_full.bat
echo.

REM Remove test scripts
echo [2/10] Removing test scripts...
del /f "logs\test_block.bat" 2>nul && echo ✅ Deleted test_block.bat
del /f "logs\test_full.bat" 2>nul && echo ✅ Deleted test_full.bat
del /f "logs\test_khoi_head.bat" 2>nul && echo ✅ Deleted test_khoi_head.bat
del /f "logs\test_min.bat" 2>nul && echo ✅ Deleted test_min.bat
del /f "logs\test_part1.bat" 2>nul && echo ✅ Deleted test_part1.bat
echo.

REM Remove duplicate tools
echo [3/10] Removing duplicate tools...
del /f "tools\start_all_manual.bat" 2>nul && echo ✅ Deleted start_all_manual.bat
del /f "tools\start_production.bat" 2>nul && echo ✅ Deleted start_production.bat
del /f "tools\start_services.bat" 2>nul && echo ✅ Deleted start_services.bat
del /f "tools\stop_services.bat" 2>nul && echo ✅ Deleted stop_services.bat
del /f "tools\start_services_hidden.bat" 2>nul && echo ✅ Deleted start_services_hidden.bat
del /f "tools\stop_services_hidden.bat" 2>nul && echo ✅ Deleted stop_services_hidden.bat
echo.

REM Remove old START/STOP scripts (keep PowerShell version as backup)
echo [4/10] Removing old one-click scripts...
del /f "START_ALL_ONECLICK.bat" 2>nul && echo ✅ Deleted START_ALL_ONECLICK.bat
REM Keep STOP_ALL_ONECLICK.bat and STOP_ALL_ONECLICK.ps1 as backup
echo.

echo ============================================
echo ✅ Cleanup complete!
echo ============================================
echo.
echo Files kept:
echo   ✅ TONY_START.bat (main start)
echo   ✅ TONY_STOP.bat (main stop)
echo   ✅ INSTALL_ONE_CLICK.bat
echo   ✅ STOP_ALL_ONECLICK.bat (backup)
echo   ✅ STOP_ALL_ONECLICK.ps1 (backup)
echo   ✅ All tools/ scripts
echo   ✅ Backup & maintenance scripts
echo.

REM Create new desktop shortcuts
echo ============================================
echo Creating new desktop shortcuts...
echo ============================================
echo.

powershell -ExecutionPolicy Bypass -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('$env:USERPROFILE\Desktop\🚀 START TONY.lnk'); ^
$Shortcut.TargetPath = 'E:\AI\QUAN AI BRAIN\TONY_START.bat'; ^
$Shortcut.WorkingDirectory = 'E:\AI\QUAN AI BRAIN'; ^
$Shortcut.Description = 'Start TONY Assistant'; ^
$Shortcut.IconLocation = 'shell32.dll,238'; ^
$Shortcut.Save(); ^
Write-Host '✅ Created: 🚀 START TONY.lnk' -ForegroundColor Green"

powershell -ExecutionPolicy Bypass -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('$env:USERPROFILE\Desktop\🛑 STOP TONY.lnk'); ^
$Shortcut.TargetPath = 'E:\AI\QUAN AI BRAIN\TONY_STOP.bat'; ^
$Shortcut.WorkingDirectory = 'E:\AI\QUAN AI BRAIN'; ^
$Shortcut.Description = 'Stop TONY Assistant'; ^
$Shortcut.IconLocation = 'shell32.dll,25'; ^
$Shortcut.Save(); ^
Write-Host '✅ Created: 🛑 STOP TONY.lnk' -ForegroundColor Green"

echo.
echo ============================================
echo 🎉 Cleanup & Shortcut creation complete!
echo ============================================
echo.
echo New shortcuts on Desktop:
echo   🚀 START TONY.lnk
echo   🛑 STOP TONY.lnk
echo.
echo Old shortcuts have been replaced.
echo.
pause