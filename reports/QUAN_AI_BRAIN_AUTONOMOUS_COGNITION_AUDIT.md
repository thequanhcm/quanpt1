# QUAN AI BRAIN — AUDIT TỰ NHẬN THỨC & HỌC TẬP (GIAI ĐOẠN 0)

**Ngày audit:** 25/10/2026  
**Chủ sở hữu:** Anh Quân — `Quanpt1`  
**Commit baseline:** `0356ccb` (docs update Sprint 2)  
**Người audit:** TONY PHAM / QUAN AI BRAIN — Agent Kỹ sư kiến trúc trưởng

---

## I. MỤC TIÊU AUDIT

Theo Master Prompt V8 — Giai đoạn 0: **Audit trước, sửa sau**.

Mục tiêu:
1. Xác định kiến trúc hiện có cho tự nhận thức, tự học, tự chăm sóc, cổng phê duyệt.
2. Đối chiếu trạng thái thực tế với tài liệu (Capability Registry, báo cáo cũ).
3. Phát hiện khoảng trống, mâu thuẫn, rủi ro.
4. Trình đề xuất Sprint 3 (Deep Knowledge & Memory) + các giai đoạn tiếp theo.

**Không thay đổi mã nguồn, không commit, không xóa file.**

---

## II. KIẾN TRÚC HIỆN CÓ — BẰNG CHỨNG THẬT

### 2.1. Module đã tồn tại (đã kiểm tra code)

| Module | File | Trạng thái | Ghi chú |
|---|---|---|---|
| **Capability Registry** | `cognition/capability_registry.py` (180 dòng) | ✅ IMPLEMENTED | 9 capabilities, 4 trạng thái (VERIFIED_ACTIVE, INERT_STAGING, EXTERNAL_PLANNED, NOT_IMPLEMENTED) |
| **Memory Store** | `memory/sqlite_store.py` (523 dòng) | ✅ IMPLEMENTED | SQLite WAL, episodes/candidate_knowledge/semantic_memory/memories tables |
| **Cognitive Retriever** | `cognition/retrieval.py` (266 dòng) | ✅ IMPLEMENTED | Token-based + BGE-M3 hybrid, explainable ranking |
| **BGE Embedding Service** | `cognition/embedding.py` (119 dòng) | ✅ IMPLEMENTED | Ollama bge-m3, in-memory cache, cosine similarity |
| **Session Memory Manager** | `cognition/session_memory.py` (181 dòng) | ✅ IMPLEMENTED | Fact extraction (identity, preferences, instructions), persist_chat_turn |
| **Autonomous Mind** | `cognition/autonomous_mind.py` (250 dòng) | ✅ IMPLEMENTED | DMN, internal thought stream, keep-warm pulses, pain awareness |
| **Owner Approval Gate** | `tools/approval.py` (278 dòng) | ✅ IMPLEMENTED | ApprovalRequest, OwnerApproval, fingerprint, 8 trạng thái |
| **Governance State Store** | `governance/state_store.py` (524 dòng) | ✅ IMPLEMENTED | Persist approvals, delegations, STOP/FREEZE state |
| **Plan Orchestrator** | `orchestration/plan_orchestrator.py` (22340 bytes) | ✅ IMPLEMENTED | DAG planning, risk assessment R0-R5 |
| **Task Registry** | `orchestration/task_registry.py` (17637 bytes) | ✅ IMPLEMENTED | Durable tasks, step execution, idempotency |

**Tổng kết:** 10/10 module nền tảng **ĐÃ CÓ** trong codebase — không cần tạo mới.

### 2.2. Database hiện trạng (kiểm tra thật)

| DB | File | Kích thước | Nội dung |
|---|---|---|---|
| **tasks.db** | `data/tasks.db` | 90,112 bytes | 86 durable_tasks, 44 durable_task_steps |
| **brain.db** | `data/brain.db` | 798,720 bytes | Memory store (episodes, memories, candidates) |
| **governance.db** | `data/governance.db` | 233,472 bytes | Approvals, delegations, STOP/FREEZE |
| **consultations.db** | `data/consultations.db` | 20,480 bytes | Consultation tickets |
| **learning_reports.db** | `data/learning_reports.db` | 28,672 bytes | Learning reports (nếu có) |
| **memory.db** | `data/memory.db` | 65,536 bytes | Memory cache (nếu có) |

**Phát hiện mâu thuẫn nghiêm trọng:**

