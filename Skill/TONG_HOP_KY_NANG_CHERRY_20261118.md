# TỔNG HỢP KỸ NĂNG CỦA CHERRY (QUAN AI BRAIN)

**Ngày tổng hợp:** 18/11/2026 | **Nguồn:** chạy thật từ hệ thống sống tại `E:\BRAIN`
— `data/skill_registry.json` (6 skills), `CapabilityRegistry` (12 capabilities),
159 API endpoints live trên 8765, `docs/PROJECT_STATUS.md` (68 entry nghiệm thu),
module `src/quan_ai_brain/` (cognition/tools/security/uaiif).

**Nguyên tắc tổng hợp (fail-honest):** mỗi mục ghi rõ nguồn + trạng thái thật.
KHÔNG liệt kê năng lực chưa test như đã hoạt động. Trạng thái lấy từ registry
chạy LIVE (CapabilityRegistry VERIFIED_ACTIVE = đã test E2E; IMPLEMENTED_UNTESTED
= có code chưa test E2E; INERT_STAGING = chờ owner duyệt kích hoạt).

---

## 1. SKILL NGHIỆP VỤ ĐÃ ĐĂNG KÝ (Skill Registry V6/V7 — data/skill_registry.json)

Lifecycle: PROPOSED → IMPLEMENTED_IN_SANDBOX → TESTED → APPROVED → AVAILABLE. Mọi
kết luận truy vết được nguồn; thiếu bằng chứng → NOT_VERIFIED (fail-honest).

| # | Skill | Trạng thái | Năng lực | Trigger |
|---|---|---|---|---|
| 1 | TASK_STATUS_RECONCILIATION | **AVAILABLE** (duyệt 27/10) | Đối chiếu trạng thái công việc email↔data/tasks.db; phát hiện mâu thuẫn; smoke thật 11/11 stage trên 553 task | "kiểm tra tiến độ", "đối chiếu tiến độ" |
| 2 | EMAIL_ANALYSIS | TESTED | Trích xuất người gửi/nội dung/dự án/thời hạn/cam kết/câu hỏi từ email (chưa có connector Vmail — nhận text trực tiếp) | "phân tích email" |
| 3 | CROSS_SOURCE_EVIDENCE_ANALYSIS | TESTED | Đối chiếu chéo nhiều nguồn (email, tasks.db, consultations, todos, reports); đánh giá nguồn theo thẩm quyền/thời điểm | "đối chiếu chéo", "mâu thuẫn" |
| 4 | PROGRESS_RISK_DETECTION | TESTED | Phát hiện quá hạn, nguy cơ chậm, phụ thuộc chưa xong, trách nhiệm không rõ | "rủi ro tiến độ", "quá hạn" |
| 5 | OWNER_ADVISORY_REPORT | TESTED | Báo cáo tư vấn 12 mục §4.2.E; mỗi kết luận truy vết nguồn | "báo cáo tư vấn" |
| 6 | VERIFIED_WORKFLOW_REUSE | TESTED | Tái sử dụng quy trình đã kiểm chứng: tìm workflow → kiểm điều kiện → tái sử dụng có điều chỉnh | "làm như lần trước" |

---

## 2. 12 CAPABILITIES HỆ THỐNG (CapabilityRegistry — ground truth chống ảo giác)

| # | Capability | Trạng thái | Chi tiết |
|---|---|---|---|
| 1 | long_term_memory | **VERIFIED_ACTIVE** | Trí nhớ dài hạn: brain.db (3,625 episodes / 2,594 semantic memory), 5 lớp chuẩn hóa, memory review cycle |
| 2 | local_llm_inference | **VERIFIED_ACTIVE** | NetMind Cloud GLM-5.3-Flash (0.34s) + failover cloud→cloud + Ollama local (đang DISABLED theo owner) |
| 3 | safe_task_planning | **VERIFIED_ACTIVE** | Lập kế hoạch DAG, phân rã tự động, DurableTaskRegistry, đánh giá rủi ro R0-R5 |
| 4 | tool_sandbox | **VERIFIED_ACTIVE** | Hộp cát tool R0-R2, path guard, approval gate |
| 5 | self_learning_v1 | **VERIFIED_ACTIVE** | Động cơ tự học CLO (Continuous Learning Engine), learning session, improvement report |
| 6 | web_ui_voice | **VERIFIED_ACTIVE** | Web chat + giọng nói Hoài My (vi-VN-HoaiMyNeural), streaming TTFT 1.2-1.5s |
| 7 | os_job_containment | INERT_STAGING | Win32 Job Object containment (chờ owner duyệt kích hoạt) |
| 8 | ecosystem_adapters | EXTERNAL_PLANNED | Hệ sinh thái vệ tinh DC-COMMAND, Kernel L3, Battery AI, BOT (preserve, chưa integrate) |
| 9 | universal_software_integration | **VERIFIED_ACTIVE** | Tích hợp đa phần mềm có kiểm soát |
| 10 | edge_embodiment_pi5 | **VERIFIED_ACTIVE** | Pi5: kiosk avatar Model A, wake voice "Cherry ơi", camera, loa, LAN-first |
| 11 | netchat_dm_channel | **VERIFIED_ACTIVE** | DM NetChat 2 chiều 4 tầng, 2-step gate confirm |
| 12 | speech_learning_quarantine | IMPLEMENTED_UNTESTED | Học văn phong từ giọng nói thật (quarantine — chưa test E2E) |

