# BÁO CÁO TỔNG THỂ CHI TIẾT HỆ THỐNG QUAN AI BRAIN VÀ ĐỊNH HƯỚNG

**Thời điểm chốt:** 27/10/2026 18:03 (GMT+7) · **Commit:** `6b6df30` (Sprint 14) · **Branch:** master · **Tổng commits:** 53
**Số liệu trong báo cáo này:** 100% từ công cụ thật (API live 127.0.0.1:8765, git log, Task Scheduler, DB) tại thời điểm chốt — không mô tả suông.
**Chuỗi nghiệm thu:** mọi sprint đều qua card duyệt của quanpt1 (consume-once trong governance.db) — 12/13 card APPROVED, 1 CANCELLED (Sprint 5 gộp vào 6-GOP).

---

## 1. TÓM TẮT ĐIỀU HÀNH

QUAN AI BRAIN là **trợ lý điều hành số an toàn-first** chạy 24/7 trên PC Windows 10 của anh Quân (Viettel), có trí nhớ bền vững, lập kế hoạch có kiểm soát, hành vi có chủ quyền phê duyệt, học từ kinh nghiệm có kiểm dịch, và trạng thái trung thực (không tự khen, không số liệu giả).

**Đã đạt đến hôm nay (27/10/2026):**
- **2 giai đoạn lớn hoàn tất:** Foundation Evolution (Sprint A/B/C/D + Sprint 1-2 core) và **V3 lộ trình 14 sprint** (Sprint 1-14, đóng đủ, mỗi sprint có card duyệt + test + smoke thật + báo cáo riêng).
- **Hệ thống live:** dual server (dashboard 8765 + điều khiển 8766, localhost-only), 12 SQLite DB, 91 file test (927 passed / 0 fail / 1 skip Pi5), Pi5 edge avatar **READY** (heartbeat 0.29s, RTT 14.6ms, 0 alert), NetChat 2 chiều 24/7.
- **Vận hành tự vệ:** watchdog tự hồi phục (cap 5 restart/h), backup 2AM + báo cáo sáng 8AM + khởi động LOGON — cả 3 task Task Scheduler trạng thái **Ready**, lịch chạy kế tiếp 28/10.
- **Trung thực có hệ thống:** ma trận năng lực 5 mức sinh từ DB thật; 3 mục đang là việc chờ anh xử lý (mục 7).

---

## 2. LỘ TRÌNH ĐÃ ĐI (TIMELINE)

