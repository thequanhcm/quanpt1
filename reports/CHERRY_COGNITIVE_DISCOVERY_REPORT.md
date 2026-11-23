# CHERRY COGNITIVE DISCOVERY REPORT — PHASE 0

> **Ngày**: 14/11/2026 · **Người thực hiện**: TONY · **Status**: IN_PROGRESS → PENDING_OWNER_APPROVAL
> **Quy định tuân thủ**: KHÔNG sửa production code · KHÔNG kích hoạt self-learning · KHÔNG tạo module mới trước khi chứng minh thiếu
> **Phương pháp**: đọc source thật, đo schema DB thật, đo wiring thật (grep import), đo benchmark thật (brain.db) — mỗi kết luận ghi rõ [VERIFIED/INFERRED/UNKNOWN]

---

## 1. TÓM TẮT ĐIỀU HÀNH

QUAN AI BRAIN **đã có nền tảng nhận thức lớn hơn nhiều so với tên gọi**: 42 module cognition (15.854 dòng) + 40 module memory (16.685 dòng) + schema knowledge graph trong brain.db + benchmark suite CIEE 8 nhóm probe. Vấn đề KHÔNG phải là "thiếu module" — mà là **"nhiều module đã tồn tại nhưng không được wiring vào chat pipeline"** (causal, conflict, temporal, reflection, critical thinking đều có code + test + benchmark probe nhưng 0 hits trong server.py) + **32 module dead code** + **4 module causal trùng lặp chức năng**.

**Định hướng đề xuất**: wiring module có sẵn thay vì tạo mới (đúng nguyên tắc MASTER PROMPT §II "khảo sát kiến trúc hiện có, tái sử dụng, tránh engine trùng lặp").

---

## 2. KIẾN TRÚC HIỆN TẠI (bằng chứng thật)

### 2.1 Quy mô [VERIFIED]

| Thành phần | Số liệu | Bằng chứng |
|---|---|---|
| cognition/ | 42 file, 15.854 dòng | os.listdir + wc |
| memory/ | 40 file, 16.685 dòng | os.listdir + wc |
| server.py | 6.999 dòng (333.279 B) | read_file |
| brain.db | 105.148.416 B, 26 tables | sqlite3 |
| tasks.db | 11.890.688 B, 8 tables | sqlite3 |

### 2.2 Chat pipeline đang chạy thật (server.py `_handle_api_chat`) [VERIFIED]

```
INPUT
 → InputInjectionShield (12 hits) — BLOCK 70 / SANITIZE 40
 → 2.0 Teach detection (teach_pipeline.detect_teaching + persist_taught_memory) [L2085–2112]
 → 2. Memory retrieval (CognitiveRetriever, top_k=5, max_chars=6000)
 → 2.x Session history (get_recent_session_history, limit=3)
 → 2.5 Grounding facts (collect_grounding_facts: _tcp_alive + _pi5_edge_truth — PROBE THẬT)
 → 2.55 Avatar THINKING push
 → 2.6 External lookup (news/tra cứu ngoài, fail-closed)
 → role_orchestrator (classify_intent → 11 vai trò: coordinator/NOC/tech/data_analyst/
    researcher/documentation/language/instructor/executive_assistant/safety/coordinator)
 → LLM Router (catalog động TTL 300s, failover 3 lớp)
 → SSE / JSON response
```

### 2.3 Module được WIRED vào server [VERIFIED — grep đúng cú pháp `from quan_ai_brain.X.Y`]

**cognition WIRED (18)**: continuous_learning_engine, conversation_state, document_rag, experience_semantic, grounding_facts, improvement_report, memory_review_cycle, memory_review_session, teach_pipeline, role_orchestrator, self_care_engine, self_model_engine, self_qa, session_memory, skill_registry, task_pipeline, v7_skills + (1 tham chiếu lỗi `owner_teach` — xem §8 R1)

**memory WIRED (3)**: deep_memory, experience_consolidation, sqlite_store

