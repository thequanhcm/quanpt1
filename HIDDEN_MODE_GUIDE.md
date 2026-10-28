# 🚀 Hướng dẫn chạy ẩn QUAN AI BRAIN

## Chế độ ẩn (Hidden Mode)

Khi chạy ở chế độ ẩn, tất cả services sẽ:
- ✅ **Không hiển thị cửa sổ** console
- ✅ Chạy hoàn toàn trong background
- ✅ Chỉ hiển thị icon ở system tray (nếu có)
- ✅ Không làm phiền khi làm việc

---

## Cách 1: Chạy ẩn ngay lập tức (Manual)

### Bước 1: Stop services hiện tại

```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\stop_services_hidden.bat
```

### Bước 2: Start services ẩn

```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\start_services_hidden.bat
```

**Kết quả:**
- Tất cả services chạy ẩn
- Không có cửa sổ nào hiện
- Dashboard vẫn accessible: http://127.0.0.1:8766/

---

## Cách 2: Setup auto-start ẩn (Recommended)

### Bước 1: Chạy PowerShell Admin

1. **Press:** `Win + X`
2. **Chọn:** "Windows PowerShell (Admin)" hoặc "Terminal (Admin)"

### Bước 2: Chạy script update

```powershell
cd "E:\AI\QUAN AI BRAIN"
.\tools\update_to_hidden.ps1
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

### Bước 3: Reboot máy

```cmd
shutdown /r /t 0
```

### Bước 4: Verify sau reboot

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

**Không có cửa sổ nào hiện!** ✅

---

## Kiểm tra services đang chạy ẩn

### Cách 1: Task Manager

1. **Press:** `Ctrl + Shift + Esc`
2. **Tab:** "Details"
3. **Tìm:** `python.exe`
4. **Check:** Không có cửa sổ nào mở

### Cách 2: Health check

```cmd
python tools\health_check.py
```

Nếu tất cả services ONLINE mà không có cửa sổ nào → Hidden mode hoạt động! ✅

### Cách 3: Dashboard

Mở browser: http://127.0.0.1:8766/

Nếu Dashboard hoạt động → Services đang chạy! ✅

---

## Stop services ẩn

```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\stop_services_hidden.bat
```

Hoặc:

```cmd
taskkill /FI "WINDOWTITLE eq QUAN AI BRAIN*" /F
```

---

## Troubleshooting

### Issue: Cửa sổ vẫn hiện

**Nguyên nhân:** Task Scheduler chưa update

**Giải pháp:**
```powershell
# Run PowerShell Admin:
cd "E:\AI\QUAN AI BRAIN"
.\tools\update_to_hidden.ps1

# Reboot:
shutdown /r /t 0
```

### Issue: Services không chạy sau reboot

**Giải pháp:**
```cmd
# Check Task Scheduler:
schtasks /Query /TN "QUAN-AI-BRAIN-Server" /V

# Re-run setup:
tools\setup_hidden_tasks.bat
```

### Issue: Dashboard không accessible

**Giải pháp:**
```cmd
# Check port:
netstat -ano | findstr :8766

# Restart:
tools\stop_services_hidden.bat
tools\start_services_hidden.bat
```

---

## Files liên quan

| File | Mục đích |
|------|----------|
| `start_services_hidden.bat` | Start services ẩn (manual) |
| `stop_services_hidden.bat` | Stop services ẩn |
| `setup_hidden_tasks.py` | Setup hidden tasks (Admin) |
| `setup_hidden_tasks.bat` | Wrapper cho setup_hidden_tasks.py |
| `update_to_hidden.ps1` | Update tasks to hidden mode (Admin) |

---

## Lưu ý quan trọng

1. **Admin privileges required** để setup Task Scheduler
2. **Reboot required** để test auto-start
3. **Logs vẫn được ghi** vào `logs/` folder
4. **Dashboard vẫn accessible** qua browser
5. **NetChat vẫn hoạt động** bình thường

---

## Benefits của Hidden Mode

✅ **Không làm phiền** khi làm việc  
✅ **Chuyên nghiệp hơn** - không có cửa sổ console  
✅ **Tiết kiệm screen space**  
✅ **Chạy như service thật**  
✅ **Auto-start invisible**  

---

**Chế độ ẩn đã sẵn sàng!** 🚀

**Next:** Run `update_to_hidden.ps1` as Admin → Reboot → Enjoy!