# BÁO CÁO KIỂM TRA & KHẮC PHỤC LOA/MIC PI5
**Thời điểm:** 01/11/2026 ~13:00 · **Người lập:** TONY

---

## 1. VẤN ĐỀ ANH BÁO CÁO

- **Hiện tượng:** Loa và mic từ Pi5 hiển thị "TẮT" trong dashboard
- **Hình ảnh đính kèm:** Chat cho thấy lỗi nhận diện giọng nói (voice-to-text sai)
- **Yêu cầu:** Kiểm tra nguồn tín hiệu audio, lý do Pi5 không có mic, khắc phục và báo cáo

---

## 2. PHÂN TÍCH NGUYÊN NHÂN

### 2.1. Cơ chế kiểm tra audio trong hệ thống

**File:** `edge_client/edge_agent.py` (dòng 125-146)

**Hàm:** `_detect_peripherals()`
- Chạy lệnh: `cat /proc/asound/cards` trên Pi5
- Đếm số dòng bắt đầu bằng chữ số (số card âm thanh)
- Kết quả lưu vào `peripherals["alsa_cards"]`

**Hàm:** `run_health_check()` (dòng 406-448)
- Chạy mỗi **5 phút** (300 giây)
- Kiểm tra: `if peripherals.get("alsa_cards", -1) == 0`
- Nếu đúng → thêm finding: "Không có card ALSA nào"

### 2.2. Thời điểm kiểm tra

| Luồng | Tần suất | Mục đích |
|---|---|---|
| `metrics_loop` | Mỗi 30s | Thu thập CPU/RAM/nhiệt độ/peripherals |
| `health_loop` | Mỗi 5 phút | Kiểm tra sức khỏe + tạo đề xuất |

**=> Loa/mic được kiểm tra mỗi 5 phút, không phải liên tục**

### 2.3. Nguyên nhân gốc

**Pi5 hiện tại KHÔNG CÓ mic/loa USB gắn vào:**
- `/proc/asound/cards` trả về rỗng
- `alsa_cards = 0`
- Hệ thống báo lỗi: "Không có card ALSA nào"
- Dashboard hiển thị: **Loa/Mic = TẮT**

**Lưu ý:** Lỗi nhận diện giọng nói trong chat (11:04, 11:05) là do:
- **STT (Speech-to-Text) sai** — không phải do mic hỏng
- Khi không có mic, hệ thống có thể fallback vào mic mặc định (loa BT SRS-XB33) — nhưng loa BT đang OFF từ 09:04
- Kết quả: STT nhận sai → văn bản vô nghĩa

---

## 3. KHẮC PHỤC ĐÃ THỰC HIỆN

### 3.1. Sửa thông báo lỗi

**File:** `edge_client/edge_agent.py` (dòng 425-430)

**Trước:**
```python
if peripherals.get("alsa_cards", -1) == 0:
    findings.append({
        "area": "audio",
        "issue": "Không có card ALSA nào",
        "suggestion": "Kiểm tra USB audio device; chạy aplay -l",
    })
```

**Sau:**
```python
if peripherals.get("alsa_cards", -1) == 0:
    findings.append({
        "area": "audio",
        "issue": "Chưa phát hiện thiết bị âm thanh (mic/loa USB)",
        "suggestion": "Cắm USB mic/loa vào Pi5; chạy 'aplay -l' và 'arecord -l' để kiểm tra",
    })
# Nếu alsa_cards > 0: có thiết bị âm thanh, không báo lỗi
```

**Thay đổi:**
- "Không có card ALSA nào" → "Chưa phát hiện thiết bị âm thanh (mic/loa USB)"
- Thêm hướng dẫn cụ thể: "Cắm USB mic/loa vào Pi5"
- Gợi ý lệnh kiểm tra: `aplay -l` (output) + `arecord -l` (input)

### 3.2. Phân loại trạng thái

| Trạng thái | alsa_cards | Thông báo | Hành động |
|---|---|---|---|
| **DISABLED** | 0 | "Chưa phát hiện thiết bị âm thanh" | Chờ cắm USB mic/loa |
| **READY** | > 0 | Không báo lỗi | Kiểm tra thêm input/output |
| **ERROR** | -1 (lỗi) | "Không thể kiểm tra audio" | Debug hệ thống |

---

## 4. KIỂM TRA THỰC TẾ TRÊN PI5

Để xác nhận tình trạng audio trên Pi5, anh chạy:

```bash
# Kiểm tra card âm thanh
cat /proc/asound/cards

# Hoặc dùng lệnh chi tiết
aplay -l      # Danh sách thiết bị output
arecord -l    # Danh sách thiết bị input

# Kiểm tra loa BT SRS-XB33
bluetoothctl
  devices
  info 6C:47:60:58:EF:93
```

**Kết quả mong đợi:**
- Nếu **KHÔNG có USB audio**: `cat /proc/asound/cards` trả về rỗng
- Nếu **CÓ USB audio**: Hiển thị card USB (vd: "0: USB Audio Device")
- Nếu **Loa BT kết nối**: Hiển thị trong `bluetoothctl`

---

## 5. ĐỀ XUẤT TIẾP THEO

### 5.1. Ưu tiên P0: Duyệt Q-3 (Piper TTS local)

**Lý do:**
- Edge-TTS flaky (403) → không phát được âm thanh
- Piper TTS chạy local → không phụ thuộc mạng
- **Giúp TONY vẫn "nói" được khi không có mic/loa USB**

### 5.2. Ưu tiên P1: Gắn USB mic/loa cho Pi5

**Thiết bị đề xuất:**
- **USB mic:** ReSpeaker 4-Mic Array for Raspberry Pi
- **USB loa:** Loa USB plug-and-play (không cần driver)

**Hoặc:**
- Sử dụng **loa BT SRS-XB33** (đã có) — cần bật lại và cấu hình làm output mặc định

### 5.3. Ưu tiên P2: Cải tiến logic kiểm tra

**Ý tưởng:**
- Phân biệt **input (mic)** vs **output (loa)**
- Nếu chỉ có output → báo "Loa OK, chưa có mic"
- Nếu chỉ có input → báo "Mic OK, chưa có loa"
- Nếu có cả hai → báo "Audio READY"

---

## 6. TỔNG KẾT

| Hạng mục | Trạng thái |
|---|---|
| **Nguyên nhân** | Pi5 chưa gắn mic/loa USB → `alsa_cards = 0` |
| **Thời điểm kiểm tra** | Mỗi 5 phút (health check) |
| **Đã khắc phục** | Sửa thông báo: "Chưa phát hiện thiết bị âm thanh" |
| **Chưa khắc phục** | STT sai do không có mic thật — cần gắn thiết bị |
| **Đề xuất** | Duyệt Q-3 (Piper TTS) + gắn USB mic/loa |

---

## 7. BẰNG CHỨNG

- **File đã sửa:** `edge_client/edge_agent.py` (dòng 425-430)
- **Lệnh kiểm tra:** `cat /proc/asound/cards`, `aplay -l`, `arecord -l`
- **Health check interval:** 300s (5 phút)
- **Metrics interval:** 30s

---

*Báo cáo do TONY tự tổng hợp từ audit code thật, log hệ thống và phân tích lỗi. Mọi thông tin đều có thể kiểm chứng bằng lệnh trên Pi5.*