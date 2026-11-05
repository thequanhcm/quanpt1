# V7 SUPER MEMORY ARCHITECTURE V2 — GIAI ĐOẠN G2
**Tài liệu:** DOC-QAB-SMEM-002 · **Trạng thái:** `DESIGNED — CHỜ OWNER DUYỆT (DESIGN-ONLY)`
**Chương trình:** QUAN AI BRAIN V7.0 — SUPERINTELLIGENCE & SUPREME SECURITY EVOLUTION
**Sở hữu:** Quanpt1 (thẩm quyền tối cao) · **Workspace:** `E:\BRAIN`
**Soạn:** 05/11/2026 (UTC+7) · **Phạm vi:** design-only — KHÔNG sửa code/test, KHÔNG bật daemon mới, KHÔNG commit
**Thang Evidence dùng toàn tài liệu:** DESIGNED → IMPLEMENTED → UNIT_TESTED → INTEGRATION_TESTED → SIMULATED → LIVE_VERIFIED → PRODUCTION_VERIFIED (test PASS không bao giờ tự động = bằng chứng vận hành thật)

---

## 0. PHẠM VI VÀ GIỚI HẠN

1. Tài liệu này **chỉ thiết kế** Super Memory V2 cho G2. Không file code/test nào bị thay đổi khi soạn tài liệu.
2. Tuân thủ nguyên tắc bất biến V7:
   - **One Cognitive Core** — không tạo bộ não/thư viện memory thứ hai cạnh tranh; mọi thứ là **lớp mỏng trên store hiện có**.
   - **Independent Security** — SENTINEL/governance không bị memory layer đụng tới.
   - **Evidence First** — mỗi tuyên bố trạng thái phải có đường dẫn file + số dòng hoặc probe runtime.
   - **Learning quarantine-only** — self-study chỉ ghi `candidate_knowledge`; promotion chỉ owner + R4 verifier.
   - **R0–R5 bất biến** — không đề xuất nâng/quay quyền; không auto-approve; không daemon/executor mới.
3. Mọi số liệu DB trong mục A là **probe SQL trực tiếp trên `data/brain.db` lúc 05/11/2026** (read-only), không trích từ báo cáo cũ.

---

## A. HIỆN TRẠNG ĐÃ KIỂM CHỨNG (AUDIT-FIRST)

### A.1. Hệ thống phân loại memory hiện có trong code (enum/types thật)

| # | Hệ phân loại | File + dòng | Giá trị | Evidence |
|---|---|---|---|---|
| 1 | `MemoryType` (enum chính) | `src/quan_ai_brain/memory/models.py:10-16` | `EPISODIC, SEMANTIC, PROCEDURAL, DECISION, PREFERENCE, CANDIDATE` (6 loại) | IMPLEMENTED + LIVE (dữ liệu thật mục A.3) |
| 2 | `VerificationStatus` | `models.py:19-25` | `USER_PROVIDED, OBSERVED, VERIFIED, INFERRED, UNVERIFIED, CANDIDATE` | IMPLEMENTED + LIVE (mục A.3) |
| 3 | `LifecycleStatus` | `models.py:28-33` | `active, superseded, archived, quarantined, deprecated` | IMPLEMENTED + LIVE |
| 4 | `KNOWLEDGE_TYPES` (Deep Memory V9) | `src/quan_ai_brain/memory/deep_memory.py:34` | `FACT, OPINION, QUESTION, RULE, PROCESS, CONCLUSION` | IMPLEMENTED + LIVE (150 KU) |
| 5 | `KU_STATUSES` | `deep_memory.py:36-39` | `RAW, EXTRACTED, CANDIDATE, VERIFIED, INFERRED, CONFLICTED, NEEDS_OWNER_REVIEW, REJECTED, SUPERSEDED, ARCHIVED` | IMPLEMENTED + LIVE |
| 6 | `RELATION_TYPES` | `deep_memory.py:41-44` | `SUPPORTS, CONTRADICTS, DERIVED_FROM, REFINES, SUPERSEDES, DEPENDS_ON, RELATED_TO, APPLIES_TO, VERIFIED_BY, REJECTED_BY` | IMPLEMENTED + LIVE (210 relations) |
| 7 | `FactLevel` (M3 ngôn ngữ chung) | `src/quan_ai_brain/memory/unified_memory.py:40-46` | `FACT, OBSERVED, INFERENCE, QUARANTINED` + ánh xạ `VERIFICATION_TO_FACT` (dòng 50-57) | UNIT_TESTED (21 tests `tests/test_m3_unified_memory.py`) |
| 8 | `KnowledgeType` V31 | `src/quan_ai_brain/memory/models_v31.py:20-27` | trùng KNOWLEDGE_TYPES + `ConflictType`, `ResolutionStatus`, `KnowledgeProvenanceV31` (dòng 30-43, 64-93) | IMPLEMENTED |
| 9 | `KnowledgeSource` / `VerificationState` (ingestion) | `src/quan_ai_brain/memory/knowledge_ingestion.py:27-35, 38-45` | 7 nguồn + `quarantined→under_review→approved→rejected→expired→conflicted` | IMPLEMENTED (daemon đang dùng) |
| 10 | `ExperienceType` / `OutcomeType` | `src/quan_ai_brain/memory/experience_store.py:28-35, 20-25` | `task, workflow, decision, problem_solving, learning, general` / `success, failure, partial, unknown` | DESIGNED + UNIT_TESTED — **UNWIRED** (mục B.3) |
| 11 | `TaskState` / `StateTransition` | `src/quan_ai_brain/memory/state_tracker.py:20-29, 32-45` | 8 trạng thái + bảng chuyển hợp lệ (dòng 49-58) | DESIGNED + UNIT_TESTED — **UNWIRED** (mục B.3) |
| 12 | `QuarantineStatus` V37.3 | `src/quan_ai_brain/memory/quarantine_store.py:20-25` | `PENDING_REVIEW, APPROVED, REJECTED, EXPIRED` | DESIGNED + UNIT_TESTED — store riêng `quarantine.db`, KHÔNG dùng trong production (candidate thật nằm ở `brain.db.candidate_knowledge`) |

