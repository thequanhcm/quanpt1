@echo off
chcp 65001 >nul
title QUAN AI BRAIN — PHONG DIEU HANH & THAM VAN (PORT 8766)
color 0B
echo ======================================================================
echo    QUAN AI BRAIN — PHÒNG ĐIỀU HÀNH & THAM VẤN CHỦ NHÂN (PORT 8766)
echo ======================================================================
echo  Bản sao Nhân sự Số của Quanpt1 — Tự học liên tục & Tham vấn trực tiếp
echo  URL: http://127.0.0.1:8766/
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [Khoi dong] Dang kich hoat moi truong Python 3.11...
    .venv\Scripts\python.exe run_executive_desk.py
) else (
    echo [Loi] Khong tim thay virtualenv .venv!
    pause
)
