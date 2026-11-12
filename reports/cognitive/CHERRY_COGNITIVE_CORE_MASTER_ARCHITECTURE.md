# CHERRY COGNITIVE CORE — MASTER ARCHITECTURE
**Phiên bản:** V1.0-draft | **Ngày:** 11/11/2026 | **Trạng thái:** CHỜ OWNER DUYỆT (chưa triển khai code)
**Người soạn:** TONY (netMind Desktop, profile tony)
**Cơ sở:** Báo cáo baseline 11/11/2026 + TASK A re-inspection thực tế cùng ngày (số liệu lấy trực tiếp, không suy đoán)

---

## 1. Nguyên tắc kiến trúc (bất biến)

1. **Không xây lại Brain Core.** Cognitive Core là LỚP NẠP trên nền hiện có (server.py 8765/8766, brain.db, chroma, voice pipeline).
2. **Không trùng lặp chức năng.** Trước khi tạo module mới bắt buộc gap-check với 5 kho đã có (mục 3). Mọi module mới phải nêu rõ "tái dùng X, mở rộng Y, tạo mới Z".
3. **Không phá API/database/voice đang chạy.** Mọi schema change là ADD COLUMN/bảng mới, idempotent, backup trước.
4. **Fail-honest:** trường chưa kiểm chứng → UNKNOWN/LAST_VERIFIED, không bao giờ giả VERIFIED.
5. **Governance-first:** R0–R5 giữ nguyên; cognitive core không có quyền vượt policy; "Learning is not deployment".
6. **Deterministic-first:** suy luận có cấu trúc (hypotheses/evidence/confidence) do CODE quản lý; LLM chỉ là 1 nguồn inference, không bao giờ là nguồn sự thật.

## 2. Đặt module mới ở đâu — quyết định kiến trúc

Code hiện tại đã có 3 vị trí liên quan:
- `src/quan_ai_brain/cognition/` — cognitive_state (V4), self_model_engine, self_qa, logical_reasoning (V9), reflection, self_study, continuous_learning_engine, cognitive_loop, context_builder
- `src/quan_ai_brain/memory/` — taxonomy (FactLevel), conflict_detector (V31), promotion_policy, knowledge_quality, unified_memory, deep_memory
- `src/quan_ai_brain/uaiif/` — agent_knowledge (epistemic statuses), qpig

**Quyết định:** Cognitive Core mở rộng trong `src/quan_ai_brain/cognition/` theo nhóm file mới, KHÔNG tạo package `cognitive/` song song (tránh 2 nhà riêng). Cấu trúc đề xuất trong master prompt §10 được điều chỉnh:

```text
src/quan_ai_brain/cognition/
  trust/            # MỚI: source_trust_engine.py, cognitive_memory_guard.py
  working/          # MỚI: working_memory.py (session-scoped)
  reasoning/        # MỚI: hypothesis_manager.py, causal_reasoner.py, uncertainty_estimator.py
                    #      (logical_reasoning.py hiện có → nâng cấp, không thay thế API)
  metacognition/    # MỚI: metacognition_engine.py, cognitive_reflection.py
                    #      (reflection.py hiện có giữ vai trò khác: CLO session reflection)
  planning/         # tái dùng src/quan_ai_brain/planning/ + orchestration/plan_orchestrator.py hiện có
                    #      chỉ BỔ SUNG action_policy.py + outcome_verifier.py (verifier đã có deom M2)
  world_model.py    # MỚI (1 file)
  self_state_monitor.py  # MỚI (bổ sung self_model_engine.py hiện có)

tests/cognitive/
  unit/ integration/ regression/ adversarial/ benchmark/   # thư mục MỚI — test hiện tại ở tests/ flat

data/cognitive/
  sessions/ working_memory/ evidence/ reflections/ evaluations/   # runtime state riêng, KHÔNG đụng brain.db lõi
  # + 2 bảng MỚI trong brain.db: cognitive_sessions, cognitive_evidence (ADD-only, có audit)

reports/cognitive/
  baseline/ sprint_reports/ audits/ benchmarks/   # ĐÃ TẠO 11/11 — để kết quả thật
```

## 3. Kiểm kê tái sử dụng (audited 11/11)

