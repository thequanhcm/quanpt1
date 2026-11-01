# M2 — MA TRẬN TÍCH HỢP 5 ENGINE NHẬN THỨC

**Dự án:** QUAN AI BRAIN — Workspace: `D:\AI\AI Quanpt1 2026\BRAIN`
**Ngày lập:** 01/11/2026 · **Phạm vi:** Chỉ đọc code + viết báo cáo. KHÔNG sửa code, KHÔNG git, KHÔNG restart server.
**Phương pháp:** Đọc trực tiếp source bằng `read_file` có line numbers; đối chiếu test trong `tests/`; truy vết caller bằng grep trên `src/`.

---

## 1. Bảng kiểm kê 5 engine

### 1.1. CognitiveLoop — `src/quan_ai_brain/cognition/cognitive_loop.py` (459 LOC)

| Mục | Chi tiết |
|---|---|
| **Class chính** | `CognitiveLoop` (cognitive_loop.py:98); dataclass `TaskSpec` (:44); exception `CognitiveLoopError` (:40) |
| **Public API** | `submit_task(spec, plan_builder=None, autonomy_level=LEVEL_A, gap_check=True)` (:130); `tick(task_id, dry_run=True)` (:275); `approve(task_id, decision, guidance="")` (:305); `cancel(task_id, reason)` (:348); `reflect(task_id)` (:359); `promote_lessons(task_id)` (:372); `resume_incomplete()` (:377); `expire_stale_pending(ttl_hours=None)` (:389); factory `build_default_cognitive_loop(workspace, db_path)` (:449) |
| **Input** | `TaskSpec` (goal, context_refs, acceptance_criteria, risk_hint 0–5, deadline_utc, priority, metadata) — :52-58; bắt buộc `acceptance_criteria` (fail-closed, :64-67) |
| **Output** | dict snapshot: `task_id / status / lifecycle_state / risk_level / checkpoint / outcome` (:436-446); khi thiếu thông tin → `NOT_SUBMITTED` + danh sách câu hỏi gap (:213-226) |
| **Dependencies** | `InformationGapAnalyzer`, `ReflectionLoop`, `AuditLogger`, `PlanOrchestrator`, `DurableTaskRegistry`, `TaskStatus/AutonomyLevel` (import :26-37); import lười `planning.models.TaskPlan/TaskStep` (:238) |
| **State lưu ở đâu** | Task state trong `data/tasks.db` qua `DurableTaskRegistry` (docstring :15-16); audit vào `logs/audit.jsonl` qua `AuditLogger` (:124) |
| **Events phát** | Audit event (JSONL, fire-and-forget): `cognitive_loop.task_rejected` (:158), `info_gap_blocked` (:205), `task_received` (:228), `task_registered` (:260), `executing` (:291), `approval_resolved` (:338), `task_cancelled` (:350), `reflected` (:362), `recovery` (:380), `pending_age_out` (:406) |
| **Events nhận** | Không — không có subscriber nào |
| **Error handling** | Ném `CognitiveLoopError` khi spec sai (:157-159); `KeyError` khi không tìm thấy task (:283, :313); gap_check chặn trước khi đăng ký (:204-226) |
| **Test coverage** | `tests/test_cognitive_loop.py` (import :20-29); `tests/test_v3_sprint3_information_gap.py` |
| **Runtime status** | **ORPHAN** — grep toàn `src/quan_ai_brain` không thấy file nào import `CognitiveLoop` ngoài chính nó; `web/server.py` và `cognition/autonomous_mind.py` đều không gọi. Chỉ test sử dụng. |

Vòng đời chuẩn hóa: `LIFECYCLE_STATES` 10 trạng thái RECEIVED → CONTEXT_BUILDING → UNDERSTANDING → PLANNING → RISK_ASSESSMENT → WAITING_APPROVAL → EXECUTING → VERIFYING → REFLECTING → LEARNING_CANDIDATE (:74-85). TTL backlog 48h (:95).

### 1.2. CriticalThinker — `src/quan_ai_brain/cognition/critical_thinker.py` (574 LOC)

