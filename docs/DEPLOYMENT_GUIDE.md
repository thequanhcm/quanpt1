# QUAN AI BRAIN — Deployment Guide

**Version:** 1.0  
**Date:** 2026-10-28  
**Status:** Production Ready ✅

---

## Quick Start (5 phút)

### Bước 1: Enable Pi 5 SSH

**Yêu cầu:** Console access (màn hình + bàn phím)

```bash
# Trên Pi 5 console:
cd ~/tools
sudo chmod +x enable_pi5_ssh.sh
sudo ./enable_pi5_ssh.sh

# Kết quả:
✅ SSH service started
✅ SSH enabled for auto-start
# IP: 192.168.1.10
```

**Verify:**
```bash
# Từ PC:
ssh quanpt1@192.168.1.10
# Nếu kết nối được → thành công
```

---

### Bước 2: Setup Windows Services

**Yêu cầu:** Administrator privileges

```cmd
# Right-click → Run as Administrator:
cd "E:\AI\QUAN AI BRAIN"
tools\setup_windows_services.bat

# Kết quả:
✅ Server task created
✅ Watchdog task created
✅ Learning task created
✅ Responder task created
✅ Dashboard task created
```

**Verify:**
```cmd
# List tasks:
schtasks /Query /TN "QUAN-AI-BRAIN-*"

# Health check:
python tools\health_check.py
```

---

### Bước 3: Reboot & Auto-start Test

```cmd
# Reboot PC:
shutdown /r /t 0

# Sau khi reboot, kiểm tra:
python tools\health_check.py

# Kết quả mong đợi:
✅ server ONLINE (port 8765)
✅ watchdog ONLINE (port 17236)
✅ learning ONLINE (port 7724)
✅ responder ONLINE
✅ dashboard ONLINE (port 8766)
```

---

## Detailed Deployment Steps

### Phase 1: Pre-Deployment Checklist

#### 1.1 System Requirements

| Component | Requirement | Status |
|-----------|-------------|--------|
| **OS** | Windows 10/11 | ✅ |
| **Python** | 3.11+ | ✅ |
| **RAM** | 8GB+ | ✅ |
| **GPU** | NVIDIA 4GB+ (optional) | ✅ T1000 4GB |
| **Disk** | 50GB free | ✅ |
| **Network** | Internet (for Ollama cloud) | ✅ |

#### 1.2 Dependencies

```bash
# Activate venv:
cd "E:\AI\QUAN AI BRAIN"
.venv\Scripts\activate

# Install all dependencies:
pip install -e ".[all]"

# Verify:
python -c "import chromadb; print('ChromaDB OK')"
python -c "import ollama; print('Ollama OK')"
```

#### 1.3 Environment Variables

```bash
# Create .env file:
cd "E:\AI\QUAN AI BRAIN"
copy .env.example .env

# Edit .env:
NOTEPAD .env

# Required variables:
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=your_region
OLLAMA_HOST=http://localhost:11434
```

---

### Phase 2: Database Setup

#### 2.1 Initialize brain.db

```bash
# Check if exists:
dir data\brain.db

# If not exists, initialize:
python -c "from quan_ai_brain.memory.models import *; print('DB ready')"
```

#### 2.2 Initialize vector_db

```bash
# Run initialization:
python tools\init_vector_memory.py

# Expected output:
✅ Vector store initialized at: data/vector_db
✅ Collection: quan_ai_brain_memory
✅ Current chunks: 0
```

#### 2.3 Ingest existing knowledge

```bash
# Ingest brain.db into vector_db:
python tools\ingest_brain_db.py

# Expected output:
✅ Found 150 knowledge units in brain.db
✅ Ingested 50 chunks, 0 errors
✅ Vector DB now has 53 total chunks
```

#### 2.4 Initialize quarantine.db

```bash
# Auto-created on first use
# Verify:
dir data\quarantine.db
```

---

### Phase 3: Service Configuration

#### 3.1 Task Scheduler Details

Each task configured with:

- **Trigger:** ONSTART (Windows boot)
- **User:** SYSTEM
- **Privileges:** Highest
- **Restart:** On failure (1 attempt, 60s)
- **Hidden:** Yes

#### 3.2 Manual Service Control

```cmd
# Start all:
tools\start_services.bat

# Stop all:
tools\stop_services.bat

# Restart specific:
schtasks /End /TN "QUAN-AI-BRAIN-Server"
schtasks /Run /TN "QUAN-AI-BRAIN-Server"
```

#### 3.3 Log Files Location

```
E:\AI\QUAN AI BRAIN\logs\
├── server.log
├── watchdog.log
├── learning.log
├── responder.log
├── dashboard.log
├── audit.log
└── uat_YYYY-MM-DD.json
```

**Log rotation:** 5 files, 10MB each

---

### Phase 4: Verification

#### 4.1 Health Check