| Thành phần mục tiêu | Đã có sẵn | Khoảng trống thật |
|---|---|---|
| CognitiveClaim/EvidenceLevel/Hypothesis/Uncertainty/MetacognitiveEvaluation | `cognitive_state.py` (1015 dòng, V4) | Chưa nối vào pipeline chat/voice thật |
| Contradiction detection | `conflict_detector.py` (687 dòng, V31 — semantic/temporal/logical/source) + `cognitive_state.record_contradiction` | Chạy riêng lẻ; chưa gắn vào luồng lưu memory mới |
| Fact taxonomy | `taxonomy.py` FactLevel: FACT/USER_PROVIDED/VERIFIED/OBSERVED/INFERENCE/QUARANTINED | Chưa có SOURCE ID + trust level 6 bậc (OWNER_VERIFIED…UNTRUSTED) |
| Promotion fail-closed | `promotion_policy.py` + R4 approval_verifier | Giữ nguyên — cognitive core phải đi qua |
| Multi-hypothesis reasoning | `logical_reasoning.py` (V9, 309 dòng — A/B/C conclusion, chống vòng tròn) | Retrieval chỉ thấy `knowledge_units` (148 hàng V9) — CHƯA thấy 10.874 tri thức chroma/semantic → trả "không đủ bằng chứng" dù kho có dữ liệu (đo thật 11/11) |
| Self model + self-QA | `self_model_engine.py` (562) + `self_qa.py` (190, 11 câu hỏi) | Đã wired DM; thiếu self_state_monitor theo dõi liên tục + phân biệt UNKNOWN vs LAST_VERIFIED |
| Working memory | `session_memory.py`, ConversationStateManager (DM) | Chưa có: active context + hypotheses + pending questions + expiry + recovery |
| World model | Không có | Tạo mới (1 file) |
| Goal & planning | `planning/coordinator.py`, `orchestration/plan_orchestrator.py`, DEOM M2 task lifecycle + Task Verifier | Outcome verifier có; thiếu action_policy tập trung (R0–R5 đã có ở governance/policy.py — wire vào) |
| Metacognition | `cognitive_state.evaluate_metacognition()` (data model) + `reflection.py` (CLO) | Thiếu engine chạy SAU mỗi nhiệm vụ quan trọng + lưu evidence |
| Learning loop | learning_daemon (5 phút/lần, LIVE) + self_study V2 | Nạp lặp (695× "Test suite: 3648 passed" trong quarantine) + chưa có contradiction gate trước ghi |
| Benchmark | test_cognitive_state_v4, adversarial_cognition, 199 test files | Chưa có CHERRY COGNITIVE BENCHMARK V1 10 nhóm độc lập |

## 4. Kiến trúc 8 thành phần (map vào code thật)

### 4.1 Perception Engine — mở rộng `cognition/context_builder.py`
- Mọi input (voice/camera/system) đi qua `PerceptionFrame {source_id, source_type, captured_at, modality, raw_ref, direct_or_inferred}`.
- Voice: wake_word_service hiện NHẬN mọi âm qua wake là owner (nguyên nhân La La School) → PerceptionFrame đánh dấu `speaker_assumption=UNKNOWN` cho đến khi có speaker verification (Phase 1: heuristic trust; voiceprint là đề xuất Phase sau, cần thu thập mẫu owner — sẽ hỏi owner).
- Không tin mặc định: timestamp + nguồn bắt buộc, thiếu → frame bị đánh `UNTRUSTED`.

### 4.2 Source & Trust Engine — MỚI `cognition/trust/source_trust_engine.py`
- 6 trust levels đúng spec: OWNER_VERIFIED > SYSTEM_VERIFIED > TRUSTED_SOURCE > MODEL_INFERENCE > UNKNOWN_SOURCE > UNTRUSTED_SOURCE.
- TrustRecord: source_id, source_type, timestamp, evidence_ref, confidence, trust_level, verification_status, owner_attribution.
- Lưu ở 2 nơi: tag đi kèm mỗi memory mới (bổ sung cột `trust_json` ADD-ONLY cho bảng lưu mới) + `data/cognitive/evidence/`.
- Wire: mọi đường ghi memory (voice interact, DM, learning ingest, self_study) BẮT BUỘC gọi trust engine trước khi ghi (cognitive_memory_guard chặn).

### 4.3 Working Memory — MỚI `cognition/working/working_memory.py`
- Session-scoped (per conversation + per cognitive session): active_context, current_task, current_hypothesis, available_evidence, pending_questions, contradictions, decisions, temporary_conclusions.
- TTL + persist ra `data/cognitive/working_memory/` (JSON, phục hồi sau restart), không đụng brain.db.
- Không tạo daemon mới — quản lý trong request lifecycle của server.

### 4.4 World Model — MỚI `cognition/world_model.py`
- Entities: people (owner/stranger), devices (PC/Pi5/router), modules (server/learning/watchdog/wake), network, events.
- Mỗi entity 2 dòng thời gian: `state_current` (probe mới nhất) + `state_last_verified` (xác nhận cuối + thời điểm) — đúng yêu cầu master prompt.
- Nguồn cập nhật: edge status API, health API, ping/SSH probe — chỉ ghi từ PROBE THẬT, không ghi từ LLM.

### 4.5 Self Model — nâng cấp `self_model_engine.py` + MỚI `self_state_monitor.py`
- Giữ SelfQA 11 câu (đang wired DM). Bổ sung: phân biệt UNKNOWN vs LAST_VERIFIED cho từng module; scope "chờ owner quyết định" lấy từ approvals + quarantine counts thật.
- `self_state_monitor.py`: 1 chu kỳ trong watchdog hiện có (KHÔNG daemon mới) — cập nhật self model từ health/edge API thật.

