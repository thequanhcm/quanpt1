# SPRINT 15 — AUDIT NHÁNH COGNITIVE STATE (GIAI ĐOẠN A)

**Thời điểm audit:** 27/10/2026 18:08–18:20 GMT+7 · **Branch:** master · **HEAD:** `6b6df30` (Sprint 14)
**Phương pháp:** chỉ đọc — git status/diff/log, đọc mã nguồn, chạy test nhánh song song, kiểm tra luồng gọi thực tế trong server.py. KHÔNG sửa gì ở giai đoạn này. KHÔNG dừng dịch vụ.

---

## 1. HIỆN TRẠNG THỰC TẾ (bằng chứng)

### 1.1 Baseline xác minh lại (không tin tài liệu)
- Test suite: **không hard-code** — chạy lại cuối sprint (baseline tài liệu: 927 PASS / 0 FAIL / 1 SKIP từ S14 — sẽ đối chiếu sau khi có thay đổi).
- Working tree (git status 18:08): có **nhánh song song chưa commit** — chủ sở hữu: session agent song song:
  - `M src/quan_ai_brain/planning/coordinator.py` (+134 dòng)
  - `M src/quan_ai_brain/planning/models.py` (+25 dòng)
  - `?? src/quan_ai_brain/cognition/cognitive_state.py` (464 dòng, MỚI)
  - `?? tests/test_cognitive_state.py` (252 dòng) + `?? tests/test_adversarial_cognition.py` (359 dòng)
  - `M docs/PROJECT_STATUS.md`, `M reports/HANDOFF_LATEST.md`, `M reports/TEST_RUN_LATEST.txt`, `D edge_client/assets/avatar/test_asset.json`, 7 handoff tự động chưa track
  - **CLEAN (an toàn để Sprint 15 patch):** `src/quan_ai_brain/web/server.py`, `src/quan_ai_brain/orchestration/plan_orchestrator.py`, toàn bộ `memory/`, `cognition/experience_semantic.py`, `cognition/context_builder.py`
- Live API 8765 hoạt động (đã gọi `/api/improvement/report`, `/api/executive/edge/status` lúc 18:03 — Pi5 READY 0.29s).

### 1.2 cognitive_state.py — chất lượng và mức tích hợp
**Thiết kế tốt, không phải engine thứ hai** — tái sử dụng `VerificationStatus` từ `memory/models.py`, redaction qua `core/redaction`, không tự tạo store:
- `BeliefItem` (frozen dataclass): statement + kind (8 loại FACT_USER/FACT_RETRIEVED/OBSERVED/VERIFIED_INDEPENDENT/INFERENCE/HYPOTHESIS/PREDICTION/UNKNOWN) + **source_ref + confidence + verification_status + superseded_by** — đầy đủ provenance (§IV.A master prompt S15).
- `is_verified_fact()`: chỉ FACT kinds + status VERIFIED/OBSERVED/USER_PROVIDED — **không nâng cấp bằng ngôn ngữ tự tin**.
- `ContradictionRecord`: giữ CẢ HAI nguồn + status UNRESOLVED/RESOLVED_A/RESOLVED_B/CONTEXT_DIFFERENCE — đúng §IV.C (không xóa lịch sử).
- `MetacognitiveEvaluation`: can_conclude / abstention_reason / grounding_score — fail-closed khi thiếu evidence.
- Mọi `to_dict()` đều redact_text — secrets không rò qua serialization.

### 1.3 Mức wiring hiện tại (câu hỏi audit §III)
| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| 1. cognitive_state có được gọi trong luồng thật? | **CÓ — trong `ExecutiveCoordinator.plan()`** (3 call-site server.py:1303/1590/1890: /api/chat create_task, executive task create/execute) | coordinator.py:114-220 (chưa commit) |
| 2. ContextBuilder dùng trạng thái xác minh? | **CÓ từ trước** — route theo verification_status, excluded_memories cho disallowed status, inline `(Source: …, Status: …)` | context_builder.py:94-200 (đã commit S14) |
| 3. Semantic retrieval trả provenance? | **CÓ** — experience_semantic trả verification_status/source_ref/similarity per match | experience_semantic.py (S14) |
| 4. Claim cũ/mâu thuẫn có nhận diện? | **CÓ trong plan()** — stale→UNKNOWN/0.1 + warning "CẢNH BÁO DỮ LIỆU CŨ"; candidate→HYPOTHESIS/0.3 (§X.7); contradiction theo topic giữ 2 nguồn | coordinator.py diff +150 |
| 5. Nâng cấp không bằng chứng? | **KHÔNG phát hiện** — learning engine không auto-promote (grep promote/VERIFIED = 0 match); candidate luôn hạ xuống HYPOTHESIS | engine.py, coordinator.py |
| 6. Hai nguồn sự thật? | **KHÔNG** — cognitive_state tái dùng VerificationStatus; không store mới | import models.py |
| 7. Thay đổi API/schema hiện hữu? | **KHÔNG** — TaskPlan.to_dict thêm field `cognitive_state` (backward-compatible additive); không đổi schema DB | models.py:257-258 |
| 8. Regression unit vs live? | **20/20 PASS** (12 cognitive_state + 8 adversarial) chạy 18:08; S14 smoke 927 pass | pytest output |