**Kết luận A.1:** taxonomy **thực tế đang dùng** = `MemoryType` 6 loại + V9 knowledge units 6 loại + lifecycle 5 trạng thái. Không có enum nào tên "8 loại memory" — 8 loại là **đích thiết kế V7 G2**, chưa tồn tại trong code.

### A.2. Store & schema thật trên `data/brain.db`

| Store / bảng | File định nghĩa | Vai trò | Bằng chứng schema |
|---|---|---|---|
| `episodes` | `sqlite_store.py:50-59` (+ no-op `deep_memory.py:284-292`) | trí nhớ sự kiện append-only, `kind` tự do (chat_turn/task/experience_lesson) | LIVE |
| `memories` | `sqlite_store.py:78-99` | record đa loại có provenance (`memory_type, verification_status, confidence_score, project_scope, version, superseded_by, lifecycle_status`) | LIVE |
| `semantic_memory` | `sqlite_store.py:70-77` | tri thức ĐÃ promote: bắt buộc `approved_by` + `regression_passed=1` (CHECK constraint) | LIVE |
| `candidate_knowledge` | `sqlite_store.py:60-69` | **quarantine R4**: `status='quarantined'` mặc định | LIVE |
| `knowledge_units` + `knowledge_relations` + `memory_exchange_log` + `memory_review_runs` + `owner_questions` | `deep_memory.py:197-315` (5 bảng ADDITIVE-ONLY, không ALTER bảng cũ) | lớp tri thức cấu trúc V9/V10: SPO, quan hệ có căn cứ, idempotency, review checkpoint, câu hỏi cho owner | LIVE |

API ghi/đọc đã kiểm chứng:
- `MemoryStore.add_episode` (`sqlite_store.py:107-127`) — redact trước khi ghi.
- `MemoryStore.add_candidate` / `promote_candidate` (`sqlite_store.py:147-158, 160-192`) — **fail-closed**: `approval_verified=False` → `PermissionError`; chỉ candidate `quarantined` mới promote được.
- `MemoryStore.store_memory` / `search_memories` / `supersede_memory` / `trace_source` (`sqlite_store.py:204-260, 274-325, 327-402, 480-512`) — supersede giữ lịch sử (version+1, `superseded_by`), không xoá.
- `DeepMemoryStore.extract_from_chat_turns` (`deep_memory.py:390-430`) — trích KU **deterministic, không LLM**, idempotent qua `memory_exchange_log` UNIQUE (dòng 243-254), max 5 KU/episode (dòng 75).
- `DeepMemoryStore.link_units` / `compare_duplicates` (`deep_memory.py:502-567, 591-618`) — mâu thuẫn bằng negation/antonym, KHÔNG tự merge, KHÔNG tự chọn phía (`_mark_contradicted` dòng 569-589).
- `DeepMemoryStore.supersede_unit` (`deep_memory.py:687-746`) — KU mới version+1, KU cũ → SUPERSEDED, quan hệ SUPERSEDES có căn cứ.
- `MemoryFacade` 5 lớp (M3, `unified_memory.py:112-200`): MemoryStore · DeepMemoryStore · ExperienceStore · ContextStore · QuarantineStore; `promote_to_fact` (dòng 260-295) bắt buộc `GovernanceApprovalVerifier` — fail-closed R4.

### A.3. Số liệu runtime probe 05/11/2026 (SQL trực tiếp, read-only)

| Bảng | Số dòng | Chi tiết phân bổ |
|---|---|---|
| `episodes` | **2.940** | kind: chat_turn / task / experience_lesson |
| `memories` | **2.397** | EPISODIC 2.377 (active 2.264 · quarantined 43 · superseded 70) · SEMANTIC 9 · PROCEDURAL 2 · PREFERENCE 2 · CANDIDATE 7 · **DECISION 0** |
| `memories` theo verification (active) | — | OBSERVED 2.194 · VERIFIED 72 · USER_PROVIDED 11 (PREFERENCE 2 + SEMANTIC 9) |
| `semantic_memory` | **5.051** | toàn bộ đã `regression_passed=1` (CHECK) |
| `candidate_knowledge` | **8.366** | quarantine backlog chờ owner |
| `knowledge_units` | **150** | EXTRACTED 148 · SUPERSEDED 2 |
| `knowledge_relations` | **210** | |
| `owner_questions` | **0** | vòng hỏi–đáp owner CHƯA vận hành thực tế |
| `memory_exchange_log` | 40 | idempotency đang hoạt động |

**Bảng KHÔNG tồn tại trong brain.db (probe `SELECT COUNT(*)` lỗi "no such table"):** `emotional_weights`, `emotion_events`, `experiences`, `experience_outcomes`, `task_states`. → Các module V16/ExperienceStore/StateTracker **chưa từng ghi vào production DB**.