**KHÔNG WIRED (58 module)**: xem §4 Gap Analysis — trong đó có 4 module causal, conflict_detector, temporal_memory, reflection, critical_thinker, logical_reasoner, counterfactual_memory, knowledge_graph...

### 2.4 Năng lực per-module tiêu biểu [VERIFIED — đọc code]

| Module | Dòng | Năng lực | Wiring |
|---|---|---|---|
| cognitive_state.py | 1.015 | Trạng thái nhận thức | qua planning/coordinator |
| deep_memory.py | 1.026 | Trí nhớ sâu | ✅ server |
| memory_review_session.py | 877 | Review trí nhớ | ✅ server |
| information_gap_analyzer.py | 856 | Phát hiện thiếu thông tin | qua cognitive_loop (dead) + governance/netchat_info_gap_adapter |
| temporal_memory.py | 697 | Trí nhớ thời gian | ❌ (chỉ memory_quality dùng — cũng dead) |
| conflict_detector.py | 687 | Phát hiện mâu thuẫn | ❌ (chỉ CIEE probe) |
| critical_thinker.py | 575 | Phản biện | ❌ dead |
| self_model_engine.py | 562 | Self-model | ✅ server |
| role_orchestrator.py | 554 | Intent 11 vai trò | ✅ server |
| causal_engine.py | 511 | Nhân quả | ❌ dead |
| logical_reasoner.py | 491 | Suy luận logic | ❌ dead |
| causal_chains.py (memory) | 901 | Chuỗi nhân quả | ❌ (chỉ CIEE group_b) |
| counterfactual_memory.py | 466 | Reasoning phản thực | ❌ dead |
| knowledge_graph.py | 407 | Đồ thị tri thức | ❌ dead |
| reflection.py | 317 | Tự phản ánh | ❌ (chỉ cognitive_loop — dead) |
| conversation_state.py | ~4.961 B | has_anaphora + build_contextualized_query (giải đại từ) | ✅ server |
| grounding_facts.py | probe thật | TCP + Pi5 truth → chặn claim sai về bản thân | ✅ server |

### 2.5 Nền tảng tri thức trong brain.db [VERIFIED — sqlite3 thật]

| Table | Rows | Ý nghĩa |
|---|---|---|
| semantic_memory | 2.594 | Tri thức đã duyệt |
| episodes | 3.469 | Nhật ký hội thoại |
| candidate_knowledge | 8.800 | Tri thức cách ly chờ duyệt |
| memories | 2.928 (13 cột có verification_status + confidence + version + superseded_by) | Trí nhớ đa loại có phiên bản |
| **knowledge_units** | 150 (148 EXTRACTED, 2 SUPERSEDED) | Đơn vị tri thức SPO (subject-predicate-object) + confidence + validity + contradiction_refs |
| **knowledge_relations** | 210 (RELATED_TO 173, REFINES 35, SUPERSEDES 2) | Quan hệ có basis + is_speculative |
| **knowledge_conflicts** | **0** | Conflict detector CHƯA TỪNG chạy trên production data |
| benchmark_runs | 10 (cpsl_mini_30, 12/11, 32 LLM calls/run) | Benchmark CIEE thật |
| kpi_snapshots | 113 | KPI đo thật |
| review_findings | 114 | Findings review trí nhớ |
| approval_cards_v2 | 1 | Governance card |

### 2.6 Benchmark CIEE [VERIFIED]

`tools/ciee/` — runner 307 dòng + 8 probe groups: problem_solving, reasoning, **epistemic (191 dòng)**, critical, **metacognition (76)**, adaptive, decision, learning. Suite `cpsl_mini_30` đã chạy 10 lần (mới nhất 12/11, 226–505s/run).

**KPI đo thật (12/11)** [VERIFIED — kpi_snapshots]:
- Causal Reasoning Accuracy: 1.0 (n=3) — sample quá nhỏ
- Evidence Coverage: **0.033 (n=30)** — RẤT THẤP: pipeline trả lời ít dựa bằng chứng
- False Confidence Rate: 0.5 (n=2) — nửa số case tự tin khi chưa đủ căn cứ
- Contradiction Detection: 1.0 (n=2) — nhỏ
- Appropriate Abstention: 1.0 (n=5)
- Self-Correction Success: 1.0 (n=3)
- Governance Compliance: 0.033 violations/case (n=30) ✅