| Mục | Chi tiết |
|---|---|
| **Class chính** | `CriticalThinker` (:107); enum `BiasType` (:35), `EvidenceQuality` (:49); dataclass `ArgumentStructure` (:60), `BiasAnalysis` (:71), `EvidenceEvaluation` (:81), `ArgumentAnalysis` (:94) |
| **Public API** | `detect_biases(text) -> BiasAnalysis` (:164); `identify_fallacies(text) -> List[str]` (:256); `evaluate_evidence(claim, evidence_list) -> EvidenceEvaluation` (:277); `analyze_argument(argument) -> ArgumentAnalysis` (:417); 3 hàm module-level tiện ích `detect_biases/evaluate_claim/analyze_argument` (:560-575) |
| **Input** | Chuỗi text tiếng Việt; danh sách evidence dạng `List[str]` |
| **Output** | Dataclass phân tích (bias, fallacy, quality_score 0.0–1.0, strength, recommendations) |
| **Dependencies** | Chỉ stdlib (`re`, `dataclasses`, `enum`, `collections`) — import :26-32. **Không phụ thuộc module nào của hệ.** |
| **State lưu ở đâu** | Chỉ in-memory: `self.knowledge_base` (:153), `self.analysis_history` (:154). **Không có persistence nào.** |
| **Events phát/nhận** | Không có |
| **Error handling** | Không có try/except nào trong file; phụ thuộc hoàn toàn caller. Lưu ý phụ: `print()` khởi tạo (:156-160) — không phù hợp chạy trong server |
| **Test coverage** | `tests/test_v39_reasoning_engine.py` (import :30-31, class `TestCriticalThinker` :290) |
| **Runtime status** | **ORPHAN** — không file runtime nào import (grep toàn src chỉ thấy file gốc + test). |

Cơ chế: regex pattern tiếng Việt cho bias (:120-138) và 7 loại fallacy (:141-149); chấm evidence bằng từ khóa mạnh/yếu + overlap với claim (:346-373).

### 1.3. SelfModelEngine — `src/quan_ai_brain/cognition/self_model_engine.py` (506 LOC)

| Mục | Chi tiết |
|---|---|
| **Class chính** | `SelfModelEngine` (:110); dataclass `SelfModel` (:33) |
| **Public API** | `generate_self_model() -> SelfModel` (:118); `get_self_model_json()` (:235); `get_self_model_summary()` (:240); `answer_state_questions() -> dict` (:253) — trả lời 12 câu tự-nhận- thức bằng live probe; `_diff_vs_last_snapshot(...)` (:456) |
| **Input** | Không tham số đầu vào chính; tự scan workspace |
| **Output** | `SelfModel` (identity, deployment, active_modules, knowledge_sources, memory_types, ai_models, limitations, verified/unverified capabilities, permissions, health_status, priorities) :36-50; dict 12 câu trả lời `q1..q12` (:278-454) |
| **Dependencies** | `CapabilityRegistry`, `SystemInventory` (:29-30); bên trong probe: `LLMProvider` (:330), `sqlite3` mở `data/tasks.db` (:346-355), `data/brain.db` (:377-395), `data/consultations.db` (:413), HTTP `127.0.0.1:8766/api/executive/edge/status` (:308), đếm dòng `logs/audit.jsonl` (:439-441) |
| **State lưu ở đâu** | Snapshot JSON `data/self_model_last.json` (hằng `_LAST_SNAPSHOT` :251; ghi :498-506) |
| **DB bảng đọc** | `durable_tasks` (:350-356), `semantic_memory` + `candidate_knowledge` (:381-394 — tự CREATE nếu thiếu), `consultation_tickets` (:415-417) |
| **Events phát/nhận** | Không |
| **Error handling** | Mỗi probe bọc try/except riêng, trả `verification_status: UNKNOWN + error` thay vì crash (:339-343, :371-373, :407-409, :424-425, :448-449); mkdir data/logs bỏ qua lỗi (:261-265) |
| **Test coverage** | `tests/test_self_awareness.py` (import :15, test generate/summary :64-96); `tests/test_sprint_cd_quality_promotion.py` (probes :227-230) |
| **Runtime status** | **ORPHAN** — không được import bởi `web/server.py` hay module runtime nào trong `src/` (grep chỉ thấy file gốc + 2 file test). |

