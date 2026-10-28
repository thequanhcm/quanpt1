@echo off
REM Remove all QUAN AI BRAIN service tasks
echo Removing QUAN AI BRAIN service tasks...
schtasks /Delete /TN "QUAN-AI-BRAIN-Server" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Watchdog" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Learning" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Responder" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Dashboard" /F
echo ✅ All service tasks removed