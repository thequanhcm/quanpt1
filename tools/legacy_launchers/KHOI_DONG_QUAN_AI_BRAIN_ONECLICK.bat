@echo off
chcp 65001 >nul
setlocal EnableExtensions
title QUAN AI BRAIN - 1-CLICK MASTER SYSTEM LAUNCHER (QUANPT1)
color 0B

cd /d "%~dp0"

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

.venv\Scripts\python.exe tools\oneclick_orchestrator.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [THONG BAO] Tien trinh ket thuc voi ma thoat: %ERRORLEVEL%
    pause
)
