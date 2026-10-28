# QUAN AI BRAIN — One-Click Installation Guide

**Version:** 1.0  
**Date:** 2026-10-28  
**For:** New computer setup

---

## 🚀 Quick Installation (1 Click)

### Step 1: Download QUAN AI BRAIN

```bash
git clone https://github.com/thequanhcm/quanpt1.git "E:\AI\QUAN AI BRAIN"
cd "E:\AI\QUAN AI BRAIN"
```

### Step 2: Run One-Click Installer

**Right-click** on `INSTALL_ONE_CLICK.bat`  
**Select:** "Run as administrator"  
**Wait:** ~2-3 minutes for completion

The script will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Initialize databases (brain.db, vector_db)
- ✅ Create Task Scheduler tasks
- ✅ Run health check

### Step 3: Reboot

```bash
shutdown /r /t 0
```

### Step 4: Verify

After reboot, services will auto-start. Run:

```cmd
cd "E:\AI\QUAN AI BRAIN"
python tools\health_check.py
```

Expected output:
```
✅ server ONLINE
✅ watchdog ONLINE
✅ learning ONLINE
✅ responder ONLINE
✅ dashboard ONLINE
```

---

## 📋 Manual Installation (If One-Click Fails)

### Prerequisites

- Windows 10/11
- Python 3.11+
- Administrator privileges
- Internet connection

### Step 1: Install Python

Download from: https://www.python.org/downloads/

During installation:
- ✅ Check "Add Python to PATH"
- ✅ Check "Install for all users"

### Step 2: Clone Repository

```bash
git clone https://github.com/thequanhcm/quanpt1.git "E:\AI\QUAN AI BRAIN"
cd "E:\AI\QUAN AI BRAIN"
```

### Step 3: Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
pip install -e ".[all]"
```

### Step 5: Initialize Databases

```bash
mkdir data logs data\uat_logs
python tools\init_vector_memory.py
```

### Step 6: Setup Services

**Right-click** `tools\setup_windows_services.bat`  
**Select:** "Run as administrator"

### Step 7: Verify

```bash
python tools\health_check.py
```

---

## 🐛 Troubleshooting

### Issue: Python not found

**Solution:**
1. Install Python 3.11+ from python.org
2. Check "Add to PATH" during installation
3. Restart terminal

### Issue: Permission denied

**Solution:**
- Run script as Administrator
- Right-click → "Run as administrator"

### Issue: Port already in use

**Solution:**
```cmd
netstat -ano | findstr :8765
taskkill /F /PID <PID>
```

### Issue: Dependencies fail to install

**Solution:**
```bash
pip install --upgrade pip
pip install -e ".[all]" --force-reinstall
```

---

## ✅ Post-Installation Checklist

- [ ] All 5 services ONLINE
- [ ] Dashboard accessible at http://127.0.0.1:8766/
- [ ] NetChat bot responding
- [ ] Logs being written to `logs/`
- [ ] Auto-start works after reboot

---

## 📞 Support

- **Email:** quanpt1@viettel.com.vn
- **Documentation:** `HDSD/trợ lý số/`
- **Logs:** `logs/` directory

---

**Installation complete!** 🎉