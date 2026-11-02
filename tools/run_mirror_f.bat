@echo off
REM Mirror workspace -> F:\BRAIN hằng ngày 02:30 (Task Scheduler)
cd /d "E:\BRAIN"
.venv\Scripts\python.exe tools\mirror_workspace_to_f.py >> logs\mirror_to_f.log 2>&1
