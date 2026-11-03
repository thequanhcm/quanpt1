# TOOL & SKILL FACTORY — IMPLEMENTATION REPORT (Master Prompt V6)

**Thời điểm:** 27/10/2026 22:55 GMT+7 · **Branch:** `feature/cognitive-state-integration` · **HEAD:** `86a0fe4`

## 1. TÁI SỬ DỤNG (không tạo engine trùng)

| Module V6 | Module thực tế dùng | Ghi chú |
|-----------|--------------------|---------|
| Task Specification | `cognition/information_gap_analyzer.TaskSpecification` | Giữ nguyên shape, không sửa |
| Capability Registry | `cognition/capability_registry.py` | Nguồn DISCOVER |
| Persistence | cơ chế `checkpoint_data_json` (S15) | `to_dict()` tương thích |
| Reusable lessons | pipeline S9 (experience.db) | REUSE chỉ ghi asset, promotion chờ owner |

## 2. MODULE MỚI

### `src/quan_ai_brain/cognition/task_pipeline.py` (~250 lines)

- **`PipelineStage`** — 11 stage chuẩn §III.
- **`StageRecord`** — audit trail: stage, timestamp, notes, evidence_refs, skipped_reason.
- **`TaskPipeline`** — bọc TaskSpecification + stage_history + evidence_manifest + validation_results + reusable_assets + final_recommendation; `to_dict()/from_dict()` đầy đủ.
- **`TaskPipelineEngine`** — `create_pipeline()` (UNDERSTAND tự động ghi bằng chứng gốc = owner_request), `advance()` với validate fail-closed.

### Quy tắc an toàn đã cài đặt (test chứng minh)

| Quy tắc | Test |
|---------|------|
| Stage chỉ đi tới trước | `test_backward_move_rejected`, `test_same_stage_rejected` |
| Skip bắt buộc có lý do | `test_skip_requires_reason` |
| VERIFY: thiếu tiêu chí/validation → chặn | `test_verify_requires_criteria`, `test_verify_missing_criterion_rejected` |
| VERIFY fail-honest: `not_verified=True` được chấp nhận | `test_verify_fail_honest_allowed` |
| **ADVISE chặn nếu chưa VERIFY** (safety gate cốt lõi) | `test_advise_before_verify_blocked`, `test_advise_after_verify_allowed` |
| ADVISE cần khuyến nghị cụ thể | `test_advise_requires_nonempty_recommendation` |
| REUSE cần asset kiểm chứng | `test_reuse_requires_assets`, `test_reuse_records_assets` |
| Persist round-trip nguyên trạng | `test_round_trip` |

### Những gì KHÔNG làm (giữ scope nhỏ, đúng nguyên tắc)

- Không tự gọi LLM phân rã bài toán (DECOMPOSE do caller/owner cung cấp).
- Không tự tạo lesson khi REUSE — chỉ ghi asset, promotion qua pipeline S9 chờ owner.
- Không đụng email thật (Vmail BLOCKED — chờ owner đổi SSO).
- Không tạo bảng DB mới — persist tái dùng checkpoint_data_json.

## 3. USE CASE NGHIỆM THU §VI (smoke với dữ liệu thật workspace)

Bài toán: "BẮT ĐẦU HỌC TẬP — kiểm tra tiến độ công việc trong hệ thống"

| Stage | Kết quả thật |
|-------|--------------|
| UNDERSTAND | owner_request ghi nguyên vẹn làm bằng chứng gốc |
| DECOMPOSE/DISCOVER/PLAN | sqlite3 stdlib + data/tasks.db (không cần tool mới) |
| LEARN/BUILD | SKIP có lý do — "stdlib đủ, reuse before creating" |
| ANALYZE | **553 task: CANCELLED=505, COMPLETED=2, PENDING=42, archived=4** |
| VERIFY | c1=passed (nguồn thật); c2=**NOT_VERIFIED** (chưa có nguồn chéo — Vmail BLOCKED) |
| ADVISE | 3 task PENDING mới nhất cần chủ xác nhận; **KHÔNG archive tự động** |
| REUSE | `procedure:task_progress_audit_tasksdb` |

Lỗi schema gặp lúc smoke: cột là `created_at_utc`/`goal` (không phải `created_at`) — đã audit PRAGMA table_info trước khi sửa, không đoán.

## 4. HẠN CHẾ & TRẠNG THÁI

- Skill Registry chưa có — đây là candidate tiếp theo (dựa trên TaskPipeline).
- Email thật BLOCKED — mọi bài toán chéo nguồn email chờ owner.
- Trạng thái pipeline core: **IMPLEMENTED + TESTED** (16 unit + smoke thật).

---
*Implementation bởi: QUAN AI BRAIN Agent · Master Prompt V6 · 27/10/2026 22:55 GMT+7*