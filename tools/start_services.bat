@echo off
REM Start all QUAN AI BRAIN services
echo Starting QUAN AI BRAIN services...
schtasks /Run /TN "QUAN-AI-BRAIN-Server"
schtasks /Run /TN "QUAN-AI-BRAIN-Watchdog"
schtasks /Run /TN "QUAN-AI-BRAIN-Learning"
schtasks /Run /TN "QUAN-AI-BRAIN-Responder"
schtasks /Run /TN "QUAN-AI-BRAIN-Dashboard"
echo ✅ All services triggered