# QUAN AI BRAIN — Emergency Stop Guide

## 🛑 One-Click Emergency Stop

Khi cần dừng toàn bộ hoạt động của trợ lý, chỉ cần:

---

## Cách 1: Double-Click (Nhanh nhất)

### Bước 1: Double-click file
```
E:\AI\QUAN AI BRAIN\STOP_ALL_ONECLICK.bat
```

### Bước 2: Xác nhận
- Script sẽ hỏi: "This will stop ALL services immediately! Continue? (y/n)"
- Gõ: `y` và Enter

### Bước 3: Done!
- Tất cả services dừng ngay lập tức
- Health check tự động chạy để verify
- Kết quả hiển thị trên màn hình

---

## Cách 2: PowerShell (Chi tiết hơn)

### Bước 1: Double-click file
```
E:\AI\QUAN AI BRAIN\STOP_ALL_ONECLICK.ps1
```

### Bước 2: Xác nhận
- PowerShell sẽ hỏi xác nhận
- Gõ: `y` và Enter

### Bước 3: Chi tiết
- Hiển thị từng bước dừng
- Show PID của từng process bị kill
- Health check tự động

---

## Cách 3: Command Line

```cmd
cd "E:\AI\QUAN AI BRAIN"
STOP_ALL_ONECLICK.bat
```

Hoặc:

```powershell
cd "E:\AI\QUAN AI BRAIN"
.\STOP_ALL_ONECLICK.ps1
```

---

## Những gì script làm

### 1. Stop Task Scheduler Tasks
- ✅ QUAN-AI-BRAIN-Server
- ✅ QUAN-AI-BRAIN-Watchdog
- ✅ QUAN-AI-BRAIN-Learning
- ✅ QUAN-AI-BRAIN-Responder
- ✅ QUAN-AI-BRAIN-Dashboard

### 2. Kill All Python Processes
- Tìm tất cả process `python.exe`
- Kill từng process
- Force kill nếu cần

### 3. Verify Stop
- Chờ 2 giây để processes terminate
- Check lại xem còn process nào không
- Chạy health check để verify

---

## Kết quả mong đợi

```
============================================
🛑 QUAN AI BRAIN — EMERGENCY STOP
============================================

✅ Server task stopped
✅ Watchdog task stopped
✅ Learning task stopped
✅ Responder task stopped
✅ Dashboard task stopped

✅ Killed all Python processes
✅ All processes stopped

============================================================
QUAN AI BRAIN — Health Check
============================================================

📊 SERVICE STATUS
------------------------------------------------------------
server          ❌ OFFLINE
watchdog        ❌ OFFLINE
learning        ❌ OFFLINE
responder       ❌ OFFLINE
dashboard       ❌ OFFLINE

============================================================
SUMMARY
============================================================
Services running: 0/5
Overall status: ✅ ALL STOPPED
```

---

## Restart sau khi stop

### Cách 1: Manual start
```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\start_services.bat
```

### Cách 2: Hidden mode
```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\start_services_hidden.bat
```

### Cách 3: Auto-start (sau reboot)
- Reboot máy
- Services tự động start (nếu đã setup Task Scheduler)

---

## Khi nào dùng Emergency Stop?

✅ **Cần restart nhanh** - Dừng rồi start lại  
✅ **Debug** - Dừng để debug vấn đề  
✅ **Tiết kiệm tài nguyên** - Dừng khi không dùng  
✅ **Emergency** - Dừng khẩn cấp khi có vấn đề  
✅ **Maintenance** - Dừng để bảo trì  

---

## Lưu ý quan trọng

⚠️ **Dữ liệu chưa save có thể mất**  
⚠️ **Tasks đang chạy sẽ bị interrupt**  
⚠️ **NetChat sẽ không phản hồi**  
⚠️ **Dashboard sẽ offline**  

✅ **Logs vẫn được ghi** trước khi stop  
✅ **Database không bị corrupt**  
✅ **Có thể restart bất cứ lúc nào**  

---

## Shortcut (Tùy chọn)

### Tạo Desktop Shortcut

1. **Right-click** trên Desktop
2. **New** → **Shortcut**
3. **Location:**
   ```
   E:\AI\QUAN AI BRAIN\STOP_ALL_ONECLICK.bat
   ```
4. **Name:** `STOP QUAN AI BRAIN`
5. **Finish**

### Đổi icon (Optional)

1. **Right-click** shortcut
2. **Properties** → **Change Icon**
3. Chọn icon đỏ/cảnh báo
4. **OK**

Bây giờ chỉ cần **double-click** icon trên Desktop để stop! 🛑

---

## Troubleshooting

### Issue: Script không chạy

**Giải pháp:**
```cmd
# Run as Administrator:
Right-click STOP_ALL_ONECLICK.bat
→ Run as administrator
```

### Issue: Một số process vẫn chạy

**Giải pháp:**
```cmd
# Manual kill:
taskkill /FI "IMAGENAME eq python.exe" /F

# Hoặc dùng PowerShell:
Get-Process python | Stop-Process -Force
```

### Issue: Services tự động start lại

**Nguyên nhân:** Task Scheduler auto-restart

**Giải pháp:**
```cmd
# Disable tasks temporarily:
schtasks /Change /TN "QUAN-AI-BRAIN-Server" /Disable
schtasks /Change /TN "QUAN-AI-BRAIN-Watchdog" /Disable
# ... disable all tasks

# Or reboot and don't let them start
```

---

## Files liên quan

| File | Mục đích |
|------|----------|
| **STOP_ALL_ONECLICK.bat** | One-click stop (Batch) |
| **STOP_ALL_ONECLICK.ps1** | One-click stop (PowerShell) |
| **start_services.bat** | Manual start |
| **start_services_hidden.bat** | Hidden start |
| **stop_services.bat** | Simple stop |
| **stop_services_hidden.bat** | Hidden stop |

---

## Quick Reference

### Stop
```
Double-click: STOP_ALL_ONECLICK.bat
```

### Start (Normal)
```
Double-click: start_services.bat
```

### Start (Hidden)
```
Double-click: start_services_hidden.bat
```

### Check Status
```
python tools\health_check.py
```

---

**Emergency Stop đã sẵn sàng!** 🛑

**Chỉ cần double-click:** `STOP_ALL_ONECLICK.bat`

**Tất cả services dừng ngay lập tức!** ✅