# FIX "MỞ TAB KHUNG HÌNH RIÊNG" BỊ LỖI (06/11)

**Owner:** ảnh tab `127.0.0.1:8766/api/executive/edge/camera/stream` hiện:
`{"success": false, "error": "Camera stream unavailable: <urlopen error timed out>"}` (18:36)

## Root cause (2 lớp)

1. **Thời điểm 18:36 Pi5 đang OFFLINE** (chưa power-cycle, boot lại 18:41) — core proxy GET
   `http://192.168.1.21:8768/api/kiosk/camera/stream` không nối được → timeout 3s → JSON lỗi thô.
   Đây là **hành vi đúng (fail-honest)**: Pi5 offline thì phải báo lỗi, không được trả ảnh giả.
2. **Lỗi độ trễ tiềm ẩn (đã fix)**: timeout proxy 3.0s trong khi rpicam-still mất ~1.4-2.5s/frame
   (đo thật trên Pi5: 3 lần chụp = 1.43s / 1.46s / 1.43s) — nếu bấm nút khi camera vừa bật từ OFF
   có thể vượt 3s → "timed out" dù Pi5 online. **Patch server.py:4635: timeout 3.0s → 8.0s**.

## Verify sau fix (bằng chứng thật)

- Restart dual servers (watchdog hồi sinh), health 8765+8766 OK
- `camera_on` qua core → `GET /api/executive/edge/camera/stream` → **200 image/jpeg, 61.289 bytes, 1.5s** (JPEG hợp lệ)
- Trạng thái camera OFF khi camera chưa bật → **403 Forbidden trong 0.1s** (không treo) — front-end dashboard hiển thị alert đỏ đúng
- Sau verify: `camera_off` — privacy giữ nguyên

## Hướng dẫn đúng cho owner

- Tab "Mở Tab Khung Hình Riêng" chỉ hiện ảnh khi **camera đang bật**: bấm **BẬT CAMERA** trước,
  rồi mở tab. Camera OFF → tab hiện JSON lỗi (thiết kế fail-honest — an toàn > tiện lợi).
- Nếu thấy "timed out" mà Pi5 online → bấm lại 1 lần nữa (frame đầu tiên sau khi bật mất ~1.5-2.5s).

## Trạng thái: FIXED + LIVE_VERIFIED (stream 200 thật 61KB)
