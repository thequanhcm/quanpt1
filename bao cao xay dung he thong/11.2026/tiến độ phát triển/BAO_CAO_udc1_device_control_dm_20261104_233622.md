# BÁO CÁO KỸ THUẬT — udc1_device_control_dm

> Sinh tự động 04/11/2026 23:36:22 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
UDC-1: Pi5 KHỐNG CHẾ thiết bị theo lệnh DM của anh — 4 lệnh mới ('thiết bị trên pi', 'bật/tắt rơ le N', 'dừng khẩn thiết bị'); lệnh ghi bắt buộc confirm 2 bước ('ok'), token Pi cấp gắn (op,target,value), TTL 10 phút, một-lần; read-only tự do. Fix kèm: 'dừng nhạc' bị rơi nhầm lệnh stop tổng (bug cũ).

## 2. PHÂN TÍCH
- Đường PC→Pi sẵn có: _send_edge_request → kiosk 8768 (/api/kiosk/control...) — chưa có kênh điều khiển THIẾT BỊ vật lý.
- ActuatorController sẵn có (8 relay BCM + 6 khớp servo PCA9685, emulated mode) chưa được nối vào kiosk API lẫn DM.
- detect_intent: 'dừng khẩn thiết bị' bị pattern 'stop' rộng nuốt; 'bật rơ le' bị pc_open nuốt.

## 3. ĐÁNH GIÁ
- 13/13 test mới PASS (test_device_control_dm.py): token one-shot + bound (op,target) + TTL; estop không cần token; 17 intent route đúng.
- 63 test edge/qpig PASS; server import OK.
- 17/17 intent check PASS (kèm fix 'dừng nhạc' pre-existing).

## 4. ĐỊNH HƯỚNG
- edge_client/device_control.py: DeviceControlService — stage_write cấp token, execute kiểm tra token khớp (op,target,value), TTL 600s, one-shot; emergency_stop chạy ngay.
- client_daemon.py: POST /api/kiosk/device → service.execute(); DaemonState giữ device_control (watcher_provider + actuator chung).
- server.py: action='device' forward op/target/value/confirm_token xuống kiosk 8768.
- netchat_command_center.py: 4 intent (device_list, relay_on/off qua _ARG_KEYWORD_RES đứng trước pc_open/close, emergency_stop_device qua _DEVICE_ESTOP_RE đứng trước 'stop'); relay stage qua stage_pending_action — 'ok' mới execute.

## 5. ĐỀ XUẤT
- (không có — không có đề xuất mới)

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- pytest tests/test_device_control_dm.py tests/test_device_reader.py: 13 passed
- pytest edge+qpig 4 file: 63 passed
- bash -n script: SYNTAX_OK; zip 5 file mới
- detect_intent 17/17 PASS

## 7. RỦI RO & TRUNG THỰC
- Chưa E2E trên Pi5 thật (SSH đóng) — trạng thái CODED+TESTED đơn vị.
- relay thật cần phần cứng ngoài (relay board); hiện emulated=True nếu không có RPi.GPIO — trung thực trong kết quả trả DM.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Chạy script trên Pi5 (zip mới 5 file) → test E2E: cắm USB → 'thiết bị trên pi' → 'bật rơ le 1' → 'ok' → relay đổi trạng thái thật.

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `edge_client/device_control.py`
- `tests/test_device_control_dm.py`
- `edge_client/client_daemon.py (sửa)`
- `src/quan_ai_brain/web/server.py (sửa)`
- `tools/netchat_command_center.py (sửa)`
- `pi5_deploy/tony_pi5_all_in_one.sh (sửa) + tony_pi5_all_in_one.zip (5 file)`