---

## 3. KỸ NĂNG GIAO TIẾP & GIỌNG NÓI (live — 159 endpoints)

### 3.1 Chat hội thoại
- `/api/chat` + `/api/chat/stream`: hội thoại tiếng Việt tự nhiên, xưng em/gọi anh; streaming SSE; self-RAG lite kiểm căn cứ (sprint MEMORY-TRUTH 18/11); memory recall hybrid + semantic recall (ChromaDB ONNX MiniLM, 6,578 chunks); Input Injection Shield 12+ pattern
- `/api/chat/history`: lịch sử hội thoại theo session

### 3.2 Giọng nói (1 giọng thống nhất = Hoài My)
- `/api/voice/interact`: STT→não→TTS, trả text NGAY, synth nền (piper warm 60-115ms)
- `/api/voice/tts-synthesize` + `/tts-voices` + `/tts-config` + `/wake-config` + `/barge-in`: tổng hợp giọng, cấu hình wake-word "Cherry ơi", ngắt giữa câu
- Circuit breaker Edge-TTS 403 → piper fallback tự động; warm-up lúc start

### 3.3 NetChat DM (kênh tin nhắn nội bộ)
- `/api/executive/netchat/{send,messages,status,command}`: DM 2 chiều, bot trả 9-10s, watchdog hồi sinh ≤30', 2-step gate gửi nội dung ra ngoài (preview + confirm)

---

## 4. KỸ NĂNG HÌNH THỂ PI5 (edge embodiment)

- **Kiosk avatar**: `/api/kiosk/{control,status,device,files,media}` — 19 trạng thái biểu cảm, lip-sync, portrait Model A
- **Camera**: snapshot, stream, library, save/delete (`/api/executive/edge/camera/*`, `/api/kiosk/camera/*`) — lệnh "chụp ảnh gửi anh" đã fix P0 + verify live
- **Audio**: phát loa Pi5, điều khiển volume (`/audio/control`, `/audio/status`) — DM→loa ~3s
- **File transfer**: chunked upload/download/sync-all 1 chiều PC→Pi5, md5 verify, guard + Task 15'
- **Telemetry & stability**: heartbeat, RTT, `/pi5-stability`, startup-sequence, release/rollback
- **Wake voice**: "Cherry ơi" + barge-in

---

## 5. KỸ NĂNG TRÍ NHỚ & HỌC (não)

- **Trí nhớ đa lớp**: memories (long-term) + episodes (chat_turn, experience_lesson) + temporal memory + semantic memory (vector search) + workflow memory
- **Semantic search**: `/api/memory/semantic/{search,stats}` — recall@3 = 1.0 (8 câu eval thật, hybrid)
- **Deep memory**: `/api/memory/deep/*` — extract, timeline, Q&A, review units
- **Memory review**: `/api/memory/review/*` — phiên ôn tập có owner confirm/undo
- **Tự học CLO**: `/api/learning/*` — start/stop/pause/resume/status, session quản lý mục tiêu
- **Teach pipeline**: anh dạy trực tiếp ("nhớ rằng…") → lưu USER_PREFERENCE
- **Experience**: `/api/experience/*` — consolidation, lessons, promote bài học
- **Self-QA / Self-model**: `/api/self/*` — Cherry tự trả lời "em biết gì/không biết gì" (fail-honest)
- **Mind/Cogitate**: `/api/mind/*` — suy nghĩ nội tại, thoughts log

---

## 6. KỸ NĂNG CÔNG VIỆC & ĐIỀU HÀNH

- **Tasks**: `/api/executive/tasks/*` — intake, create, execute, transitions, duplicates, cognitive-state; plan DAG `/api/plan`
- **Todos**: `/api/todos/*`
- **Email**: `/api/email/{intake,intake/sync,proposals,task/create}` — intake email → đề xuất → tạo task
- **Consultations**: hỏi owner khi không chắc (consultation inbox)
- **Approvals**: `/api/approvals/*` — approval cards R2+ bắt buộc owner duyệt
- **Supervisor / work-queue / workbench**: điều phối nền
- **Advisory**: báo cáo tư vấn có nguồn (skill OWNER_ADVISORY_REPORT)

---

## 7. KỸ NĂNG TRA CỨU & THÔNG TIN

- **Tra cứu ngoài**: `/api/web/{search,rss,page}` + external_lookup (Gemini + Google News RSS, 2 tầng, fail-closed, nhãn UNTRUSTED) — tin thời sự, thời tiết
- **TTNS nội bộ**: `/api/executive/...` ttns_lookup — nhân sự, lịch họp (CHỈ TRA CỨU, không đặt/sửa, không cache DB)
- **Music**: `/api/music/{play,search,stop,status}`
- **Grounding facts**: bộ sự thật sống (probe thật) — Cherry trả lời đúng về bản thân hệ thống