### 1.4 KHOẢNG TRỐNG THỰC SỰ (căn cứ chọn increment)
1. **Cognitive state KHÔNG được lưu bền vững**: `submit_plan()` đăng ký task + steps nhưng **không ghi `checkpoint_data_json`** (writer duy nhất của cột này là `update_task_status` — không ai gọi trong luồng submit; grep toàn src). Kết quả: beliefs/contradictions/uncertainties/metacognition của một plan **mất ngay sau response API** — không truy xuất được, vi phạm yêu cầu "Lịch sử thay đổi" + "khôi phục trạng thái nhất quán" (§I mục 1,5; §IV.A).
2. **Plan warnings bị nuốt**: server chỉ dùng `task_rec.to_dict()` (TaskRecord — không chứa warnings của plan); `plan_warnings` như "CẢNH BÁO DỮ LIỆU CŨ" và adversarial warning **không tới được owner** qua kênh nào.
3. **Không có API truy xuất evidence**: sau khi task được tạo, không cách nào (API/DB API) xem lại "khi lập kế hoạch, hệ thống dựa trên bằng chứng nào, trạng thái xác minh gì".

## 2. THAY ĐỔI CHƯA NGHIỆM THU (phân định quyền sở hữu)
- Nhánh song song (KHÔNG phải Sprint 15, không nghiệm thu trong sprint này): cognitive_state.py, coordinator wiring, models wiring, test_cognitive_state, test_adversarial_cognition, PROJECT_STATUS/HANDOFF/TEST_RUN docs, xóa test_asset.json.
- **Sprint 15 KHÔNG đụng các file trên** (trừ việc SỬ DỤNG chúng như dependency đã có test xanh).

## 3. TRÙNG LẶP / XUNG ĐỘT
- Không phát hiện trùng lặp engine (cognitive_state KHÔNG tạo store/loop mới).
- Xung đột ghi: working tree chia sẻ — Sprint 15 chỉ patch `plan_orchestrator.py` + `server.py` (đang CLEAN) + thêm file mới; rủi ro session song song sửa cùng lúc được ghi trong §Rủi ro.

## 4. PHẠM VI SỬA TỐI THIỂU (increment — đúng priority 1 master prompt)
**EVIDENCE TRACEABILITY + COGNITIVE STATE RECONCILIATION**:
1. `plan_orchestrator.submit_plan()`: persist `plan.cognitive_state.to_dict()` + plan warnings vào **schema hiện hữu** `durable_tasks.checkpoint_data_json` (JSON, không migration; chỉ ghi khi đăng ký task mới — idempotency hiện có bảo vệ không ghi đè task existing).
2. API mới **GET /api/tasks/{task_id}/cognitive-state** (localhost-only, read-only): trả beliefs/contradictions/uncertainties/metacognition/warnings; 404 trung thực; task cũ không có state → `has_cognitive_state: false` (không 0 giả); flag `needs_review: true` khi còn UNRESOLVED contradiction (không tự phân giải — §IV.C).
3. Passthrough plan warnings vào kênh `all_warnings` hiện hữu của response chat (3 dòng trong server.py) — cảnh báo stale/adversarial tới owner.

## 5. RỦI RO & ROLLBACK
- Rủi ro ghi checkpoint: schema TEXT json hiện hữu, chưa có reader/writer khác trong submit path → xung đột thấp; nếu task existing (idempotent replay) → không ghi đè.
- Rủi ro session song song sửa cùng file: patch nhỏ, tách bạch; nếu conflict → đọc lại file trước khi retry (bài học S14 — không stash).
- Rollback: revert 1 commit (hoặc hoàn tác 2 patch + 1 file mới) — không đụng dữ liệu live (API read-only; checkpoint chỉ ghi thêm thông tin, không xoá).
- Không commit cho tới khi Quanpt1 xem xét (theo §VII — chỉ báo cáo + diff).
