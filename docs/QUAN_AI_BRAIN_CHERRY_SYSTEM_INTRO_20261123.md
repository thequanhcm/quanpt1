# BÁO CÁO GIỚI THIỆU HỆ THỐNG QUAN AI BRAIN & CHERRY
**Phiên bản:** 1.0 · **Ngày:** 23/11/2026 · **Owner:** Phạm Thế Quân (quanpt1@viettel.com.vn)

---

## 1. TỔNG QUAN

**Quan AI Brain** là hệ thống AI trợ lý số (Digital Executive Assistant) tích hợp đa năng, chạy trên nền tảng Windows 10 với khả năng mở rộng sang Raspberry Pi 5 (màn hình cảm ứng 7"). Hệ thống được thiết kế theo kiến trúc **Shared Cognitive Core** — một bộ não AI duy nhất phục vụ nhiều agent (TONY, Cherry) với khả năng:

- **Persistent Memory**: Ghi nhớ dài hạn, học hỏi liên tục
- **Governance & Audit**: Phê duyệt có kiểm soát, audit mọi hành động
- **Tool Use**: Truy cập email, lịch họp, mạng nội bộ, thiết bị IoT
- **24/7 Operation**: Tự động backup, monitor, đồng bộ Pi5

**Cherry** là agent chuyên biệt của hệ thống, tập trung vào:
- Trợ lý email & văn phòng (Vmail, Voffice)
- Điều khiển qua NetChat (DM owner)
- Giao diện hình thể trên Pi5 (avatar động, voice, motion)

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Core Modules (63,033 lines code)

| Module | Lines | Chức năng chính |
|---|---|---|
| **Cognitive Core** | 17,327 | Tư duy, lập luận, phản xạ, tự học, self-reflection |
| **Memory** | 16,696 | 3 tầng: Working (short-term), Episodic (sự kiện), Semantic (kiến thức) + semantic recall |
| **Governance** | 3,861 | Phê duyệt có kiểm soát (R4), audit trail, consultation inbox, injection shield |
| **Web Server** | 7,910 | Dashboard điều hành (port 8766), API cho Pi5, static files |
| **Tools** | 25,294 | 170+ script: email, VoIP, Pi5 sync, monitoring, backup, automation |
| **Pi5 Edge** | 7,945 | Client daemon, avatar engine, kiosk, audio routing, motion control |

### 2.2. Tích hợp chuyên biệt

| Hệ thống | Lines | Mô tả |
|---|---|---|
| **Email/VoIP** | 749 | Zimbra SOAP (Vmail Viettel), VoIP qua mail vofficeadmin, 10 nhóm phân loại, deadline detection |
| **NetChat** | 4,903 | Bot DM owner, approval cards, command center (30+ lệnh), auto-responder, dedup 60' |
| **Pi5 Sync** | 3,765 | Đồng bộ 5 file edge (kiosk.html, avatar_engine.js, kiosk.js, kiosk.css, avatar_protocol.js), md5 verify, auto-restart service |
| **Monitoring** | 2,791 | Watchdog (PC health), Pi5 monitor (5'), alert engine, RCA (root cause analysis) |
| **Backup/Automation** | 295 | Backup DB 2AM (sqlite API, integrity check), morning report 8AM |

---

## 3. TÍNH NĂNG CHÍNH

### 3.1. Cognitive Core — Bộ não AI

**Tư duy & Lập luận:**
- **Critical Thinking**: Phân tích vấn đề, đánh giá bằng chứng, phát hiện bias
- **Logical Reasoning**: Suy luận logic, causal reasoning, gap detection
- **Self-Reflection**: Tự đánh giá, cải tiến liên tục, lesson learning
- **Autonomous Mind**: Tự khởi tạo session học, tự đặt câu hỏi, tự tìm kiến thức

**Học hỏi & Thích nghi:**
- **Continuous Learning**: Học từ conversation, document, experience
- **Knowledge RAG**: Truy xuất kiến thức từ vector DB, semantic search
- **Skill Registry**: Quản lý skill, tự động load skill phù hợp
- **Vietnamese Conversation**: Giao tiếp tiếng Việt tự nhiên, ngữ cảnh văn hóa

### 3.2. Memory — Trí nhớ dài hạn

**3 Tầng Memory:**
1. **Working Memory**: Context hiện tại, state tạm thời
2. **Episodic Memory**: Ghi lại sự kiện, conversation, decision (timestamped)
3. **Semantic Memory**: Kiến thức tổng quát, facts, skills, patterns

**Cơ chế truy xuất:**
- **Semantic Recall**: Tìm kiếm ngữ nghĩa (embedding), top-3 relevant
- **Temporal Memory**: Theo dõi timeline, sequence sự kiện
- **Workflow Memory**: Ghi nhớ quy trình, SOP, best practices
- **Experience Semantics**: Học từ thành công/thất bại, pattern matching

**Governance:**
- **Audit Trail**: Mọi truy xuất memory đều được log
- **Consent & Privacy**: Owner kiểm soát quyền truy cập
- **CPSL Hidden Set**: Dữ liệu nhạy cảm (chưa triển khai)

### 3.3. Governance — Kiểm soát & Phê duyệt

**Approval Workflow:**
- **R4 Approval Gate**: Phê duyệt có kiểm soát cho action nhạy cảm
- **Consultation Inbox**: Ticket chờ duyệt (FIFO), approval cards qua NetChat
- **Decision Audit**: Mọi quyết định đều được ghi lại, có thể truy xuất
- **Injection Shield**: Bảo vệ khỏi prompt injection, malicious input

**Safety Guardrails:**
- **Secret Protection**: Không đọc .env, credentials, production DB
- **R5 Hard-block**: Không có override secret, không bypass approval
- **Fail-Honest**: Báo lỗi thật, không fake kết quả
- **Read-Only Default**: Mặc định chỉ đọc, ghi cần phê duyệt riêng

### 3.4. Email & VoIP Intelligence

**Vmail Viettel (Zimbra SOAP):**
- **Connector**: `mail_reader.py` (268 lines) — SOAP authentication, folder listing, message search
- **Intake**: `email_intake.py` (306 lines) — store, dedupe, conversation tracking
- **Analysis**: `office/email_connector.py` (342 lines) — 10 nhóm phân loại, priority scoring, deadline detection (explicit/suggested)
- **10 Nhóm Email**:
  1. ACTION_REQUIRED (cần hành động ngay)
  2. NEED_REPLY (chờ phản hồi)
  3. MEETING (lịch họp)
  4. APPROVAL (chờ phê duyệt)
  5. FOLLOW_UP (theo dõi tiến độ)
  6. INFORMATION (thông tin chung)
  7. TASK (nhiệm vụ)
  8. DEADLINE (sắp đến hạn)
  9. ARCHIVED (lưu trữ)
  10. SPAM/UNCATEGORIZED

**VoIP Viettel (Gián tiếp qua mail):**
- **Reader**: `voffice_reader.py` (134 lines) — parse mail vofficeadmin@viettel.com.vn
- **Fields**: Thời gian, địa điểm, chủ trì, trang phục, thành phần
- **Lệnh DM**: `lịch họp`, `lịch họp voip`, `lịch họp hôm nay`
- **Kết quả thật**: 14 lịch họp active (Đào tạo Kỹ sư AI 24/11, Họp KV1 23/11 15h...)

**R2 Constraint:** Chỉ ĐỌC — không gửi, không đánh dấu đã đọc, không xóa. Gửi cần phê duyệt riêng từng lần.

### 3.5. NetChat Integration — Điều khiển qua DM

**Command Center (4,903 lines):**
- **30+ Lệnh DM**:
  - `email hôm nay` / `kiểm tra email` → tóm tắt hộp thư (10 nhóm + priority)
  - `lịch họp` / `lịch họp voip` → lịch họp VoIP (14 cuộc active)
  - `status` / `report` / `tasks` / `knowledge` → trạng thái hệ thống
  - `approve` / `duyệt` → phê duyệt ticket (FIFO)
  - `tony_on` / `tony_off` / `tony_status` → điều khiển Pi5
  - `chụp ảnh` / `phân tích ảnh` → camera + OCR
  - `ghi âm` → mic PC → STT → tóm tắt
  - `việc cần làm` / `todo` → to-do list
  - `dừng khẩn thiết bị` → emergency stop IoT
  - `mở youtube` / `phát nhạc` → media control
  - `hdmi show` / `hdmi hide` → xuất hình ra TV
  - `help` → danh sách lệnh

**Approval Cards:**
- **2-step Gate**: Preview + xác nhận `--confirmed <token>`
- **Consultation Inbox**: Ticket PENDING → APPROVE / REJECT
- **Info Gap Pattern**: Bot hỏi bổ sung thông tin trước khi duyệt

**Auto-Responder:**
- **Dedup 60'**: Không trả lời trùng trong 60 phút
- **Lock File**: Single-instance, tránh race condition
- **Fail-Honest**: Lỗi → báo lỗi, không spam

### 3.6. Pi5 Edge — Giao diện hình thể

**Avatar Engine:**
- **kiosk.html**: Giao diện chính (7,945 lines tổng edge)
- **avatar_engine.js**: Render face, eyes, mouth, expression
- **kiosk.js**: Logic điều khiển, state machine
- **kiosk.css**: Styling, animation
- **avatar_protocol.js**: Giao tiếp với server

**Motion & Voice:**
- **Body Motion**: Head rotation, gesture, posture
- **Audio Routing**: PipeWire/WirePlumber, USB audio I/O
- **Wake Word**: "Hi TONY" / "Cherry ơi" (local wake engine)
- **TTS**: vi-VN-HoaiMyNeural (Hoài My)

**Sync Guard:**
- **5 File Whitelist**: kiosk.html, avatar_engine.js, kiosk.js, kiosk.css, avatar_protocol.js
- **MD5 Verify**: PC vs Pi5, lệch → scp → verify → restart service
- **15 phút/lần**: Task Scheduler `QUAN_AI_BRAIN_PI5_FILE_SYNC_15MIN`
- **Monitor 5 phút**: `QUAN_AI_BRAIN_PI5_MONITOR_5MIN`

### 3.7. Monitoring & Automation

**Watchdog:**
- **PC Health**: CPU, RAM, disk, network, services
- **Alert Engine**: Threshold breach → DM owner
- **RCA (Root Cause Analysis)**: Tự động phân tích nguyên nhân
- **Self-Care**: Auto-restart, resource cleanup

**Backup:**
- **2AM Hằng ngày**: `backup_database.py` (sqlite backup API, integrity check)
- **Giữ 30 bản**: Tự xóa backup cũ
- **Verify NGAY**: Backup hỏng → xóa + báo FAIL (fail-honest)

**Morning Report:**
- **8AM Hằng ngày**: `morning_report.py` → NetChat DM owner
- **Nội dung**: Email mới, lịch họp, task pending, alert, KPI

### 3.8. Dashboard & Web Interface

**Server (port 8765/8766):**
- **Dashboard 8766**: Phong điều hành (PC health, Pi5 status, alerts, KPI)
- **API 8765**: REST API cho Pi5, file upload, control commands
- **Static Files**: Serve avatar assets, demo harness (v1-v8)

**Demo Harness:**
- **8 Phiên bản**: demo_harness.html → v8.html
- **Motion Analysis**: Dashboard phân tích motion, viseme, mouth sync
- **Preview MP4**: Render preview, benchmark, A/B test

---

## 4. HOẠT ĐỘNG 24/7

### 4.1. Task Scheduler (4 task READY)

| Task | Chạy | Chu kỳ | Mục đích |
|---|---|---|---|
| `QUAN_AI_BRAIN_BACKUP_2AM` | `tools/backup_database.py` | 2AM mỗi ngày | Backup brain.db, verify integrity |
| `QUAN_AI_BRAIN_MORNING_REPORT_8AM` | `tools/morning_report.py` | 8AM mỗi ngày | Báo cáo NetChat |
| `QUAN_AI_BRAIN_PI5_FILE_SYNC_15MIN` | `tools/pi5_edge_file_sync_guard.py` | 15 phút | Đồng bộ Pi5, md5 verify |
| `QUAN_AI_BRAIN_PI5_MONITOR_5MIN` | `tools/pi5_monitor.py` | 5 phút | Monitor Pi5 health |

### 4.2. Manual Start (Owner 19/11)

- **`KHOI_DONG_CHERRY.bat`**: Khởi động 1 cửa sổ (servers + NetChat + learning)
- **`TAT_CHERRY.bat`**: Dừng toàn bộ Cherry (servers, responder, learning, watchdog)
- **Task Disabled**: `KHOI_DONG_LOGON`, `LIVENESS_30MIN`, `CHERRY_AUTONOMOUS` (owner chọn manual-start)

---

## 5. MẠNG & BẢO MẬT

### 5.1. Kết nối

- **Vmail Viettel**: Zimbra SOAP (mail_reader.py) — READONLY
- **Voffice Viettel**: 10.60.7.120 (LAN-only) — chờ M-Suite tunnel
- **M-Suite (Mobility Suite Agent)**: SDP per-app ZTNA, owner login thủ công
- **NetChat**: bot-netchat.viettel.vn (bot token)
- **GLM Cloud**: zai-org/GLM-5.3-Flash (NetMind cloud)
- **Ollama Local**: qwen2.5:7b (offline fallback, GPU T1000 4GB)

### 5.2. Bảo mật

- **Secrets**: `user, pass, token/secrets.local.json` — không đọc, không log
- **R2 Draft-Only**: Email/VoIP chỉ đọc, ghi cần phê duyệt
- **R4 Approval**: Action nhạy cảm cần owner duyệt
- **R5 Hard-block**: Không override, không bypass
- **Audit Trail**: Mọi hành động đều được log
- **Injection Shield**: Phát hiện prompt injection

---

## 6. HIỆN TRẠNG & LIMITATIONS

### 6.1. Đã hoàn thành (Live)

- ✅ Cognitive Core (17k lines) — tư duy, học hỏi, self-reflection
- ✅ Memory 3 tầng (16k lines) — persistent, semantic recall
- ✅ Governance (3.8k lines) — approval, audit, safety
- ✅ Email SOAP (749 lines) — 10 nhóm, deadline detection, live smoke 10 mail
- ✅ VoIP (134 lines) — 14 lịch họp active, live smoke
- ✅ NetChat (4.9k lines) — 30+ lệnh, approval cards, dedup
- ✅ Pi5 Sync (3.7k lines) — 5 file, md5 verify, 15'
- ✅ Pi5 Monitor (5') — health check, alert
- ✅ Backup 2AM + Report 8AM — sqlite API, integrity check
- ✅ Dashboard 8766 — PC health, Pi5 status, alerts

### 6.2. Đang phát triển (Pending Approval)

- 🔄 **Sprint 1 VMAIL (TASK-VMAIL-S1)**: VmailConnector class (interface đầy đủ, structured result)
- 🔄 **Sprint 1b OFFICE**: Thread Analyzer (ghép luồng email, tổng hợp conversation)
- 🔄 **Sprint 2 VMAIL**: Email Intelligence + Thread Analyzer
- 🔄 **Sprint 3 VMAIL**: Shared Memory Integration
- 🔄 **Sprint 4 VMAIL**: Context-Aware Reply Draft
- 🔄 **M-Suite Tunnel**: Chờ owner login → scrape VoIP trực tiếp

### 6.3. Limitations (Fail-Honest)

- ⚠️ **Voffice trực tiếp**: 10.60.7.120 LAN-only — chờ M-Suite tunnel
- ⚠️ **Email gửi**: R2 Draft-Only — cần phê duyệt riêng từng lần
- ⚠️ **Pi5 Offline**: 192.168.1.21 — WiFi yếu (ping loss, SSH timeout)
- ⚠️ **GPU T1000 4GB**: Local model qwen2.5:7b partial offload — GLM-5.3-Flash ưu tiên
- ⚠️ **Autonomous Mode**: Disabled (owner chọn manual-start)

---

## 7. ĐƯỜNG DẪN PHÁT TRIỂN (Roadmap)

### Sprint 1-4: Vmail Intelligence (Đã có nền)
1. **Sprint 1**: VmailConnector class (interface, SOAP, structured result) — *PENDING_APPROVAL*
2. **Sprint 2**: Email Intelligence + Thread Analyzer (conversation stitching)
3. **Sprint 3**: Shared Memory Integration (memory adapter, semantic recall)
4. **Sprint 4**: Context-Aware Reply Draft (3 phương án, owner chọn)

### Sprint 5-7: Workflow & Dashboard
5. **Sprint 5**: Workflow Engine (action executor, staging approval)
6. **Sprint 6**: Dashboard nâng cao (KPI, analytics, visualization)
7. **Sprint 7**: 24/7 Operations (resource tuning, auto-healing, KPI ≥95%)

### Sprint 8+: Advanced Features
8. **Sprint 8**: IoT Integration (UDC-1, device control, automation)
9. **Sprint 9**: Voice Intelligence (voice print, emotion detection)
10. **Sprint 10+**: Continuous improvement, new capabilities

---

## 8. THỐNG KÊ HỆ THỐNG

| Hạng mục | Số lượng |
|---|---|
| **Tổng code** | ~100,000+ lines |
| **Python modules** | 170+ scripts |
| **Task Scheduler** | 4 task READY, 3 task DISABLED |
| **NetChat commands** | 30+ lệnh |
| **Email groups** | 10 nhóm phân loại |
| **Pi5 sync files** | 5 file whitelist |
| **Backup retention** | 30 bản |
| **Memory recall** | Top-3 semantic |
| **Test coverage** | 24/24 (office), 24/24 (command_center) |
| **Live smoke** | 10 email, 14 lịch họp VoIP |

---

## 9. TÀI LIỆU THAM KHẢO

- `docs/PROJECT_STATUS.md` — Trạng thái dự án
- `docs/CHERRY_OFFICE_INTELLIGENCE/ARCHITECTURE_AUDIT.md` — Audit Office
- `docs/CHERRY_OFFICE_INTELLIGENCE/VMAIL_EXISTING_SYSTEM_AUDIT.md` — Audit Vmail
- `docs/AUDIT_SYNC_QUARANTINE_20261123.md` — Audit toàn hệ thống 23/11
- `reports/HANDOFF_LATEST.md` — Handoff báo cáo
- `reports/TEST_RUN_OFFICE_S1.txt` — Test evidence
- `bao cao xay dung he thong/BAO_CAO_OFFICE_S1_20261123.md` — Báo cáo Sprint 1a

---

## 10. LIÊN HỆ & HỖ TRỢ

**Owner:** Phạm Thế Quân (quanpt1@viettel.com.vn)  
**Workspace:** E:\BRAIN  
**Profile:** netMind Desktop `tony`  
**NetChat:** bot_tony (DM owner)  
**Dashboard:** http://127.0.0.1:8766/ (khi server chạy)

**Hỗ trợ:**
- Lệnh DM: `help` → danh sách lệnh
- Lệnh DM: `status` → trạng thái hệ thống
- Lệnh DM: `email hôm nay` → hộp thư
- Lệnh DM: `lịch họp` → lịch VoIP
- Báo cáo: `docs/AUDIT_SYNC_QUARANTINE_20261123.md`

---

**Lưu ý:** Báo cáo này phản ánh hiện trạng tại 23/11/2026. Mọi thay đổi sẽ được cập nhật trong `docs/PROJECT_STATUS.md` và `reports/HANDOFF_LATEST.md`.

**Fail-Honest Contract:** Hệ thống không bao giờ tuyên bố hoàn thành nếu chưa có bằng chứng kiểm chứng (test evidence, live smoke, owner approval).