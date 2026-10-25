@echo off
cd /d "%~dp0"
title QUAN AI BRAIN - Khoi Dong Ollama

echo ======================================================================
echo           QUAN AI BRAIN - KHOI DONG DICH VU LOCAL OLLAMA
echo ======================================================================
echo.

echo [1/3] Kiem tra dich vu Ollama tren cong 11434...
netstat -ano | findstr 11434 >nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Dich vu Ollama da dang hoat dong tren cong 127.0.0.1:11434.
    goto check_health
)

echo [2/3] Dang khoi dong Ollama tu E:\AI\Ollama...
if exist "E:\AI\Ollama\ollama app.exe" (
    start "" "E:\AI\Ollama\ollama app.exe"
) else if exist "E:\AI\Ollama\ollama.exe" (
    start "Ollama Server" /min "E:\AI\Ollama\ollama.exe" serve
) else (
    echo [LOI] Khong tim thay Ollama tai E:\AI\Ollama!
    pause
    exit /b 1
)

echo [Doi] Dang cho Ollama san sang...
set RETRIES=0
:wait_loop
timeout /t 2 /nobreak >nul
netstat -ano | findstr 11434 >nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Ollama da khoi dong thanh cong!
    goto check_health
)
set /a RETRIES+=1
if %RETRIES% lss 8 (
    echo ... dang cho ket noi (lan %RETRIES%/8)...
    goto wait_loop
)

:check_health
echo.
echo [3/3] Kiem tra trang thai va danh sach model tu QUAN AI BRAIN:
echo ----------------------------------------------------------------------
if exist ".venv\Scripts\python.exe" (
    set PYTHONIOENCODING=utf-8
    .venv\Scripts\python.exe -m quan_ai_brain.cli llm-health
)
echo ----------------------------------------------------------------------
echo.
echo [HOAN TAT] Ollama da san sang phuc vu.
echo.
pause