| Khía cạnh | Tài liệu tuyên bố | Thực tế DB |
|---|---|---|
| **Episodes** | Capability Registry: "Verified by 214 tests; active in brain.db" | **0 rows** trong `episodes` table |
| **Memories** | "Trí Nhớ Dài Hạn: VERIFIED_ACTIVE" | **0 rows** trong `memories` table |
| **Candidate knowledge** | "Self-Learning Engine V1: VERIFIED_ACTIVE" | **0 rows** trong `candidate_knowledge` table |

**Kết luận:** Module memory **ĐÃ CÓ CODE** nhưng **CHƯA CÓ DỮ LIỆU THẬT** — trạng thái đúng là `IMPLEMENTED_UNTESTED_E2E`, không phải `VERIFIED_ACTIVE`.

### 2.3. Capability Registry — Phân tích

9 capabilities hiện tại:

| # | Capability | Status | Đánh giá |
|---|---|---|---|
| 1 | Trí Nhớ Dài Hạn | VERIFIED_ACTIVE | ❌ **Mâu thuẫn** — DB rỗng, chưa test E2E |
| 2 | Suy Luận AI Cục Bộ | VERIFIED_ACTIVE | ✅ Đúng — Ollama online, test PASS |
| 3 | Lập Kế Hoạch Nhiệm Vụ | VERIFIED_ACTIVE | ✅ Đúng — 86 tasks trong DB |
| 4 | Hộp Cát Công Cụ | VERIFIED_ACTIVE | ✅ Đúng — R0-R2 sandbox có test |
| 5 | Động Cơ Tự Học & Nâng Cấp | VERIFIED_ACTIVE | ❌ **Mâu thuẫn** — learning_reports.db chỉ 28KB, chưa có dữ liệu |
| 6 | Giao Diện Web Chat & Giọng Nói | VERIFIED_ACTIVE | ✅ Đúng — 8765/8766/8768 đều online |
| 7 | Kiểm Soát Tiến Trình OS | INERT_STAGING | ✅ Đúng — chưa bật production executor |
| 8 | Hệ Sinh Thái Vệ Tinh | EXTERNAL_PLANNED | ✅ Đúng — DC-COMMAND, Battery AI là project riêng |
| 9 | Tích Hợp Đa Phần Mềm | VERIFIED_ACTIVE | ✅ Đúng — universal integration có test |

**Vấn đề:** 2/9 capabilities ghi `VERIFIED_ACTIVE` nhưng **chưa có bằng chứng E2E thật**.

---

## III. KHOẢNG TRỐNG NĂNG LỰC (GAP ANALYSIS)

### 3.1. Tự nhận thức hệ thống (Self-Awareness)

| Yêu cầu Master Prompt V8 | Hiện trạng | Khoảng trống |
|---|---|---|
| **System Inventory** — bản đồ thành phần | Capability Registry có 9 mục | ❌ Không có component_id, location, version, last_verified_at, evidence_refs |
| **Runtime Self-Awareness** — trạng thái thời gian thực | AutonomousMind có DMN, keep-warm | ❌ Không có health check real-time, không phát hiện service down |
| **Self-Model** — trả lời "tôi là gì" | ExecutivePersona có 18-field profile | ❌ Không có self-model tổng hợp (thành phần, năng lực, giới hạn, pending approvals) |

**Đề xuất:** Nâng cấp Capability Registry → SystemInventory + SelfModelEngine.

### 3.2. Tự học (Continuous Learning)

| Yêu cầu | Hiện trạng | Khoảng trống |
|---|---|---|
| **Learning Pipeline** — DETECT→COLLECT→EXTRACT→STORE→INDEX→TEST | SessionMemoryManager có fact extraction | ❌ Không có provenance check, evaluation, test generation, reflection |
| **Phân tách loại học** — A (tri thức), B (kinh nghiệm), C (sử dụng), D (thử nghiệm), E (thay đổi hệ thống) | Không có | ❌ Toàn bộ học tập chưa phân loại |
| **Chống học sai** — provenance, conflict detection | Candidate knowledge có status=quarantined | ❌ Không có conflict detection, không có review cycle |
| **Tự đánh giá hiệu quả** — benchmark trước/sau | Không có | ❌ Không có LearningEvaluationMemory, không đo improvement |

**Đề xuất:** Xây dựng ContinuousLearningEngine với 5 loại học, provenance tracking, evaluation benchmark.

### 3.3. Tự chăm sóc (Self-Care)

