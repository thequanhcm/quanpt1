@echo off
REM CHERRY AUTONOMOUS MODE - khoi dongqua spawn_detached (idempotent qua marker)
cd /d "E:\BRAIN"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ensure_single_instance.ps1" -Marker "cherry_autonomous" >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" tools\spawn_detached.py ".venv\Scripts\pythonw.exe" tools\cherry_autonomous.py
