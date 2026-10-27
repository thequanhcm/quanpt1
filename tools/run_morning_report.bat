@echo off
REM Wrapper cho Task Scheduler: bao cao sang 8AM qua NetChat (user-level)
cd /d "E:\AI\QUAN AI BRAIN"
.venv\Scripts\python.exe tools\morning_report.py >> logs\morning_report.log 2>&1
