# TONY SYSTEM HEALTH ASSESSMENT — Sức khỏe PC + Pi5 + tự chăm sóc
**Cập nhật:** 01/11/2026 16:45 · PHẦN VII · Mọi số liệu đo live 16:32-16:34

## 7.1. PC (DESKTOP-SNMI929)

| Hạng mục | Giá trị live | Đánh giá |
|---|---|---|
| Services 8765/8766 | HTTP 200 ×2 | ✅ |
| RAM 16 GB | 3 service cặp PID ổn định từ 16:13 | ✅ |
| CPU | học daemon cycle 5' + BLAS=2 | ✅ |
| Disk | D: 155 GB free; F: mirror 6,21/270 GB; **C: 88 GB free** | ✅ |
| brain.db | 91 MB, 19 bảng, integrity OK | ✅ |
| WAL/locks | không có lock kẹt | ✅ |
| Logs | logs/ 124 MB — xoay chưa có (P3) | ⚠️ |
| Backup DB 2AM | **brain_*.db mới nhất 28/10 — DỪNG 4 NGÀY** | ❌ P1 |
| Mirror F | task 02:30 Ready | ✅ |
| Model | GLM-5.3-Flash netmind + Ollama 8 models | ✅ |

## 7.2. Pi5 (SSH 16:32)

| Hạng mục | Giá trị | Đánh giá |
|---|---|---|
| CPU | 14,6% | ✅ |
| Nhiệt độ | 56,5°C | ✅ |
| Undervoltage/Throttle | throttled=0x0 | ✅ |
| RAM | 1.248/4.049 MB dùng | ✅ |
| Storage | 14/117 GB (13%) | ✅ |
| Uptime | 9h16m | ✅ |
| Edge daemon | pgrep=1, READY, RTT 220ms, heartbeat 1,4s | ✅ |
| Bluetooth (loa BT) | owner-ACK giữ TẮT (cố ý) | ✅ tôn trọng |
| Microphone | không gắn (alsa_cards=0) | ⚠️ trạng thái đã rõ |
| Camera | ✅ (ảnh 117 KB hôm nay) | ✅ |
| HDMI kiosk | 8768 | ✅ |
| STT/TTS | code có; audio device thiếu | ⚠️ P1 AUDIO |

## 7.3. Health Intelligence

| Khả năng | Trạng thái | Bằng chứng |
|---|---|---|
| Thu telemetry | ✅ | edge status + health API |
| Phát hiện bất thường | ✅ | bt_speaker spam phát hiện + ACK |
| Phân loại mức độ | ✅ | WARNING/CRITICAL severity |
| Nguyên nhân khả dĩ | ✅ | root-cause analyses (HMAC, PYTHONPATH) |
| Dự báo nguy cơ | ⚠️ Cấp 1 | chỉ CLO-stall predictor |
| Cảnh báo | ✅ | health_alerts 187 bản ghi; **owner-ACK mới: sent=0 khi đã duyệt** |
| Đề xuất khắc phục | ✅ | GAP + DECISION REGISTER |
| Theo dõi kết quả | ✅ | verify sau từng fix |
| UNKNOWN khi thiếu dữ liệu | ✅ | đúng policy |

## 7.4. Tự chăm sóc

| Khả năng | Trạng thái |
|---|---|
| Tự kiểm tra | ✅ SelfCareEngine TCP checks |
| Tự phát hiện lỗi | ✅ hôm nay phát hiện 30 router-error cũ + backup dừng |
| Tự tạo báo cáo | ✅ 305+ reports + handoff auto |
| Tự tạo candidate sửa lỗi | ✅ CLO |
| Tự kiểm thử | ✅ pytest 3.002 |
| Theo dõi sau áp dụng | ✅ giám sát 120s HMAC; 4 chu kỳ alert |

## ⚠️ PHÁT HIỆN AUDIT MỚI (2 hạng mục P1)

1. **Watchdog MISSING (0 process)** — server đang khỏe nhờ restart chuẩn 16:13, nhưng lớp tự hồi phục vĩnh viễn ĐANG TẮT. Khắc phục: chạy lại `KHOI_DONG_24_7.bat` phần [4/5] hoặc spawn watchdog.py — cần duyệt vì restart service quan trọng.
2. **Backup 2AM dừng từ 28/10** — Task Scheduler QUAN_AI_BRAIN_BACKUP_2AM cần kiểm tra (schtasks /Query) + bật lại; rủi ro mất dữ liệu ngày. Đề xuất khẩn: mirror F 02:30 ĐANG BÙ ĐẮP một phần (F:\BRAIN\data\brain.db snapshot hằng ngày) — **tạm chấp nhận rủi ro 24h**.

**Điểm System Health: CẤP 2 — đo được, cảnh báo được, tự chăm sóc có (trừ watchdog); 2 lỗ hổng vận hành mới đã gắn nhãn P1.**