### 1.4. SelfCareEngine — `src/quan_ai_brain/cognition/self_care_engine.py` (350 LOC)

*(Tìm bằng `search_files(pattern='self_care', path='src')` → đúng file `self_care_engine.py`)*

| Mục | Chi tiết |
|---|---|
| **Class chính** | `SelfCareEngine` (:101); enum `HealthLevel` (:32), `ActionType` (:41); dataclass `HealthCheck` (:51), `Alert` (:67), `Incident` (:85) |
| **Public API** | `check_ollama_health()` (:123); `check_web_health(port=8765)` (:168); `check_pi5_connection(pi_ip, port=8768)` (:209); `run_all_health_checks()` (:238); `generate_alerts(checks=None)` (:249); `create_incident(alert, root_cause=None)` (:298); `resolve_incident(incident_id, resolution, lessons=None)` (:311); `get_health_summary()` (:322); `get_active_alerts(limit=20)` (:345); `get_incidents(limit=20)` (:349) |
| **Input** | Không tham số (probe TCP localhost:11434 Ollama :131, :8765/:8766 web :175, Pi5 192.168.1.21:8768 :215) |
| **Output** | `HealthCheck` / `Alert` / `Incident` dataclass + dict summary (:333-343) |
| **Dependencies** | Chỉ stdlib (`socket`, `time`, `logging`) — import :21-27. Không nối governance, không nối memory |
| **State lưu ở đâu** | **In-memory thôi**: 3 list `_health_checks/_alerts/_incidents` (:106-108). Restart process = mất sạch lịch sử sự cố |
| **Events phát/nhận** | Không. Chỉ `logger.info/warning` (:281, :286, :291, :296) |
| **Error handling** | try/except `(socket.timeout, socket.error, OSError)` từng probe (:156, :197, :226) → trả `HealthLevel.DOWN` thay vì raise |
| **Test coverage** | `tests/test_self_care.py` (import :14, 11 test :23-186) |
| **Runtime status** | **ORPHAN** — grep toàn `src/` không thấy caller nào; không endpoint `api/self*` trong `web/server.py`. |

⚠️ **Rủi ro an toàn trong code thật:** auto-recovery đang ở dạng **mô phỏng** (`"Attempted Ollama restart (simulated)"` :279; web :284; Pi5 :289) — chưa có executor thật, đúng nguyên tắc fail-safe, nhưng `auto_recovered=True` bị set ngay cả khi chỉ mô phỏng (:280, :285, :290) → dễ gây hiểu nhầm báo cáo "đã phục hồi". Ngưỡng cảnh báo khai tại :109-115; chính sách recovery khai tại :116-121 nhưng chưa gọi code thật.

### 1.5. ContinuousLearningEngine — `src/quan_ai_brain/cognition/continuous_learning_engine.py` (654 LOC)

