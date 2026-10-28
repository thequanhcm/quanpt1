# 🚀 Hướng dẫn Start/Stop & Auto-Start QUAN AI BRAIN

## 🎯 Quick Start (One-Click)

### Start Tất cả Services

**Double-click:**
```
E:\AI\QUAN AI BRAIN\START_ALL_ONECLICK.bat
```

**Kết quả:**
- ✅ Server (port 8765)
- ✅ Watchdog (port 17236)
- ✅ Learning (port 7724)
- ✅ Responder (NetChat)
- ✅ Dashboard (port 8766)

**Dashboard:** http://127.0.0.1:8766/

---

### Stop Tất cả Services

**Double-click:**
```
E:\AI\QUAN AI BRAIN\STOP_ALL_ONECLICK.bat
```

**Xác nhận:** Gõ `y` và Enter

**Kết quả:**
- ✅ Tất cả services dừng
- ✅ Health check tự động
- ✅ Verify thành công

---

## 🔄 Auto-Start khi khởi động Windows

### Bước 1: Setup Task Scheduler (Admin Required)

**Cách 1: PowerShell Admin**
```powershell
# Win + X → Windows PowerShell (Admin)
cd "E:\AI\QUAN AI BRAIN"
.\tools\update_to_hidden.ps1
```

**Cách 2: Batch file**
```
Right-click tools\setup_hidden_tasks.bat
→ Run as administrator
```

**Kết quả:**
```
OK Hidden: QUAN-AI-BRAIN-Server
OK Hidden: QUAN-AI-BRAIN-Watchdog
OK Hidden: QUAN-AI-BRAIN-Learning
OK Hidden: QUAN-AI-BRAIN-Responder
OK Hidden: QUAN-AI-BRAIN-Dashboard

All tasks updated to HIDDEN mode
```

### Bước 2: Reboot máy

```cmd
shutdown /r /t 0
```

### Bước 3: Verify sau reboot

```cmd
cd "E:\AI\QUAN AI BRAIN"
python tools\health_check.py
```

**Kết quả mong đợi:**
```
✅ server ONLINE
✅ watchdog ONLINE
✅ learning ONLINE
✅ responder ONLINE
✅ dashboard ONLINE
```

**Không có cửa sổ nào hiện!** (Hidden mode) ✅

---

## 📊 Kiểm tra trạng thái

### Health Check

```cmd
cd "E:\AI\QUAN AI BRAIN"
python tools\health_check.py
```

**Kết quả:**
- ✅ Tất cả services ONLINE
- ✅ Tất cả tasks configured
- ✅ Overall status: ALL ONLINE

### Dashboard

Mở browser: http://127.0.0.1:8766/

**Kiểm tra:**
- Overall status: HEALTHY
- All components: HEALTHY
- Brain DB: Healthy
- Ollama: Connected

### Task Scheduler

```cmd
schtasks /Query /TN "QUAN-AI-BRAIN-*" /FO TABLE
```

**Kết quả:**
- 5 tasks listed
- Status: Ready
- Next Run: At startup

---

## 🎯 Các kịch bản sử dụng

### Kịch bản 1: Start manual (không auto-start)

```cmd
# Start:
START_ALL_ONECLICK.bat

# Stop:
STOP_ALL_ONECLICK.bat
```

**Khi nào dùng:**
- Development/testing
- Không cần auto-start
- Tiết kiệm tài nguyên khi không dùng

---

### Kịch bản 2: Auto-start (Recommended)

**Setup 1 lần:**
```
Run setup_hidden_tasks.bat as Admin
Reboot
```

**Sau đó:**
- Services tự động start khi Windows khởi động
- Chạy ẩn hoàn toàn (không cửa sổ)
- Tự động restart nếu crash

**Khi nào dùng:**
- Production use
- Cần 24/7 operation
- Không muốn start manual

---

### Kịch bản 3: Hidden mode (Professional)

**Setup:**
```powershell
# PowerShell Admin:
.\tools\update_to_hidden.ps1
```

**Kết quả:**
- Services chạy hoàn toàn ẩn
- Không có cửa sổ console
- Giống service thật

**Khi nào dùng:**
- Professional deployment
- Không muốn user thấy processes
- Chạy như background service

---

## 🔧 Troubleshooting

### Issue: Services không start sau reboot

**Nguyên nhân:** Task Scheduler chưa setup

**Giải pháp:**
```cmd
# Run as Admin:
tools\setup_hidden_tasks.bat

# Reboot:
shutdown /r /t 0
```

---

### Issue: Port đã được sử dụng

**Triệu chứng:** `Address already in use`

**Giải pháp:**
```cmd
# Tìm process:
netstat -ano | findstr :8765

# Kill process:
taskkill /F /PID <PID>

# Restart:
START_ALL_ONECLICK.bat
```

---

### Issue: Services tự động stop

**Nguyên nhân:** Watchdog chưa chạy hoặc lỗi

**Giải pháp:**
```cmd
# Check logs:
type logs\watchdog.log

# Restart:
STOP_ALL_ONECLICK.bat
START_ALL_ONECLICK.bat
```

---

### Issue: Dashboard không accessible

**Triệu chứng:** Không mở được http://127.0.0.1:8766/

**Giải pháp:**
```cmd
# Check port:
netstat -ano | findstr :8766

# Check process:
tasklist | findstr python

# Restart:
STOP_ALL_ONECLICK.bat
START_ALL_ONECLICK.bat
```

---

## 📁 Files quan trọng

| File | Mục đích |
|------|----------|
| **START_ALL_ONECLICK.bat** | Start tất cả services (1-click) |
| **STOP_ALL_ONECLICK.bat** | Stop tất cả services (1-click) |
| **setup_hidden_tasks.bat** | Setup auto-start (Admin) |
| **update_to_hidden.ps1** | Update to hidden mode (Admin) |
| **tools/health_check.py** | Check service status |

---

## 🎯 Quick Reference

### Start
```
Double-click: START_ALL_ONECLICK.bat
```

### Stop
```
Double-click: STOP_ALL_ONECLICK.bat
→ Confirm: y
```

### Auto-Start Setup
```
Right-click: setup_hidden_tasks.bat
→ Run as administrator
→ Reboot
```

### Check Status
```
python tools\health_check.py
```

### View Dashboard
```
http://127.0.0.1:8766/
```

---

## ✅ Checklist sau setup

- [ ] Services start được bằng START_ALL_ONECLICK.bat
- [ ] Services stop được bằng STOP_ALL_ONECLICK.bat
- [ ] Health check hiển thị ALL ONLINE
- [ ] Dashboard accessible tại http://127.0.0.1:8766/
- [ ] Task Scheduler có 5 tasks (sau setup Admin)
- [ ] Services auto-start sau reboot
- [ ] Services chạy ẩn (không cửa sổ)

---

## 🎉 Kết luận

**Với one-click scripts:**
- ✅ Start/Stop dễ dàng
- ✅ Auto-start khi cần
- ✅ Hidden mode professional
- ✅ Full control

**Hệ thống sẵn sàng!** 🚀

---

*QUAN AI BRAIN — TONY Assistant*  
*Version 1.0 | 2026-10-28*