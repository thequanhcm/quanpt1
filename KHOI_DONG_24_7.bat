@echo off
title QUAN AI BRAIN - 24/7 AUTO START (QUANPT1)
cd /d "E:\AI\QUAN AI BRAIN"
color 0A

echo ============================================================
echo    QUAN AI BRAIN - KHOI DONG 24/7 (AUTO START)
echo    Server 8765+8766 + NetChat Bot + Learning + Watchdog
echo    (Bat dau tu 27/10/2026: dual servers + env GLM Cloud)
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai E:\AI\QUAN AI BRAIN
    pause
    exit /b 1
)

REM ---- Env cho GLM Cloud + Gemini tra cứu ngoài (key stored user-level qua
REM ---- persist_netmind_env.ps1 / persist_gemini_env.ps1; khoi lenh nay dam bao
REM ---- process con ke thừa env kể cả khi user env chua nap)
set "NETMIND_EXTERNAL_DATA_ALLOWED=true"
if "%NETMIND_API_KEY%"=="" call :LoadUserEnv
if "%GEMINI_API_KEY%"=="" call :LoadUserEnv

REM [1/5] Dual Web Servers (8765 Local UI + 8766 Executive)
echo [1/5] Khoi dong Dual Servers (8765 + 8766)...
start "QAB-DualServers" /MIN .venv\Scripts\python.exe start_dual_servers.py
timeout /t 8 /nobreak >nul

REM [2/5] NetChat Auto-Responder (bot Tony Pham, heartbeat cho watchdog)
echo [2/5] Khoi dong NetChat Auto-Responder (bot_quanpt1)...
start "QAB-NetChatBot" /MIN .venv\Scripts\python.exe tools\netchat_auto_responder.py
timeout /t 3 /nobreak >nul

REM [3/5] Learning Daemon (tu hoc 24/7)
echo [3/5] Khoi dong Learning Daemon (tu hoc moi 5 phut)...
start "QAB-Learning" /MIN .venv\Scripts\python.exe tools\learning_daemon.py
timeout /t 2 /nobreak >nul

REM [4/5] Watchdog (tu restart dual servers neu crash, max 5 lan/gio)
echo [4/5] Khoi dong Watchdog (health check moi 60s, ca 2 cong)...
start "QAB-Watchdog" /MIN .venv\Scripts\python.exe tools\watchdog.py

REM [5/5] Daily Backup 2AM (Task Scheduler user-level, idempotent)
echo [5/5] Dat lich backup 2AM (Task Scheduler, user-level)...
schtasks /Create /F /SC DAILY /ST 02:00 /TN "QUAN_AIBRAIN_Backup_2AM" /TR "\"E:\AI\QUAN AI BRAIN\tools\run_backup.bat\"" >nul 2>&1
if %errorlevel%==0 (echo    OK: backup 2AM da dat) else (echo    Binh thuong: backup da dat tu truoc hoac can Admin - bo qua)

echo.
echo ============================================================
echo    HOAN TAT! He thong dang chay ngam (4 cua so MINIMIZED):
echo      - QAB-DualServers : http://127.0.0.1:8765 + http://127.0.0.1:8766
echo      - QAB-NetChatBot  : Bot Tony Pham (NetChat 24/7)
echo      - QAB-Learning    : Tu hoc lien tuc
echo      - QAB-Watchdog    : Tu restart neu crash (ca 2 cong)
echo    Backup tu dong 2AM: QUAN_AIBRAIN_Backup_2AM (Task Scheduler)
echo.
echo    DE DUNG HE THONG: Dong 4 cua so MINIMIZED tuong ung.
echo ============================================================
echo.
REM Tu dong dong cua so launcher nay sau 15 giay
timeout /t 15 >nul
exit /b 0

:LoadUserEnv
REM Doc key tu user-level registry env (khong hien thi gia tri) vao process nay
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_API_KEY 2^>nul') do set "NETMIND_API_KEY=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_DESKTOP_LLM_BASE_URL 2^>nul') do set "NETMIND_DESKTOP_LLM_BASE_URL=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v GEMINI_API_KEY 2^>nul') do set "GEMINI_API_KEY=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v GEMINI_MODEL 2^>nul') do set "GEMINI_MODEL=%%B"
exit /b 0
