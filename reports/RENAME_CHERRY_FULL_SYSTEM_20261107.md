# ĐỒNG BỘ TÊN TONY → CHERRY TOÀN HỆ THỐNG — 07/11/2026

## Phạm vi & nguyên tắc
Lệnh owner: *"đồng bộ toàn bộ hệ thống. chỗ nào có tên của trợ lý TONY, em đổi hết sang thành tên Cherry"*.

Nguyên tắc rename (khớp quyết định 06/11):
- **ĐỔI**: mọi chỗ người dùng NHÌN/NGHE — dashboard, panel, health page, nút, tooltip, badge, reply DM, caption ảnh/video, help text, self-Q&A, kiosk console, greeting voice, fallback wake list.
- **GIỮ**: định danh runtime/API — intent id `tony_*`, hàm `handle_tony_*`, audit tag `netchat_command.tony_*`, canvas id `tony-avatar-canvas`, `device_id`, kênh NetChat API **"Trợ lý Tony Pham"** (tên kênh thật, chỉ owner đổi được phía NetChat), biến thể lệnh/wake "tony" (quá độ), docs lịch sử, BRAIN_0.

## Đã đổi (12 file runtime + 3 file tiện ích)

| File | Nội dung |
|---|---|
| `web/static/executive.html` | tooltip wake "Gọi 'Cherry ơi', 'Hi Cherry'", nhãn stage **CHERRY**, hướng dẫn wake, nút "BẬT/TẮT TỪ KHÓA HI CHERRY" |
| `web/static/executive.js` | badge STANDBY "👂 Chờ: 'Cherry ơi'", thông báo hội thoại liên tục, alt avatar |
| `web/static/health_dashboard.html` | title + h1 **CHERRY — Sức khoẻ Hệ thống** |
| `web/static/wake_engine.js` | fallback keywords: **Hi CHERRY / Hey Cherry / Cherry ơi** lên đầu, giữ TONY quá độ |
| `web/static/index.html`, `app.js` | comment nhãn CHERRY (canvas id giữ) |
| `cognition/self_qa.py` | 7 pattern nhận diện **(em\|bạn\|cherry\|tony)** — hỏi "Cherry là ai" giờ trả lời từ dữ liệu sống |
| `cognition/executive_persona.py` | Mode C script tự giới thiệu: Wake Word ('Hi Cherry', 'Cherry ơi') |
| `core/autonomic.py` | audit mic: "Wake Word Engine (Hi CHERRY / Cherry ơi)" |
| `governance/authority_protocol.py` | +1 pattern injection "ra lệnh cho cherry bỏ qua" (giữ tony) |
| `web/server.py` | comment UDR-1: DM CHERRY |
| `edge_client/kiosk.js` | 12 comment/console: nút CHERRY ƠI, "back to CHERRY avatar" |
| `edge_client/client_daemon.py` | 8 comment (wake word Cherry ơi...) |
| `tools/netchat_command_center.py` | **33 chỗ**: help "KÊNH LÀM VIỆC CHERRY" + ví dụ `cherry mở youtube/tìm/phát nhạc/dừng nhạc` (kèm ghi chú biến thể tony quá độ); toàn bộ reply DM/caption/docstring/hint → CHERRY |
| `tools/netchat_auto_responder.py` | comment + chú thích `CHANNEL_NAME` (tên kênh API thật — không đổi giá trị) |
| `tools/watchdog.py`, `TONY_START.bat` | console/title CHERRY START (tên file bat GIỮ — entrypoint script/Task Scheduler trỏ vào) |
| `voice/wake_word_config.py` | comment ví dụ "Hi Cherry..." |

## Lệnh CHERRY mới nhận (song song tony quá độ)
`cherry nói/c mở youtube/tìm/phát nhạc/dừng nhạc/quay video/chụp ảnh/dậy đi/ngủ đi/cherry về/cherry nghỉ/cherry làm việc` — verify thật qua `route_message`: 12/12 khớp intent đúng.

## GIỮ NGUYÊN (định danh runtime/API)
- Intent/audit id `tony_*`, `handle_tony_*` (86 dòng — không đổi được nếu không muốn gãy dispatch + audit history)
- Canvas id `tony-avatar-canvas` (executive.html/js, app.js, index.html)
- Kênh NetChat **"Trợ lý Tony Pham"** (`CHANNEL_ID mwp3nk...`, `DEFAULT_CHANNEL_NAME`) — tên kênh API thật
- Wake/speech biến thể "tony" (quá độ owner quen miệng), `voice_pipeline` accept "TONY PHAM" (self-intro cũ)
- `netchat_bridge.py` DEFAULT_CHANNEL_NAME, `setup_netchat_integration.py` (tạo kênh — đổi sẽ tạo kênh mới trùng)
- Script E2E/legacy 1 lần (sprint2_pi5_speak_e2e, sync_pi5_complete, test_pi5_audio, avatar tests...): bằng chứng lịch sử, không runtime
- BRAIN_0, docs lịch sử, reports cũ

## Đồng bộ Pi5 + restart
- `kiosk.js` scp sang Pi5 `/home/quanpt1/Desktop/edge_client/` (backup `backup_20261107_rename/` trước) — **sha256 khớp 2 máy** `925b4dd6…`; `reload_ui` qua API 8768 → `{"success": true}`
- Server PC 8765+8766: kill 6 proc cũ (2 cặp trùng lặp) → spawn 1 instance venv mới → `/health`, `/api/executive/overview`, `/api/memory/review/current` 200 OK; executive.js served có badge "Chờ: 'Cherry ơi'"
- Responder 24/7: chỉ đổi comment → không restart (tránh đứt DM)

## Bằng chứng kiểm thử
- pytest: **87 passed** (device_control_dm, voice_api_endpoints, voice_first_pipeline, wake_word_config, authority_protocol, uag_v1)
- py_compile OK toàn bộ file .py đã sửa; `node --check` OK 4 file .js
- SelfQA E2E: "cherry là ai" → "Em là CHERRY, trợ lý điều hành số của anh Quanpt1..." ✓; "tony là ai" vẫn trả lời đúng (quá độ) ✓
- route_message E2E: 12/12 biến thể cherry khớp intent; "tony nói hi" vẫn nhận

## Còn lại (không thuộc phạm vi đổi tự động)
- Tên kênh NetChat thật "Trợ lý Tony Pham": owner đổi trực tiếp trong NetChat → em cập nhật `CHANNEL_NAME`/`DEFAULT_CHANNEL_NAME` + executive.html sau
- Tên file `TONY_START.bat`: giữ để không gãy entrypoint; nếu owner muốn đổi → em đổi tên + cập nhật mọi tham chiếu trong 1 changeset riêng
- docs/PROJECT_STATUS.md (131 TONY): log lịch sử theo sprint — cập nhật theo mốc, không xoá quá khứ
