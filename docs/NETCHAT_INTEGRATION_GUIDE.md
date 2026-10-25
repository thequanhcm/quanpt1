# HƯỚNG DẪN TÍCH HỢP NETCHAT — QUAN AI BRAIN

## 🎯 MỤC TIÊU
Kết nối trợ lý **QUAN AI BRAIN** (Tony Pham) với kênh NetChat:
- **Channel ID:** `4phc9b1mx78ajq3grccw89u94a`
- **Channel Name:** `Trợ lý Tony Pham`
- **Mục đích:** Anh giao tiếp với trợ lý qua NetChat

---

## 📋 BƯỚC 1: LẤY BOT ACCESS TOKEN

### 1.1 Mở trang quản trị bot
1. Mở browser: `https://bot-netchat.viettel.vn/`
2. Login bằng tài khoản Viettel của anh
3. Vào **Bot Management** → Chọn bot của anh (hoặc tạo mới nếu chưa có)

### 1.2 Copy Access Token
1. Tìm mục **Access Token** hoặc **Bot Token**
2. Click **Copy** hoặc **Show** để xem token
3. Token thường là chuỗi dài (50-100 ký tự)

**Lưu ý:** 
- Token này **bí mật** — không share cho ai
- Nếu bị lộ, click **Regenerate** để tạo token mới

---

## 📋 BƯỚC 2: CẤU HÌNH BOT

### Option A: Qua Command Line (Nhanh)

1. **Mở CMD/PowerShell**
2. **Chạy lệnh:**
```bash
cd E:\AI\QUAN AI BRAIN
python tools\configure_netchat_bot.py <YOUR_ACCESS_TOKEN_HERE>
```
Thay `<YOUR_ACCESS_TOKEN_HERE>` bằng token anh vừa copy.

**Ví dụ:**
```bash
python tools\configure_netchat_bot.py abc123xyz456...
```

3. **Kiểm tra kết quả:**
- Nếu thành công: `✅ Token saved!` + `✅ Bot connected successfully!`
- Nếu lỗi: Xem thông báo lỗi và thử lại

### Option B: Qua NetMind Desktop (Nếu có)

1. Mở **netMind Desktop**
2. Vào **Settings** → **Channels** → **NetChat**
3. Paste **Access Token** vào ô tương ứng
4. Click **Save**

---

## 📋 BƯỚC 3: KIỂM TRA KẾT NỐI

### 3.1 Kiểm tra bot identity
```bash
python -m bot_netchat whoami
```

**Kết quả mong đợi:**
```
Bot: Tony Pham Assistant (bot_xxx)
ID: bot_xxx
Source: MATTERMOST_TOKEN
```

### 3.2 Liệt kê các kênh bot đang ở
```bash
python -m bot_netchat list
```

**Kết quả mong đợi:**
```
Channels:
  • Trợ lý Tony Pham (4phc9b1mx78ajq3grccw89u94a)
  • ...
```

Nếu **không thấy** kênh `4phc9b1mx78ajq3grccw89u94a`:
- Bot chưa được mời vào kênh
- Anh cần **invite bot** vào kênh NetChat

---

## 📋 BƯỚC 4: INVITE BOT VÀO KÊNH (Nếu cần)

### 4.1 Mở kênh NetChat
1. Mở NetChat
2. Vào kênh **Trợ lý Tony Pham** (`4phc9b1mx78ajq3grccw89u94a`)

### 4.2 Invite bot
1. Click **Add Member** (hoặc biểu tượng +)
2. Tìm bot của anh (tên: **Tony Pham Assistant** hoặc tương tự)
3. Click **Add** / **Invite**
4. Bot sẽ vào kênh và sẵn sàng nhận tin nhắn

---

## 📋 BƯỚC 5: TEST GỬI TIN NHẮN

### 5.1 Gửi test message vào kênh
```bash
python -m bot_netchat send 4phc9b1mx78ajq3grccw89u94a "Xin chào, đây là test message từ QUAN AI BRAIN" --to-channel
```

**Kết quả:**
- Bot sẽ gửi tin nhắn vào kênh
- Anh sẽ thấy tin nhắn trong NetChat

### 5.2 Đọc tin nhắn từ kênh
```bash
python -m bot_netchat read 4phc9b1mx78ajq3grccw89u94a 5
```

**Kết quả:**
- Hiển thị 5 tin nhắn gần nhất từ kênh
- Bao gồm file attachments (nếu có)

---

## 📋 BƯỚC 6: TÍCH HỢP TỰ ĐỘNG (Auto-Response)

Để bot **tự động trả lời** tin nhắn trong kênh:

### 6.1 Tạo script auto-responder
```python
# tools/netchat_auto_responder.py
import sys
sys.path.insert(0, "src")

from quan_ai_brain.web.server import handle_chat_message
from bot_netchat import read_channel, send_message

channel_id = "4phc9b1mx78ajq3grccw89u94a"
last_message_id = None

while True:
    # Read new messages
    messages = read_channel(channel_id, count=10)
    
    for msg in messages:
        if msg.id != last_message_id and not msg.is_bot:
            # Process message through QUAN AI BRAIN
            response = handle_chat_message(msg.text)
            
            # Send response back
            send_message(channel_id, response, to_channel=True)
            last_message_id = msg.id
    
    # Wait 5 seconds
    time.sleep(5)
```

### 6.2 Chạy auto-responder
```bash
python tools/netchat_auto_responder.py
```

**Hoặc** setup như Windows Service/Task Scheduler để chạy 24/7.

---

## 🚨 XỬ LÝ LỖI

### Lỗi: "Bot chưa được phép nhắn riêng cho người nhận này"
- **Nguyên nhân:** Admin bot chưa thêm user vào **allowlist**
- **Giải pháp:** 
  1. Vào `https://bot-netchat.viettel.vn/`
  2. Bot Management → **Người nhận được phép**
  3. Thêm user cần nhắn

### Lỗi: "Access token invalid"
- **Nguyên nhân:** Token sai hoặc hết hạn
- **Giải pháp:** 
  1. Lấy token mới từ bot management
  2. Chạy lại: `python tools\configure_netchat_bot.py <new_token>`

### Lỗi: "Channel not found"
- **Nguyên nhân:** Channel ID sai hoặc bot chưa vào kênh
- **Giải pháp:**
  1. Kiểm tra lại Channel ID: `4phc9b1mx78ajq3grccw89u94a`
  2. Invite bot vào kênh (BƯỚC 4)

---

## ✅ CHECKLIST HOÀN THÀNH

- [ ] Đã lấy Bot Access Token từ `bot-netchat.viettel.vn`
- [ ] Đã cấu hình token: `python tools\configure_netchat_bot.py <token>`
- [ ] Đã kiểm tra: `python -m bot_netchat whoami` → thành công
- [ ] Đã kiểm tra: `python -m bot_netchat list` → thấy kênh `4phc9b1mx78ajq3grccw89u94a`
- [ ] Đã test gửi tin: `python -m bot_netchat send ...` → nhận được trong NetChat
- [ ] (Optional) Đã setup auto-responder để bot tự trả lời

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề:
1. Check log: `logs/netchat.log`
2. Check token: `python tools\configure_netchat_bot.py <token>`
3. Test manual: `python -m bot_netchat whoami`
4. Report lỗi với output chi tiết

---

**Ngày setup:** 2026-10-25  
**Version:** 1.0  
**Author:** TONY PHAM (QUAN AI BRAIN)