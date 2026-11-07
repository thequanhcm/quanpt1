# AUDIT TỔNG THỂ CHERRY (PC) + PI5 — 06/11/2026 23:20 (LIVE)

Phạm vi: yêu cầu owner "audit và kiểm tra tổng thể toàn bộ cherry và pi5".
Phương pháp: kiểm tra thật qua SSH, HTTP, DB read-only, journal, Task Scheduler.
KHÔNG đọc secret value (chỉ hash/đếm).

## 1. PC — CHERRY CORE

### Git & bảo mật
- Branch `feat/deom-m1-m2-task-lifecycle`, HEAD `4ecbf47` (= origin, sync).
- Working tree còn 4 file runtime state (conversation/chroma/responder/hmac-bak) — đúng quy ước KHÔNG commit.
- File nhạy cảm trong git: KHÔNG có. `edge_client/config.json` trong HEAD chứa key
  `shared_secret` — **ĐÃ LƯU Ý RỦI RO** (QPIG §6: mã bí mật không dạng rõ) → khuyến nghị
  chuyển sang biến môi trường/file ngoài git (đề xuất, chờ owner duyệt).

### Tiến trình & HTTP
- start_dual_servers: 2 proc (1 instance chuẩn, 23:10) — 8765 HTTP 200 (17KB, "Cherry" ✓).
- netchat_auto_responder: 2 proc (1 instance chuẩn, venv shim→py311).
- Edge: READY, paired, RTT 31ms, misses=0, kiosk=True, alerts=0.
- Supervisor: state=READY, LLM E2E 2.7s reply "OK" ✓ (NetMind Cloud GLM-5.3-Flash).
- Memories API: 100 bản ghi (tab Trí Nhớ + nút xóa hoạt động).

### DB brain.db (read-only)
- episodes 2.974 (mới nhất 16:16:11 — đang ghi sống ✓)
- semantic_memory 5.052 · candidate_knowledge 9.500
  (approved 1.491 / promoted 3.209 / quarantined 4.800)

### Learning daemon
- Chu kỳ 5 phút chạy OK: 5.868 facts/cycle, quarantine 4.793 chờ duyệt
  (KHÔNG tự promote — V3 governance đúng thiết kế).

### Audit log
- audit.jsonl hoạt động: chụp ảnh/video/listen qua DM ghi nhận (15:53).
- 1 lỗi cũ `tony_pi_photo HTTP 500` lúc 15:53 — camera status bây giờ OK
  (IMX708 hardware_detected=True). Đã tự hồi phục / không tái diễn trong audit này.

### Task Scheduler 24/7
- KHOI_DONG_LOGON: chạy 06/11 12:43 result=0 ✓
- **BỎ LỠ**: BACKUP_2AM LastRun=11/05 07:33, MORNING_REPORT_8AM LastRun=11/05 08:00
  → không chạy ngày 06/11 (next 11/07). Nguyên nhân: máy tắt/ngủ lúc 02:00–08:00
  ngày 06/11 và task đặt **StartWhenAvailable=False** → không bù chạy khi bỏ lỡ.
  → ĐỀ XUẤT: bật StartWhenAvailable=True cho cả 2 task (chờ owner duyệt).

## 2. PI5 — HÌNH THỂ SỐ

### Units (system-level)
- quan_ai_edge: active ✓ · quan_ai_wake: active ✓ · quan_ai_kiosk_guard: active ✓
- tony_channel_selector.timer: active ✓ (service oneshot exit 0 mỗi 30s — "Failed"
  trong journal 23:0x là kiểu serwis oneshot báo nhầm khi chạy quá 2s, các lần sau
  đều SUCCESS — đã xác minh status hiện tại: inactive(dead) status=0/SUCCESS).

### Kết nối & chọn kênh
- Selector state: **active=LAN, rtt=6.2ms** · core_host=192.168.1.9 (LAN-first đúng lệnh owner).
- Kiosk status: core_connected=True, core_host=192.168.1.9:8766 ✓.

### Sức khỏe phần cứng
- Nhiệt 51.25°C (an toàn) · RAM 1.396/4.045MB dùng (2.648 trống) · root 13%.
- throttled=0x0 (không under-voltage, không throttle) · uptime 40 phút.
- Time sync: synchronized=yes, Asia/Ho_Chi_Minh ✓.
- Camera /dev/video0 có ✓ · aplay 3 cards (2 HDMI + Jieli USB mic).

### Đồng bộ code PC↔Pi5
- client_daemon.py sha256: 375b7dc4… — KHỚP 2 máy ✓
- tony_channel_selector.py sha256: cafd6b4a… — KHỚP 2 máy ✓
- Avatar: kiosk.html ?v=smooth_06nov_r1, chromium 10 proc chạy.

### Audio
- WirePlumber/PipeWire/PipeWire-Pulse: active ✓ (loa HDMI card1).
- Mic Jieli UACDemoV1.0: mic_enabled=True, unmuted, −18dB, WAKE_WORD mode ✓.
- **Vấn đề 24h**: 22× TTS timeout + 5× Edge TTS 503 (cloud flaky) — đã biết,
  TTSManager chưa auto-fallback piper (đang chờ owner duyệt đề xuất Q-3 cũ).

### Wake word
- 1h: 26 lần [WAKE] thật + 422 dòng debug.
- **FALSE WAKE PHÁT HIỆN**: bộ khớp mờ khớp token 'ơi' với 'toi'/'tôi'
  (Levenshtein ≤2) + has_oi cùng lúc → câu TV như "và soát sắp xếp ngoài
  khơi…" cũng wake. Thiết kế chấp nhận false-positive thấp (wake = bật màn
  hình, vô hại) nhưng đang nhiều hơn dự kiến. → ĐỀ XUẤT: yêu cầu has_oi là
  token ĐỘC LẬP và bỏ 'ơi' khỏi danh sách has_name (chờ owner duyệt).

### Lỗi journal 24h (edge)
- 22× tts-synthesize timeout, 11× converse Connection timed out (LAN chết
  phiên trước — đã fix LAN-first hôm nay), 7× BrokenPipe (client ngắt — vô hại),
  4× resume Unauthorized (phiên secret cũ — đã fix HMAC đồng bộ).
- kiosk_guard chỉ 2 lần "Started" trong 24h (không restart loop) ✓.

## 3. KẾT LUẬN

**Tổng thể: HỆ THỐNG KHỎE MẠNH** — 4 units Pi5 active, kết nối LAN-first ổn định
(RTT 6–35ms), code 2 máy đồng bộ sha256, camera/mic/wake/LLM/DB/learning đều
hoạt động thật (có bằng chứng E2E từng mục).

**3 vấn đề mở (theo mức độ):**
1. [PC] Backup 2AM + Morning Report 8AM bỏ lỡ 06/11 — StartWhenAvailable=False
   → đề xuất bật (chờ duyệt).
2. [Pi5] Wake false-positive từ khớp mờ 'ơi'~'toi' (TV noise) → đề xuất siết
   matcher (chờ duyệt).
3. [PC] shared_secret dạng rõ trong git-tracked config.json (rủi ro QPIG §6)
   → đề xuất chuyển ENV/file ngoài git (chờ duyệt).
4. (Đã tồn tại trong hàng chờ) TTSManager chưa fallback piper khi Edge 503.

Trạng thái bằng chứng: mọi mục ghi LIVE_VERIFIED đều có lệnh kiểm thật kèm kết
quả trong phiên này. Không tự sửa gì ngoài audit (read-only) — thay đổi chờ duyệt.