---

## 3. ĐÁNH GIÁ 10 NĂNG LỰC THEO MASTER PROMPT §II

| # | Năng lực | Status | Bằng chứng |
|---|---|---|---|
| 1 | Contextual Understanding | **PARTIALLY_IMPLEMENTED** | conversation_state (anaphora + contextualized query) + session history ✅ wired; nhưng không có topic tracking / entity linking / context confidence |
| 2 | Semantic Understanding | **PARTIALLY_IMPLEMENTED** | classify_intent 11 vai trò ✅; KHÔNG có Intent Representation đầy đủ (subject/object/constraints/expected_outcome/missing_info) |
| 3 | World Model | **PARTIALLY_IMPLEMENTED** | knowledge_units 150 + relations 210 + 11 loại quan hệ chuẩn trong schema ✅; nhưng knowledge_graph.py DEAD — không có query runtime trong chat |
| 4 | Causal Understanding | **NOT WIRED (code có sẵn)** | 4 module (causal_engine 511 + causal_reasoning ×2 + causal_chains 901 = ~1.850 dòng) — 0 chạy trong chat; KPI 1.0 chỉ từ probe n=3 |
| 5 | Temporal Understanding | **NOT WIRED (schema có sẵn)** | temporal_memory 697 dòng + knowledge_units có valid_from/valid_until + episodes có timestamp — nhưng không wiring runtime |
| 6 | Epistemic Understanding | **PARTIALLY_IMPLEMENTED** | GroundingStatus chỉ có VERIFIED/INFERRED/UNVERIFIED (models.py) — THIẾU ASSUMED/UNKNOWN/CONFLICTED/STALE như 7-state chuẩn; grounding_facts probe thật ✅; CIEE epistemic probe 191 dòng |
| 7 | Self-Model | **IMPLEMENTED** | self_model_engine + system_inventory + capability_registry + grounding_facts tất cả WIRED ✅ — tốt nhất trong 10 năng lực |
| 8 | Human & Social Understanding | **PARTIALLY_IMPLEMENTED** | role_orchestrator + teach pipeline (owner authority) + DM 2-step token ✅; KHÔNG có speaker verification (Test F: TV/YouTube/replay "Cherry" → chưa phòng được) |
| 9 | Metacognition | **NOT WIRED (code có sẵn)** | reflection + critical_thinker + logical_reasoner + counterfactual_memory + self_qa(wired) — chỉ self_qa wired; CIEE metacognition probe có |
| 10 | Knowledge Integration | **PARTIALLY_IMPLEMENTED** | deep_memory + experience_semantic + sqlite_store ✅ wired; learning_daemon dùng knowledge_ingestion; nhưng conflict/duplicate/quarantine/promotion pipeline chưa chạy production (conflicts=0 rows) |

**Tổng**: 1 IMPLEMENTED (Self-Model) · 5 PARTIALLY · 3 NOT-WIRED-but-code-exists · 1 cần verify runtime (Human/Social speaker auth)

---

## 4. GAP ANALYSIS (đủ bằng chứng, không đoán)

### GAP-1 [VERIFIED] Nhiều engine nhận thức tồn tại nhưng không chạy trong chat
58/82 module cognition+memory không được server import; trong đó 32 module **hoàn toàn dead** (không ai import, kể cả tools/edge): causal_engine, critical_thinker, logical_reasoner, counterfactual_memory, knowledge_graph, knowledge_pipeline, duplicate_detector, memory_quality, lesson_learner, best_practices, unified_memory, state_tracker, system_state, task_journal, workflow_state, quarantine_store, promotion_policy, privacy_preserving, metrics_tracker, owner_feedback, multi_agent_memory, emotional_memory, action_logger, benchmark, experience_store, session_manager, context_retriever, context_store, taxonomy, causal_chains, cognitive_loop, self_study.