| Mục | Chi tiết |
|---|---|
| **Class chính** | `ContinuousLearningEngine` (:120); enum `LearningType` A–E (:40), `LearningMode` A–G (:49), `LearningStatus` (:60); dataclass `LearningReport` (:79), `LearningEvaluation` (:100) |
| **Public API** | `learn_type_a_knowledge(content, source_type, source_ref, tags=None)` (:144); `learn_type_b_experience(task_goal, task_result, success, errors=None, root_cause=None, lesson_learned=None)` (:215); `learn_type_c_usage(query, retrieved_knowledge, success, feedback=None)` (:279); `learn_type_d_sandbox(hypothesis, experiment_design, baseline_metrics, experiment_results, conclusion)` (:337); `learn_type_e_system(change_description, diff, test_results, risk_level, rollback_plan)` (:412); `evaluate_learning(...6 tham số baseline/post...)` (:466); `get_reports(learning_type=None, limit=50)` (:503); `get_pending_approvals()` (:510); `get_evaluation_summary()` (:514); CLO V1: `start_continuous_learning(objectives, source_manifest)` (:532), `start_session_with_mode(...)` (:536), `end_session(session_id, evaluation_result, unresolved_questions, next_plan)` (:560), `pause/resume/stop_continuous_learning` (:604/:615/:627), `get_learning_status()` (:638) |
| **Input** | Nội dung tri thức / kết quả nhiệm vụ / phản hồi truy xuất / chỉ số thí nghiệm / đề xuất sửa hệ thống |
| **Output** | `LearningReport` (status lifecycle DETECTED→…→COMPLETED/FAILED/REJECTED :60-75); `LearningEvaluation` (precision/recall/MRR improvement, passed :466-501) |
| **Dependencies** | `KnowledgeIngestionEngine` + `KnowledgeSource` từ `memory/knowledge_ingestion.py` (:25-31); `MemoryStore` từ `memory/sqlite_store.py` (:32); `LearningSessionManager` từ `cognition/learning_session.py` (:33-37) |
| **State lưu ở đâu** | (1) `data/brain.db` — bảng `candidate_knowledge` (quarantine) qua `knowledge_engine.ingest` (gọi :176-181, :250-255, :308-313, :375-380, :447-452; bảng khai tại sqlite_store.py:60-68); (2) `data/learning_checkpoints.db` — bảng `learning_sessions` + `learning_state` (tạo tại learning_session.py:102, :123; đường dẫn setup :139-142); (3) `_reports`/`_evaluations` **chỉ in-memory** (:133-134) |
| **Events phát/nhận** | Không có event; proposal xung đột lưu trong `LearningReport.proposal` (:197-203, :262-266, :319-324, :394-399, :432-440) |
| **Error handling** | Mỗi `learn_type_*` bọc try/except → `status=FAILED + notes=str(e)` (:208-210, :272-274, :330-332, :405-407, :459-461); `RuntimeError` khi CLO đang chạy (:542); `ValueError` session không tồn tại (:565) |
| **Test coverage** | `tests/test_continuous_learning.py` (import :15, 11 test :24-242); `tests/test_clo_v1_continuous_session.py` (import :16-25, test session handoff :53+) |
| **Runtime status** | **INTEGRATED (duy nhất trong 5 engine)** — `web/server.py`: (a) chat task creation kích hoạt CLO session end/start (:1669-1673 và khối xử lý sau đó); (b) 6 endpoint `/api/learning/status|start|stop|pause|resume` + POST `/api/learning` (route :564-577, :792-793; handler `_handle_api_learning_status` :5404-5415 và 5 handler còn lại :5417-5486) |

---

## 2. Đọc nhanh 3 module nền để vẽ map tích hợp

### 2.1. Governance — `src/quan_ai_brain/governance/`

| File | LOC | Nội dung cốt lõi |
|---|---|---|
| `policy.py` | 67 | `RiskLevel` R0–R5 (:8-14); `PolicyEngine.authorize(ActionRequest) -> PolicyDecision` (:49-67): **R5 hard-block** (:52), R4 `APPROVAL_REQUIRED` (:54), R3 allow-with-notice (:56), R2 bắt buộc target_path trong workspace qua `PathGuard` (:58-66) |
| `state_store.py` | 859 | `GovernanceStateStore` (:70) — SQLite WAL, fail-closed khi corrupt (:135-138); bảng `emergency_states` (:151), **`governance_events`** (:231-241: event_id, event_type, timestamp_utc, entity_type, entity_id, details_json, risk_level, outcome), replay nonces |
| `consultation_inbox.py` | 344 | `ConsultationStore` (:147) — `consultations.db`; `create_ticket` (:224), `list_tickets` (:233), `respond_ticket` (:300), `count_pending` (:333) |
| `approval_cards.py` | 346 | `ApprovalCardStore` (:75) — thẻ phê duyệt TTL trong governance.db |
| `netchat_approval_adapter.py` | 428 | `NetChatApprovalAdapter` (:53) — nhận tin nhắn owner qua NetChat, parse phê duyệt (:103), `_do_approve` (:205) |

### 2.2. Orchestration — `src/quan_ai_brain/orchestration/task_registry.py` (438 LOC)

`DurableTaskRegistry` (:30) — SQLite `data/tasks.db`; bảng `durable_tasks` (:56) + `durable_task_steps` (:87); API: `register_task` (:110), `get_task` (:184), `get_by_idempotency_key` (:190 — **idempotency có sẵn ở tầng task**), `list_tasks` (:196), `update_task_status` (:212), `recover_in_flight_tasks` (:267), `save_step` (:321), `update_step_status` (:381).

