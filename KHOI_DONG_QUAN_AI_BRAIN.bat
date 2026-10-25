@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul
title QUAN AI BRAIN - 1-CLICK MASTER SYSTEM LAUNCHER (QUANPT1)
color 0B

set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo ======================================================================
    echo [LOI] Khong tim thay moi truong Python ao .venv tai thu muc:
    echo %~dp0
    echo Vui long kiem tra lai workspace.
    echo ======================================================================
    pause
    exit /b 1
)

echo ======================================================================
echo    QUAN AI BRAIN - KICH HOAT HE THONG TOAN DIEN (1-CLICK MASTER)
echo          CHU SO HUU: QUANPT1 - PHIEN BAN DIEU HANH V4 EVOLUTION
echo ======================================================================
echo  1. Kiem tra va Kich hoat Loi suy luan Ollama LLM (:11434)
echo  2. Khoi dong May chu Dieu hanh PC Core Executive Desk (:8766)
echo  3. Ket noi va Dong bo Pi 5: Phat loa Chao + Tu kiem tra Mic/Camera
echo  4. Tu dong mo Phong Dieu hanh Cockpit tren trinh duyet Chrome
echo ======================================================================
echo.

.venv\Scripts\python.exe tools\oneclick_orchestrator.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [THONG BAO] Tien trinh ket thuc voi ma thoat: %ERRORLEVEL%
    pause
)