### GAP-2 [VERIFIED] Trùng lặp engine causal — vi phạm nguyên tắc "không tạo engine trùng lặp"
4 module cùng chủ đề nhân quả: `cognition/causal_engine.py` (511), `cognition/causal_reasoning.py`, `memory/causal_chains.py` (901, có test_v23 + CIEE group_b probe), `memory/causal_reasoning.py` (440, được causal_chains import). Cần chọn 1 chuẩn hóa, đọc-đį chỉ phương án trong Phase 2.

### GAP-3 [VERIFIED] Epistemic states thiếu 4/7 mức chuẩn
MASTER PROMPT yêu cầu KNOW/INFERRED/ASSUMED/UNKNOWN/CONFLICTED/STALE/UNVERIFIED. Code hiện chỉ có VERIFIED/INFERRED/UNVERIFIED (cognition/models.py GroundingStatus). STALE đặc biệt quan trọng cho Test C (Stale Knowledge).

### GAP-4 [VERIFIED] Conflict detection chưa chạy production
knowledge_conflicts = 0 rows dù conflict_detector.py 687 dòng + test tồn tại. Hai nguồn mâu thuẫn chưa từng được ghi nhận trong DB.

### GAP-5 [VERIFIED] Evidence Coverage 0.033 (n=30)
Trả lời của Cherry hiện gần như không gắn bằng chứng truy xuất được — đối chiếu trực tiếp với triết lý "VERIFY BEFORE BELIEVING".

### GAP-6 [VERIFIED] Speaker verification không tồn tại
wake_word_service.py (15.990 B): 0 hits "speaker/verify/authentic/whitelist/replay". netchat responder có token confirm nhưng không có xác thực giọng nói. Test F (TV/YouTube có từ "Cherry") hiện chưa được phòng — CẦN BỔ SUNG.

### GAP-7 [VERIFIED] Intent Representation thiếu cấu trúc
Chỉ có intent label (11 vai trò), không có {Subject, Object, Action, Constraints, Expected Outcome, Priority, Time Context, Missing Information}.

### GAP-8 [VERIFIED] Bug thật — dead import trong nhánh SSE
server.py L2668: `from quan_ai_brain.cognition.owner_teach import detect_teaching` — **file không tồn tại** (teach logic thật ở teach_pipeline.py). Except nuốt im lặng → nhánh SSE stream mất teach detection âm thầm. (R1 — chờ duyệt fix trong sprint sau, KHÔNG sửa trong Phase 0.)

### GAP-9 [INFERRED] Context confidence chưa có
conversation_state xử lý anaphora nhưng không xuất Context Confidence — MASTER PROMPT §II.1 yêu cầu "Context Model + Context Confidence".

### GAP-10 [UNKNOWN] Adaptive Cognitive Routing chưa đo được
Không có bằng chứng chọn pipeline theo độ phức tạp câu hỏi (đơn giản vs cần ngữ cảnh vs rủi ro cao). Có v7_skills + role_orchestrator là điểm tựa, cần khảo sát sâu hơn ở Phase 1.

---

## 5. DEPENDENCY MAP (đề xuất)

```
                    ┌──────────────────────────────────────────┐
                    │            COGNITIVE LOOP (đề xuất)      │
                    │  perceive → understand → reason → verify │
                    │  → estimate uncertainty → decide → act   │
                    │  → observe → reflect → update            │
                    └───────┬──────────────────────────────────┘
                            │
   ┌────────────────────────┼─────────────────────────────┐
   │                        │                             │
[ĐÃ WIRE — giữ nguyên]  [WIRE BỔ SUNG Phase 1]   [CHUẨN HÓA Phase 2+]
   │                        │                             │
role_orchestrator      + conflict_detector          4 causal → chọn 1
shield                 + temporal_memory             (khuyến nghị:
teach_pipeline         + knowledge_graph (query)     memory/causal_chains
grounding_facts        + epistemic 7-state mở rộng   vì có test + CIEE
self_model_engine      + Intent Representation       probe + 901 dòng)
conversation_state     + evidence attach vào reply
session_memory         + speaker verification (Phase 4)
deep_memory / retrieval
```

