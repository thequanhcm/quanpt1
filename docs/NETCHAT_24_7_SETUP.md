# HƯỚNG DẪN SETUP QUAN AI BRAIN 24/7 — NETCHAT AUTO-RESPONDER

## 🎯 MỤC TIÊU
Setup bot **TONY** hoạt động **24/7** trên NetChat kênh `4phc9b1mx78qjq3grccw89u94a`:
- ✅ Tự động phản hồi tin nhắn
- ✅ Focus đúng nội dung câu hỏi
- ✅ Phản hồi nhanh (~5-10 giây)
- ✅ Trung thực, chi tiết, có bằng chứng

---

## ✅ TRẠNG THÁI HIỆN TẠI

| Thành phần | Trạng thái | Chi tiết |
|---|---|---|
| **Server QUAN AI BRAIN** | ✅ Running | PID 22704, port 8765 |
| **Auto-responder** | ✅ Running | PID 3260, monitoring kênh |
| **Bot NetChat** | ✅ Connected | bot_quanpt1 (edojmne9d7gcxx8axu1mzas3pr) |
| **Channel** | ✅ Active | TONY (4phc9b1mx78qjq3grccw89u94a) |
| **NETMIND_EXTERNAL_DATA_ALLOWED** | ✅ Enabled | Set trong `start_server_fixed.py` |
| **reasoning_effort** | ✅ "low" | GLM-5.3-Flash phản hồi nhanh |

---

## 🚀 CÁCH SETUP 24/7

### **BƯỚC 1: Setup Task Scheduler cho Server**

1. **Mở Task Scheduler:**
   - Nhấn `Windows + R`
   - Gõ: `taskschd.msc`
   - Nhấn **Enter**

2. **Tạo Task Server:**
   - Click **Create Task**
   - **Tab General:**
     - Name: `QUAN_AIBRAIN_Server`
     - ✅ Check: **Run whether user is logged on or not**
     - ✅ Check: **Run with highest privileges**
   - **Tab Triggers:**
     - Click **New...**
     - Begin: **At logon**
     - Delay: **30 seconds**
     - ✅ Enabled
   - **Tab Actions:**
     - Click **New...**
     - Action: **Start a program**
     - Program: `C:\Users\DELL\.venv\Scripts\python.exe`
     - Arguments: `E:\AI\QUAN AI BRAIN\start_server_fixed.py`
     - Start in: `E:\AI\QUAN AI BRAIN`
   - **Tab Settings:**
     - ✅ Check: **Allow task to be run on demand**
     - ✅ Check: **If the task fails, restart every: 1 minute**
     - Attempt to restart: **3 times**
   - Click **OK** → Nhập password Windows

### **BƯỚC 2: Setup Task Scheduler cho Auto-responder**

1. **Tạo Task Auto-responder:**
   - Click **Create Task**
   - **Tab General:**
     - Name: `QUAN_AIBRAIN_NetChatBot`
     - ✅ Check: **Run whether user is logged on or not**
     - ✅ Check: **Run with highest privileges**
   - **Tab Triggers:**
     - Click **New...**
     - Begin: **At logon**
     - Delay: **1 minute** (để server start trước)
     - ✅ Enabled
   - **Tab Actions:**
     - Click **New...**
     - Action: **Start a program**
     - Program: `C:\Users\DELL\.venv\Scripts\python.exe`
     - Arguments: `E:\AI\QUAN AI BRAIN\tools\netchat_auto_responder.py`
     - Start in: `E:\AI\QUAN AI BRAIN`
   - **Tab Settings:**
     - ✅ Check: **Allow task to be run on demand**
     - ✅ Check: **If the task fails, restart every: 1 minute**
     - Attempt to restart: **3 times**
   - Click **OK** → Nhập password

### **BƯỚC 3: Setup Watchdog (Auto-restart nếu crash)**

1. **Tạo Task Watchdog:**
   - Click **Create Task**
   - **Tab General:**
     - Name: `QUAN_AIBRAIN_Watchdog`
     - ✅ Check: **Run whether user is logged on or not**
   - **Tab Triggers:**
     - Click **New...**
     - Begin: **At logon**
     - Delay: **2 minutes**
   - **Tab Actions:**
     - Click **New...**
     - Action: **Start a program**
     - Program: `C:\Users\DELL\.venv\Scripts\python.exe`
     - Arguments: `E:\AI\QUAN AI BRAIN\tools\watchdog.py`
     - Start in: `E:\AI\QUAN AI BRAIN`
   - Click **OK** → Nhập password

