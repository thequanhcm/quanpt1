# SPRINT 15 — IMPLEMENTATION (GIAI ĐOẠN B)

**Thời điểm:** 27/10/2026 18:20–18:40 GMT+7 · **Card:** TASK-V3-SPRINT15 (APPROVED + consumed, `approvals.consumed=1` verified trong governance.db; auth_method=`desktop_master_prompt_sprint15` — phê duyệt phạm vi theo văn bản MASTER PROMPT Sprint 15 của quanpt1)

## Increment đã chọn
**EVIDENCE TRACEABILITY + COGNITIVE STATE RECONCILIATION** (§IV priority-1) — audit chứng minh 3 thiếu sót thật: state không persist, warnings bị nuốt, không API truy xuất.

## Trạng thái từng phần
| Phần | Trạng thái | Chi tiết |
|---|---|---|
| (a) Persist cognitive state | **IMPLEMENTED + UNIT_TESTED + LIVE_SMOKE_VERIFIED** | `plan_orchestrator.submit_plan()` ghi `sprint15_cognitive_state` vào `checkpoint_data_json` HIỆN HỮU (không migration): cognitive_state.to_dict() + plan_warnings (redact) + plan_id + plan_source + persisted_at_utc + evidence_ref `plan:{plan_id}`. CHỈ ghi task MỚI (`if not task_rec.checkpoint_data`) — replay idempotency không ghi đè bằng chứng lần đầu. Fail-open: registry lỗi → submit vẫn thành công (test fail-open). |
| (b) API traceability | **IMPLEMENTED + UNIT_TESTED + LIVE_SMOKE_VERIFIED** | GET `/api/executive/tasks/cognitive-state?task_id=` — localhost-only (403 remote), 400 thiếu param, 404 task lạ, task cũ → `has_cognitive_state: false` + lý do trung thực "đăng ký trước Sprint 15", UNRESOLVED contradiction → `needs_review: true` + giữ CẢ HAI nguồn (không tự phân giải — §IV.C). |
| (c) Passthrough warnings | **IMPLEMENTED + UNIT_TESTED** (path chat) | Sau `submit_plan` trong `/api/chat` create_task: `plan.warnings` → `all_warnings` (prefix "Plan:"). Path `/api/executive/tasks/create` KHÔNG cần vá — đã trả `plan.to_dict()` chứa warnings từ trước. |

## File thay đổi (Sprint 15)
1. `src/quan_ai_brain/orchestration/plan_orchestrator.py` — PATCH (persist block sau save_step)
2. `src/quan_ai_brain/web/server.py` — PATCH (1 route GET + 1 handler mới + passthrough warnings trong chat path)
3. `tests/test_v3_sprint15_cognitive_evidence.py` — FILE MỚI (13 test)
4. `tools/submit_sprint15_approval.py` — FILE MỚI (card)
5. `reports/SPRINT15_AUDIT.md`, `SPRINT15_IMPLEMENTATION.md`, `SPRINT15_TEST_RESULTS.md` — báo cáo

## KHÔNG sửa (giữ nguyên theo phạm vi)
- Nhánh song song chưa commit: cognitive_state.py, coordinator.py, models.py, test_cognitive_state, test_adversarial, PROJECT_STATUS.md, HANDOFF docs, xóa test_asset.json — **Sprint 15 chỉ SỬ DỤNG làm dependency đã có test xanh (20/20)**.
- Không tạo engine/store thứ hai; không đổi R4/R5; không Vmail; không M-Suite; không batch 249 task; không bulk promote 57 lesson; không đụng Task Scheduler/watchdog/NetChat config (respawn server theo đúng cơ chế watchdog hiện hành để nạp code mới — không đổi cấu hình).

## Bug thật gặp phải trong sprint (minh bạch)
1. **NameError `now_utc`**: block persist đầu tiên dùng biến local của `register_task` — exception bị nuốt bởi fail-open (bài học: fail-open phải có test khẳng định tích cực, không chỉ "không chết"). Instrument tạm → tìm gốc → sửa bằng timestamp tự tạo → instrumentation gỡ sạch.
2. **Checkpoint ghi đè khi replay**: thiết kế đầu để block persist chạy cả khi replay → test bắt được → sửa gốc bằng gate `if not task_rec.checkpoint_data`.
3. Hai lỗi trên được BẮT BỞI TEST (không phải smoke) — đúng vai trò của từng lớp kiểm chứng.
