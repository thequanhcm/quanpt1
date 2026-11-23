@echo off
chcp 65001 >nul
title CHERRY - TAT (dong tat ca)
REM ============================================================
REM  T?T CHERRY ? ??ng to?n b? th?nh ph?n Cherry tr?n PC
REM  (owner 19/11: Cherry ch? ch?y khi b?t tay ? file n?y t?t s?ch)
REM  T?t: Dual Servers + NetChat Responder + Learning + Watchdog
REM       + Cherry Autonomous (n?u c?n s?t)
REM  KH?NG ??ng: Task Scheduler backup 2AM / report 8AM / Pi5 monitor
REM  KH?NG ??ng: Pi5 (192.168.1.21) ? kiosk Pi5 v?n ch?y ri?ng
REM ============================================================
cd /d "E:\BRAIN"
echo Dang tat Cherry...

REM T?t theo t?n script (c? python.exe l?n pythonw.exe, c? venv l?n wrapper)
for %%S in ("start_dual_servers.py" "cherry_autonomous.py" "watchdog.py" "netchat_auto_responder.py" "learning_daemon.py") do (
    wmic process where "commandline like '%%~S'" delete >nul 2>&1
)

REM C?a s? console Cherry (start "CHERRY-...") ??ng khi process ch?t ? x?a title r?ng
taskkill /FI "WINDOWTITLE eq CHERRY-*" /T /F >nul 2>&1

REM Ki?m tra s?ch
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 8765); $c.Close(); 'STILL RUNNING' } catch { 'CHERRY DA TAT' }"
echo.
echo Hoan tat. Cherry tat toan bo. Dashboard 8765/8766 dong.
pause
exit /b 0