**Probe mạng 05/11:** Ollama `127.0.0.1:11434` → **OFFLINE** (TCP TimeoutError); core server 8766 → LISTENING. Khớp `/api/health` probe trong `src/quan_ai_brain/web/server.py:1291-1301` (TCP probe 11434 timeout 1.5s → báo `ollama_daemon: OFFLINE`).

### A.4. Luồng đã kiểm chứng đang chạy thật

| Luồng | Code | Cơ chế quyền | Evidence |
|---|---|---|---|
| **Owner teach** (anh dạy trong chat) | `src/quan_ai_brain/cognition/teach_pipeline.py:62-113` (`detect_teaching`, `persist_taught_memory`) | chỉ owner được dạy; `USER_PROVIDED` ngay, `source_ref="owner_teach:..."`; append-only, không ghi đè | LIVE_VERIFIED (V8 handoff — teach persist marker; DB có 11 rows USER_PROVIDED) |
| **Experience consolidation** (Sprint 11) | `src/quan_ai_brain/memory/experience_consolidation.py:1-17` + hook `web/server.py:3404-3420` | task COMPLETED/FAILED → lesson **CANDIDATE quarantined** (UNVERIFIED); `promote_lesson` (server 5406) bắt buộc `approval_verified=True` | INTEGRATION_TESTED (hook live trong lifecycle; tests `test_v3_sprint11_experience_memory.py` trên tmp_path) |
| **Self-study V2** | `src/quan_ai_brain/cognition/self_study.py:186-242` (SCAN→STUDY→SYNTHESIZE→DEDUP→QUARANTINE→REPORT) | mọi tri thức mới ghi `candidate_knowledge status='quarantined'` (`_quarantine` dòng 301-319); không tự nạp memory (dòng 16-18, 241) | LIVE (candidate 8.366; 3 items 03/11 theo V7 audit dòng 82) |
| **Learning daemon** | `tools/learning_daemon.py:223-241` | Sprint 7(b) governance fix: **KHÔNG tự promote quarantine**, chỉ đếm + log; bỏ pytest tự chạy (đọc `reports/TEST_RUN_LATEST.txt`, dòng 179-220); idempotent `skip_duplicates` (dòng 132) | LIVE (daemon pythonw trong stack 10 processes) |
| **Owner feedback** (V9 Slice 4) | `src/quan_ai_brain/memory/owner_feedback.py:39-100` | 12 bước traceable; mâu thuẫn với VERIFIED → hỏi lại, không âm thầm đổi (dòng 67-75); `production_approved: False` luôn (dòng 98 — câu trả lời ≠ phê duyệt production) | UNIT_TESTED (`test_v9_owner_feedback.py`) — `owner_questions=0` nên **chưa chạy thật trong production** |
| **Q-4 promotion có audit trail** | `governance/approval_verifier.py` FAIL-CLOSED (docs/PROJECT_STATUS.md dòng 155) | card APPROVED + auth_method + TTL + ledger 1-lần | LIVE_VERIFIED (3.209 candidates promoted; semantic 1.491→5.051) |

### A.5. Embedding & retrieval hiện trạng

- `BGEEmbeddingService` (`src/quan_ai_brain/cognition/embedding.py:47-96`): BGE-M3 1024-dim qua Ollama; `timeout=10.0s` (dòng 55), ping 0.5s (dòng 64-66); lỗi → trả `[]` (dòng 89-91).
- `OllamaClient` (`src/quan_ai_brain/llm/client.py:24-27`): default 30s, kẹp [0.1, 300]s.
- Khi Ollama OFFLINE (hiện trạng thật — probe A.3): mỗi lần gọi **chờ tới timeout mới fallback** — audit trước ghi nhận ~6s; mức timeout trong code là 10s/0.5s/1.5s tuỳ điểm gọi.
- Tác động đã kiểm chứng trong code:
  - `search_memories` chỉ là `content LIKE` (`sqlite_store.py:291-293`) → semantic search SQL không bao giờ dùng vector.
  - `document_rag.py` fail-closed: embedding lỗi → keyword scoring (0.4 keyword + 0.6 dense chỉ khi có embedding) (dòng 5-11, 219, 254-281).
  - `experience_semantic.py` fail-open: Ollama offline → trả rỗng + cờ `semantic_available=False` (dòng 5-8).
  - Deep Memory V9 **không phụ thuộc embedding** (deterministic Jaccard/token — `deep_memory.py:121-122, 563-566`) — vẫn chạy khi offline nhưng recall yếu hơn.
- ChromaDB tiered memory V37.2 (`memory/vector_store.py:1-14, 31-41`) — dùng trong knowledge ingestion; kho `data/knowledge_db` đã dọn/tái tạo 31/10 (PROJECT_STATUS dòng 396).

---

## B. PHÂN TÍCH GAP

### B.1. Đối chiếu 8 loại memory đích (V7) vs hiện trạng đã kiểm chứng

Định hướng V7 (`reports/V7_MASTER_BASELINE_AUDIT.md:81`): *"8-loại memory V7 chưa đủ (preference/experience)"*; `reports/SUPER_AI_MASTER_BASELINE.md:82`: *"Memory 8 loại + provenance/versioning — PHỦ RỘNG — cần kiểm kê lại theo 8 loại"*.

