@echo off
cd /d "E:\BRAIN"
start "QAB-DualServers" /MIN ".venv\Scripts\pythonw.exe" "start_dual_servers.py"
exit /b 0
