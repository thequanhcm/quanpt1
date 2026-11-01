@echo off
REM Wrapper cho Task Scheduler: backup DB 2AM hằng ngày (user-level, không cần Admin)
cd /d "D:\AI\AI Quanpt1 2026\BRAIN"
.venv\Scripts\python.exe tools\backup_database.py >> logs\backup.log 2>&1