### Giai đoạn Foundation (26/10 → sáng 27/10)
| Sprint | Nội dung chính | Commit |
|---|---|---|
| A/B | CognitiveLoop, Reflection, watchdog monitor, /api/health | 9fbbf48 |
| C+D | Self-model live probes, knowledge quality scanner, chính sách thăng hạng L0-L3 | 9cf92e8 |
| 1 | NetChat command center 2 chiều (routing tiếng Việt, catch-up) | 842d30a |
| 2 | ApprovalOrchestrator: card bền vững + ApprovalGate consume-once + R5 double-block | f6bcabd |
| Core 24/7 | Stack reboot-proof, watchdog venv thật, backup task, env HKCU | 938d5ba |
| Honesty | Grounding facts sống, teach pipeline (nhớ rằng/ghi nhớ), /api/status thật | 3f72c58, 86484ba |
| OK-Confirm | "ok" = duyệt hành động staged (TTL 15', consume-once), không vòng vo | 634a7c1 |
| Pi5 truth | Sửa probe sai lớp (8768) → single source edge/status | f92b32a |
| External lookup | Gemini key HKCU + Google News RSS + synthesis, fail-closed | 54a670f |
| Avatar sync | Biểu cảm chat→Pi5 (THINKING/RESEARCHING/SPEAKING/IDLE) | fe0f3fe |
| NetChat tab | Tab "Quan Tri Kenh NetChat" trên dashboard | 808e585 |

### Giai đoạn V3 — 14 sprint (27/10, một ngày)
| Sprint | Nội dung | Card | Commit | Tests |
|---|---|---|---|---|
| 1 | Walking skeleton + audit nền móng | ✓ | 81b6a22 era | — |
| 2 | ApprovalOrchestrator V3 | ✓ | f6bcabd | 625 |
| 3 | Information Gap Awareness (9 nhóm A-I, silence≠consent) | ✓ | 39770d9 | 717 |
| 4 | LLM gap detect fail-closed + auto-reminder + dedup 108.969→678 | ✓ | 7d72f02 | 736 |
| 6-GOP | 4 hướng gộp: RAG tài liệu hybrid + 24/7 hardening + báo cáo 8AM + ttns lookup | ✓ | 06b9f06 | 767 |
| 7 | Bền vững thật: reboot 12:02 nghiệm thu, RAG real BGE-M3 10/10, daemon governance | ✓ | 1da1847, 7886890 | 780 |
| 8 | To-do + email DRAFT-ONLY (.eml) + Approval Center UI | ✓ | 277f21b | 799 |
| 9 | Workbench 🧰 + email_intake mock (Vmail BLOCKED trung thực) + experience retrieval | ✓ | 679b6e9 | 817 |
| 10 | Email Intelligence: proposal 11 trường + tạo task PENDING idempotent | ✓ | 6b96646 | 833 |
| 11 | Experience Memory: lesson kiểm dịch, promote chỉ owner (DUYET) | ✓ | b3fb665 | 857 |
| 12 | Web & Internal READ-ONLY: SSRF-guard, robots, Bing RSS (DDG bị chặn bot) | ✓ | cd626c0 | 893 |
| 13 | Continuous Improvement: ma trận 5 mức từ DB thật + export .md | ✓ | 360a392 | 905 |
| 14 | Info-gaps schema thật + semantic search kinh nghiệm BGE-M3 | ✓ | 6b6df30 | 927 |

**Tăng trưởng test: 625 → 927 bài (48%+) trong một ngày, 0 fail ở từng điểm nghiệm thu.**

---

## 3. KIẾN TRÚC HIỆN TẠI

### 3.1 Module Python (`src/quan_ai_brain/` — 20 gói)
- **cognition/** (24 module): cognitive_loop, session_memory, context_builder, grounding_facts, self_model_engine, information_gap_analyzer, llm_gap_detector, document_rag, embedding (BGE-M3), **experience_semantic (mới — S14)**, improvement_report, cognitive_state*, role_orchestrator…
- **memory/**: sqlite_store (brain.db), models, experience_retrieval (keyword), experience_consolidation, knowledge_ingestion
- **governance/**: approval_cards (consume-once, TTL, fingerprint), state_store, consultation_inbox
- **orchestration/planning/**: durable task registry (tasks.db), plan orchestrator, task_registry
- **integration/**: web_connector (read-only), email_intelligence, email_draft, ttns_lookup
- **web/**: server (BrainAPIHandler dual 8765/8766), static executive dashboard + Workbench
- **daemon/edge/llm/voice/execution/learning/core**: watchdog, edge heartbeat HMAC, LLMRouter (NetMind cloud + Ollama local), voice pipeline XiaoZhi, guardrails, redaction

### 3.2 Dữ liệu — 12 SQLite DB (data/)
`brain.db` (trí nhớ: episodes/memories/candidates/semantic — 86MB sau dedup), `tasks.db` (454 task), `governance.db` (13 card), `todos.db`, `email_intake.db`, `information_gaps.db`, `document_index.db` (RAG), `consultations.db`, `learning_reports.db`, `learning_sandbox.db`, `gov_sandbox.db`, `memory.db`

### 3.3 Giao diện & kênh
- **Executive Dashboard** (8765): tab Trạng thái / LLM / Kênh NetChat (avatar) / **Workbench 🧰** (overview, tasks, Approval Center, to-do, Email Intelligence, Bài học + **ô tìm semantic S14**, Web & Intranet, **📈 Continuous Improvement**)
- **NetChat** "Trợ lý Tony Pham": 2 chiều 24/7 — lệnh trạng thái/báo cáo/nhiệm vụ/tri thức/việc cần làm/nhớ giúp tôi + DUYỆT/TỪ CHỐI/SỬA TASK-xxx + trả lời info-gap
- **Pi5 avatar** (EDGE-PI5-DESK-01): kiosk biểu cảm đồng bộ theo chat

### 3.4 LLM
- **NetMind Cloud GLM-5.3-Flash** (mặc định, ~1.2s) · **Ollama local** qwen2.5:7b + **bge-m3 embedding** (RAG + semantic search) · mock mode trung thực khi không có provider

---

## 4. MA TRẬN NĂNG LỰC 5 MỨC — SỐ LIỆU THẬT 18:03 27/10

| # | Năng lực | Mức | Bằng chứng (trích live API) |
|---|---|---|---|
| 1 | Nhiệm vụ (tasks) | **Đã có và hoạt động** | 454 task; completed 2; failed 0; **249 in-flight** (đa số task staged cũ — xem mục 7.3) |
| 2 | Phê duyệt | **Đã có và hoạt động** | 13 card; 12 APPROVED; 0 REJECTED; consume-once |
| 3 | Kinh nghiệm (memory) | **Đã có và hoạt động** | 58 lesson (1 confirmed, **57 chờ anh duyệt**); 1.841 semantic confirmed |
| 4 | Email Intelligence | **Có một phần** | 3 email intake (mock); 1 proposal đã link task; **Vmail thật: BỊ CHẶN** |
| 5 | Web read-only | **Đã có và hoạt động** | SSRF-guard + Bing RSS + robots; smoke commit cd626c0 |
| 6 | Thông tin thiếu | **Đã có và hoạt động** (S14 đóng) | info_gap_tasks schema thật: 0 mở, 0 giải quyết, 3 events |
| 7 | Test regression | **Đã có và hoạt động** | 927 passed / 0 fail / 1 skip (Pi5 phần cứng) |

**Edge:** Pi5 READY — heartbeat cách 0.29s, RTT 14.6ms, 0 alert, timeout 4s.
**Task Scheduler:** BACKUP_2AM (chạy kế 28/10 02:00) · KHOI_DONG_LOGON · MORNING_REPORT_8AM (28/10 08:00) — cả 3 **Ready**.

---

## 5. AN TOÀN & CHỦ QUYỀN (KHÔNG THAY ĐỔI TỪ ĐẦU)

- **R1–R5**: work-only-workspace, R2 ghi file trong workspace khi owner bấm, R3 email DRAFT-ONLY, **R4 duyệt có xác thực** (card + consume-once + auth_method), **R5 hard-block không ghi đè** (13 card gần nhất: 0 R5).
- **Mọi hành động thật đều qua 1 trong 2 cổng**: card duyệt (governance.db) hoặc "ok" confirm TTL 15'.
- **Learning ≠ deployment**: lesson mới luôn UNVERIFIED+quarantined; chỉ owner_confirm=DUYET mới nâng VERIFIED; chưa duyệt không rò vào retrieval (có test chứng minh).
- **Không đọc/ghi secret**; Gemini key lưu HKCU user-level, không log không commit; redaction + guardrails trên output.

---

## 6. KIỂM CHỨNG & PHƯƠNG PHÁP

- **927 test** (91 file; 17 file V3 sprint) — unit mock 100% + E2E + hardening + adversarial (session song song).
- **Smoke live BẮT BUỘC mỗi sprint** — bài học cố hữu: mock không bắt được NameError route (S12) và timeout hiệu năng (S14); smoke thật mới bắt được.
- **Fail-honest như nguyên tắc thiết kế**: DB hỏng → CHƯA XÁC MINH (có test riêng); không 0 giả; không tự khen; số liệu luôn kèm evidence truy vết.
- **Vấn đề thật đã sửa trong ngày**: route do_GET/do_POST sai (S9, S10, S12), KHOI_DONG.bat CRLF/ASCII (S7), UnicodeEncodeError morning report, dedup 108k duplicates, probe Pi5 sai lớp, embedding service per-request timeout → singleton+prefilter (S14).

---

## 7. VIỆC MỞ (TRUNG THỰC — KHÔNG GIẤU)

1. **Vmail thật BỊ CHẶN** (từ S8): chờ **anh đổi mật khẩu SSO** → mở card "Real Email Connector". Luồng email thật dừng ở đây — mọi phần khác của email intelligence đã sẵn sàng.
2. **57 bài học chờ anh duyệt** trong Workbench → duyệt để làm căn cứ mạnh cho đề xuất email (hiện chỉ 1/58 confirmed).
3. **249 nhiệm vụ in-flight** (đa số task staged/lịch sử từ giai đoạn trước): cân nhắc duyệt hoặc huỷ hàng loạt — cần tiêu chí dọn từ anh.
4. **DuckDuckGo bị chặn bot** (anomaly) → Bing RSS là primary; nếu cần tìm sâu hơn thì xem xét API có khoá (card riêng).
5. **Session agent song song** đang phát triển chu kỳ mới trên cùng working tree (cognitive_state, context_builder mở rộng, planning wiring — adversarial test 12 bài). Phần này CHƯA nghiệm thu, không tính trong ma trận trên.
6. **Pi5 skip cố hữu** 1 test khi phần cứng offline (không phải lỗi).

---

## 8. ĐỊNH HƯỚNG TIẾP THEO (ĐỀ XUẤT — CHỜ ANH PHÊ DUYỆT RIÊNG, KHÔNG TỰ TRIỂN KHAI)

### 8.1 Việc của anh (mở khoá năng lực bị nghẽn)
| Việc | Mở được gì |
|---|---|
| Đổi mật khẩu SSO Vmail | Email thật end-to-end (intake → proposal → task) |
| Duyệt 57 bài học | Kinh nghiệm xác nhận mạnh cho đề xuất + truy vấn |
| Chốt tiêu chí dọn 249 task | Ma trận tasks phản ánh đúng health thật |
| Chỉ định thư mục tài liệu thật | RAG kho thật (hiện kho mẫu Lab-Mini-RAG 10/10) |

### 8.2 Đề xuất chu kỳ Sprint 15+ (mỗi item cần card riêng)
1. **Connector M-Suite read-only** (Outlook mail/Calendar qua COM trên máy anh) — thay thế hoàn toàn phần Vmail BLOCKED; thiết kế riêng vì đụng ứng dụng thật.
2. **Dọn kho task**: công cụ ArchW batch (duyệt/huỷ theo filter) + audit trail — giải quyết 249 in-flight an toàn.
3. **Semantic search mở rộng**: áp experience_semantic cho candidate_knowledge + RAG tài liệu (unity embedding pipeline).
4. **Lesson digest hàng ngày**: sáng 8AM kèm "bài học mới chờ duyệt" (tận dụng morning_report).
5. **Hoàn thiện chu kỳ mới của session song song** (cognitive_state + adversarial) — khi họ xong, tích hợp nghiệm thu theo đúng quy trình card.

### 8.3 Nguyên tắc tiếp tục giữ
Mỗi sprint: audit → card duyệt → diff nhỏ test được → smoke thật BẮT BUỘC → báo cáo trung thực → commit. Không tự mở sprint, không tự khen, không số liệu giả.

---

## 9. PHỤ LỤC

- **53 commits** (26/10-27/10); chi tiết từng sprint: các file `BAO_CAO_V3_SPRINT*.md` cùng thư mục này.
- **Báo cáo liên quan trực tiếp**: `BAO_CAO_SELF_ASSESSMENT_20261027_081941.md` (S13 export), `BAO_CAO_V3_SPRINT14_20261027.md` (mới nhất), `BAO_CAO_KY_THUAT_TONG_THE_HE_THONG_20261027.md` (kỹ thuật tổng thể buổi sáng), `HANDOFF_LATEST.md` (reports/).
- **Live endpoints chính**: `/api/status`, `/api/health`, `/api/workbench/overview`, `/api/approvals`, `/api/experience/lessons`, `/api/experience/search`, `/api/web/search|page|rss`, `/api/improvement/report`, `/api/executive/edge/status`.

*Báo cáo được tạo bởi netMind Desktop (GLM-5.3-Flash) theo lệnh owner 27/10/2026 — mọi số liệu lấy trực tiếp từ hệ thống lúc 18:03.*
