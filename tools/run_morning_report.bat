@echo off
REM Wrapper cho Task Scheduler: bao cao sang 8AM qua NetChat (user-level)
REM 28/10/2026: Task Scheduler console mặc định cp1252 → print tiếng Việt crash
REM (UnicodeEncodeError hằng ngày). Buộc UTF-8 ở cả PYTHONIOENCODING lẫn chcp.
cd /d "E:\AI\QUAN AI BRAIN"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
.venv\Scripts\python.exe tools\morning_report.py >> logs\morning_report.log 2>&1