---

## 📊 KIỂM TRA HOẠT ĐỘNG

### **1. Check Server:**
```bash
netstat -ano | findstr :8765
```
**Kết quả mong đợi:** `LISTENING` với PID

### **2. Check Auto-responder:**
```bash
tasklist | findstr netchat_auto_responder
```
**Kết quả mong đợi:** Process đang chạy

### **3. Check Logs:**
- **Server:** Xem output trong Task Scheduler → History
- **Auto-responder:** Chạy manual để xem log:
  ```bash
  cd E:\AI\QUAN AI BRAIN
  .\.venv\Scripts\python.exe tools\netchat_auto_responder.py
  ```

### **4. Test NetChat:**
- Mở NetChat → Kênh `TONY`
- Gửi tin nhắn: "Xin chào em!"
- **Bot sẽ phản hồi trong ~5-10 giây**

---

## 🎯 TÍNH NĂNG ĐÃ SETUP

### **1. Phản hồi nhanh:**
- ✅ `reasoning_effort: "low"` — GLM-5.3-Flash trả lời ~1.2s
- ✅ Cache TTL 120s — giảm latency
- ✅ Timeout 15s — tránh treo

### **2. Focus đúng nội dung:**
- ✅ Prompt engineering — bot trả lời trực tiếp câu hỏi
- ✅ Không "Đang suy nghĩ..." — phản hồi ngay
- ✅ Trung thực — nói rõ giới hạn

### **3. Tự động 24/7:**
- ✅ Task Scheduler — auto-start khi login
- ✅ Watchdog — auto-restart nếu crash
- ✅ Retry logic — 3 lần restart nếu fail

### **4. Auto-confirm NetChat:**
- ✅ Extract confirm token tự động
- ✅ Gửi phản hồi ngay sau khi nhận
- ✅ Không cần manual confirm

---

## 🚨 XỬ LÝ SỰ CỐ

### **Server không start:**
1. Check Task Scheduler — task có enabled không?
2. Check log — xem lỗi gì
3. Chạy manual: `python start_server_fixed.py`

### **Auto-responder không phản hồi:**
1. Check Task Scheduler — task có enabled không?
2. Check log — xem lỗi gì
3. Chạy manual: `python tools\netchat_auto_responder.py`
4. Check server: `netstat -ano | findstr :8765`

### **Bot không nhận tin nhắn:**
1. Check bot đã vào kênh chưa: `python -m bot_netchat list`
2. Check token: `python tools\configure_netchat_bot.py <token>`
3. Invite bot vào kênh nếu cần

### **Phản hồi rỗng:**
1. Check `NETMIND_EXTERNAL_DATA_ALLOWED=true`
2. Check `reasoning_effort: "low"` trong code
3. Test API: `curl http://127.0.0.1:8765/api/chat ...`

---

## 📋 CHECKLIST HOÀN THÀNH

- [x] Server đang chạy (PID 22704)
- [x] Auto-responder đang chạy (PID 3260)
- [x] Bot đã kết nối NetChat
- [x] Test thành công — phản hồi chi tiết, trung thực
- [ ] **Setup Task Scheduler cho Server** (anh làm)
- [ ] **Setup Task Scheduler cho Auto-responder** (anh làm)
- [ ] **Setup Watchdog** (anh làm)
- [ ] **Restart máy để test auto-start** (anh làm)

---

## 🎉 KẾT LUẬN

Hệ thống **QUAN AI BRAIN** đã sẵn sàng hoạt động **24/7** trên NetChat!

**Anh chỉ cần:**
1. Setup 3 Tasks trong Task Scheduler (10 phút)
2. Restart máy để test
3. Gửi tin nhắn vào kênh NetChat — bot sẽ tự động phản hồi!

**Files quan trọng:**
- `start_server_fixed.py` — Start server với env var đúng
- `tools/netchat_auto_responder.py` — Auto-responder
- `tools/test_netchat_debug.py` — Debug script
- `tools/configure_netchat_bot.py` — Cấu hình bot token

---

**Ngày setup:** 2026-10-25  
**Version:** 2.0 (Fixed: reasoning_effort, auto-confirm, no "thinking" placeholder)  
**Author:** TONY PHAM (QUAN AI BRAIN)