### 4.6 Reasoning Engine — nâng cấp `logical_reasoning.py` + MỚI hypothesis_manager/causal_reasoner/uncertainty_estimator
- **Fix gap thật đo được 11/11:** retrieval của reasoning hiện chỉ đọc `knowledge_units` (148) → phải nối thêm semantic_memory + chroma (10.874) qua interface DeepMemoryStore mà KHÔNG đổi API answer_question.
- 8 bước phân tích (problem → evidence → hypotheses → support/against → likelihood → missing info → conditional conclusion → action proposal) đã có khung V9 — giữ nguyên cấu trúc, mở rộng nguồn evidence.
- Confidence: giữ nguyên lời cảnh báo "chỉ số khai báo, KHÔNG phải xác suất hiệu chuẩn" (đúng §3.6 master prompt) + thêm uncertainty_estimator để chấm độ chắc từng giả thuyết.
- Causal reasoner: cấm kết luận nhân quả chỉ từ đồng thời (guard test bắt buộc).

### 4.7 Goal & Planning — tái dùng + MỚI action_policy.py
- PlanOrchestrator + DurableTaskRegistry + Task Verifier (DEOM M2) giữ nguyên.
- `action_policy.py` = bảng phân quyền hành động R0–R5 map vào policy.py hiện có; mọi đề xuất hành động của reasoning phải qua policy check trước khi vào queue; R4 đi approval_verifier (fail-closed).
- Rollback: hành động R3 phải khai rollback_plan; thất bại → rollback + audit.

### 4.8 Metacognition — MỚI `cognition/metacognition/metacognition_engine.py`
- Sau mỗi nhiệm vụ quan trọng (định nghĩa: có decision/ACT hoặc multi-hypothesis): chạy 10 câu đánh giá theo master prompt §3.8, lưu Cognitive Evidence Record vào `data/cognitive/reflections/` + bảng `cognitive_sessions` (brain.db ADD-only).
- LLM không tự chấm điểm duy nhất: reflection ghi bằng chứng (evidence_refs) + kết quả đo được (outcome_verified từ Task Verifier).

## 5. Cognitive Loop & 4 kết quả hợp lệ
PERCEIVE→VERIFY→UNDERSTAND→THINK→PLAN→ACT/COMMUNICATE→OBSERVE→REFLECT→LEARN — đóng gói trong `cognitive_loop.py` hiện có (479 dòng, nâng cấp).
Mỗi session có `COG-<YYYYMMDD>-<uuid8>`; kết quả ANSWER/ASK/WAIT/ACT — "Tôi chưa đủ dữ liệu để kết luận" là kết quả chuẩn khi evidence không đủ (logical_reasoning ĐÃ trả đúng câu này thật 11/11 — giữ hành vi).
Không bắt buộc ACT sau mỗi vòng.

## 6. Data & API
- **brain.db ADD-only:** 2 bảng mới `cognitive_sessions(session_id, task, decision_json, hypotheses_json, evidence_json, confidence_json, outcome_verified, reflection_json, created_at_utc)`, `cognitive_evidence(session_id, kind, ref, sha256, created_at_utc)`. Không sửa cột cũ. Bảng `memory_review_sessions/runs` hiện có tiếp tục dùng cho review.
- **data/cognitive/** — file evidence/reflections/working_memory (JSON, append-only khi có thể).
- **API mới (Phase cuối mỗi phase):** GET `/api/cognitive/session/<id>`, GET `/api/cognitive/sessions?limit=`, GET `/api/cognitive/self-model`, POST `/api/cognitive/ask` (đường reasoning có cấu trúc) — tất cả read-only hoặc R1, không hành động production.
- **HMAC:** mọi API từ Pi5 giữ nguyên `_edge_hmac_verify`.

## 7. Bảo mật & rủi ro kiến trúc
| Rủi ro | Giải pháp |
|---|---|
| Trust engine bị "tự nâng" trust của memory do mình sinh | Trust do CODE quy ước theo source_type; MODEL_INFERENCE không bao giờ được promote lên SYSTEM_VERIFIED; promote chỉ qua R4 |
| Cognitive thêm trễ pipeline voice (đang 230ms) | Trust guard O(1) hash/lookup; working memory in-process; KHÔNG gọi LLM thêm trong hot path |
| brain.db phình (đã 102MB) | cognitive_sessions chỉ lưu JSON tóm tắt + evidence file ngoài; retention 90 ngày |
| Dual learning instance (đang có 2 learning_daemon PID) | Phase 0 dọn về 1 trước khi wire guard |
| Test suite lớn (199 file, ~10 phút) | Benchmark cognitive chạy riêng, không đưa vào full regression mỗi sprint |

## 8. Phân phase (chi tiết kế hoạch ở CHERRY_COGNITIVE_IMPLEMENTATION_PLAN.md)
Phase 0 ổn định → Phase 1 trust/working memory/contradiction gate → Phase 2 reasoning (fix retrieval gap là việc đầu) → Phase 3 self-awareness → Phase 4 goal/controlled autonomy → Phase 5 evolution. Mỗi phase có cổng nghiệm thu + benchmark trước khi sang phase sau. **Chưa có phase nào được bắt đầu khi chưa có owner approval (TASK E xong → chờ duyệt).**

---
*Tài liệu thiết kế — KHÔNG kèm claim "đã triển khai". Mọi mục status là PROPOSED.*