**Nguyên tắc**: KHÔNG tạo engine mới; wiring có chọn lọc + chuẩn hóa trùng lặp + mở rộng enum.

---

## 6. DATA FLOW (hiện trạng, bằng chứng L2085–2900 server.py)

```
User input (chat/voice/DM)
  → InputInjectionShield (BLOCK≥70 / SANITIZE≥40)
  → teach_pipeline.detect_teaching → persist (semantic, USER_PROVIDED)
  → CognitiveRetriever.retrieve (top_k=5, max_chars=6000, DB=brain.db)
  → SessionMemoryManager.get_recent_session_history (limit=3)
  → PromptContextBuilder.build (system_instructions + memories + history)
  → collect_grounding_facts → render block (probe TCP + Pi5 truth)
  → [optional] external_lookup (news, fail-closed)
  → role_orchestrator.process (classify_intent → role handler)
  → LLM Router (GLM-5.3-Flash mặc định; catalog TTL 300s; failover cloud→cloud→Ollama)
  → Response + provenance + elapsed_ms
Background: learning_daemon (episodes → candidate_knowledge quarantined → owner review)
            memory_review_cycle/session (review_findings 114 rows)
            backup 2AM · watchdog · audit log
```

**Điểm mù hiện tại**: giữa retrieval và LLM KHÔNG có bước verify/conflict-check/temporal-check/epistemic-tag trên memories được retrieve — đây là chỗ cắm Cognitive Loop (đề xuất, không phá pipeline reply-first).

---

## 7. COGNITIVE FLOW ĐỀ XUẤT (tối thiểu can thiệp)

```
RETRIEVED memories
  → [MỚI] MemoryHealthCheck: STALE check (created_at + validity) · conflict check
          (conflict_detector) · provenance (provenance_tracker) · epistemic tag
  → [MỚI] Evidence Block: gắn evidence_refs vào context → tăng Evidence Coverage
  → LLM
  → [MỚI] Post-check (metacognition lite): claim vs evidence mismatch → flag
```

Ước lượng latency thêm: <50ms (đọc DB local + regex/hash) — không phá reply-first 3–9ms hiện tại. [INFERRED — phải đo khi Phase 1]

---

## 8. RỦI RO

| ID | Rủi ro | Loại | Mitigation |
|---|---|---|---|
| R1 | server.py L2668 dead import `owner_teach` — nhánh SSE mất teach detection silent | BUG (VERIFIED) | Sprint riêng: đổi thành teach_pipeline + test |
| R2 | Memory contamination: audio TV/YouTube "Cherry" chưa có speaker verification | SECURITY GAP (VERIFIED) | Phase 4 — speaker verification + nguồn hợp lệ whitelist; TRƯỚC ĐÓ: không auto-persist bất kỳ gì từ voice vào semantic_memory |
| R3 | 4 causal engines trùng lặp → dual-maintenance, benchmark khó so sánh | TECH DEBT (VERIFIED) | Phase 2: chọn 1, cách ly 3 còn lại (quarantine, không xóa) |
| R4 | Evidence Coverage 0.033 — trả lời thiếu bằng chứng | QUALITY (VERIFIED) | Phase 1: Evidence Block |
| R5 | False Confidence 0.5 (n=2) — tự tin thiếu căn cứ | QUALITY (VERIFIED, sample nhỏ) | Phase 3: epistemic 7-state + abstention |
| R6 | Wiring thêm module có thể làm chậm chat | PERFORMANCE (INFERRED) | đo trước–sau; gate <50ms; adaptive routing |
| R7 | knowledge_conflicts=0 → chưa từng phát hiện mâu thuẫn thật | VERIFICATION GAP (VERIFIED) | Phase 1: chạy conflict detector trên 2.594 semantic_memory (zone B — sandbox trước) |
| R8 | 8.800 candidate_knowledge quarantined — review backlog | GOVERNANCE (VERIFIED) | đã có memory_review infrastructure; trình owner backlog review |

