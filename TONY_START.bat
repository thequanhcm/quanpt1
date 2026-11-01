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
REM ---- (30/10/2026) May 16GB: gioi han BLAS threads tranh cap RAM ----
set "OMP_NUM_THREADS=2"
set "OPENBLAS_NUM_THREADS=2"
set "MKL_NUM_THREADS=2"

cd /d "D:\AI\AI Quanpt1 2026\BRAIN"

REM ---- (31/10/2026) Tu nap API key tu registry user-level (neu chua co trong env) ----
REM Server doc key tu env khi goi GLM. Key da duoc persist vao HKCU\Environment
REM bang tools\persist_netmind_env.ps1, nhung process sinh ra tu terminal/env cu
REM (hoac Task Scheduler service cache) KHONG nhan duoc. Doc truc tiep tu reg
REM vao bien moi truong cua session nay — KHONG BAO GIO in gia tri ra man hinh.
if not defined NETMIND_API_KEY (
    for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v NETMIND_API_KEY 2^>nul ^| findstr /I "NETMIND_API_KEY"') do set "NETMIND_API_KEY=%%B"
)
if not defined HERMES_CUSTOM_NETMIND_API_KEY (
    for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v HERMES_CUSTOM_NETMIND_API_KEY 2^>nul ^| findstr /I "HERMES_CUSTOM"') do set "HERMES_CUSTOM_NETMIND_API_KEY=%%B"
)
REM Xac nhan bang DO DAI, khong in gia tri
set "KEY_STATUS=CHUA_CO"
if defined NETMIND_API_KEY set "KEY_STATUS=DA_NAP"
if defined HERMES_CUSTOM_NETMIND_API_KEY set "KEY_STATUS=DA_NAP"
echo [0/6] API key GLM: %KEY_STATUS% (chi kiem tra ton tai, khong hien gia tri)

echo.
echo ============================================
echo  TONY START - Starting QUAN AI BRAIN
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai D:\AI\AI Quanpt1 2026\BRAIN
    pause
    exit /b 1
)

REM ---- Stop existing TONY processes first (idempotent, co muc tieu) ----
REM (30/10/2026) May moi: kill theo MARKER script (command line), bat duoc ca
REM launcher .venv lAN interpreter con (base python) ? truoc day loc theo Path
REM '*QUAN AI BRAIN*' khong con dung vi workspace la 'AI Quanpt1 2026\BRAIN'
REM va interpreter con mang path khac (van song sot thanh orphan giu port).
REM Khong goi TONY_STOP.bat vi no co prompt confirm -> treo start script.
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_tony_services.ps1"

REM ---- [1/6] Ollama (embedding BGE-M3) ----
echo [1/6] Kiem tra / khoi dong Ollama (port 11434)...
if exist "C:\Users\quocd\AppData\Local\Programs\Ollama\ollama.exe" (
    ".venv\Scripts\python.exe" tools\khoi_dong_ollama.py
) else (
    echo     CANH BAO: khong thay C:\Users\quocd\AppData\Local\Programs\Ollama\ollama.exe - bo qua
)
echo     (chi tiet: logs\khoi_dong_ollama.log)

REM ---- [2/6] Dual Web Servers 8765 + 8766 ----
echo [2/6] Khoi dong Dual Servers (8765 UI + 8766 Dashboard)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "start_dual_servers" >nul 2>&1
if errorlevel 1 start "TONY - DualServers" /MIN ".venv\Scripts\pythonw.exe" start_dual_servers.py
ping -n 6 127.0.0.1 >nul

REM ---- [3/6] NetChat Auto-Responder (bot TONY) ----
echo [3/6] Khoi dong NetChat Auto-Responder (bot_quanpt1)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "netchat_auto_responder" >nul 2>&1
if errorlevel 1 start "TONY - Responder" /MIN ".venv\Scripts\pythonw.exe" tools\netchat_auto_responder.py
ping -n 3 127.0.0.1 >nul

REM ---- [4/6] Learning Daemon (tu hoc moi 5 phut) ----
echo [4/6] Khoi dong Learning Daemon...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "learning_daemon" >nul 2>&1
if errorlevel 1 start "TONY - Learning" /MIN ".venv\Scripts\pythonw.exe" tools\learning_daemon.py
ping -n 3 127.0.0.1 >nul

REM ---- [5/6] Watchdog (tu restart, gioi han 5/gio) ----
echo [5/6] Khoi dong Watchdog...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "watchdog.py" >nul 2>&1
if errorlevel 1 start "TONY - Watchdog" /MIN ".venv\Scripts\pythonw.exe" tools\watchdog.py
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
