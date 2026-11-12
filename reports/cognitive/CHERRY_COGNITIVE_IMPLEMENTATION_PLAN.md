# CHERRY COGNITIVE IMPLEMENTATION PLAN — kế hoạch triển khai theo Sprint
**Trạng thái:** PROPOSED — chờ owner duyệt sau TASK A→E. **Không sprint nào bắt đầu nếu chưa có approval card.**
**Nguyên tắc từ skill `quan-ai-brain-development`:** mỗi sprint = approval card (PENDING_APPROVAL → owner duyệt → consume-once) → implement → tests → full regression → live smoke → honest report → commit → DM. Mỗi phase có cổng nghiệm thu + benchmark trước khi sang phase sau.

---

## PHASE 0 — SYSTEM STABILIZATION (Sprint COG-0, ~1 phiên làm việc, R2)
**Sprint COG-0a — Dọn nền (không đụng cognitive):**
1. Kill dual learning daemon (giữ 1 instance), thêm guard single-instance theo PID marker.
2. Verify backup task 2AM (result≠0 hôm nay): đọc log, fix, chạy backup thật + integrity check, ghi bằng chứng.
3. Dedupe write-path: kiểm chứng `KnowledgeIngestionEngine.ingest(skip_duplicates=True)` hoạt động trên learning_daemon thật; chạy 1 cycle quan sát "6459 ingested → 0 new" phải thành "ingested nhỏ, dup counter tăng".
4. Dọn semantic dup 88 nhóm: backup DB → dedupe archive-never-delete (pattern skill 27/10) → reconcile counts → VACUUM.
5. Quarantine: KHÔNG tự duyệt — chỉ làm tool batch-review (export CSV cho owner duyệt ngoài) + báo cáo 6.231.

**Nghiệm thu COG-0:** backup mới + integrity ok; 1 learning instance; sau 24h quarantine tăng ≤ 20 (không còn nạp lặp test-suite); semantic dup = 0; pytest full PASS (kết quả TASK A làm baseline).
**Điều kiện dừng (master prompt §13):** backup chết không sửa được → DỪNG, báo owner.

## PHASE 1 — COGNITIVE FOUNDATION (Sprint COG-1, R2)
**Module:** `cognition/trust/source_trust_engine.py` + `cognition/trust/cognitive_memory_guard.py` + `cognition/working/working_memory.py` (contradiction dùng conflict_detector hiện có — wire vào, không viết lại).
**Wire:** mọi đường ghi memory (voice interact, DM, learning ingest) qua guard; tag trust JSON vào bản ghi mới (ADD-ONLY schema).
**Kiểm thử bắt buộc (từ master prompt):** TV noise (34 câu thật đã có từ a760ff3 — tái dùng làm regression), giọng lạ, giọng owner, thiếu nguồn, dup facts, mâu thuẫn facts, cũ/mới — TẤT CẢ trong tests/cognitive/adversarial/.
**Nghiệm thu:** 0 memory TV-noise vào trusted semantic; dup fact bị chặn ở WRITE path; contradiction phát hiện trong bộ test; audit trail mỗi quyết định lưu/từ chối.
**Chặn dừng:** nếu guard làm voice pipeline vượt 500ms → tách async, báo owner.

