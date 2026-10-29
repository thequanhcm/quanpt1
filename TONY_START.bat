@echo off
REM ============================================
REM TONY START - One-Click System Launch
REM ============================================
REM Khoi dong toan bo he thong QUAN AI BRAIN
REM Dashboard phong dieu hanh: http://127.0.0.1:8766/
REM Tat ca cua so Python chay ngam (MINIMIZED)
REM ============================================

title TONY START - Starting QUAN AI BRAIN

REM ---- UTF-8 cho cac tien trinh Python con (fix loi tieng Viet / charmap) ----
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "E:\AI\QUAN AI BRAIN"

echo.
echo ============================================
echo  TONY START - Starting QUAN AI BRAIN
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai E:\AI\QUAN AI BRAIN
    pause
    exit /b 1
)

REM ---- Stop existing processes first (idempotent) ----
tasklist | findstr /I "python.exe ollama.exe" >nul 2>&1
if %errorLevel% equ 0 (
    echo [!] Phat hien process cu. Dung lai truoc khi khoi dong...
    call TONY_STOP.bat
    ping -n 4 127.0.0.1 >nul
)

REM ---- [1/6] Ollama (embedding BGE-M3) ----
echo [1/6] Kiem tra / khoi dong Ollama (port 11434)...
if exist "E:\AI\Ollama\ollama.exe" (
    ".venv\Scripts\python.exe" tools\khoi_dong_ollama.py
) else (
    echo     CANH BAO: khong thay E:\AI\Ollama\ollama.exe - bo qua
)
echo     (chi tiet: logs\khoi_dong_ollama.log)

REM ---- [2/6] Dual Web Servers 8765 + 8766 ----
echo [2/6] Khoi dong Dual Servers (8765 UI + 8766 Dashboard)...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "start_dual_servers" >nul
if errorlevel 1 start "TONY - DualServers" /MIN ".venv\Scripts\python.exe" start_dual_servers.py
ping -n 6 127.0.0.1 >nul

REM ---- [3/6] NetChat Auto-Responder (bot TONY) ----
echo [3/6] Khoi dong NetChat Auto-Responder (bot_quanpt1)...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "netchat_auto_responder" >nul
if errorlevel 1 start "TONY - Responder" /MIN ".venv\Scripts\python.exe" tools\netchat_auto_responder.py
ping -n 3 127.0.0.1 >nul

REM ---- [4/6] Learning Daemon (tu hoc moi 5 phut) ----
echo [4/6] Khoi dong Learning Daemon...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "learning_daemon" >nul
if errorlevel 1 start "TONY - Learning" /MIN ".venv\Scripts\python.exe" tools\learning_daemon.py
ping -n 3 127.0.0.1 >nul

REM ---- [5/6] Watchdog (tu restart, gioi han 5/gio) ----
echo [5/6] Khoi dong Watchdog...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "tools\watchdog" >nul
if errorlevel 1 start "TONY - Watchdog" /MIN ".venv\Scripts\python.exe" tools\watchdog.py
ping -n 3 127.0.0.1 >nul

REM ---- [6/6] Health check ----
echo [6/6] Health check...
ping -n 6 127.0.0.1 >nul
set ALL_OK=1

netstat -ano | findstr ":11434" | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo   [OK] Ollama: ONLINE (port 11434)
) else (
    echo   [!!] Ollama: OFFLINE - embedding se chay fail
    set ALL_OK=0
)

netstat -ano | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo   [OK] Server UI: ONLINE (port 8765)
) else (
    echo   [!!] Server UI: OFFLINE
    set ALL_OK=0
)

netstat -ano | findstr ":8766" | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo   [OK] Dashboard: ONLINE (port 8766)
) else (
    echo   [!!] Dashboard: OFFLINE
    set ALL_OK=0
)

echo.
echo ============================================
if %ALL_OK% equ 1 (
    echo  TONY SYSTEM STARTED - ALL SYSTEMS OPERATIONAL
) else (
    echo  TONY DA KHOI DONG - MOT SO DICH VU CAN KIEM TRA
    echo  Xem logs\ trong thu muc du an
)
echo ============================================
echo.
echo   Dashboard: http://127.0.0.1:8766/
echo   UI:        http://127.0.0.1:8765/
echo   NetChat:   kenh "TONY"
echo.
echo   Tat ca cua so dang chay NGAM (MINIMIZED).
echo   De dung: nhan dup STOP TONY tren Desktop.
echo.
pause
