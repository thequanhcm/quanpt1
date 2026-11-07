# WAKE WORD CHERRY + TAB TRẠNG THÁI KÍCH HOẠT — 07/11/2026

## Yêu cầu owner
1. *"các từ wakeup. các từ gọi để giao tiếp với trợ lý cũng đổi"* → từ gọi CHERRY toàn hệ thống.
2. *"cấu hình lại các tab này để thể hiện chức năng được kích hoạt thì tab sáng, và ngược lại"*.

## Phần 1 — Từ wakeup / từ gọi → CHERRY

| Vị trí | Trước | Sau |
|---|---|---|
| `edge_client/config.py` L34 | `wake_word: "TONY ơi"` | `wake_word: "Cherry ơi"` |
| `edge_client/setup_pi5.py` L305 | default `"TONY ơi"` | default `"Cherry ơi"` |
| `edge_client/wake_engine.js` (kiosk thật) | keywords đầu: Hi TONY / Hey Tony / Tony ơi | **Cherry ơi / Hi Cherry / Hey Cherry** |
| `web/static/wake_engine.js` (fallback) | TONY trước | CHERRY trước, TONY sau (quá độ) |
| `wake_word_config.py` (server API) | đã CHERRY (06/11) | giữ — `/api/voice/wake-config` trả **Cherry ơi, Hi Cherry…** (verify live) |
| `wake_word_service.py` (Pi5 Vosk) | cherry + tony quá độ | giữ nguyên — Vosk nhận cả 2, cherry là chính |
| Lệnh DM `tony nói/dậy đi tony…` | — | giữ song song với `cherry …` (quá độ owner quen miệng) |
| systemd descriptions Pi5 | "Edge Kiosk (TONY 24/7)", "nghe 'TONY ơi' 24/7" | **"CHERRY 24/7"**, **nghe "CHERRY ơi" 24/7** (tên unit + ExecStart giữ nguyên) |

Sync Pi5: backup `backup_20261107_wake_rename/` → scp `wake_engine.js` + `config.py` + `setup_pi5.py` → **sha256 khớp 2 máy** (3/3) → `reload_ui` OK. Pi5 `config.json` đã `"CHERRY ơi"` từ 06/11.

## Phần 2 — Tab sáng/mờ theo trạng thái chức năng

**Cơ chế**: mỗi tab thêm chấm trạng thái (`tab-state-dot`); JS helper toàn cục `window.updateTabActivation(tabId, active, label)`; CSS `.tab-on` (chấm xanh phát sáng) / `.tab-off` (mờ 45%). Trạng thái lấy từ dữ liệu sống đã có của từng loader (không tạo API mới):

| Tab | Sáng khi | Nguồn |
|---|---|---|
| 👤 Nhân Sự Số | có năng lực VERIFIED_ACTIVE | `/api/executive/capabilities` |
| 📬 Tham Vấn & Duyệt | có phiếu PENDING_REVIEW | `/api/executive/consultations` |
| 🔬 Báo Cáo Tự Học | có báo cáo | `/api/executive/learning/reports` |
| ⚙️ Điều Hành & An Toàn | API nhiệm vụ OK (số nhiệm vụ) | `/api/executive/tasks` |
| 💬 Hội Thoại Trực Tiếp | wake word BẬT | `/api/executive/edge/audio/status` |
| 📡 Kênh NetChat | LIVE | `/api/executive/netchat/messages` |
| 📡 Đồng Bộ Pi 5 | Pi5 online | `/api/executive/edge/telemetry` |
| ✨ Hình Thể Pi 5 | Pi5 online | cùng telemetry |
| 🧰 Workbench | overview OK | `/api/workbench/overview` |
| 🧠 Trí Nhớ Sâu V9 | stats OK | `/api/memory/deep/stats` |

Cache bump: `executive.css?v=cherry_07nov_r2`, `executive.js?v=cherry_07nov_r2`.

## Bằng chứng
- **E2E Pi5**: screenshot `logs/kiosk_cherry_wake_check.png` — nút **"CHERRY ƠI..."**, header CHERRY ASSISTANT, đồng hồ 07:57:55 (vision xác nhận).
- **E2E dashboard**: screenshot `logs/dashboard_tabs_check2.png` (vision xác nhận): 10 tab đủ chấm trạng thái — **6 sáng** (Nhân Sự Số, Báo Cáo Tự Học, Điều Hành & An Toàn, Kênh NetChat LIVE, Đồng Bộ Pi 5 LIVE, Hình Thể Pi 5 STANDBY*), **4 mờ** (Tham Vấn & Duyệt 0 phiếu, Hội Thoại Trực Tiếp WAKE TẮT, Workbench chưa load, Trí Nhớ Sâu chưa load). Không vỡ layout.
  *STANDBY = kiosk Pi5 sống nhưng đang ngủ — tính là "kết nối OK, chưa active"; tab mờ sẽ khi OFFLINE.
- `/api/voice/wake-config` live trả keywords: Cherry ơi, Hi Cherry, Chào trợ lý… (không còn TONY).
- **96 tests passed** (device_control_dm, voice×3, authority, UAG, web_netchat_tab); `node --check` + `py_compile` OK toàn bộ file sửa.
- Services Pi5: quan_ai_edge + quan_ai_kiosk_guard + quan_ai_wake **active**.

## Giữ nguyên có chủ đích
- Tên unit systemd (`quan_ai_*`, `tony_bt_nap`) — đổi tên unit gãy scripts; chỉ đổi Description.
- Biến thể wake/lệnh "tony" (quá độ), intent id `tony_*`, kênh NetChat "Trợ lý Tony Pham".
