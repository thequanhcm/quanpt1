# QUAN AI BRAIN — Deployment Instructions

**Date:** 2026-10-28  
**Status:** Ready for deployment ✅

---

## ⚠️ IMPORTANT: Administrator Required

Windows Task Scheduler setup requires **Administrator privileges**.

---

## 🚀 Quick Deployment (3 Steps)

### Step 1: Enable Pi 5 SSH (Optional - if using Pi 5)

**On Pi 5 console (monitor + keyboard):**

```bash
cd ~/tools
sudo chmod +x enable_pi5_ssh.sh
sudo ./enable_pi5_ssh.sh
```

**Expected output:**
```
✅ SSH service started
✅ SSH enabled for auto-start
```

**Verify from PC:**
```bash
ssh quanpt1@192.168.1.10
# Should connect without error
```

---

### Step 2: Setup Windows Services (Administrator Required)

**Method A: Using Batch File (Recommended)**

1. **Right-click** on `tools\setup_windows_services.bat`
2. **Select** "Run as administrator"
3. **Click** "Yes" on UAC prompt

**Expected output:**
```
============================================
QUAN AI BRAIN — Windows Service Setup
============================================

✅ Server task created
✅ Watchdog task created
✅ Learning task created
✅ Responder task created
✅ Dashboard task created

All 5 tasks configured successfully!
```

**Method B: Using PowerShell (Alternative)**

1. **Open PowerShell as Administrator:**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Run:**
```powershell
cd "E:\AI\QUAN AI BRAIN"
.\tools\setup_windows_services.bat
```

---

### Step 3: Verify Deployment

**Run health check:**
```cmd
cd "E:\AI\QUAN AI BRAIN"
python tools\health_check.py
```

**Expected output:**
```
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

---

## 🔄 Test Auto-Start

**Reboot PC:**
```cmd
shutdown /r /t 0
```

**After reboot, verify:**
```cmd
cd "E:\AI\QUAN AI BRAIN"
python tools\health_check.py
```

All services should be **ONLINE** automatically!

---

## 📋 Manual Service Control

### Start All Services
```cmd
tools\start_services.bat
```

### Stop All Services
```cmd
tools\stop_services.bat
```

### Check Specific Task
```cmd
schtasks /Query /TN "QUAN-AI-BRAIN-Server" /V
```

### List All Tasks
```cmd
schtasks /Query /TN "QUAN-AI-BRAIN-*"
```

---

## 🐛 Troubleshooting

### Issue: "Access is denied"

**Solution:** Run as Administrator

### Issue: "Task already exists"

**Solution:**
```cmd
# Remove existing tasks first:
tools\remove_services.bat

# Then re-run setup:
tools\setup_windows_services.bat
```

### Issue: Services not starting after reboot

**Solution:**
1. Check Task Scheduler GUI:
   - Press `Win + R`
   - Type `taskschd.msc`
   - Look for "QUAN-AI-BRAIN-*" tasks
   - Check "Last Result" column

2. Check logs:
```cmd
type logs\server.log
type logs\watchdog.log
```

3. Re-run setup as Administrator

### Issue: Port already in use

**Solution:**
```cmd
# Find process using port:
netstat -ano | findstr :8765

# Kill process:
taskkill /F /PID <PID>

# Or change port in config
```

---

## 📊 Post-Deployment Checklist

After deployment, verify:

- [ ] All 5 services ONLINE
- [ ] All 5 tasks configured in Task Scheduler
- [ ] Health check passes
- [ ] Auto-start works after reboot
- [ ] NetChat responds to commands
- [ ] Logs rotating properly
- [ ] No errors in last 24h

---

## 🎯 Next Steps

1. **Run Integration Tests:**
```cmd
pytest tests/test_v37_integration.py -v
```

2. **Start UAT Week:**
```cmd
python tools\uat_runner.py
```

3. **Monitor Daily:**
```cmd
python tools\health_check.py
```

4. **Review Weekly:**
```cmd
type data\uat_logs\uat_*.json
```

---

## 📞 Support

**Logs Location:**
- `logs/server.log`
- `logs/watchdog.log`
- `logs/learning.log`
- `logs/responder.log`
- `logs/dashboard.log`
- `logs/audit.log`

**UAT Logs:**
- `data/uat_logs/uat_YYYY-MM-DD.json`

**Contact:**
- **Email:** quanpt1@viettel.com.vn
- **NetChat:** "TONY" channel

---

## ✅ Deployment Complete When:

- ✅ All 5 services show ONLINE
- ✅ All 5 tasks configured
- ✅ Health check passes
- ✅ Auto-start verified after reboot
- ✅ Integration tests pass
- ✅ UAT week completed

---

**Ready to deploy!** 🚀

**Next:** Run `tools\setup_windows_services.bat` as Administrator