| Yêu cầu | Hiện trạng | Khoảng trống |
|---|---|---|
| **Health monitoring** — CPU, RAM, VRAM, latency, errors | AutonomousMind có keep-warm, pain awareness | ❌ Không có health check real-time, không có threshold, không có alert |
| **Phân loại biện pháp** — Mức 0-4 | Governance có RiskLevel R0-R5 | ❌ Không có mapping R-level → action level, không có auto-recovery policy |
| **Chẩn đoán lỗi** — triệu chứng, bằng chứng, nguyên nhân | Không có | ❌ Không có error analyzer, root cause analysis |

**Đề xuất:** SelfCareEngine với health monitor, threshold config, auto-recovery policy (Mức 0-2), đề xuất (Mức 3-4).

### 3.4. Cổng phê duyệt (Approval Gate)

| Yêu cầu | Hiện trạng | Đánh giá |
|---|---|---|
| **OwnerApproval** — fingerprint, lifecycle | approval.py có ApprovalRequest, OwnerApproval, 8 trạng thái | ✅ ĐỦ |
| **Approval Center UI** — giao diện duyệt | Không tìm thấy | ❌ Chưa có UI cho anh Quân duyệt |
| **STOP/FREEZE** — ngăn thay đổi | state_store có STOP/FREEZE state | ✅ ĐỦ (code) |
| **Audit log** — nhật ký quyết định | governance.db có approvals table | ✅ ĐỦ (code) |

**Đề xuất:** Xây dựng OwnerApprovalCenter UI (Tab 8 trong Executive Cockpit).

### 3.5. Deep Memory (Sprint 3)

| Yêu cầu | Hiện trạng | Khoảng trống |
|---|---|---|
| **Knowledge ingestion** — source, version, timestamp, verification | candidate_knowledge có source_ref, status | ❌ Không có version, timestamp chi tiết, không có review cycle |
| **Retrieval benchmark** — cold/warm, batch, incremental | BGE-M3 có warm 0.39-0.47s (Sprint 0) | ❌ Không có benchmark framework, không đo retrieval relevance |
| **Memory state recovery** — khôi phục sau restart | SQLite WAL có persistence | ✅ ĐỦ (code) |
| **Conflict handling** — mâu thuẫn, lỗi thời | Không có | ❌ Không có conflict detection, not-outdated policy |

**Đề xuất:** Sprint 3 — Deep Knowledge & Memory với ingestion pipeline, benchmark, conflict handling.

---

## IV. MA TRẬN KHOẢNG TRỐNG (PRIORITIZED)

| Priority | Gap | Impact | Effort | Risk | Đề xuất |
|---|---|---|---|---|---|
| **P0** | Memory DB rỗng — Capability Registry sai trạng thái | Cao — mất niềm tin vào hệ thống | Thấp — chỉ cần update status | Thấp | Sửa CapabilityRegistry: VERIFIED_ACTIVE → IMPLEMENTED_UNTESTED |
| **P0** | Không có Self-Model tổng hợp | Cao — không biết mình có gì/không có gì | Trung bình | Thấp | Build SelfModelEngine từ CapabilityRegistry + health check |
| **P1** | Không có ContinuousLearningEngine | Trung bình — không tự học được | Cao | Thấp | Implement 5-type learning pipeline |
| **P1** | Không có Health Monitor real-time | Trung bình — không phát hiện lỗi sớm | Trung bình | Trung bình | SelfCareEngine với threshold, alert |
| **P1** | Không có Approval Center UI | Cao — anh Quân không thể duyệt | Thấp | Thấp | Tab 8 trong Executive Cockpit |
| **P2** | Không có Retrieval Benchmark | Trung bình — không đo improvement | Trung bình | Thấp | Benchmark framework cho BGE-M3 |
| **P2** | Không có Conflict Detection | Thấp — có thể học sai | Thấp | Trung bình | Conflict detection trong knowledge ingestion |
| **P3** | Không có Auto-Recovery Policy | Thấp — phải manual fix | Cao | Trung bình | Mức 0-2 auto-recovery policy |

---

## V. KIẾN TRÚC ĐỀ XUẤT — SPRINT 3+

### 5.1. Sprint 3 — Deep Knowledge & Memory (2-3 tuần)

**Mục tiêu:**
1. Sửa Capability Registry — trạng thái trung thực.
2. Knowledge ingestion pipeline với provenance, version, verification cycle.
3. Retrieval benchmark (cold/warm, batch, incremental, relevance).
4. Conflict detection & handling.
5. Memory state recovery test.