`PlanOrchestrator` (`plan_orchestrator.py`): `submit_plan` (:63), `execute_lifecycle` (:175) — **R5 hard-block tại :249**, tự tạo consultation ticket khi cần phê duyệt (:270-277), `cancel_task` (:364), `recover_tasks` (:386), wiring `ConsultationStore` tại :61.

### 2.3. Memory — `src/quan_ai_brain/memory/sqlite_store.py` (523 LOC)

`MemoryStore` (:17) — SQLite `data/brain.db`; 4 bảng: `episodes` (:50-57), `candidate_knowledge` (:60-68), `semantic_memory` (:70-76, CHECK regression_passed=1), `memories` (:78-96). API: `add_episode` (:107), `add_candidate` (:147), `promote_candidate` (:160), `store_memory` (:204), `search_memories` (:274), `supersede_memory` (:327), `record_task_result` (:414), `quarantine_candidate_knowledge` (:443), `trace_source` (:480).

---

## 3. Ma trận tích hợp — 8 năng lực của vòng nhận thức

Ký hiệu: **ĐÃ CÓ** = code hiện hữu đạt chức năng; **CÓ-NHƯNG** = có code nhưng chưa nối vào vòng chung; **THIẾU** = chưa có; *(sandbox)* = chỉ chế độ dry-run.

| # | Năng lực | Engine/module đảm nhiệm | Bằng chứng path:line | Trạng thái |
|---|---|---|---|---|
| 1 | **Nhận yêu cầu** (receive) | `CognitiveLoop.submit_task` + validation fail-closed | cognitive_loop.py:130-159 | **CÓ-NHƯNG** — API chuẩn tồn tại nhưng loop là ORPHAN; luồng chat thật đi qua `web/server.py` tự phân rã task (:1660-1668), không qua CognitiveLoop |
| 2 | **Phân tích** (understand/reason) | `InformationGapAnalyzer` (được loop gọi) ; `CriticalThinker` (độc lập) | cognitive_loop.py:184-226; critical_thinker.py:417 | **CÓ-NHƯNG** — gap-analyzer đã chạy trong submit_task; CriticalThinker có đủ bias/fallacy/evidence nhưng **không ai gọi** trong runtime |
| 3 | **Truy xuất trí nhớ** (remember) | `MemoryStore.search_memories/store_memory/add_episode` | sqlite_store.py:274, :204, :107 | **ĐÃ CÓ** ở tầng memory; nhưng **THIẾU** mối nối: CognitiveLoop không đọc ghi MemoryStore trực tiếp (chỉ qua ReflectionLoop.persist_lessons → add_episode, reflection.py:141-155) |
| 4 | **Lập kế hoạch** (plan) | `PlanOrchestrator.submit_plan` + `TaskPlan/TaskStep` | plan_orchestrator.py:63; task_registry.py:110 | **ĐÃ CÓ** — placeholder plan an toàn khi không có plan_builder (cognitive_loop.py:237-258) |
| 5 | **Kiểm tra quyền** (govern) | `PolicyEngine.authorize` + ConsultationStore + ApprovalCards + GovernanceStateStore | policy.py:49-67; plan_orchestrator.py:249, :270-277; state_store.py:70 | **ĐÃ CÓ** — R5 block, R4 approval, ticket tạo tự động trong execute_lifecycle |
| 6 | **Thực hiện** (execute) | `PlanOrchestrator.execute_lifecycle` (dry_run=True mặc định) | plan_orchestrator.py:175; cognitive_loop.py:275-303 | **ĐÃ CÓ (sandbox)** — executor thật ngoài sandbox **THIẾU đúng chủ đích** (R4 cần phê duyệt, AGENTS.md cấm tự thêm) |
| 7 | **Xác minh** (verify) | `ReflectionLoop.reflect_task` (evidence-based, lessons verified vs hypothesis) | reflection.py:47-132; cognitive_loop.py:359-370 | **ĐÃ CÓ** — phân tách verified/hypothesis (:134-166); hypothesis bị cách ly vào candidate_knowledge (:181-215) |
| 8 | **Ghi nhận học tập** (learn) | `ReflectionLoop.persist_lessons` (episodic + quarantine) và `ContinuousLearningEngine` Type A–E | reflection.py:134-166; continuous_learning_engine.py:144-464 | **CÓ-NHƯNG** — **hai đường học song song chưa nối nhau**: CognitiveLoop.persist_lessons ghi vào brain.db (episodes/quarantine), còn CLE dùng KnowledgeIngestionEngine ghi candidate_knowledge qua đường riêng; không event nào kết nối hai luồng |

