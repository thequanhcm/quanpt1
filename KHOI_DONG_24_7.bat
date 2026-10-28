@echo off
title QUAN AI BRAIN - 24/7 AUTO START (QUANPT1)
cd /d "E:\AI\QUAN AI BRAIN"
color 0A

echo ============================================================
echo    QUAN AI BRAIN - KHOI DONG 24/7 (AUTO START)
echo    Sprint 7a: 5 phan tu + Ollama check bang python
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai E:\AI\QUAN AI BRAIN
    pause
    exit /b 1
)

REM ---- Env cho GLM Cloud + Gemini (doc user-level registry, khong hien thi) ----
set "NETMIND_EXTERNAL_DATA_ALLOWED=true"
if "%NETMIND_API_KEY%"=="" call :LoadUserEnv
if "%GEMINI_API_KEY%"=="" call :LoadUserEnv

REM ---- [0/5] Ollama (port 11434, E:\AI\Ollama\ollama.exe): kiem tra + start bang python ----
echo [0/5] Kiem tra Ollama (BGE-M3 embedding)...
if exist "E:\AI\Ollama\ollama.exe" (
    ".venv\Scripts\python.exe" tools\khoi_dong_ollama.py
)
echo    (chi tiet xem logs\khoi_dong_ollama.log)

REM ---- [1/5] Dual Web Servers ----
echo [1/5] Khoi dong Dual Servers (8765 + 8766)...
REM 28/10/2026: guard chong khoi dong trung — tim theo command-line python
REM (dung ca window 'start' lan tien trinh tay), idempotent tuyet doi.
wmic process where "name='python.exe'" get commandline 2>nul | find /I "start_dual_servers" >nul
if errorlevel 1 start "QAB-DualServers" /MIN ".venv\Scripts\python.exe" start_dual_servers.py
ping -n 9 127.0.0.1 >nul

REM ---- [2/5] NetChat Auto-Responder ----
echo [2/5] Khoi dong NetChat Auto-Responder (bot_quanpt1)...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "netchat_auto_responder" >nul
if errorlevel 1 start "QAB-NetChatBot" /MIN ".venv\Scripts\python.exe" tools\netchat_auto_responder.py
ping -n 4 127.0.0.1 >nul

REM ---- [3/5] Learning Daemon ----
echo [3/5] Khoi dong Learning Daemon (tu hoc moi 5 phut)...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "learning_daemon" >nul
if errorlevel 1 start "QAB-Learning" /MIN ".venv\Scripts\python.exe" tools\learning_daemon.py
ping -n 3 127.0.0.1 >nul

REM ---- [4/5] Watchdog ----
echo [4/5] Khoi dong Watchdog (tu restart, cap 5/gio)...
wmic process where "name='python.exe'" get commandline 2>nul | find /I "tools\watchdog" >nul
if errorlevel 1 start "QAB-Watchdog" /MIN ".venv\Scripts\python.exe" tools\watchdog.py
ping -n 3 127.0.0.1 >nul

REM ---- [5/5] Backup 2AM (QUAN_AI_BRAIN_BACKUP_2AM) + Report 8AM (Task Scheduler, idempotent) ----
echo [5/5] Dat lich backup 2AM + report 8AM (Task Scheduler)...
".venv\Scripts\python.exe" tools\sched_task_setup.py

echo.
echo ============================================================
echo    HOAN TAT! He thong dang chay ngam (4 cua so MINIMIZED):
echo      - QAB-DualServers : http://127.0.0.1:8765 + 8766
echo      - QAB-NetChatBot  : Bot TONY (NetChat 24/7)
echo      - QAB-Learning    : Tu hoc lien tuc
echo      - QAB-Watchdog    : Tu restart neu crash
echo    Backup tu dong 2AM + Bao cao sang 8AM (Task Scheduler)
echo ============================================================
echo.
ping -n 16 127.0.0.1 >nul
exit /b 0

:LoadUserEnv
REM Doc key tu user-level registry env (khong hien thi gia tri)
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_API_KEY 2^>nul') do set "NETMIND_API_KEY=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_DESKTOP_LLM_BASE_URL 2^>nul') do set "NETMIND_DESKTOP_LLM_BASE_URL=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v GEMINI_API_KEY 2^>nul') do set "GEMINI_API_KEY=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v GEMINI_MODEL 2^>nul') do set "GEMINI_MODEL=%%B"
exit /b 0
