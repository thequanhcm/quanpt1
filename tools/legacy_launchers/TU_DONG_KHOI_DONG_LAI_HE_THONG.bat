@echo off
chcp 65001 >nul
cd /d "%~dp0"
title QUAN AI BRAIN — TU DONG KHOI DONG LAI HE THONG
color 0A

echo ======================================================================
echo    QUAN AI BRAIN — LỆNH TỰ ĐỘNG KHỞI ĐỘNG LẠI HỆ THỐNG AN TOÀN
echo ======================================================================
echo  Chủ nhân: Quanpt1
echo  Chức năng: Quét mã mới, dừng cổng cũ, khởi động lại Port 8766 và 8765
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe tools\restart_system.py %*
) else (
    python tools\restart_system.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Canh bao] Khoi dong lai that bai hoac co loi trong ma nguon moi!
    pause
) else (
    timeout /t 5 >nul
)
