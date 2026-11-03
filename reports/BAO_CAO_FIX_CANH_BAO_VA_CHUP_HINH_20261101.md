# BÁO CÁO XỬ LÝ DỨT ĐIỂM — CẢNH BÁO SPAM + LỆNH "CHUP HINH" BỊ RƠI
**Thời điểm:** 01/11/2026 16:22 · **Yêu cầu owner:** image_f2e006 — "anh đã xác nhận tắt cảnh
báo thì em cần xử lý để hệ thống không báo lại. xử lý dứt điểm lỗi chụp hình"
**Thực hiện:** TONY · **Trạng thái:** ✅ HOÀN TẤT — regression 3.002 PASS / 0 FAIL, E2E live đã kiểm chứng

---

## 1. LỖI "CHUP HINH" 14:21 — ROOT CAUSE VÀ FIX

### Bằng chứng (log `logs/netchat_auto_responder_stdout.log`)
```
📩 New message at 07:21:55:  Chụp hình   (= 14:21 giờ VN)
   ⚠️ Command router error: No module named 'tools.netchat_command_center'
   → GLM bịa: "em chưa có công cụ chụp ảnh từ camera Pi 5 nào được kiểm chứng"
```
Lỗi này lặp cho MỌI lệnh hệ thống từ 05:17 UTC (12:17 VN), kể cả sau restart 15:36.

### Root cause (tái hiện + xác nhận trong lab)
Responder được spawn thừa hưởng `PYTHONPATH` của netMind Desktop
(`…\netmind_desktop\netmind-agent`). Thư mục này có package `tools` RIÊNG (không chứa
`netchat_command_center`) → Python nạp `tools` GIẢ vào `sys.modules` TRƯỚC khi
`sys.path.insert(BRAIN)` chạy → mọi `from tools.netchat_command_center import …` chết.
→ Lệnh của anh rơi xuống luồng chat AI thường → bot từ chối sai (camera Pi5 thực ra
SẴN SÀNG — chụp thử 15:49 thành công 117 KB, gửi DM OK).

### Fix gốc (`tools/netchat_auto_responder.py` đầu file)
1. Đẩy BRAIN root lên **đầu** `sys.path` ngay khi import,
2. Dọn cache `tools` không thuộc BRAIN khỏi `sys.modules`.
3. Tương tự vá `tools/learning_daemon.py` + `tools/watchdog.py` (phòng ngừa).

### Kiểm chứng
- E2E lab: PYTHONPATH ô nhiễm y hệt → `detect_intent('Chup hinh')` → `tony_pi_photo` ✅
- Chụp thật bằng cùng luồng `route_message("Chup hinh")` → ảnh chụp thành công, gửi DM ✅
- Regression full: **3.002 PASS / 0 FAIL / 44 skipped** (142,7s) ✅

---

## 2. CẢNH BÁO `bt_speaker_connected=no` SPAM — OWNER-ACK MỚI

### Vấn đề
AlertEngine chỉ có cooldown 300s — KHÔNG có khái niệm "owner đã quyết định giữ nguyên".
Anh xác nhận "Tiếp tục giữ tắt" 14:21 → hệ thống vẫn cảnh báo lại 14:24/14:31/14:38/14:44.

### Fix (`src/quan_ai_brain/monitoring/alert_engine.py` + command center)
- Mới: `data/alert_owner_ack.json` — store quyết định owner (check_id + reason + thời gian).
- `evaluate_checks` kiểm tra ack: cảnh báo đã ack **vẫn ghi DB để audit** (dòng
  `[OWNER-ACK] …`, `suppressed_reason='owner_ack'`) nhưng **KHÔNG gửi DM nữa**.
- Lệnh DM mới: **"giữ nguyên loa" / "tắt cảnh báo loa" / "không cảnh báo nữa"** → tự ghi
  ack (map: loa→bt_speaker_connected, mic, nhiệt độ, cpu, ram, đĩa).
- Em đã ghi ack `bt_speaker_connected` thay anh theo quyết định 14:21 của anh.

### Kiểm chứng LIVE (DB health_alerts.db, sau khi bật)
| Thời gian | sent | reason |
|---|---|---|
| 16:03:29 | 1 | (cảnh báo cuối cùng trước ack) |
| 16:13:24 | **0** | **owner_ack** |
| 16:15:37 | **0** | **owner_ack** |
| 16:17:48 | **0** | **owner_ack** |
| 16:19:59 | **0** | **owner_ack** |

→ 4 chu kỳ liên tiếp bị chặn đúng lý do `owner_ack`. Không còn spam.

---

## 3. TRẠNG THÁI HỆ THỐNG SAU XỬ LÝ (16:20)
- Servers 8765 + 8766: HTTP 200 ✅ · Edge: READY, heartbeat 3s, RTT 234ms, HMAC live ✅
- Responder: heartbeat 2s trước ✅ · Learning daemon: cycle OK (4.565 knowledge) ✅
- Process: mỗi service 1 launcher `.venv` + 1 child (cấu trúc launcher→child của venv
  đã được chứng minh bằng thí nghiệm — KHÔNG phải duplicate).
- Lưu ý vận hành: restart bằng PowerShell Start-Process (spawn từ kernel tool bị Job
  Object giết theo khi kernel timeout).

## 4. FILE THAY ĐỔI
1. `tools/netchat_auto_responder.py` — fix import P0 (đầu file)
2. `tools/learning_daemon.py` — fix path (phòng ngừa)
3. `tools/watchdog.py` — fix path (phòng ngừa)
4. `src/quan_ai_brain/monitoring/alert_engine.py` — owner-ACK store + gate trong evaluate_checks
5. `tools/netchat_command_center.py` — intent `ack_alert` + handler `handle_ack_alert`
6. `data/alert_owner_ack.json` — ACK loa TẮT (theo quyết định anh 14:21)

## 5. CÁCH DÙNG SAU NÀY (cho anh)
- Muốn ngừng 1 cảnh báo: nhắn DM **"giữ nguyên loa"** (hoặc mic/nhiệt độ/cpu/ram/đĩa).
- Em vẫn theo dõi ngầm — nếu tình trạng thay đổi thật (loa được bật), em báo anh.
- Lệnh "Chup hình"/"Chụp ảnh" giờ CHẠY THẬT camera Pi5, không rơi vào chat AI nữa.
