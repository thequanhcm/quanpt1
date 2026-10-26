@echo off
title QUAN AI BRAIN - 24/7 ONE-CLICK START (QUANPT1)
cd /d "E:\AI\QUAN AI BRAIN"
color 0A

echo ============================================================
echo    QUAN AI BRAIN - KHOI DONG 24/7 (ONE-CLICK)
echo    Tu dong start: Server + NetChat Bot + Learning + Watchdog
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv tai E:\AI\QUAN AI BRAIN
    pause
    exit /b 1
)

REM [1/4] Web Server (co NETMIND_EXTERNAL_DATA_ALLOWED=true san trong script)
echo [1/4] Khoi dong PC Core Server (port 8765)...
start "QAB-Server" /MIN .venv\Scripts\python.exe start_server_fixed.py
timeout /t 8 /nobreak >nul

REM [2/4] NetChat Auto-Responder (bot Tony Pham)
echo [2/4] Khoi dong NetChat Auto-Responder (bot_quanpt1)...
start "QAB-NetChatBot" /MIN .venv\Scripts\python.exe tools\netchat_auto_responder.py
timeout /t 3 /nobreak >nul

REM [3/4] Learning Daemon (tu hoc 24/7)
echo [3/4] Khoi dong Learning Daemon (tu hoc moi 5 phut)...
start "QAB-Learning" /MIN .venv\Scripts\python.exe tools\learning_daemon.py
timeout /t 2 /nobreak >nul

REM [4/4] Watchdog (tu restart server neu crash)
echo [4/4] Khoi dong Watchdog (health check moi 60s)...
start "QAB-Watchdog" /MIN .venv\Scripts\python.exe tools\watchdog.py

echo.
echo ============================================================
echo    HOAN TAT! He thong dang chay ngam (4 cua so MINIMIZED):
echo      - QAB-Server      : http://127.0.0.1:8765
echo      - QAB-NetChatBot  : Bot Tony Pham (NetChat)
echo      - QAB-Learning    : Tu hoc lien tuc
echo      - QAB-Watchdog    : Tu restart neu crash
echo.
echo    KINH TE MONITOR: http://127.0.0.1:8765/health_dashboard.html
echo    DE DUNG HE THONG: Dong 4 cua so MINIMIZED tuong ung.
echo ============================================================
echo.
REM Tu dong dong cua so launcher nay sau 15 giay
timeout /t 15 >nul
exit /b 0