**File sẽ thay đổi:**
- `cognition/capability_registry.py` — update status
- `memory/knowledge_ingestion.py` — MỚI (300 dòng)
- `memory/benchmark.py` — MỚI (200 dòng)
- `tests/test_knowledge_ingestion.py` — MỚI (150 dòng)
- `tests/test_memory_benchmark.py` — MỚI (100 dòng)

**Không thay đổi:**
- `sqlite_store.py` — schema đã đủ
- `retrieval.py` — logic đã đủ, chỉ thêm benchmark

### 5.2. Sprint 4 — Self-Awareness Engine (2 tuần)

**Mục tiêu:**
1. SystemInventory — component_id, location, version, last_verified_at, evidence_refs.
2. SelfModelEngine — tổng hợp thành phần, năng lực, giới hạn, pending approvals.
3. Health Monitor — real-time check, threshold, alert.

**File sẽ thay đổi:**
- `cognition/system_inventory.py` — MỚI (250 dòng)
- `cognition/self_model_engine.py` — MỚI (200 dòng)
- `cognition/health_monitor.py` — MỚI (180 dòng)

### 5.3. Sprint 5 — Continuous Learning Engine (3 tuần)

**Mục tiêu:**
1. 5-type learning pipeline (A-E).
2. Provenance tracking, conflict detection.
3. Learning evaluation benchmark.
4. LearningReport generation.

**File sẽ thay đổi:**
- `cognition/continuous_learning_engine.py` — MỚI (400 dòng)
- `cognition/learning_evaluator.py` — MỚI (200 dòng)
- `tests/test_continuous_learning.py` — MỚI (200 dòng)

### 5.4. Sprint 6 — Self-Care & Approval Center (2 tuần)

**Mục tiêu:**
1. SelfCareEngine — health monitor, threshold, auto-recovery (Mức 0-2).
2. OwnerApprovalCenter UI — Tab 8 trong Executive Cockpit.
3. Audit log viewer.

