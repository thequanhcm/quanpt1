@echo off
title QUAN AI BRAIN - 24/7 AUTO START (QUANPT1)
cd /d "E:\BRAIN"
color 0A
REM (02/11/2026) UTF-8 cho tien trinh Python con - phong UnicodeEncodeError cp1252
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ============================================================
echo    QUAN AI BRAIN - KHOI DONG 24/7 (AUTO START)
echo    Sprint 7a: 5 phan tu + Ollama check bang python
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai E:\BRAIN
    pause
    exit /b 1
)

REM ---- Env cho GLM Cloud + Gemini (doc user-level registry, khong hien thi) ----
set "NETMIND_EXTERNAL_DATA_ALLOWED=true"
if "%NETMIND_API_KEY%"=="" call :LoadUserEnv
if "%GEMINI_API_KEY%"=="" call :LoadUserEnv

REM ---- [0/5] Ollama (port 11434, C:\Users\DELL\AppData\Local\Programs\Ollama\ollama.exe): kiem tra + start bang python ----
echo [0/5] Kiem tra Ollama (BGE-M3 embedding)...
if exist "C:\Users\DELL\AppData\Local\Programs\Ollama\ollama.exe" (
    ".venv\Scripts\pythonw.exe" tools\khoi_dong_ollama.py
)
echo    (chi tiet xem logs\khoi_dong_ollama.log)

REM ---- [1/5] Dual Web Servers ----
echo [1/5] Khoi dong Dual Servers (8765 + 8766)...
REM (30/10/2026) may moi Windows 11 26300: wmic da bi loai bo -> dung helper
REM PowerShell ensure_single_instance.ps1 (exit 0 = da co, exit 1 = chua co).
REM 28/10/2026: guard chong khoi dong trung — idempotent tuyet doi.
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "start_dual_servers" >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" tools\spawn_detached.py ".venv\Scripts\pythonw.exe" start_dual_servers.py
ping -n 9 127.0.0.1 >nul

REM ---- [2/5] NetChat Auto-Responder ----
echo [2/5] Khoi dong NetChat Auto-Responder (bot_tony)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "netchat_auto_responder" >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" tools\spawn_detached.py ".venv\Scripts\pythonw.exe" tools\netchat_auto_responder.py
ping -n 4 127.0.0.1 >nul

REM ---- [3/5] Learning Daemon ----
echo [3/5] Khoi dong Learning Daemon (tu hoc moi 5 phut)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "learning_daemon.py" >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" tools\spawn_detached.py ".venv\Scripts\pythonw.exe" tools\learning_daemon.py
ping -n 3 127.0.0.1 >nul

REM ---- [4/5] Watchdog ----
echo [4/5] Khoi dong Watchdog (tu restart, cap 5/gio)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "tools\watchdog.py" >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" tools\spawn_detached.py ".venv\Scripts\pythonw.exe" tools\watchdog.py
ping -n 3 127.0.0.1 >nul

REM ---- [5/5] Backup 2AM (QUAN_AI_BRAIN_BACKUP_2AM) + Report 8AM (Task Scheduler, idempotent) ----
echo [5/5] Dat lich backup 2AM + report 8AM (Task Scheduler)...
".venv\Scripts\python.exe" tools\sched_task_setup.py

echo.
echo ============================================================
echo    HOAN TAT! He thong dang chay ngam (hoan toan an, khong cua so):
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