| # | Lớp đích V2 | Hiện trạng đã kiểm chứng | Gap thật | Đánh giá |
|---|---|---|---|---|
| 1 | **Episodic** | `episodes` 2.940 + `memories` EPISODIC 2.377; `record_task_result` (`sqlite_store.py:414-441`) | có; chưa chuẩn hóa retrieval theo thời gian/kind cho 8 lớp | ✅ nền tốt |
| 2 | **Semantic** | `semantic_memory` 5.051 + `memories` SEMANTIC 9 + `knowledge_units` 150 | **3 nơi lưu semantic song song** (memories / semantic_memory / knowledge_units) — cùng nội dung có thể lệch; chưa có view hợp nhất per-item | ⚠️ phân mảnh |
| 3 | **Procedural** | `MemoryType.PROCEDURAL` chỉ **2 rows**; `experience_retrieval.py:99` đã tra PROCEDURAL; RULE/PROCESS có trong knowledge_units nhưng không có đường nào chuyển RULE/PROCESS → PROCEDURAL | thiếu pipeline "KU loại RULE/PROCESS đã review → procedural memory"; 2 rows hiện tại là teach thủ công | ❌ gần như trống |
| 4 | **Preference** | `MemoryType.PREFERENCE` **2 rows** (USER_PROVIDED, từ teach pipeline); không có expiry, không có conflict-check riêng cho preference | thiếu lifecycle preference (hết hạn, phạm vi, mâu thuẫn giữa 2 preference) — audit gap gọi tên | ⚠️ tối thiểu |
| 5 | **Experience** | experience_consolidation (candidate lessons) + `experience_retrieval.py` (keyword trên PROCEDURAL/EPISODIC) + ExperienceStore **UNWIRED** (bảng `experiences` không tồn tại) | bài học tồn tại dạng candidate trong `memories` tags `sprint11_lesson`; không có trải nghiệm dạng cấu trúc (context→action→outcome) dùng được cho retrieval | ❌ chưa đủ (audit gap gọi tên) |
| 6 | **Emotional / Social** | `emotional_memory.py` V16 có code + 18 tests (tmp_path) nhưng **UNWIRED**; bảng không tồn tại; lexicon **tiếng Anh** (`EMOTION_LEXICON` dòng 19-28) | không có dữ liệu cảm xúc/xã hội nào được ghi; lexicon không xử lý tiếng Việt | ❌ chỉ có mã chết |
| 7 | **Task / State** | `state_tracker.py` + `workflow_state.py` + `task_journal.py` UNWIRED (bảng `task_states` không tồn tại); trạng thái task thật nằm ở **tasks.db** (`durable_tasks`, probe self_study `_lesson_content` dòng 121-128) | memory layer không có view state task hiện hành; tâm mem-TaskState trùng lặp với tasks.db | ⚠️ dữ liệu có ở DB khác, chưa là "memory" |
| 8 | **Reflective / Metacognitive** | nguyên liệu có: `owner_questions` (0 rows), `memory_review_runs`, review session owner-gated (`cognition/memory_review_session.py:69-71`), self-study reports, KU CONCLUSION | vòng phản tư không chạy định kỳ; không có journal phản tư tổng hợp ("em đã học được gì trong tuần"); owner_questions trống = không bao giờ hỏi owner | ❌ vòng lặp chưa vận hành |

Ngoài 8 lớp: `DECISION` (enum) hiện **0 rows** — là content-kind (quyết định + lý do) chứ không phải lớp nhớ độc lập; `CANDIDATE` là **trạng thái lifecycle/quarantine**, không phải loại nhớ. Thiết kế V2 xử lý ở mục C.2.

### B.2. Gap embedding OFFLINE

1. **Không có semantic retrieval vector cho memory engine** — `search_memories` chỉ LIKE (A.5); khi kho tri thức lớn (5.051 semantic + 8.366 candidate) recall từ khóa sụt mạnh với paraphrase tiếng Việt.
2. **Timeout trễ đầu-cuối**: Ollama OFFLINE → mỗi lắng gọi embedding treo tới timeout (10s mặc định; probe thực tế 05/11 chờ >1s mới TimeoutError ở TCP) → làm chậm RAG/experience retrieval thay vì từ chối ngay.
3. **Không có "circuit breaker" chuẩn**: mỗi điểm gọi tự fallback một kiểu (fail-closed RAG, fail-open experience) nhưng không có trạng thái chia sẻ "EMBEDDING OFFLINE — bỏ qua thử trong N phút" → lặp lại chờ timeout vô ích.
4. **Dedup yếu đi**: self-study `_is_duplicate` và Deep Memory `compare_duplicates` dùng word-set containment/Jaccard — miss paraphrase → một phần nguyên nhân backlog 8.366 candidate (trùng nghĩa chưa trùng chữ).
5. Không ảnh hưởng: Deep Memory extraction (deterministic), episodes ghi, governance — các luồng này không gọi embedding.

### B.3. Gap kiến trúc khác

