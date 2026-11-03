# M1 — PI5 HEALTH REPORT (RASPBERRY PI 5 — EDGE-PI5-DESK-01)

**Người lập:** TONY · **Thời điểm đo:** 01/11/2026 09:35–11:05 giờ VN
**Nguồn:** `pi5_collector.py` — SSH BatchMode (key sẵn có) · **Chế độ:** chỉ đọc (`vcgencmd`, `free`, `df`, `bluetoothctl info`, `systemctl is-active`, `uptime -s`)

## Snapshot đặc trưng (đo thật nhiều lần trong ngày)

| Chỉ số | Giá trị | Ngưỡng WARN/CRIT | Trạng thái |
|---|---|---|---|
| Nhiệt độ SoC | 57,1–58,7°C (nền load ~1,0) | 70 / 80 | ✅ NORMAL |
| Throttled flags | `0x0` (mọi lần đo) | khác 0x0 → warn | ✅ NORMAL |
| RAM | 1.234/4.049 MB dùng (30,5%) | 85 / 95 | ✅ NORMAL |
| Dĩa root | 14.322/119.432 MB (13%) | 85 / 95 | ✅ NORMAL |
| Boot | 2026-11-01 07:16:40 — ổn định ≥ 2h48 | reboot mới → cảnh báo qua boot_time đổi | ✅ |
| Loa BT SRS-XB33 | **Connected: no** (từ 09:04 — owner tắt nguồn) | yes→ok, no→warn | ⚠️ WARNING |
| Services | quan_ai_edge / quan_ai_wake / quan_ai_kiosk_guard | — | ✅ cả 3 active |

## Undervoltage / nguồn (chỉ đọc được hiện tại)

- `vcgencmd get_throttled` = 0x0 mọi lần đo trong phiên → không có dấu hiệu thiếu nguồn **hiện tại**.
- Firmware log hiện tại (vclog --msg, 30 dòng): AVS core 0.86V bình thường, không thấy under-voltage event trong dữ liệu còn lại.
- **KHÔNG kết luận về nguồn 31/10** — xem `M1_PI5_REBOOT_INVESTIGATION.md` (INSUFFICIENT_HISTORICAL_EVIDENCE).
- `POWER_HEALTH = UNKNOWN` về quá khứ (không có log persistent) — trung thực theo §4.7 master prompt.

## Trạng thái hình thể (từ service status + phiên trước)

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Tai (mic BT HFP) | ⚠️ phụ thuộc loa BT bật | wake/VAD cần mic loa XB33; hôm nay loa tắt |
| Mắt (camera) | chưa probe trong M1 | đề xuất M1.1 bổ sung sau |
| Miệng (TTS) | ✅ engine sẵn | edge-tts + greet WAV cục bộ |
| Kiosk HDMI | ✅ service active | quan_ai_kiosk_guard active |
| Wake word | ✅ service active | quan_ai_wake active |

## Nhận định

1. Pi5 khỏe về nhiệt/ram/disk/throttle — không có dấu hiệu sự cố hiện tại.
2. Cảnh báo duy nhất là **loa BT tắt** (ngoài phần mềm) — Alert Engine đã tự DM anh 4 lần (đúng cooldown 5 phút), sẽ tự khỏi khi anh bật nguồn.
3. Khoảng trống đo: camera + HDMI vật lý + undervoltage quá khứ — cần Q-2 (persistent journal) + bổ sung probe v4l2/DRM ở M1 tiếp theo nếu anh duyệt.
