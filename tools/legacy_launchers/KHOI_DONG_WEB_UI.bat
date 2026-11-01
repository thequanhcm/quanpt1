@echo off
cd /d "%~dp0"
title QUAN AI BRAIN - Web UI Dashboard

echo ======================================================================
echo        QUAN AI BRAIN - KHOI DONG GIAO DIEN WEB CHAT VOI VOICE
echo ======================================================================
echo.

REM 1. Kiem tra va khoi dong Ollama neu chua chay
netstat -ano | findstr 11434 >nul
if %ERRORLEVEL% neq 0 (
    echo [1/2] Dang bat dich vu Ollama tai E:\AI\Ollama...
    if exist "E:\AI\Ollama\ollama app.exe" (
        start "" "E:\AI\Ollama\ollama app.exe"
    ) else if exist "E:\AI\Ollama\ollama.exe" (
        start "Ollama Server" /min "E:\AI\Ollama\ollama.exe" serve
    )
    timeout /t 3 /nobreak >nul
) else (
    echo [1/2] Ollama da dang hoat dong tren cong 11434.
)

echo [2/2] Dang khoi dong Web UI Server va mo Trinh duyet...
echo.
echo URL: http://127.0.0.1:8765
echo (Nhan Ctrl+C de dung may chu bat cu luc nao)
echo ----------------------------------------------------------------------

set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe run_web_ui.py

pause
