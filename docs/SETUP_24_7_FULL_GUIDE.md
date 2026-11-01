# HƯỚNG DẪN SETUP QUAN AI BRAIN 24/7 — CHI TIẾT TỪNG BƯỚC

## 🎯 MỤC TIÊU
Setup 4 Task Scheduler để hệ thống chạy 24/7 tự động:
1. **QUAN_AIBRAIN_Watchdog** — Auto-restart server khi crash
2. **QUAN_AIBRAIN_Backup** — Backup database hàng ngày lúc 2AM
3. **QUAN_AIBRAIN_Learning** — Continuous learning 24/7
4. **QUAN_AIBRAIN_ResourceMonitor** — Monitor CPU/MEM/DISK/GPU mỗi 5 phút

---

## 📋 BƯỚC 1: MỞ TASK SCHEDULER

1. Nhấn `Windows + R`
2. Gõ: `taskschd.msc`
3. Nhấn **Enter**

---

## 📋 BƯỚC 2: TẠO TASK WATCHDOG (Auto-restart)

### 2.1 Tạo Task mới
- Ở cột phải, click **Create Task...** (KHÔNG phải "Create Basic Task")

### 2.2 Tab General
- **Name:** `QUAN_AIBRAIN_Watchdog`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**
- **Configure for:** Windows 10

### 2.3 Tab Triggers
- Click **New...**
- **Begin the task:** `At logon`
- **Delay task:** `5 minutes`
- ✅ Check: **Enabled**
- Click **OK**

### 2.4 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\watchdog.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 2.5 Tab Conditions
- ❌ **Uncheck:** `Start the task only if the computer is on AC power`

### 2.6 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- ✅ Check: `If the task fails, restart every:` `1 minute`
- **Attempt to restart up to:** `3 times`
- Click **OK**

### 2.7 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 3: TẠO TASK BACKUP (2AM hàng ngày)

### 3.1 Tạo Task mới
- Click **Create Task...**

### 3.2 Tab General
- **Name:** `QUAN_AIBRAIN_Backup`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**

### 3.3 Tab Triggers
- Click **New...**
- **Begin the task:** `Daily`
- **Recur every:** `1 day`
- **Start:** `2:00:00 AM`
- ✅ Check: **Enabled**
- Click **OK**

### 3.4 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\backup_database.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 3.5 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- Click **OK**

### 3.6 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 4: TẠO TASK LEARNING DAEMON (24/7)

### 4.1 Tạo Task mới
- Click **Create Task...**

### 4.2 Tab General
- **Name:** `QUAN_AIBRAIN_Learning`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**

### 4.3 Tab Triggers
- Click **New...**
- **Begin the task:** `At logon`
- **Delay task:** `1 minute`
- ✅ Check: **Enabled**
- Click **OK**

### 4.4 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\learning_daemon.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 4.5 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- Click **OK**

### 4.6 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 5: TẠO TASK RESOURCE MONITOR (mỗi 5 phút)

### 5.1 Tạo Task mới
- Click **Create Task...**

### 5.2 Tab General
- **Name:** `QUAN_AIBRAIN_ResourceMonitor`
- ✅ Check: **Run whether user is logged on or not**
- ✅ Check: **Run with highest privileges**

### 5.3 Tab Triggers
- Click **New...**
- **Begin the task:** `On a schedule`
- **Settings:** `Every:` `5` `minutes`
- ✅ Check: **Enabled**
- Click **OK**

### 5.4 Tab Actions
- Click **New...**
- **Action:** `Start a program`
- **Program/script:** `C:\Users\DELL\.venv\Scripts\python.exe`
- **Add arguments:** `E:\AI\QUAN AI BRAIN\tools\resource_monitor.py`
- **Start in:** `E:\AI\QUAN AI BRAIN`
- Click **OK**

### 5.5 Tab Settings
- ✅ Check: `Allow task to be run on demand`
- ✅ Check: `If the task fails, restart every:` `1 minute`
- **Attempt to restart up to:** `1 time`
- Click **OK**

