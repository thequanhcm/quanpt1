# PANEL SỨC KHỎE PI5 TRÊN PHÒNG ĐIỀU HÀNH (8766) — 06/11/2026

## Yêu cầu owner
"kiểm tra về tốc độ phản hồi của Pi5, cấu hình và mức độ sử dụng RAM trên Pi5.
em hãy cho hiển thị thông số đó lên trên phòng điều hành."

## Thiết kế (smallest safe — dùng dữ liệu ĐÃ CÓ, không thêm daemon)
- Edge Agent V41 trên Pi5 ĐÃ đo metrics thật mỗi 30s (CPU/RAM/nhiệt/throttle/
  load/uptime) và ĐÃ gửi theo heartbeat 1s (`edge_agent` trong payload).
- Thiếu duy nhất 1 mắt xích: handler `/api/executive/edge/telemetry` chưa trả
  `edge_agent` → đã thêm 1 field (server.py).

## Files đổi
1. `src/quan_ai_brain/web/server.py` — telemetry trả thêm `edge_agent`
   (metrics thật từ Pi5, không suy diễn).
2. `src/quan_ai_brain/web/static/executive.html` — panel mới
   "Sức khỏe Pi 5 (thời gian thực)" cạnh box kết nối Pi5 ở Cockpit:
   RTT / Kênh truyền / CPU / RAM / Nhiệt độ / Uptime + dòng cấu hình
   (Pi 5 Model B · 4GB RAM · Edge Agent V41).
3. `src/quan_ai_brain/web/static/executive.js` — `loadEdgeTelemetry`
   (poll 1.5s) render 6 ô mới; màu cảnh báo: RTT >150ms đỏ, >60ms vàng;
   CPU >85% đỏ, >60% vàng; RAM >90% đỏ, >75% vàng; nhiệt >75°C đỏ, >65°C vàng.
   Kênh truyền suy từ edge_ip thật: 192.168.x = "LAN/WiFi (ưu tiên)",
   100.x = "Tailscale Mesh" (đo được, không giả).

## Bằng chứng live (23:15, sau restart servers)
- `/api/executive/edge/telemetry` trả:
  RTT 49.4ms · edge_ip 192.168.1.21 (LAN) · CPU 34.9% · RAM 2620/4045 MB trống
  · nhiệt 50.15°C · throttle OK · load 1.46/1.5/1.51 · uptime 2088s · V41.
- executive.js serve có `pi5-health-rtt` + `edge_agent` ✓
- executive.html serve có `pi5-health-box` ✓
- Đối chiếu SSH trực tiếp Pi5: top 65.9% idle (~34% dùng) — KHỚP metrics.
  free -m: available 2621MB — KHỚP metrics.
- Tests: 76 passed (web_server + edge_monitor + web_executive_endpoints +
  v41_edge_agent + edge_client).
- node --check executive.js OK.

## Trung thực
- CPU metric mẫu đầu tiên sau restart agent có thể lệch (cần 2 mẫu liên tiếp)
  — panel hiển thị "đang đo..." cho đến khi số liệu hợp lệ.
- RAM tính % trên MemTotal thực tế 4045MB (Pi5 chia 1GB cho GPU).
- Uptime đo từ boot hệ điều hành Pi5.
- KHÔNG commit (chờ lệnh owner) — thuộc changeset "pi5-health-dashboard".