---

## 8. KỸ NĂNG AN NINH & QUẢN TRỊ (Agentic Security)

- **Input Injection Shield**: 12+ pattern EN+VN (EchoLeak CVE-2025-32711), score 0-100, verdict ALLOW/SANITIZE/BLOCK — live test: injection → BLOCK 0.03s không gọi LLM
- **Untrusted Label**: bọc nhãn `[DỮ LIỆU KHÔNG TIN CẬY]` cho bằng chứng ngoài
- **Lethal Trifecta Guard**: đủ 3 điều kiện (dữ liệu riêng tư + nội dung không tin cậy + egress) → FORCE PROPOSE
- **Audit nguồn dữ liệu**: record shield/trifecta events
- **Path guard + sandbox + signature + verifier**: tool R0-R2 kiểm soát đường dẫn, chữ ký, xác minh kết quả
- **Secret tập trung**: `E:\BRAIN\user, pass, token` — 0 hardcode (audit + loader)

---

## 9. KỸ NĂNG ĐIỀU TRA & TỰ CHUẨN ĐOÁN (năng lực đặc thù)

- **QPIG V2.0** (`uaiif/qpig.py`): Universal Action & Intervention Gateway **19 tool** trên Pi5 — device discovery/identification, network inspection, capability list, communication send, security classify, control/contain, evidence collection, rollback… (đăng ký ToolRegistry, R3 cần owner duyệt)
- **UAIIF Agent Knowledge** (`uaiif/agent_knowledge.py`): 7 LAYER × 20 nhóm Agent; epistemic statuses VERIFIED/OBSERVED/INFERRED/UNKNOWN; scorecard 8 câu gắn bằng chứng
- **System Inventory** (`system_inventory.py`): inventory trung thực services/models/DB/Pi5/tests
- **Causal engine** (`causal_engine.py` 511 LOC + causal_reasoning): phân tích nhân quả RCA
- **Critical thinker + logical reasoner + information gap analyzer**: tư duy phản biện, suy luận logic, phân tích lỗ hổng thông tin
- **Health/RCA**: `/api/health/{rca,machine,monitor,maintenance,history}` — tự chuẩn đoán sức khỏe hệ thống

---

## 10. VAI TRÒ CHERRY ĐẢM NHẬN (10 vai trò bắt buộc — role_orchestrator.py)

1. **EXECUTIVE_ASSISTANT** — Trợ lý điều hành cá nhân
2. **COORDINATOR** — Điều phối viên công việc
3. **TECH_SPECIALIST** — Chuyên gia kỹ thuật IT/OT
4. **NOC_OPERATOR** — Trợ lý NOC & giám sát vận hành
5. **DATA_ANALYST** — Nhà phân tích dữ liệu
6. **RESEARCHER** — Trợ lý nghiên cứu
7. **DOCUMENTATION_OFFICER** — Trợ lý hồ sơ, tài liệu, báo cáo
8. **LANGUAGE_SPECIALIST** — Trợ lý ngôn ngữ (tiếng Việt chuẩn)
9. **INSTRUCTOR** — Người hướng dẫn và huấn luyện
10. **SAFETY_OFFICER** — Người bảo vệ an toàn

Kiến trúc: 1 trợ lý thống nhất chia sẻ memory/tasks/tools/governance — không phải 10 bot riêng lẻ.

---

## 11. VẬN HÀNH 24/7 (sống thật trên máy QUANPT)

- Dual servers 8765/8766 + watchdog tự hồi sinh ≤30' (Task LIVENESS_30MIN)
- Backup 2AM, resource monitoring, health dashboard
- Pi5 file sync guard 15' (md5 verify, scp tự động khi lệch)
- Responder bot NetChat: PYTHON_EXE ưu tiên BRAIN venv (fix bot điếc 18/11)
- AC=0/display-off 600 GIỮ/DC=240s; learning liveness = brain.db mtime

---

## 12. GIỚI HẠN ĐÃ KHAI BÁO (fail-honest — không tuyên bố quá)

| Giới hạn | Chi tiết |
|---|---|
| Vmail/Outlook connector | CHƯA có — email phân tích từ text anh cung cấp trực tiếp |
| Ollama local | DISABLED theo owner (dùng NetMind cloud) |
| Speech learning quarantine | IMPLEMENTED_UNTESTED — chưa test E2E |
| Win32 job containment | INERT_STAGING — chờ duyệt kích hoạt |
| Ecosystem adapters | DC-COMMAND/Kernel L3/Battery AI/BOT — preserve, chưa integrate |
| Self-check wire | Chưa phủ stream endpoint + DM responder (sprint sau) |
| BM25/synonyms/parent-child | Chưa có — đang dùng LIKE (từ phân tích vivi-agent, chờ duyệt) |
| 11 pre-existing test fail | Không đổi, đã stash-proof 4 run độc lập |

---

*Tổng hợp bởi TONY từ bằng chứng sống của hệ thống — không có mục nào bịa thêm.
Mọi thay đổi năng lực cần card duyệt + test + cập nhật PROJECT_STATUS theo quy trình.*
