@echo off
REM Wrapper cho Task Scheduler: backup DB 2AM hằng ngày (user-level, không cần Admin)
cd /d "E:\AI\QUAN AI BRAIN"
.venv\Scripts\python.exe tools\backup_database.py >> logs\backup.log 2>&1
