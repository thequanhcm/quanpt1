# HDMI MIRROR — 'OK' KHÔNG BẬT ĐƯỢC HÌNH (23:14, 06/11/2026)

## Diễn biến
- 22:49 + 23:00: bot DM hỏi "có muốn xuất hình lên HDMI không? phê duyệt: 'phê duyệt hdmi' hoặc 'ok'".
- 23:14: owner nhắn "ok" (tick xanh đôi — bot NHẬN được).
- KHÔNG có gì xảy ra: HDMI mirror không bật, bot không phản hồi.

## ROOT CAUSE 1 — vòng phê duyệt bị đứt (design bug)
- Tin hỏi HDMI do **server.py** (`_handle_api_edge_hdmi_event`) gửi khi daemon
  Pi báo hdmi_event. Nó chỉ set `_GLOBAL_HDMI_STATE["awaiting_approval"]=True`
  + DM hỏi — **KHÔNG stage pending action** cho command_center.
- Owner gõ "ok" → command_center `_OK_RE` → `run_pending_action(session)` →
  KHÔNG có pending action → **ok_silent** (im lặng theo thiết kế 27/10).
- Path "ok" có 'hdmi' (`tony_hdmi_approve`) chỉ khớp khi text CHỨA từ 'hdmi' —
  "ok" đơn thuần không chứa → không bao giờ bật mirror.
→ "ok" trong tin này là lệnh HỎI UY QUYỀN của bot nhưng hệ thống không gắn nó
với pending action nào = hẹn mà không ghi sổ.

## ROOT CAUSE 2 — HDMI video pipeline bị từ chối enable (Pi5)
- Bật mirror thủ công qua /edge/control: daemon báo success NHƯNG
  `wlr-randr --output HDMI-A-2 --on` bị labwc trả `failed()` cho MỌI mode
  (4K/1080p/720p/480p, --preferred, kèm/tắt NOOP-1). Kernel DRM:
  card1-HDMI-A-2 status=connected nhưng enabled=disabled; không có CRTC nào
  nhận. Chromium mirror chạy vào output đang disabled → không có hình.
- Audio HDMI (card1 sound) vẫn OK — chỉ VIDEO pipe từ chối.
- Màn DSI 7": DRM không còn connector DSI (không fb, không backlight) —
  hệ thống hình hiện chỉ còn NOOP-1 (headless). Kiosk chính vẫn chạy
  (guard rebuild OK, kiosk_running=true).
- Daemon có **false-success**: `launch_hdmi_mirror()` return True chỉ vì
  Popen không raise — không kiểm output thật (vi phạm fail-honest).

## Đã làm trong phiên (không tự sửa code)
- Bật mirror thử qua /edge/control → phát hiện false-success → đã dọn
  chromium mirror zombie; guard rebuild kiosk chính ✓ (kiosk_running=true).

## ĐỀ XUẤT FIX (chờ owner duyệt)
1. [PC+Pi5] Sửa vòng phê duyệt: khi bot hỏi HDMI → stage_pending_action
   (chính thức, TTL 15 phút) trong command_center → "ok" thực thi
   `tony_hdmi_approve` thật. Sửa thêm: daemon xác nhận mirror_running=true
   sau 2s mới báo success (fail-honest).
2. [Pi5] HDMI video: 2 phương án
   a. Thêm `video=HDMI-A-2:1920x1080@60D` vào cmdline /boot/firmware/cmdline.txt
      (force enable qua KMS) + reboot Pi5 (hẹn giờ reboot 03:00, không đụng 24/7).
   b. Kiểm dây/cổng HDMI + thử HDMI-A-1 — nếu Samsung TV chấp nhận 1080p thì
      modeset có thể qua được (hiện 4K@30 preferred bị từ chối).
3. [PC] Sửa DM hỏi HDMI: bot sẽ tự hủy câu hỏi sau 10 phút không trả lời
   (tránh "hỏi rồi quên").

## Bằng chứng chính (lệnh thật trong phiên)
- audit.jsonl 0 event ok_confirmed/tony_hdmi_approve sau 16:10 UTC.
- `wlr-randr --output HDMI-A-2 --on` → rc=1 'failed to apply configuration'
  (mọi mode + WAYLAND_DEBUG thấy zwlr_output_configuration.failed()).
- `/sys/class/drm/card1-HDMI-A-2/{status,enabled}` = connected/disabled.
- /edge/control hdmi_show → success:true nhưng kiosk/hdmi mirror_running=false.
- Guard rebuild kiosk chính sau khi dọn mirror: kiosk_running=true ✓.
