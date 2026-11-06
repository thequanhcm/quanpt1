# BÁO CÁO: "duyệt merge" PR #7 + Deploy/Verify E2E sau power-cycle Pi5 — 06/11/2026

## 1. Merge PR #7 qua API (lệnh owner: "duyệt merge")

| Bước | Bằng chứng |
|---|---|
| Pre-check | PR #7 state=open, mergeable=True, mergeable_state=clean, head `9cd471d` |
| Merge API | **merged=True, merge commit `6435155`** |
| Post | origin/master `53b1de8`→`6435155`; local ff khớp; branch pushed |
| PR #7 nội dung | 4 commits: `da3d46f` fix(dm) _NO_WIN+session inject+watchdog lớp 2 · `94f50b2` fix(camera) IMX708 labels+timeout 8s · `b05dc88` fix(pi5) BT-NAP+selector · `9cd471d` docs 5 reports |

## 2. Phát hiện + sửa BUG MỚI khi pre-commit test (test bắt được thật)

`test_relay_dm_stages_pending_not_execute` FAIL ổn định → điều tra root cause:
- **route_message KHÔNG inject `chat_session_id` vào payload** → `handle_relay_on` đọc `payload['chat_session_id']='default'` → pending rơi vào key 'default' dù owner DM thật
- **Hậu quả thực**: owner nhắn "bật rơ le 3" → "ok" → `run_pending_action(session thật)` KHÔNG thấy pending → im lặng (vi phạm cam kết DM 100%)
- **Fix**: `process_message` (responder entry point) inject `chat_session_id` vào payload nếu thiếu — test cập nhật đúng hợp đồng
- **Kết quả**: 18/18 PASS (test_device_control_dm + fail_honest + web_server)

## 3. Deploy sync Pi5 (SSH mesh — LAN PC↔Pi5 2 chiều CHẾT)

- SCP `client_daemon.py` → sha256 **MATCH** `fec95a806578` → restart `quan_ai_edge` → active
- Restart responder PID 22648 (nạp code inject fix) — heartbeat 1-2s LIVE
- SCP `bt_nap_server.py` (mới: DiscoverableTimeout=0) → restart `tony_bt_nap` → active, journal "discoverable(timeout=0)+pairable, alias=TONY-PI5"

## 4. E2E FINAL MATRIX (bằng chứng thật 20:05–20:12)

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Core 8765+8766 | HEALTHY (DEGRADED duy nhất: ollama đã gỡ) | `/api/health` VERIFIED_LIVE |
| Kiosk Pi5 8768 | core_connected=True, IDLE, mesh core 100.92.219.98:8766 | curl SSH |
| Services Pi5 5/5 | edge/BT-NAP/wifi-watchdog/selector/bluetooth = active | systemctl |
| Selector | MESH 52ms (LAN null — chết 2 chiều; BT-PAN null — chưa pair) | `.tony_channel_state.json` ts mới |
| DM responder | heartbeat 1s; **10/10 tin owner ✓answered** (kể cả 'Chào em' 19:55) | read DM 60 tin |
| Catchup thực chứng | restart 20:06 → state 395→406 (+11 tin cũ trong cửa sổ 12h được trả lời) | answered_ids |
| Self-filter | tin TEST do bot tự gửi bị bỏ qua ĐÚNG thiết kế (chống self-loop) | id 5oocqtc... ✗CHƯA là tin BOT |
| Camera E2E | on→snapshot **58.550B JPEG** (vision: nội thất bếp, IMX708 thật)→off | capture_id cap_1793970567532 |
| Stream tab | on→chờ 8s warm-up→**200 image/jpeg 58.553B /1.9s**→off | HTTP 200 |
| Camera OFF | 403/JSON fail-honest ngay khi chưa warm-up — không treo | stream 503 lần 1 (warm-up thiếu) |

## 5. Root cause phụ stream 503 lần đầu

`camera_on` trả success NGAY nhưng rpicam cần **~6-8s cold start** — snapshot/stream gọi sau 3-4s → `CAMERA_UNAVAILABLE` (fail-honest đúng, không ảnh giả). **Quy trình owner: BẬT CAMERA → đợi ~8s → mở tab/mở snapshot.**

## 6. Còn lại — chờ owner

1. **Pair TONY-PI5** (1 bấm duy nhất): Windows Settings → Bluetooth & devices → Add device → chọn **TONY-PI5** (đang discoverable VĨNH VIỄN, timeout=0) → nhắn "paired xong" → em join PAN phía PC + verify selector nhận kênh BT thứ 3
2. Gửi 1 tin DM bất kỳ từ máy anh để test phản hồi thời gian thực (tin test bằng bot bị self-filter đúng thiết kế — không thể tự gửi giả owner vì chống giả mạo)

## 7. Commit state

- master = `6435155` (PR #7 merged); working tree còn: runtime state (chroma/conversation/responder — KHÔNG commit) + `pi5_deploy/bt_nap_server.py` (fix DiscoverableTimeout — chờ lệnh commit kế)
