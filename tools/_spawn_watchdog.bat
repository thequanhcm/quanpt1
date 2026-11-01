@echo off
REM Spawn watchdog độc lập (không bị job object cha giết) — dùng bởi TONY khi vận hành
cd /d "D:\AI\AI Quanpt1 2026\BRAIN"
start "QAB-Watchdog" /MIN ".venv\Scripts\pythonw.exe" "tools\watchdog.py"
exit /b 0
