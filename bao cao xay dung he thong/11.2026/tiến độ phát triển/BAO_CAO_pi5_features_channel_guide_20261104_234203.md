# BÁO CÁO KỸ THUẬT — pi5_features_channel_guide

> Sinh tự động 04/11/2026 23:42:03 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Tổng hợp toàn bộ tính năng Pi5 + hoàn thiện KÊNH TRUYỀN THÔNG LIÊN TỤC Core↔Pi5 + file cài đặt zip 11 file + hướng dẫn đầy đủ. Lỗ hổng thật đã vá: Pi online lại sau mất mạng KHÔNG báo — thêm BRAIN_CONNECTION_RESTORED → ALERT_E_PI5_RECOVERED → DM owner 'Pi5 online lại sau Xs'.

## 2. PHÂN TÍCH
- Kênh xuôi PC→Pi: heartbeat 1s (Pi chủ động gọi /api/executive/supervisor HMAC) — pending_commands FIFO, mỗi nhịp 1 lệnh.
- Kênh ngược Pi→PC: EdgeEventBuffer (deque giới hạn) — send fail → push lại đầu buffer, retry mỗi vòng, KHÔNG mất event khi offline.
- Lỗ hổng: detect_connection_lost chỉ xử lý CONNECTED→LOST; LOST→CONNECTED không sinh event — owner không biết khi nào Pi sống lại.
- Script sync 3 file device_* nhưng client_daemon.py/edge_agent.py trên Pi là bản CŨ → UDC-1 sẽ hỏng khi E2E (endpoint /api/kiosk/device không tồn tại trên Pi).

## 3. ĐÁNH GIÁ
- 18/18 test_continuous_channel PASS (lost/restored, callback, queue FIFO, DeviceStore roundtrip).
- 13+5 UDC/UDR + 54 edge/monitor PASS lại sau vá; server import OK; bash -n SYNTAX_OK.
- Zip 11 file (script + pub + 9 module lõi edge_client) — script tự sync 9/9, cảnh báo nếu thiếu.

## 4. ĐỊNH HƯỚNG
- edge_agent.py: _offline_since_epoch + detect_connection_lost sinh BRAIN_CONNECTION_RESTORED (offline_seconds) khi LOST→CONNECTED.
- server.py _handle_api_edge_events: RESTORED → _trigger_alert ALERT_E_PI5_RECOVERED severity INFO (enum sẵn có chưa dùng).
- tony_pi5_all_in_one.sh bước 2b: sync 9 module lõi từ edge_client/ cạnh script (zip mới có thư mục edge_client/).
- docs/HUONG_DAN_PI5_CAI_DAT_VA_KENH_LIEN_LAC.md: 6 phần — tính năng, kênh liên lạc 3 lớp, cài đặt 6 bước, lỗi thường gặp, trạng thái trung thực.

## 5. ĐỀ XUẤT
- (không có — không có đề xuất mới)

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- pytest tests/test_continuous_channel.py + test_device_control_dm.py + test_device_reader.py: 18 passed
- pytest test_v41_edge_agent + test_edge_client + test_edge_monitor: 54 passed
- zip 58,480 bytes sha256 1b9ae4b448c9df40… 11 file; bash -n SYNTAX_OK

## 7. RỦI RO & TRUNG THỰC
- Vẫn CHƯA E2E trên Pi5 (SSH đóng) — mọi tính năng Pi5 giữ trạng thái CODED+TESTED đơn vị.
- ALERT_E severity INFO không tạo DM trực tiếp qua alert_engine (chỉ CRITICAL/WARNING) — recovery thấy trên dashboard + event history; DM 'mất kết nối' vẫn CRITICAL như cũ.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Chạy script trên Pi5 (zip 11 file mới trong DM) → em test E2E toàn bộ: heartbeat, UDR, UDC, kênh liên tục.

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `edge_client/edge_agent.py (sửa — RESTORED event)`
- `src/quan_ai_brain/web/server.py (sửa — ALERT_E map)`
- `tests/test_continuous_channel.py (mới — 5 test)`
- `pi5_deploy/tony_pi5_all_in_one.sh (sửa — sync 9 module)`
- `tony_pi5_all_in_one.zip (11 file)`
- `docs/HUONG_DAN_PI5_CAI_DAT_VA_KENH_LIEN_LAC.md (mới)`
