@echo off
REM Wrapper cho Task Scheduler: backup DB 2AM hằng ngày (user-level, không cần Admin)
cd /d "E:\BRAIN"
.venv\Scripts\pythonw.exe tools\backup_database.py >> logs\backup.log 2>&1
