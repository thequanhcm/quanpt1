@echo off
chcp 65001 >nul
title QUAN AI BRAIN — KIEM TRA & TEST AM THANH RASPBERRY PI 5
color 0B
echo ======================================================================
echo    QUAN AI BRAIN — KIỂM TRA & TEST ÂM THANH RASPBERRY PI 5
echo ======================================================================
echo  Mục tiêu: Raspberry Pi 5 (IP: 192.168.1.21 : 8768)
echo  Kiểm tra: Kết nối mạng, Mixer âm lượng, TTS Giọng nữ tiếng Việt, Loa
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [Dang chay] Tien trinh kiem tra va phat am thanh...
    echo.
    .venv\Scripts\python.exe tools\test_pi5_audio.py %*
) else (
    echo [Loi] Khong tim thay virtualenv .venv!
)

echo.
pause
