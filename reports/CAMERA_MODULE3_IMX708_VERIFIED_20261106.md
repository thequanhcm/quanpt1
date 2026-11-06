# CAMERA PI5 = CAMERA MODULE 3 (IMX708) — ĐÃ XÁC MINH + SỬA LABEL (06/11)

**Owner:** "camera trên Pi5 đang là loại modul V3"

## 1. Xác minh phần cứng (bằng chứng SSH thật)
- `rpicam-still --list-cameras`: **`0 : imx708 [4608x2592 10-bit RGGB]`** — Camera Module 3, sensor IMX708, chế độ 1536x864@120fps / 2304x1296@56fps / 4608x2592@14.35fps
- `/boot/firmware/config.txt`: `dtoverlay=imx708,cam0` — CSI overlay đúng
- Driver rp1-cfe + unicam đăng ký đúng node CSI2

## 2. E2E chụp ảnh THẬT qua pipeline production (khenh chuẩn)
- `POST /api/kiosk/camera/control {"action":"camera_on"}` → 200 READY
- `GET /api/kiosk/camera/snapshot` → **200 image/jpeg 71.962 bytes**
- Vision phân tích frame: rõ nét, autofocus PDAF khóa đúng, 640x480, màu/WB chuẩn — camera KHỎE
- Ảnh lưu: `reports/camera_v3_live_20261106.jpg` (nội dung: bếp + tủ lạnh + hồ cá — khung nhìn thật của Module 3)
- Sau verify: `camera_off` (privacy policy — camera không bật khi không dùng)
- Lưu ý: rpicam-still CLI trực tiếp có thể báo "Device busy" vì pipewire/wireplumber giữ video node (libcamera monitor) — pipeline client_daemon qua API vẫn chụp được bình thường.

## 3. Sửa label sai "USB WEBCAM V4L2 / Sirius" (dashboard hiện Sai tên phần cứng)
Code vốn ghi label USB webcam cũ (sai từ trước khi gắn Module 3) — đã sửa toàn bộ:
| File | Trước → Sau |
|---|---|
| `web/static/executive.html:1093` | "REMOTE CAMERA & VISION • USB WEBCAM V4L2" → "• PI CAMERA MODULE 3 (IMX708 CSI)" |
| `web/static/executive.html:1099` | badge "/dev/video0 (V4L2)" → "libcamera (IMX708)" |
| `web/static/executive.html:1117` | "640x480 • V4L2 USB" → "640x480 • CSI IMX708" |
| `web/static/executive.html:1122` | "Sirius USB2.0 Camera" → "Raspberry Pi Camera Module 3" |
| `web/static/executive.js:2740, 2875, 2932-2933` | device_node "/dev/video0" → "libcamera/imx708"; alert + metadata ghi đúng Module 3 |
| `web/server.py:4610` | fallback offline label → "Raspberry Pi Camera Module 3 (Chưa kết nối)" |
| `edge_client/client_daemon.py` (đã sync Pi5, sha256 khớp) | error msg "/dev/video0" → "Camera Module 3 (IMX708/libcamera)" |

## 4. Verify sau sửa
- server 8766 restart (watchdog hồi sinh), JS `node --check` OK
- `/api/kiosk/camera/status` (LAN) + `/api/executive/edge/camera/status` (core): **device_name = "Raspberry Pi Camera Module 3 (IMX708, libcamera)"**, pi5_online=True
- Camera cuối phiên: **OFF** (đúng privacy)

## Trạng thái: LIVE_VERIFIED (chụp thật qua API + vision phân tích frame) — label = đúng phần cứng