## PHASE 2 — REASONING INTELLIGENCE (Sprint COG-2, R2)
**Việc đầu tiên (gap #1):** nối retrieval reasoning vào semantic_memory + chroma (interface qua DeepMemoryStore, giữ API answer_question).
**Module mới:** hypothesis_manager.py, causal_reasoner.py, uncertainty_estimator.py; wire cognitive_loop.
**Kiểm thử:** 7 kịch bản thật (Pi5 mất kết nối, DHCP đổi IP, PC offline, service chết, heartbeat stale, cảm biến mâu thuẫn, đa nguyên nhân) — dùng lịch sử sự cố 10-11/11 làm dataset tái lập.
**Nghiệm thu:** ≥2 giả thuyết khi data cho phép; evidence cho từng giả thuyết; từ chối kết luận khi thiếu data (đã có — regression); cập nhật kết luận khi evidence mới; 0 kết luận nhân quả không căn cứ (guard test).

## PHASE 3 — SELF-AWARENESS & METACOGNITION (Sprint COG-3, R2)
**Module:** self_state_monitor.py (chu kỳ trong watchdog — không daemon mới); metacognition_engine.py; cognitive_reflection.py; world_model.py.
**Nâng cấp:** self_model_engine — UNKNOWN vs LAST_VERIFIED từng module; pending owner decisions đọc cả quarantine.
**Kiểm thử:** hỏi trạng thái Pi5 (offline thật → phải trả DISCONNECTED/LAST VERIFIED 10/11 13:31, KHÔNG ONLINE); camera; module lỗi; nhiệm vụ đang làm; điều chưa biết; bằng chứng trái nhận định.
**Nghiệm thu:** self model từ probe thật; 0 khai báo ONLINE không heartbeat; phân biệt UNKNOWN/LAST VERIFIED; chỉ ra giới hạn bản thân; ghi nhận + điều chỉnh nhận định sai; benchmark độc lập pass.

## PHASE 4 — GOAL & CONTROLLED AUTONOMY (Sprint COG-4, R3 — CẦN OWNER DUYỆT RỘNG HƠN)
**Module:** action_policy.py (map R0–R5 vào policy.py có sẵn), goal_manager.py, task_planner.py (tái dùng PlanOrchestrator), outcome_verifier.py (tái dùng Task Verifier M2), rollback executor trong whitelist.
**Nghiệm thu:** plan trước hành động quan trọng; risk assessment; permission check; outcome verified; rollback khi fail; audit log đầy đủ; KHÔNG có hành động R4 chạy không approval (test fail-closed).

## PHASE 5 — CONTINUOUS COGNITIVE EVOLUTION (Sprint COG-5+, R3)
**Module:** cognitive_learning_engine.py (từ learning_daemon hiện có — nâng cấp, không tạo daemon), experience_consolidator.py, capability_registry.py, cognitive_evaluation.py.
**Quy tắc:** học → quarantine-only → owner duyệt → promote qua R4; mọi upgrade năng lực qua Sandbox + Regression + Independent Audit; không tự promote.

## BENCHMARK (song song, Sprint COG-B sau Phase 1)
CHERRY COGNITIVE BENCHMARK V1 — 10 nhóm theo master prompt §9, mỗi case: input → expected → actual → pass/fail → log → evidence → procedure tái lập. Chạy bằng script riêng `tools/run_cognitive_benchmark.py`, kết quả vào reports/cognitive/benchmarks/. **Quy tắc vàng:** không hardcode câu hỏi để Cherry trả đúng; đo cả false-accept và false-reject; phân biệt hiểu/ghi nhớ/may mắn bằng biến thể câu hỏi + dữ liệu chưa gặp.

## Timeline tổng (đề xuất, phụ thuộc duyệt từng sprint)
| Sprint | Nội dung | Est. |
|---|---|---|
| COG-0 | Ổn định + dedupe + backup | 1 phiên |
| COG-1 | Trust + guard + working memory | 1-2 phiên |
| COG-B | Benchmark V1 (nhóm 1-4 trước) | 1 phiên |
| COG-2 | Reasoning + retrieval gap fix | 1-2 phiên |
| COG-3 | Self-awareness + world model | 1-2 phiên |
| COG-4 | Goal + controlled autonomy (R3) | 2 phiên |
| COG-5 | Evolution + audit độc lập | 1-2 phiên |

## Rủi ro tổng & rollback
- Mỗi sprint: branch riêng, commit conventional, không merge thiếu approval; rollback = revert commit (code) + restore backup (data).
- brain.db: mọi migration ADD-only, backup ngay trước, integrity check sau.
- Pi5 offline: mọi E2E edge đánh dấu BLOCKED, không chặn các sprint PC-side.
- Test suite ~10 phút: cognitive benchmark tách khỏi full regression.

---
*Plan PROPOSED — chờ owner duyệt từng sprint theo approval card flow.*
