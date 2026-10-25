@echo off
REM Start server with NETMIND_EXTERNAL_DATA_ALLOWED=true
set NETMIND_EXTERNAL_DATA_ALLOWED=true
cd /d "E:\AI\QUAN AI BRAIN"
call .venv\Scripts\python.exe src\quan_ai_brain\web\server.py