### 5.6 Nhập password
- Nhập password Windows của anh
- Click **OK**

---

## 📋 BƯỚC 6: KIỂM TRA TASKS

### 6.1 Verify tasks
- Trong Task Scheduler, ở cột trái, click **Task Scheduler Library**
- Tìm 4 tasks:
  - `QUAN_AIBRAIN_Watchdog`
  - `QUAN_AIBRAIN_Backup`
  - `QUAN_AIBRAIN_Learning`
  - `QUAN_AIBRAIN_ResourceMonitor`
- **Status** phải là: **Ready**

### 6.2 Test Watchdog
- Click phải vào `QUAN_AIBRAIN_Watchdog`
- Click **Run**
- Đợi 10 giây
- Check log: `E:\AI\QUAN AI BRAIN\logs\watchdog.log`
- Phải có dòng: `QUAN AI BRAIN Watchdog Starting`

### 6.3 Test Backup
- Click phải vào `QUAN_AIBRAIN_Backup`
- Click **Run**
- Check folder: `E:\AI\QUAN AI BRAIN\backups\`
- Phải có file: `brain_YYYYMMDD_HHMMSS.db`

### 6.4 Test Learning
- Click phải vào `QUAN_AIBRAIN_Learning`
- Click **Run**
- Đợi 30 giây
- Check log: `E:\AI\QUAN AI BRAIN\logs\learning_daemon.log`
- Phải có dòng: `Learning cycle complete`

---

## 📋 BƯỚC 7: KHỞI ĐỘNG HỆ THỐNG

### 7.1 Restart máy
- Restart Windows để tasks auto-start

### 7.2 Kiểm tra sau restart
1. **Open browser:** `http://127.0.0.1:8765/`
2. **Open health dashboard:** `http://127.0.0.1:8765/health_dashboard.html`
3. **Check logs:** `E:\AI\QUAN AI BRAIN\logs\`
4. **Check backups:** `E:\AI\QUAN AI BRAIN\backups\`

---

## 📋 BƯỚC 8: MONITORING HẰNG NGÀY

### 8.1 Health Dashboard
- Mở: `http://127.0.0.1:8765/health_dashboard.html`
- Check tất cả components đều **Healthy**

### 8.2 Logs
- **Watchdog:** `logs/watchdog.log` — server restart events
- **Learning:** `logs/learning_daemon.log` — facts ingested
- **Resource:** `logs/resource_monitor.log` — CPU/MEM/DISK/GPU

### 8.3 Task Scheduler
- `taskschd.msc`
- Check **Last Run Result** — phải là `0x0` (Success)
- Check **History** — xem chi tiết mỗi lần chạy

---

## 🚨 XỬ LÝ SỰ CỐ

### Task không chạy:
1. Check **Last Run Result** — nếu khác `0x0`, click **Run** manual
2. Check **History** — xem lỗi gì
3. Check password — task yêu cầu password Windows
4. Check path — có đúng `C:\Users\DELL\.venv\Scripts\python.exe` không?

### Server không start:
1. Check Ollama: `ollama list`
2. Check port: `netstat -ano | findstr :8765`
3. Check log: `logs/watchdog.log`
4. Chạy manual: `python tools/watchdog.py`

### Backup không tạo:
1. Check folder: `backups/` có write permission?
2. Check disk space — có đủ space không?
3. Chạy manual: `python tools/backup_database.py`

---

## ✅ CHECKLIST HOÀN THÀNH

- [ ] Task `QUAN_AIBRAIN_Watchdog` created (Status: Ready)
- [ ] Task `QUAN_AIBRAIN_Backup` created (Status: Ready)
- [ ] Task `QUAN_AIBRAIN_Learning` created (Status: Ready)
- [ ] Task `QUAN_AIBRAIN_ResourceMonitor` created (Status: Ready)
- [ ] Watchdog log exists: `logs/watchdog.log`
- [ ] Backup folder exists: `backups/`
- [ ] Learning log exists: `logs/learning_daemon.log`
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