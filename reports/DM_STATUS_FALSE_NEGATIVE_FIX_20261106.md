# FIX: DM báo "kiosk: đang tắt" trong khi Pi5 đang bật — 06/11/2026

> Nguồn gốc: anh Quân hỏi lúc ~20:54 "pi vẫn đang bật, vì sao báo kiosk: đang tắt"
> (tin DM TONY: `🧭 Hình thể Pi 5: DEGRADED | ghép nối: rời | tim đập: ? | kiosk: đang tắt`).

## Root cause — 3 lỗi xếp lớp trong 1 dòng status

| # | Lỗi | Hậu quả hiển thị |
|---|---|---|
| 1 | `handle_tony_status` đọc `edge.last_heartbeat_epoch` — field **không tồn tại** trong response `/api/executive/edge/status` (chỉ có `last_heartbeat_utc` + `seconds_since_heartbeat`) | "tim đập (heartbeat): **?**" vĩnh viễn |
| 2 | `edge.status` **không có field `kiosk_running`** — Pi5 gửi kèm `telemetry.kiosk_running` trong heartbeat nhưng server bỏ qua; `edge.get("kiosk_running")` luôn None | "kiosk: **đang tắt**" vĩnh viễn (báo giả) |
| 3 | Ngưỡng heartbeat timeout **4.0s** trong khi heartbeat gửi mỗi ~1s qua mesh DERP RTT 100–190ms; chu kỳ loop (heartbeat + poll tasks + pgrep kiosk) dễ vượt 4s khi mesh lag → **1 nhịp lỡ = DISCONNECTED + Alert CRITICAL "MẤT KẾT NỐI PI5"** (misses=1) | "DEGRADED/DISCONNECTED" + cảnh báo đỏ giả |

**Bằng chứng lúc 20:57:** response status cho `seconds_since_heartbeat=4.25s` (vừa vượt 4.0s) → state DISCONNECTED + Alert B CRITICAL, trong khi SSH tới Pi5 xác nhận `kiosk_running=True, core_connected=True, chromium --kiosk PID 49028 đang chạy`.

## Fix (commit kèm PR #9)

1. **`edge_monitor.py`**:
   - `record_heartbeat` lưu `metadata` → `last_telemetry` (nguồn sự thật từ Pi5).
   - `get_status` trả thêm `kiosk_running`, `telemetry`, `last_heartbeat_epoch`, `consecutive_misses`.
   - Alert B chỉ bắn sau `alert_on_misses` (mặc định 3) lần miss **liên tiếp** — 1 nhịp lỡ qua mesh không còn là "Pi5 tắt nguồn".
2. **`server.py`**: `heartbeat_timeout_sec` 4.0 → **12.0** (tha thứ ~10 nhịp chậm; thật sự rớt mạng vẫn bị bắt) + heartbeat handler đẩy telemetry vào monitor.
3. **`netchat_command_center.py`** `handle_tony_status`: đọc `seconds_since_heartbeat` (server tự tính) + `kiosk_running` từ field mới; thêm ghi chú miss liên tiếp khi DISCONNECTED.

## Kiểm chứng

- pytest: **37/37 PASS** (edge_monitor 8 — gồm test mới telemetry + test thiết kế 3-miss; device_control_dm; web executive; deep memory).
- **Live sau restart server:** `state=READY | kiosk_running=True | heartbeat age 0.93s | RTT 133ms | alerts 0`.
- **Line DM chạy thật qua `handle_tony_status()`:**
  `🧭 Hình thể Pi 5: SẴN SÀNG | ghép nối: rồi | tim đập (heartbeat): 1s trước | kiosk: đang bật`
- Responder restart sạch (409 answered_ids nạp lại, không trùng lặp).

## Giới hạn trung thực

- Khi mesh DERP lag nặng (RTT > 2.8s), trạng thái vẫn thể hiện `DEGRADED` — đó là **đúng sự thật** kênh truyền chậm, không phải lỗi hiển thị.
- `kiosk_running` phản ánh snapshot heartbeat gần nhất (≤12s tuổi); nếu kiosk vừa tắt trong 12s qua, DM có thể báo trễ 1 nhịp — chấp nhận được cho báo cáo định kỳ.
