@echo off
REM Mirror workspace -> F:\BRAIN hằng ngày 02:30 (Task Scheduler)
cd /d "D:\AI\AI Quanpt1 2026\BRAIN"
.venv\Scripts\python.exe tools\mirror_workspace_to_f.py >> logs\mirror_to_f.log 2>&1