**File sẽ thay đổi:**
- `cognition/self_care_engine.py` — MỚI (300 dòng)
- `src/quan_ai_brain/web/server.py` — thêm /api/approvals/* endpoints
- `src/quan_ai_brain/web/static/executive.html` — Tab 8
- `src/quan_ai_brain/web/static/executive.js` — Approval Center UI

---

## VI. RỦI RO & GIỚI HẠN

### 6.1. Rủi ro đã xác định

| Rủi ro | Mức độ | Biện pháp |
|---|---|---|
| **Capability Registry sai trạng thái** — mất niềm tin | Cao | Sửa ngay (P0), thêm test verify DB state |
| **Không có bằng chứng E2E** — code có nhưng chưa chạy thật | Trung bình | Sprint 3-6 có test E2E cho từng module |
| **Học sai kiến thức** — conflict, lỗi thời | Trung bình | Sprint 5 có conflict detection, review cycle |
| **Không phát hiện lỗi sớm** — health check thiếu | Trung bình | Sprint 4 có Health Monitor |
| **Anh Quân không thể duyệt** — không có UI | Cao | Sprint 6 có Approval Center UI |

### 6.2. Giới hạn hiện tại

- **Không có ASR thật** — voice E2E chưa chạy (BLOCKED)
- **Không có camera thật** — Pi 5 camera chưa test (BLOCKED)
- **Không có production executor** — R3+ bị chặn (DESIGN)
- **Không có Approval Center UI** — anh Quân phải approve qua CLI/chat (LIMITATION)

---

## VII. ĐỀ XUẤT TIẾP THEO

### 7.1. Anh Quân phê duyệt Sprint 3

**Phạm vi:**
- Sửa Capability Registry — trạng thái trung thực (P0).
- Knowledge ingestion pipeline với provenance (Sprint 3).
- Retrieval benchmark (Sprint 3).
- Conflict detection (Sprint 3).

**Không bao gồm:**
- Self-Awareness Engine (Sprint 4).
- Continuous Learning Engine (Sprint 5).
- Self-Care & Approval UI (Sprint 6).

**Thời gian ước tính:** 2-3 tuần.

**Test coverage mục tiêu:** 80%+ cho module mới.

**Rollback:** Git revert commit Sprint 3.

### 7.2. Nếu không phê duyệt Sprint 3

Giữ nguyên hiện trạng:
- Capability Registry sai trạng thái (mất niềm tin).
- Memory DB rỗng (không có deep memory).
- Không có benchmark (không đo improvement).
- Không có conflict detection (có thể học sai).

**Rủi ro:** Hệ thống không thể tự học, không có bằng chứng trung thực, khó mở rộng.

---

## VIII. BẰNG CHỨNG AUDIT

### 8.1. File đã kiểm tra

- `cognition/capability_registry.py` — 180 dòng, 9 capabilities
- `memory/sqlite_store.py` — 523 dòng, schema đầy đủ
- `cognition/retrieval.py` — 266 dòng, hybrid retrieval
- `cognition/embedding.py` — 119 dòng, BGE-M3 service
- `cognition/session_memory.py` — 181 dòng, fact extraction
- `cognition/autonomous_mind.py` — 250 dòng, DMN, thought stream
- `tools/approval.py` — 278 dòng, approval gate
- `governance/state_store.py` — 524 dòng, persist approvals
- `orchestration/plan_orchestrator.py` — 22KB, DAG planning
- `orchestration/task_registry.py` — 17KB, durable tasks

### 8.2. Database đã kiểm tra

- `data/tasks.db` — 90KB, 86 tasks, 44 steps
- `data/brain.db` — 798KB, **0 episodes, 0 memories, 0 candidates**
- `data/governance.db` — 233KB, approvals/delegations
- `data/learning_reports.db` — 28KB, empty/minimal

### 8.3. Test suite hiện tại

- **Total tests:** 512 passed, 1 skipped (Sprint 2)
- **Memory tests:** Không có test E2E cho memory ingestion
- **Learning tests:** Không có test cho continuous learning
- **Health tests:** Không có test cho health monitor

---

## IX. KẾT LUẬN

### 9.1. Những gì ĐÃ CÓ

✅ 10 module nền tảng đã implement (Capability Registry, Memory Store, Retriever, Embedding, Session Memory, Autonomous Mind, Approval Gate, Governance Store, Plan Orchestrator, Task Registry).

✅ Schema database đầy đủ (episodes, memories, candidates, approvals, delegations).

✅ Cổng phê duyệt có code (approval.py, state_store.py).

✅ STOP/FREEZE state có implementation.

### 9.2. Những gì CHƯA CÓ

❌ **Trạng thái trung thực** — Capability Registry ghi `VERIFIED_ACTIVE` nhưng DB rỗng.

❌ **Self-Model tổng hợp** — không có bản đồ thành phần + năng lực + giới hạn.

❌ **Continuous Learning Pipeline** — không có 5-type learning, provenance, evaluation.

❌ **Health Monitor real-time** — không có threshold, alert, auto-recovery.

❌ **Approval Center UI** — anh Quân không có giao diện để duyệt.

❌ **Retrieval Benchmark** — không đo cold/warm, relevance, improvement.

### 9.3. Đề xuất ưu tiên

**P0 (ngay lập tức):** Sửa Capability Registry — trạng thái trung thực.

**Sprint 3 (2-3 tuần):** Deep Knowledge & Memory — ingestion, benchmark, conflict handling.

**Sprint 4 (2 tuần):** Self-Awareness Engine — SystemInventory, SelfModel, Health Monitor.

**Sprint 5 (3 tuần):** Continuous Learning Engine — 5-type learning, evaluation.

**Sprint 6 (2 tuần):** Self-Care & Approval Center — auto-recovery, UI duyệt.

---

## X. QUYẾT ĐỊNH CẦN ANH QUÂN

| Mục | Hành động | Thời gian | Rủi ro nếu không làm |
|---|---|---|---|
| **1. Sửa Capability Registry** | Update status: VERIFIED_ACTIVE → IMPLEMENTED_UNTESTED cho memory/learning | Ngay | Mất niềm tin vào hệ thống |
| **2. Duyệt Sprint 3** | Deep Knowledge & Memory (ingestion, benchmark, conflict) | 2-3 tuần | Không có deep memory, không đo improvement |
| **3. Duyệt Sprint 4** | Self-Awareness Engine (inventory, self-model, health) | 2 tuần | Không biết mình có gì/không có gì |
| **4. Duyệt Sprint 5** | Continuous Learning Engine (5-type learning) | 3 tuần | Không tự học được |
| **5. Duyệt Sprint 6** | Self-Care & Approval Center UI | 2 tuần | Không có UI để duyệt, phải manual |

**Anh trả lời:**
- [ ] **Duyệt Sprint 3 ngay** (khuyến nghị — nền tảng cho tự học)
- [ ] **Duyệt tất cả Sprint 3-6** (full autonomous cognition)
- [ ] **Chỉ duyệt P0** (sửa status trung thực, chờ thêm)
- [ ] **Không duyệt — giữ nguyên hiện trạng**

---
*Hết báo cáo audit Giai đoạn 0. Chờ quyết định anh Quân để tiếp tục Sprint 3.*