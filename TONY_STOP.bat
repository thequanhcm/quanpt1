@echo off
REM ============================================
REM TONY STOP - One-Click System Shutdown
REM ============================================
REM Dung toan bo services QUAN AI BRAIN (TONY)
REM KHONG dong den process Python cua ung dung khac
REM (netMind Desktop, Ollama, ... deu an toan)
REM ============================================

title TONY STOP - Stopping QUAN AI BRAIN

echo.
echo ============================================
echo  TONY STOP - Stopping QUAN AI BRAIN
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

REM Confirmation
echo Luu y: Lenh nay se dung TONY (server, bot NetChat, learning, watchdog).
echo Ollama va cac ung dung khac KHONG bi anh huong.
echo.
set /p confirm="Ban chac chan muon dung? (y/n): "
if /i not "%confirm%"=="y" (
    echo [x] Da huy.
    pause
    exit /b 0
)

echo.
echo ============================================
echo Step 1: Dung services TONY (co muc tieu)
echo ============================================
echo.

REM (29/10/2026) FIX quan trong: truoc day taskkill blanket TAT CA python.exe /
REM pythonw.exe tren may -- lam chet ca netMind Desktop va ung dung Python khac.
REM Gio chi kill process co file thuc thi nam trong thu muc workspace
REM (E:\AI\QUAN AI BRAIN\.venv\...) -- chinh xac 4 services cua TONY.
powershell -NoProfile -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*QUAN AI BRAIN*' } | ForEach-Object { Write-Host ('   Stopping PID ' + $_.Id + ' [' + $_.Path + ']'); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo Step 2: Verification
echo ============================================
echo.

REM Check TONY ports released
netstat -ano | findstr ":8765 " | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo [!!] Server 8765 van con chay.
) else (
    echo [OK] Server 8765 da dung.
)

netstat -ano | findstr ":8766 " | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo [!!] Dashboard 8766 van con chay.
) else (
    echo [OK] Dashboard 8766 da dung.
)

REM Check TONY python processes gone
powershell -NoProfile -Command "$left = Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*QUAN AI BRAIN*' }; if ($left) { Write-Host '[!!] Van con TONY process chua dung:' $left.Id } else { Write-Host '[OK] Toan bo TONY process da dung.' }"

REM Ollama status (thong tin, khong dong)
netstat -ano | findstr ":11434" | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Ollama van dang chay (khong bi anh huong - dung y).
)

echo.
echo ============================================
echo  TONY SYSTEM STOPPED
echo ============================================
echo.
echo  Bot NetChat se KHONG tra loi khi he thong dung.
echo  De khoi dong lai: nhan dup START TONY tren Desktop.
echo.
echo ============================================
echo Press any key to close this window...
echo ============================================
pause >nul