---

## 4. Các điểm giao tiếp còn thiếu giữa 5 engine

1. **CognitiveLoop ↔ mọi engine: ORPHAN toàn phần.** Không một điểm runtime nào (server, daemon) gọi `submit_task/tick/approve` (grep src: 0 caller ngoài test). Vòng nhận thức "xương sống" chỉ tồn tại trong test.
2. **CriticalThinker ⇄ CognitiveLoop / ReflectionLoop: không có dây nối.** Kết quả `analyze_argument`/`evaluate_evidence` không được dùng để chấm chất lượng lessons trong `reflect()` (reflection.py:245-259 chỉ trích text từ steps) — năng lực phản biện đang đứng ngoài vòng.
3. **SelfCareEngine → ConsultationStore / NetChatApprovalAdapter: không có đường báo động.** Alert DOWN chỉ `logger.warning` (self_care_engine.py:296); không tạo ticket, không gửi NetChat cho owner. Owner không được biết khi Ollama/web/Pi5 chết.
4. **SelfModelEngine ⇄ SelfCareEngine: logic probe TRÙNG LẶP.** `answer_state_questions` tự viết `_probe_tcp` (self_model_engine.py:270-275) thay vì gọi `SelfCareEngine.check_ollama_health/check_web_health` — hai nguồn sự thật về sức khỏe có thể lệch nhau; song SelfModelEngine lại đọc được DB thật (tasks/brain/consultations) mà SelfCareEngine không có.
5. **ContinuousLearningEngine ⇄ ReflectionLoop: hai đường học song song.** CLE không nhận output của `persist_lessons`; Type B (`learn_type_b_experience`) mong đợi caller tự truyền task_goal/result — nhưng không caller runtime nào truyền cả (server chỉ kích hoạt session handoff, server.py:1672-1690).
6. **Không có event bus chung.** Audit `logs/audit.jsonl` là ghi-đơn-thuần (core/audit.py:21-29) — không subscriber; `InMemoryMessageBroker` (gateway/message_queue.py:128, có pub/sub + retry + DLQ) chỉ được test dùng (tests/test_v28_enterprise_modules.py) — ORPHAN; các bảng event rời rạc: `governance_events` (state_store.py:231), `info_gap_events` (information_gap_analyzer.py:316), `emotion_events` (emotional_memory.py:82).
7. **State of SelfCareEngine volatile.** Alerts/incidents chỉ sống trong list in-memory (self_care_engine.py:106-108) — mất khi restart; không tái sử dụng được cho học Type B (không có "kinh nghiệm sự cố" bền vững).
8. **`get_pending_approvals()` của CLE (continuous_learning_engine.py:510-512) không đọc từ governance.db** — danh sách đề xuất Type E chỉ nằm trong `_reports` in-memory, không khớp ApprovalCardStore/GovernanceStateStore; owner duyệt qua NetChat không thấy các đề xuất này.

---

## 5. Kết luận ngắn

- **Chỉ 1/5 engine được nối runtime** (ContinuousLearningEngine qua web server). 4/5 còn lại là ORPHAN — code thật, test thật, nhưng không ai gọi.
- **Phần khung dưới đã mạnh**: policy gate R0–R5, durable task registry có idempotency, quarantine→semantic có CHECK regression, consultation/approval 2 kênh (in-app + NetChat).
- **Lỗ hổng lớn nhất** là tầng **kết nối**: không có event bus bền vững, không có đường alert→owner, và 2 đường học chưa hợp nhất. Thiết kế khắc phục xem `M2_COGNITIVE_CORE_DESIGN.md`.

---

*Người lập: TONY (M2 research subagent)*
*Ngày: 01/11/2026*
