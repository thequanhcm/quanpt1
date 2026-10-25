# QUAN AI BRAIN 24/7 Setup - Hướng dẫn chi tiết

## 🎯 MỤC TIÊU
Setup 2 Task Scheduler để hệ thống chạy 24/7:
1. **QUAN_AIBRAIN_Watchdog** - Auto-restart server khi crash
2. **QUAN_AIBRAIN_Backup** - Backup database hàng ngày lúc 2AM

---

## 📋 BƯỚC 1: SETUP WATCHDOG (1 phút)

### 1.1 Mở Task Scheduler
- Nhấn `Windows + R`
- Gõ: `taskschd.msc`
- Nhấn **Enter**

### 1.2 Tạo Task mới
- Ở cột phải, click **Create Task...** (KHÔNG phải "Create Basic Task")

### 1.3 Tab General
- **Name:** `QUAN_AIBRAIN_Watchdog`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**
- **Configure for:** Windows 10

### 1.4 Tab Triggers
- Click **New...**
- **Begin the task:** `At logon`
- **Delay task:** `5 minutes`
- ✅ Check: **Enabled**
- Click **OK**

### 1.5 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\watchdog.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 1.6 Tab Conditions
- ❌ **Uncheck:** `Start the task only if the computer is on AC power`

### 1.7 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- ✅ Check: `If the task fails, restart every:` `1 minute`
- **Attempt to restart up to:** `3 times`
- ✅ Check: `If running this task exceeds:` `1 hour` → `Stop the task`
- Click **OK**

### 1.8 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 2: SETUP BACKUP (1 phút)

### 2.1 Tạo Task mới
- Click **Create Task...**

### 2.2 Tab General
- **Name:** `QUAN_AIBRAIN_Backup`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**

### 2.3 Tab Triggers
- Click **New...**
- **Begin the task:** `Daily`
- **Recur every:** `1 day`
- **Start:** `2:00:00 AM`
- ✅ Check: **Enabled**
- Click **OK**

### 2.4 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\backup_database.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 2.5 Tab Conditions
- ❌ **Uncheck:** `Start the task only if the computer is on AC power`

### 2.6 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- Click **OK**

### 2.7 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 3: KIỂM TRA (30 giây)

### 3.1 Verify tasks
- Trong Task Scheduler, ở cột trái, click **Task Scheduler Library**
- Tìm 2 tasks:
  - `QUAN_AIBRAIN_Watchdog`
  - `QUAN_AIBRAIN_Backup`
- **Status** phải là: **Ready**

### 3.2 Test Watchdog
- Mở CMD, chạy:
  ```bash
  schtasks /Run /TN "QUAN_AIBRAIN_Watchdog"
  ```
- Đợi 10 giây
- Check log: `E:\AI\QUAN AI BRAIN\logs\watchdog.log`
- Phải có dòng: `QUAN AI BRAIN Watchdog Starting`

### 3.3 Test Backup (thủ công)
- Chạy:
  ```bash
  schtasks /Run /TN "QUAN_AIBRAIN_Backup"
  ```
- Check folder: `E:\AI\QUAN AI BRAIN\backups\`
- Phải có file: `brain_YYYYMMDD_HHMMSS.db`

---

## 📋 BƯỚC 4: MỞ HEALTH DASHBOARD

### 4.1 Start server (nếu chưa chạy)
```bash
cd E:\AI\QUAN AI BRAIN
./.venv/Scripts/python.exe src/quan_ai_brain/web/server.py
```

### 4.2 Mở dashboard
- Browser: `http://127.0.0.1:8765/health_dashboard.html`
- Dashboard sẽ hiển thị:
  - Ollama status
  - Web server status
  - Pi 5 connection
  - Database size

### 4.3 Auto-refresh
- Dashboard tự động refresh mỗi 30 giây

---

## 📋 BƯỚC 5: MONITORING HẰNG NGÀY

### 5.1 Check logs
- **Watchdog log:** `E:\AI\QUAN AI BRAIN\logs\watchdog.log`
- **Resource monitor:** `E:\AI\QUAN AI BRAIN\logs\resource_monitor.log`
- **Backup log:** `E:\AI\QUAN AI BRAIN\logs\backup.log`

### 5.2 Check backups
- Folder: `E:\AI\QUAN AI BRAIN\backups\`
- Nên có 1 backup mỗi ngày
- Giữ lại 30 backup gần nhất

### 5.3 Health dashboard
- Mở: `http://127.0.0.1:8765/health_dashboard.html`
- Check tất cả components đều **Healthy**

---

## 🚨 XỬ LÝ SỰ CỐ

### Nếu Watchdog không chạy:
1. Check Task Scheduler → Task status
2. Check log: `logs/watchdog.log`
3. Chạy thủ công: `python tools/watchdog.py`

### Nếu Backup không chạy:
1. Check Task Scheduler → Last Run Result
2. Chạy thủ công: `python tools/backup_database.py`
3. Check disk space

### Nếu server không start:
1. Check log: `logs/watchdog.log`
2. Check Ollama: `ollama list`
3. Check port 8765: `netstat -ano | findstr :8765`

---

## ✅ CHECKLIST HOÀN THÀNH

- [ ] Task `QUAN_AIBRAIN_Watchdog` created (Status: Ready)
- [ ] Task `QUAN_AIBRAIN_Backup` created (Status: Ready)
- [ ] Watchdog log exists: `logs/watchdog.log`
- [ ] Backup folder exists: `backups/`
- [ ] Health dashboard opens: `http://127.0.0.1:8765/health_dashboard.html`
- [ ] All components show **Healthy**

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề:
1. Check logs trong `E:\AI\QUAN AI BRAIN\logs\`
2. Check Task Scheduler → Last Run Result
3. Chạy test manual: `python tools/watchdog.py`
4. Report lỗi với log file

---

**Ngày setup:** 2026-10-25  
**Version:** 1.0  
**Author:** TONY PHAM (QUAN AI BRAIN)