- **Mã chết nhiều store**: ExperienceStore, StateTracker, WorkflowState, TaskJournal, EmotionalMemory, QuarantineStore(V37.3) — có code + tests trên tmp_path nhưng không được wire vào server và không có bảng trong brain.db (A.3). Nguy cơ: ai đó "bật" chúng sau này sẽ tạo store cạnh tranh MemoryFacade, phá One Cognitive Core.
- **Semantic phân mảnh** (B.1 #2): 3 nơi lưu, chưa có quy định canonical source-of-truth per nội dung.
- **Backlog quarantine 8.366** — chỉ owner duyệt được; không được bulk-promote tự động (vi phạm Learning≠Deployment).
- **Reflection chưa chạy**: owner_questions=0 → vòng "hỏi owner khi không chắc" (thiết kế đúng) chưa được sử dụng.
- **Không có báo cáo coverage 8 lớp** — audit gap chỉ có thể trả lời bằng tay.

---

## C. KIẾN TRÚC ĐÍCH SUPER MEMORY V2

### C.1. Nguyên tắc thiết kế (bắt buộc)

1. **Overlay, không store mới tràn lan**: V2 là **lớp taxonomy + routing mỏng trên store hiện có** (memories/episodes/knowledge_units/semantic_memory/candidate_knowledge). Tối đa **2 bảng additive mới** trong toàn lộ trình (`emotional_signals`, `reflection_notes`) — mỗi bảng phải có owner duyệt trước khi tạo.
2. **Additive-only schema**: chỉ `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`; không ALTER, không DELETE, không đổi CHECK constraint có sẵn.
3. **Fail-closed nhận thức**: mặc định INFERENCE/QUARANTINED khi không chắc (kế thừa `classify_statement` `unified_memory.py:73-83`).
4. **Owner-gated promotion**: mọi đường INFERENCE/CANDIDATE → FACT/VERIFIED đi qua R4 verifier (`unified_memory.py:260-295`, `sqlite_store.py:160-192`).
5. **Append-only + supersede**: không xóa; versioning giữ lịch sử (chuẩn `supersede_memory`/`supersede_unit`).
6. **Redact bắt buộc** tại mọi điểm ghi (chuẩn `redact_text` đã có ở cả 2 store).
7. **Embedding là tăng tốc, không phải phụ thuộc**: mọi tính năng mới phải hoạt động đầy đủ khi EMBEDDING=OFFLINE với cờ trung thực.

### C.2. Định nghĩa 8 lớp + ánh xạ từ enum hiện có

**Quyết định thiết kế theo bằng chứng code (mục A.1):**
- `DECISION` **không** thành lớp thứ 9 — là **content-kind tag** phủ trên Episodic/Reflective (dữ liệu legacy giữ nguyên value trong DB, taxonomy map `DECISION → EPISODIC(kind=decision)`).
- `CANDIDATE` **không** phải lớp nhớ — là **trạng thái lifecycle** của item trong bất kỳ lớp nào (chuẩn `LifecycleStatus.QUARANTINED` + `FactLevel.QUARANTINED`).

| Lớp V2 | Nguồn dữ liệu (store thật) | Cách ghi mới | Đọc qua | Quyền ghi |
|---|---|---|---|---|
| **M1 EPISODIC** | `episodes` + `memories(memory_type=EPISODIC)` | giữ nguyên: chat turn, task result, session | MemoryFacade.search / add_episode | R1–R2 tự động (hệ thống quan sát) |
| **M2 SEMANTIC** | `semantic_memory` (canonical cho tri thức đã duyệt) + `knowledge_units` (cấu trúc SPO) + `memories(SEMANTIC)` | chỉ qua promotion owner-gated (đường D2/D3/D4) | MemoryFacade.search(fact_only) | **Owner + R4** |
| **M3 PROCEDURAL** | `memories(memory_type=PROCEDURAL)`; nguyên liệu từ KU `RULE/PROCESS` đã owner-review | đường mới: KU RULE/PROCESS status NEEDS_OWNER_REVIEW → owner duyệt → store PROCEDURAL + regression_passed | experience_retrieval | **Owner + regression** |
| **M4 PREFERENCE** | `memories(memory_type=PREFERENCE, USER_PROVIDED)` (canonical — không bảng mới) | chỉ owner teach (teach_pipeline); bổ sung: scope + expiry_check read-only + antonym-conflict check giữa preferences | facade API mới `search_preferences(scope)` | **Chỉ owner** |
| **M5 EXPERIENCE** | candidate lessons trong `memories` (tags `sprint11_lesson`, từ experience_consolidation) → promoted VERIFIED | giữ đường Sprint 11 hiện có; bổ sung view cấu trúc context→action→outcome từ episode metadata | experience_retrieval + facade | Task lifecycle (ghi candidate R2) + **Owner** (promote R4) |
| **M6 EMOTIONAL/SOCIAL** | bảng mới `emotional_signals` (additive, DESIGNED — chờ duyệt) | telemetry chat: sentiment/emotion theo V16 + **lexicon tiếng Việt bổ sung**; ghi ở trạng thái CANDIDATE (OBSERVED, không suy luận nội tâm owner) | facade API chỉ-đọc; **không** tự điều chỉnh tính cách | OFF mặc định; bật = owner quyết định |
| **M7 TASK/STATE** | **view read-only trên tasks.db `durable_tasks`** + `episodes(kind='task')`; KHÔNG tạo bảng task mới (tránh trùng tasks.db) | trạng thái thuộc tasks.db (nguồn đã LIVE); memory chỉ ánh xạ + snapshot OBSERVED khi task kết thúc | facade API `get_task_state(task_id)` | R1–R2 (hệ thống) |
| **M8 REFLECTIVE/METACOGNITIVE** | `owner_questions` + `memory_review_runs` + self-study cycle results; bảng mới `reflection_notes` (additive, DESIGNED — chờ duyệt) | review session owner-gated sinh note tổng hợp; mỗi note trỏ KU/episode nguồn | facade API `list_reflections()` | Owner review session + hệ thống (nháp CANDIDATE) |

### C.3. Thành phần kiến trúc đích

```
                        ┌────────────────────────────────────────────────┐
                        │            ONE COGNITIVE CORE (TONY)           │
                        │        đọc duy nhất qua MemoryFacade V2        │
                        └───────────────┬────────────────────────────────┘
                                        │ search(8 lớp) / add / stats
                     ┌──────────────────▼───────────────────┐
                     │  SuperMemoryRouter (mới, lớp mỏng)   │
                     │  - taxonomy map enum cũ → M1..M8     │
                     │  - fact_level + lifecycle giữ nguyên │
                     │  - KHÔNG giữ dữ liệu, KHÔNG store mới│
                     └───┬─────┬─────┬─────┬─────┬─────┬────┘
        ┌────────────────┘     │     │     │     │     └───────────────┐
        ▼                      ▼     ▼     ▼     ▼                     ▼
  MemoryStore(sqlite)   DeepMemoryStore  ExperienceStore   ContextStore  QuarantineStore
  episodes/memories/    5 bảng V9/V10    (candidate lessons  (session)     (facade view trên
  semantic_memory/      (canonical       trong memories —                  candidate_knowledge
  candidate_knowledge   structured)      KHÔNG bảng riêng)                 — không store cạnh tranh)
        ▲                      ▲                                  ▲
        │                      │                                  │
   [GHI R1–R2]           [GHI deterministic]                [GHI quarantine]
   teach (owner) → M4/M2  extract_from_chat_turns           self-study → candidate
   task lifecycle → M5    review/supersede (owner)          learning_daemon (đếm only)
   episodes → M1/M7       owner_questions → M8
   emotional_signals → M6 (DESIGNED, OFF mặc định)
   reflection_notes  → M8 (DESIGNED, chỉ trong review session)
```

- **SuperMemoryRouter** (`src/quan_ai_brain/memory/taxonomy.py` — dự kiến): enum `MemoryCategory` 8 giá trị M1–M8 + hàm `map_memory_record() / map_knowledge_unit() / map_episode()`; thuần hàm, không I/O.
- **Báo cáo coverage** (`tools/memory_taxonomy_report.py` — dự kiến): probe read-only brain.db + tasks.db → `reports/MEMORY_TAXONOMY_LATEST.md` (số lượng per lớp, số item quarantined, gap explicit fail-honest).
- **Embedding Health Gate** (`src/quan_ai_brain/cognition/embedding_health.py` — dự kiến): trạng thái dùng chung `ONLINE/OFFLINE+retry_after`, tái sử dụng `is_available()` ping 0.5s có sẵn; mọi caller tra gate TRƯỚC khi gọi embed → hết treo timeout lặp. Không đổi hành vi fail-open/fail-closed của caller hiện có.

### C.4. Schema additive dự kiến (chỉ khi owner duyệt, từng bảng một)

```sql
-- Bảng 1/2 (M6) — DESIGNED, mặc định KHÔNG ghi:
CREATE TABLE IF NOT EXISTS emotional_signals (
    id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL,            -- dashboard | netchat | voice
    sentiment TEXT NOT NULL,          -- positive|negative|neutral
    sentiment_score REAL NOT NULL,
    emotions_json TEXT NOT NULL DEFAULT '{}',
    dominant_emotion TEXT NOT NULL,
    intensity REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',  -- không bao giờ tự ACTIVE
    redacted_preview TEXT NOT NULL DEFAULT ''
);

-- Bảng 2/2 (M8) — DESIGNED, chỉ ghi trong review session owner-gated:
CREATE TABLE IF NOT EXISTS reflection_notes (
    note_id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    run_id TEXT,                       -- memory_review_runs.run_id
    period TEXT NOT NULL,              -- 2026-W45 ...
    summary TEXT NOT NULL,             -- đã redact
    lessons_json TEXT NOT NULL DEFAULT '[]',   -- ref KU/episode/task
    owner_ack TEXT NOT NULL DEFAULT '' -- ACK của anh sau khi đọc
);
```

Không bảng nào khác được tạo trong G2. Mọi nhu cầu "thêm một loại nhớ mới" phải trả lời: *lớp M1–M8 nào chưa chứa được nó?* trước khi đề xuất store mới.

---

## D. LUỒNG DỮ LIỆU + QUYỀN SỞ HỮU

### D.1. Năm đường ghi (tất cả đã kiểm chứng tồn tại ở mục A.4, V2 chỉ chuẩn hoá)

| Đường | Trigger | Đích lớp | Trạng thái ban đầu | Ai duyệt tiếp |
|---|---|---|---|---|
| **D1 Teach** | anh dạy trong chat (dashboard/NetChat) | M4 PREFERENCE / M2 SEMANTIC | USER_PROVIDED (fact ngay — nguồn sự thật tối cao) | không cần — chỉ owner dạy được |
| **D2 Task lifecycle** | execute_lifecycle COMPLETED/FAILED | M5 EXPERIENCE (candidate) + M1 episode | UNVERIFIED + QUARANTINED (tags `sprint11_lesson`) | Owner `promote_lesson` (R4) |
| **D3 Self-study** | chu kỳ StudyCycleEngine (chạy khi được gọi — không daemon mới) | M2 candidate | `candidate_knowledge.status='quarantined'` | Owner duyệt (R4 verifier, ledger 1-lần) |
| **D4 Chat-turn extraction** | Deep Memory review run | M2 structured (KU) | EXTRACTED (không LLM, confidence theo `_confidence` 4 thành phần — `deep_memory.py:158-164`) | Owner review → VERIFIED/supersede |
| **D5 Emotional telemetry** (DESIGNED, OFF) | chat telemetry nếu owner bật | M6 | CANDIDATE, không bao giờ tự ACTIVE | Owner bật/tắt + đọc |

### D.2. Chuỗi promotion duy nhất (không đường tắt)

```
[ghi] R1–R2 tự động ──► CANDIDATE/INFERENCE/EXTRACTED (quarantine · redact · provenance)
        │
        ▼  (duy nhất qua R4 — GovernanceApprovalVerifier FAIL-CLOSED)
[duyệt] Owner (Quanpt1) + approval evidence + regression_passed ──► VERIFIED/FACT
        │                                                        (M2/M3/M5 active)
        ▼  (sai → supersede, không xóa)
[thay thế] supersede_unit / supersede_memory ──► version+1, lịch sử giữ nguyên,
        quan hệ SUPERSEDES có căn cứ, audit trail qua memory_exchange_log
```

Cấm: bulk-promote; promote không evidence; sửa DB tay; daemon promote; LLM tự xác nhận LLM.

### D.3. Ma trận quyền theo R0–R5 (không đổi ma trận — chỉ ghi nhận áp dụng)

| Hành động memory | Mức R | Điều kiện |
|---|---|---|
| Ghi episode/telemetry/extraction (append-only) | R1–R2 | tự động, redact bắt buộc |
| Ghi emotional_signals, reflection_notes nháp | R2 (nếu được bật) | cấm mặc định, owner bật từng bảng |
| Promote candidate → semantic/procedural | **R4** | verifier + regression + audit trail |
| Supersede tri thức VERIFIED | **R4** | owner feedback qua review session |
| Xoá/chỉnh sửa dữ liệu memory trực tiếp | **R5** | hard-block, không có đường |
| Đọc memory (Core, báo cáo) | R0 | không secret, redact ở display |

### D.4. Ràng buộc "không memory cạnh tranh Core"

1. Core đọc/ghi **duy nhất qua MemoryFacade V2** — không module nào mở sqlite riêng vào brain.db để ghi (read-only probe tools được phép).
2. Không store mới cạnh tranh: M6/M8 là bảng additive dưới facade; M7 là **view** trên tasks.db — tasks.db vẫn là source-of-truth cho trạng thái task.
3. Learning daemon/self-study không tự nạp — đã kiểm chứng (A.4) và giữ nguyên.
4. SENTINEL/governance đọc audit — không đi qua memory layer; memory layer không ghi vào governance.db.

---

## E. KẾ HOẠCH SPRINT G2 — NHỎ NHẤT CÓ GIÁ TRỊ

Điều kiện vào: không phụ thuộc G1 (Pi5); chạy song song an toàn như đề xuất S-D (`V7_MASTER_BASELINE_AUDIT.md:108`). Mỗi WP là **file mới + test mới**, không sửa file hiện có (trừ wire điểm đọc nếu owner duyệt ở WP4+).

### WP1 — Taxonomy Adapter + Coverage Report (ưu tiên 1)
- **Nội dung:** `src/quan_ai_brain/memory/taxonomy.py` (map thuần M1–M8) + `tools/memory_taxonomy_report.py` (probe read-only brain.db, tasks.db) + `tests/test_memory_taxonomy.py`.
- **Nghiệm thu (test được):**
  1. Mapping đơn vị: 100% giá trị `MemoryType` + `KNOWLEDGE_TYPES` + episode kind map được vào đúng 1 lớp M1–M8 (test bảng case đầy đủ, kể cả giá trị lạ → fail-honest `UNMAPPED`).
  2. Report chạy THẬT trên brain.db (read-only) → sinh `reports/MEMORY_TAXONOMY_LATEST.md` với số liệu khớp probe A.3 (episodes 2.940, memories 2.397, semantic 5.051, candidate 8.366, KU 150).
  3. Report phải ghi rõ gap từng lớp (M3=2, M4=2, M6=0, M8=0) — không làm đẹp số.
  4. `pytest` mới pass + full suite không vỡ + `python tools/validate_and_report.py` exit 0 + HANDOFF cập nhật.
  5. 0 byte ghi vào DB production.
- **Evidence dự kiến:** UNIT_TESTED → **LIVE_VERIFIED** (chạy thật trên brain.db).

### WP2 — Preference & Experience read-API (ưu tiên 2)
- **Nội dung:** 2 hàm read-only trên MemoryFacade (file facade mới hoặc mở rộng taxonomy adapter — không sửa `unified_memory.py` nếu tránh được): `search_preferences(scope)` (M4: PREFERENCE + USER_PROVIDED + active + antonym-conflict check giữa các preference dùng `_antonym_flip` có sẵn) và `list_experience_lessons()` (M5: candidate + promoted, kèm trạng thái).
- **Nghiệm thu:** unit test với tmp DB (đặt 2 preference mâu thuẫn → API báo `conflict_with`); test trên DB thật read-only trả đúng 2/2 preference và N lessons; không ghi.
- **Evidence dự kiến:** UNIT_TESTED → LIVE_VERIFIED (đọc DB thật).

### WP3 — Embedding Health Gate (ưu tiên 3)
- **Nội dung:** `src/quan_ai_brain/cognition/embedding_health.py`: singleton trạng thái `EMBEDDING_ONLINE/OFFLINE` (ping 0.5s đã có), khi OFFLINE các caller skip ngay trong cửa sổ retry (mặc định 120s) thay vì chờ timeout từng lần; không thay đổi hành vi fail-open/fail-closed của RAG/experience_semantic; chỉ thêm gate + metric + test mock 2 nhánh.
- **Nghiệm thu:** (1) test offline-mock: lần gọi thứ 2 trong cửa sổ retry KHÔNG đụng network; (2) test online-mock: gate trong suốt; (3) đo được ở stats: `gate_skips`, `last_probe`; (4) full suite không vỡ.
- **Evidence dự kiến:** UNIT_TESTED (Ollama thật đang OFFLINE nên nhánh offline verify được LIVE; nhánh online SIMULATED-mock cho đến khi Ollama bật).

### WP4 — Thiết kế M6/M8 chờ duyệt (DESIGNED-ONLY)
- Nộp schema mục C.4 cho anh duyệt riêng. **Không tạo bảng, không wire** trong G2 lần này. Sau duyệt mới thành WP triển khai có test riêng.

### Không làm trong G2 (cấm rõ)
- Không tạo store/library memory mới ngoài mục C.4; không merge 3 nơi semantic (chỉ map + báo cáo); không bulk-promote 8.366 candidate; không bật daemon/scheduler mới; không sửa R0–R5; không migrate data DECISION/CANDIDATE; không commit (chờ anh duyệt).

**Định nghĩa "xong G2":** WP1+WP2+WP3 LIVE/UNIT_TESTED theo trên, HANDOFF + PROJECT_STATUS cập nhật đúng thang Evidence, taxonomy report là bằng chứng coverage 8 lớp đầu tiên của V7.

---

## F. RỦI RO + ROLLBACK

| # | Rủi ro | Khả năng/ảnh hưởng | Giảm thiểu | Rollback |
|---|---|---|---|---|
| 1 | Taxonomy map sai làm lệch số liệu báo cáo | TB / TB | bảng case test đầy đủ; đối chiếu số report vs SQL probe thủ công; fail-honest UNMAPPED | xóa 3 file WP1 (taxonomy, report, test) — DB không đụng |
| 2 | Read-API WP2 vô tình ghi DB | TB / CAO | hàm read-only thuần; test assert 0 ghi (count trước/sau); chạy trên bản sao trước | xóa file; brain.db nguyên vẹn (không có đường ghi) |
| 3 | Gate WP3 chặn nhầm khi Ollama online | TB / TB | cửa sổ retry ngắn (120s) + ping lại trước khi skip; kill-switch env `QUAN_AI_BRAIN_EMBEDDING_GATE_OFF` | đặt env var / xóa file |
| 4 | Ai đó hiểu nhầm "8 lớp = 8 store mới" → phá One Cognitive Core | TB / CAO | mục C.1/C.4 chốt cứng; WP4 DESIGNED-ONLY; review trước khi wire | không wire = không có gì để rollback |
| 5 | Backlog 8.366 candidate bị xử lý tắt | THẤP / CAO | cấm bulk-promote (D.2); duyệt theo lô nhỏ có audit trail như Q-4 (3.209 promoted có trail) | ledger 1-lần + audit_logs immutable |
| 6 | Ollama OFFLINE kéo dài làm mọi semantic feature suy giảm | CAO / TB | WP3 gate + keyword fallback đã có (A.5); ghi rõ cờ trung thực trong mọi trả lời | không cần — trạng thái hiện tại |
| 7 | Regression vỡ test cũ khi thêm file | THẤP / TB | chỉ file mới; `python tools/validate_and_report.py` bắt buộc trước khi kết sprint | `git checkout -- <file>` + xóa file mới; không commit |
| 8 | Backup lỗi trong thời gian sprint | THẤP / CAO | `tools/backup_database.py` LIVE_VERIFIED (V7 audit mục 2.1, Task Scheduler 2AM `StartWhenAvailable=True`); chạy backup thủ công trước khi chạy report lần đầu | restore drill có kiểm soát khi anh duyệt |

---

## PHỤ LỤC — BẰNG CHỨNG THU THẬP LÚC SOẠN (05/11/2026)

- Code đọc trực tiếp: `memory/models.py`, `memory/sqlite_store.py` (523 dòng), `memory/deep_memory.py` (934 dòng), `memory/unified_memory.py` (328 dòng), `memory/experience_store.py`, `memory/experience_consolidation.py`, `memory/experience_retrieval.py`, `memory/emotional_memory.py`, `memory/state_tracker.py`, `memory/quarantine_store.py`, `memory/knowledge_ingestion.py`, `memory/models_v31.py`, `memory/owner_feedback.py`, `memory/vector_store.py`, `cognition/self_study.py` (349 dòng), `cognition/teach_pipeline.py`, `cognition/embedding.py`, `llm/client.py`, `tools/learning_daemon.py` (395 dòng), `web/server.py` (điểm health 1288-1318, hook consolidation 3404-3420, lessons API 5338-5407).
- SQL probe trực tiếp `data/brain.db` (read-only): số liệu mục A.3; xác nhận không tồn tại các bảng `emotional_weights/emotion_events/experiences/experience_outcomes/task_states`.
- TCP probe: Ollama 11434 OFFLINE (TimeoutError); server 8766 LISTENING.
- Tài liệu đối chiếu: `reports/V7_MASTER_BASELINE_AUDIT.md`, `reports/SUPER_AI_MASTER_BASELINE.md`, `docs/ARCHITECTURE_GAP_ANALYSIS.md`, `docs/PROJECT_STATUS.md`, `reports/V8_FINAL_HANDOFF.md`.

*Hết tài liệu — DESIGNED, chờ Quanpt1 duyệt trước khi bất kỳ WP nào được triển khai.*
