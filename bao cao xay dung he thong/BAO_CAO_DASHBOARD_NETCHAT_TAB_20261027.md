# BÁO CÁO: Tab "Quản Trị Kênh NetChat" trên Dashboard Điều Hành (8766) + Avatar đồng bộ

**Mã báo cáo:** RPT-QAB-DASH-NETCHAT-20261027
**Thời điểm:** 27/10/2026 ~00:10 ICT
**Yêu cầu chủ sở hữu:** Bổ sung tab quản trị kênh NetChat vào dashboard `http://127.0.0.1:8766/`; đồng bộ ảnh giao diện bot/kênh giống hệt avatar anh đã xây để nhận diện.

## 1. Đã bàn giao

### 1.1. Tab "📡 Quản Trị Kênh NetChat" (dashboard 8766)
- **Chat 2 chiều trực tiếp:** xem 30 tin gần nhất của kênh "Trợ lý Tony Pham", gửi tin nhắn AS BOT (2 bước CONFIRM tự động), auto-refresh 10s (bật/tắt).
- **Lệnh nhanh:** dropdown (trạng thái / phê duyệt / báo cáo / nhiệm vụ / tri thức / giúp) + nút "▶ Chạy lệnh" — chạy Command Center NGAY, hiện kết quả kèm intent.
- **Tin nhắn được phân loại:** bot (bubble trái + avatar Tony tròn 30px) / anh quanpt1 (bubble phải cyan); tin lệnh có tag vàng "LỆNH".
- **Badge trạng thái kênh:** LIVE / LỖI / OFF trên tab.
- **Panel thông tin:** bot username + ID, tên kênh, quy ước lệnh (bắt đầu từ khóa = thực thi; câu hỏi = hội thoại AI; phê duyệt luôn hiện ticket_id + audit).

### 1.2. Avatar Digital Human đồng bộ (đúng yêu cầu nhận diện)
- **Dùng CHUNG engine** `avatar_engine.js` (Model A/V2) với hình thể Pi 5 và khung Persona của dashboard — cùng bộ ảnh `avatar_v2_portrait.jpg`, mắt/miệng/biểu cảm cùng nguồn.
- Avatar canvas 240px ở header tab + ảnh đại diện trong từng bubble của bot.
- **Avatar phản ứng theo công việc:** THINKING khi chạy lệnh → SUCCESS khi xong → ERROR khi lỗi → SPEAKING 2.5s khi gửi tin; vòng pulse quanh avatar khi đang "nói".

### 1.3. Backend (4 endpoint mới, không đụng secret)
`src/quan_ai_brain/integration/netchat_bridge.py`:
- `GET /api/executive/netchat/status` — whoami bot (không token)
- `GET /api/executive/netchat/messages?count=N` — tin nhắn phân sender
- `POST /api/executive/netchat/send` — gửi tin (rate-limit 3s, max 3500 ký tự, audit)
- `POST /api/executive/netchat/command` — chạy lệnh Command Center (an toàn câu hỏi như kênh chat)
- **Bảo mật:** mọi thao tác qua skill script `netchat_bot.py` (token tự resolve từ env var, không bao giờ đọc/ghi/log giá trị); gửi tin + lệnh đều ghi `logs/audit.jsonl` (`dashboard_netchat.*`).

### 1.4. Vận hành
- `start_dual_servers.py` MỚI: 1 process chạy cả 8765 (UI) + 8766 (Executive).
- **Dọn 4 process zombie Python311** chạy code cũ (gồm responder cũ = nguồn tin placeholder "Đang suy nghĩ..." bị cấm) — nguyên nhân tin rác 16:59 trong kênh.
- Fix `tools/watchdog.py`: `os.disk_usage` → `shutil.disk_usage` (bug lộ ra khi chạy thật).
- Khởi động lại đủ 4 thành phần bằng code mới (.venv): dual-servers (PID nhóm proc_5cc56d29feb8), responder, learning daemon, watchdog.

## 2. Bối cảnh hòa hợp Sprint 2 V3 (commit f6bcabd)
Trong lúc triển khai, luồng song song đã commit `f6bcabd` (ApprovalOrchestrator + ApprovalCardStore + NetChatApprovalAdapter): lệnh "Duyệt" trong kênh giờ đi qua **Approval Card bền vững** (consume-once, TTL, fingerprint, binding user quanpt1). Anh đã duyệt TASK-V3-SPRINT2 lúc 16:51 UTC qua kênh — reply "consume-once" hoạt động đúng. Code của em không đụng chạm: bridge `run_command` gọi `route_message` nên tự hưởng luôn lớp approval mới. **Không xung đột; full test cùng pass.**

## 3. Kiểm chứng
- **Unit/API tests mới:** 9/9 PASSED (`tests/test_web_netchat_tab.py` — fake bridge, không đụng NetChat thật, không token).
- **Executive regression:** 34/34 PASSED (executive endpoints + persona + roles + web server).
- **Full regression:** **634 passed (+9), 1 failed (test_keep_warm_pulse — Ollama offline, lỗi môi trường đã biết), 2 skipped** (164.43s) — 0 regression.
- **Live smoke (HTTP thật):** `/api/executive/netchat/status` → bot_quanpt1 OK; `/messages?count=2` → tin thật phân sender đúng; executive.html chứa tab + avatar canvas.
- Commit: **`808e585`**.

## 4. Giới hạn trung thực
- Ollama 11434 vẫn OFFLINE → watchdog báo DEGRADED (đúng thật), avatar ảnh hưởng nhẹ nếu sau này dùng ảnh BGE.
- Dashboard tab gửi tin **as bot** — nếu anh muốn gửi "as admin" cần token user thật (hiện không có, không tự ý đòi quyền).
- 4 thành phần đang chạy nền phiên này; lần khởi động máy kế tiếp vẫn dùng `KHOI_DONG_24_7.bat` — đề xuất update .bat sang `start_dual_servers.py` (chờ anh duyệt để có 1 nguồn khởi động duy nhất).

## 5. Bước kế tiếp đề xuất
1. Anh mở `http://127.0.0.1:8766/` → tab "📡 Quản Trị Kênh NetChat" kiểm tra avatar + thử "trạng thái".
2. Duyệt update `KHOI_DONG_24_7.bat` → `start_dual_servers.py`.
3. 2 quyết định đang chờ: Sprint E (BATTERY AI V4 connector) + dedup ~40k tri thức trùng.