```bash
python tools\health_check.py

# Expected output:
============================================================
QUAN AI BRAIN — Health Check
============================================================

📊 SERVICE STATUS
------------------------------------------------------------
server          ✅ ONLINE (port 8765 listening)
watchdog        ✅ ONLINE (port 17236 listening)
learning        ✅ ONLINE (port 7724 listening)
responder       ✅ ONLINE
dashboard       ✅ ONLINE (port 8766 listening)

📅 TASK SCHEDULER STATUS
------------------------------------------------------------
QUAN-AI-BRAIN-Server      ✅ Task configured
QUAN-AI-BRAIN-Watchdog    ✅ Task configured
QUAN-AI-BRAIN-Learning    ✅ Task configured
QUAN-AI-BRAIN-Responder   ✅ Task configured
QUAN-AI-BRAIN-Dashboard   ✅ Task configured

============================================================
SUMMARY
============================================================
Services running: 5/5
Tasks configured: 5/5
Overall status: ✅ ALL ONLINE
```

#### 4.2 API Endpoints

```bash
# Test server:
curl http://127.0.0.1:8765/api/health

# Test dashboard:
curl http://127.0.0.1:8766/api/health

# Test Ollama:
curl http://localhost:11434/api/tags
```

#### 4.3 NetChat Integration

```bash
# Verify responder connected:
type logs\responder.log | findstr "Monitoring"

# Send test message via NetChat:
# Channel: "Trợ lý Tony Pham"
# Message: "trạng thái"
# Expected: System status response
```

---

### Phase 5: Troubleshooting

#### Issue 1: Services Not Starting

**Symptoms:** `❌ OFFLINE` in health check

**Solution:**
```cmd
# Check Task Scheduler:
schtasks /Query /TN "QUAN-AI-BRAIN-Server" /V

# Check logs:
type logs\server.log

# Re-run setup as Administrator:
tools\setup_windows_services.bat
```

#### Issue 2: Port Already in Use

**Symptoms:** `Address already in use` error

**Solution:**
```cmd
# Find process using port:
netstat -ano | findstr :8765

# Kill process:
taskkill /F /PID <PID>

# Or change port in config
```

#### Issue 3: Ollama Not Responding

**Symptoms:** `Connection refused`

**Solution:**
```bash
# Check Ollama:
ollama list

# Start Ollama:
ollama serve

# Pull model:
ollama pull bge-m3
```

#### Issue 4: Permission Denied

**Symptoms:** `Access is denied`

**Solution:**
```cmd
# Run as Administrator
# Check Windows Security logs
# Verify Python path in batch files
```

---

### Phase 6: Monitoring

#### 6.1 Daily Checks

```bash
# Morning check:
python tools\health_check.py

# Check logs:
type logs\server.log | more

# Check disk space:
wmic logicaldisk get size,freespace,caption
```

#### 6.2 Weekly Review

```bash
# Generate weekly report:
python tools\uat_runner.py

# Review issues:
type data\uat_logs\uat_*.json | findstr "issue"

# Check quarantine:
python -c "from quan_ai_brain.memory.quarantine_store import *; s=create_quarantine_store(); print(s.get_stats())"
```

#### 6.3 Monthly Maintenance

```bash
# Rotate logs:
# (Automatic, but can force)

# Backup databases:
copy data\brain.db data\backup\brain_YYYY-MM-DD.db
copy data\quarantine.db data\backup\quarantine_YYYY-MM-DD.db

# Clean old logs:
forfiles /p logs /s /m *.log /d -30 /c "cmd /c del @path"
```

---

## Rollback Plan

### If Deployment Fails

```cmd
# 1. Stop all services:
tools\stop_services.bat

# 2. Remove tasks:
tools\remove_services.bat

# 3. Restore from backup:
copy data\backup\* data\

# 4. Revert code:
git reset --hard HEAD~1

# 5. Re-run setup:
tools\setup_windows_services.bat
```

---

## Support

### Contact
- **Email:** quanpt1@viettel.com.vn
- **NetChat:** "Trợ lý Tony Pham" channel
- **Logs:** `logs/` directory

### Emergency Commands

```cmd
# Emergency stop:
tools\stop_services.bat

# Freeze system:
echo "freeze" | python tools\netchat_auto_responder.py

# Kill all Python:
taskkill /F /IM python.exe
```

---

## Success Criteria

Deployment successful when:

- ✅ All 5 services ONLINE
- ✅ All 5 tasks configured
- ✅ Health check passes
- ✅ Auto-start works after reboot
- ✅ NetChat responds to commands
- ✅ Logs rotating properly
- ✅ No errors in last 24h

---

**Deployment Date:** _________________  
**Deployed By:** _________________  
**Verified By:** _________________  
**Status:** ☐ Ready ☐ Deployed ☐ Verified

---

**Next:** Run integration tests → Begin UAT week