---

## 9. LỘ TRÌNH ĐỀ XUẤT (Phase 1–8, mỗi phase 1 sprint + owner approval)

| Phase | Nội dung | Tái sử dụng | File dự kiến thay đổi |
|---|---|---|---|
| 1 | Context & Semantic: Intent Representation + Context Confidence + Evidence Block | conversation_state, retrieval, information_gap_analyzer | server.py, cognition/models.py, mới cognition/intent_representation.py |
| 2 | World & Causal: chuẩn hóa 4 causal → 1, wiring knowledge_graph query + conflict_detector sandbox | causal_chains, knowledge_graph, conflict_detector | server.py, memory/*, cognition/* |
| 3 | Epistemic & Temporal: 7-state + STALE check + abstention policy | grounding_facts, temporal_memory, CIEE epistemic probe | cognition/models.py, server.py |
| 4 | Human & Social: speaker verification + nguồn hợp lệ (Test F) | wake_word_service, netchat responder | edge_client/wake_word_service.py, tools/netchat_auto_responder.py |
| 5 | Self-Model nâng cấp: đo Self-Model Accuracy (Test G) định kỳ | self_model_engine, system_inventory | tools/ciee/probes/ |
| 6 | Metacognition: wiring critical_thinker + reflection vào post-check | critical_thinker, reflection, self_qa | server.py, cognition/* |
| 7 | Knowledge Integration: duplicate/conflict/promotion pipeline chạy production | conflict_detector, duplicate_detector, promotion_policy | memory/*, tools/learning_daemon.py |
| 8 | Benchmark & Audit: mở rộng CIEE 12 test A–J của MASTER PROMPT, independent audit | tools/ciee | tools/ciee/probes/, reports/ |

**Ưu tiên Phase 1 trước** vì: (a) mở khóa Evidence Coverage (KPI đang 0.033); (b) không đụng vùng nhạy cảm; (c) nền cho mọi phase sau.

---

## 10. KẾ HOẠNH KIỂM THỬ

1. **Unit**: mỗi wiring 1 test pytest (mock 100% DB/LLM theo policy)
2. **Regression**: pytest focused hiện có (184 baseline) + test CIEE probes
3. **Benchmark**: cpsl_mini_30 trước/sau mỗi phase (so sánh KPI: Evidence Coverage, False Confidence, Causal Accuracy, n phải ≥10)
4. **Test A–J MASTER PROMPT**: chuyển thành CIEE probe group mới (group_i_cross_tests) — Test F (contamination) bắt buộc trước khi mở voice persist
5. **E2E sống**: health 200 + reply-first không thoái lùi (>20ms → cảnh báo)

## 11. KẾ HOẠCH ROLLBACK

- Mỗi phase 1 branch riêng `feature/cognitive-phase<N>-*` + flag toggle
- Rollback = revert commit + restart server (watchdog) — không đụng DB
- DB migration (nếu có): chỉ ADD column/table, không drop; backup brain.db trước (đã có backup 2AM)

---

## 12. XÁC NHẬN TUÂN THỦ PHASE 0

- ✅ Không sửa production code (chỉ đọc + đo)
- ✅ Không kích hoạt self-learning/autonomous upgrade
- ✅ Không tạo module mới
- ✅ Mọi kết luận có bằng chứng: source line, schema, số đo
- ✅ Phân loại VERIFIED/INFERRED/UNKNOWN dùng nhất quán
- ⏸ **DỪNG — chờ Owner Authority (Quanpt1) phê duyệt Phase 1**

---

*Báo cáo bởi TONY lúc 14/11/2026. Số liệu đo trực tiếp từ E:/BRAIN lúc ~01:00 (15/11 UTC+7). Không có mục nào tuyên bố hoàn thành nếu chưa có bằng chứng kiểm chứng được.*
