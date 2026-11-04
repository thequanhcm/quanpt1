# BÁO CÁO KỸ THUẬT — udr1_universal_device_reader

> Sinh tự động 04/11/2026 23:29:50 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
UDR-1 Universal Device Reader: Pi5 đọc TẤT CẢ thiết bị cắm vào (USB/Serial/I2C/SPI/GPIO/Storage/HDMI/Camera/BLE/LAN/1-Wire) mỗi 60s, diff cắm/rút tự gửi về Core qua kênh HMAC sẵn có, Core lưu SQLite + DM NetChat TONY cho anh biết hiện trạng. 5/5 test PASS; 102 test edge+qpig không vỡ.

## 2. PHÂN TÍCH
- Trục V41 sẵn có: EdgeAgent event buffer -> /api/executive/edge/events (HMAC) -> edge_monitor; chỉ cần cắm reader mới, KHÔNG tạo trục thứ hai.
- Nghiệp vụ anh yêu cầu: cắm thiết bị qua USB/LAN -> Pi5 đọc tất cả -> DM TONY báo hiện trạng.
- Lỗ hổng cũ: _detect_peripherals chỉ đọc camera/I2C/ALSA — không thấy USB/serial/storage/BLE/LAN.

## 3. ĐÁNH GIÁ
- 5/5 test mới PASS (test_device_reader.py): scanner trung thực trên Windows (0 thiết bị + note), watcher diff cắm/rút, store DM cooldown.
- 102 test edge/qpig/uaiif PASS — không vỡ danh mục 25 tool QPIG, không vỡ Edge Agent V41.
- server import OK: _GLOBAL_DEVICE_STORE (DeviceStore) + sender netchat gắn sẵn.

## 4. ĐỊNH HƯỚNG
- edge_client/device_readers.py: 10 scanner read-only stdlib-only fail-closed (USB lsusb+sysfs, serial by-id, I2C, GPIO/SPI, block+mounts, HDMI drm, v4l2, bluetoothctl, ip neigh, hwmon+w1).
- edge_client/device_watcher.py: DeviceWatcher diff 60s -> DEVICE_ADDED/DEVICE_REMOVED vào EdgeEventBuffer; start_background cắm vào start_background_loops; snapshot đi cùng heartbeat (edge_agent.devices).
- web/device_store.py + server.py: DeviceStore SQLite (data/edge_devices.db) + DM NetChat cooldown 300s; GET /api/executive/edge/devices (?history=1); heartbeat snapshot persist.
- pi5_deploy/tony_pi5_all_in_one.sh bước 2b rsync 2 module mới; zip đóng gói đủ 4 file (script+pub+2 module) sha256 788b147ce6bd1c8a.

## 5. ĐỀ XUẤT
- (không có — không có đề xuất mới)

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- pytest tests/test_device_reader.py: 5 passed
- pytest 6 file edge+qpig: 102 passed (124.86s)
- bash -n tony_pi5_all_in_one.sh: SYNTAX_OK
- server import: _GLOBAL_DEVICE_STORE=DeviceStore, sender=True

## 7. RỦI RO & TRUNG THỰC
- Chưa test E2E trên Pi5 thật (Pi5 chưa mở SSH) — trạng thái CODED+TESTED-đơn-vị, KHÔNG khai VERIFIED trên phần cứng.
- bluetoothctl có thể chậm — đã bọc timeout 6s; scanner nào lỗi chỉ nuốt kênh đó.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Chạy sudo bash tony_pi5_all_in_one.sh (zip mới đã có đủ) trên Pi5 để mở kênh — lúc đó UDR-1 chạy thật + DM TONY hoạt động E2E.
- Merge PR #3 (chứa UDR-1 sau commit này).

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `edge_client/device_readers.py`
- `edge_client/device_watcher.py`
- `src/quan_ai_brain/web/device_store.py`
- `tests/test_device_reader.py`
- `pi5_deploy/tony_pi5_all_in_one.sh`
- `tony_pi5_all_in_one.zip`
