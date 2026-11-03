# DEOM M6 — KẾ HOẠCH THIẾT KẾ: RECURRING TASK ENGINE + LEARNING FEEDBACK

**Ngày:** 02/11/2026 · **Cơ sở:** DEOM GAP #5 (Task Scheduler), #14 (Learning Feedback), #16 (Notification Manager) + nền M2 (TaskRecord 578 records, work_queue, expire_overdue) + M3 (dispatcher) + M5 (goal_decomposer) · **Trạng thái:** THIẾT KẾ — 0 code ở bước này

---

## 1. Phạm vi M6 (đúng GAP analysis)

| Thành phần | Hiện trạng | M6 bổ sung |
|---|---|---|
| Recurring engine | `TaskRecord` KHÔNG có trường recurring; morning report + mirror chạy Task Scheduler Windows (ngoài não) | `RecurringTaskEngine` — template → instance trong registry, đúng chu kỳ |
| Learning feedback | `promote_lessons(task_id)` có sẵn (cognitive_loop) nhưng KHÔNG tự chạy sau task | `TaskFeedbackRecorder` — sau mỗi task terminal → bản ghi kinh nghiệm |
| Notification policy | alert_engine cooldown 300s + owner-ACK (health) | ĐÃ ĐỦ cho M6 — không đụng (giữ scope nhỏ) |

## 2. RecurringTaskEngine (`orchestration/recurring_engine.py` — MỚI)

### 2.1. Nền tảng: KHÔNG đổi schema TaskRecord
- `progress_weight` (dict, đã có từ M2) thêm key `recurring`: chứa spec — không ADD COLUMN, không migration, 578 records cũ không đụng.
- Template task = task thường + `progress_weight.recurring = {pattern, interval, hour_vn, minute_vn, weekday?, next_run_utc, enabled, last_instance_id}`.
- Instance = task con `parent_task_id = template.task_id`, goal "『recurring』<goal gốc> — lần <n>".

### 2.2. Chu kỳ hỗ trợ (parse từ tiếng Việt — kế thừa nl_intake)
```
daily  — "hằng ngày", "mỗi ngày" + giờ (8h sáng → 08:00 VN)
weekly — "hằng tuần", "mỗi tuần" + thứ (thứ 2 → weekday=0) + giờ
interval — "mỗi 30 phút", "mỗi 2 giờ", "mỗi 3 ngày"
```
Parse thất bại → ValueError (fail-honest, không đoán chu kỳ).

### 2.3. API
- `register_recurring(goal, pattern, *, hour_vn, minute_vn, weekday=None, interval_minutes=None, risk_level, priority, source="owner")` → tạo template task (status=READY, không đưa vào work_queue của dispatcher — lọc bằng `progress_weight.recurring`).
- `create_due_instances(now)` — quét mọi template: `now ≥ next_run_utc` → tạo instance (max 1 lần/lượt quét, chống double-run khi restart: so sánh `last_instance_id` + next_run), đẩy next_run theo chu kỳ. Trả list instance mới.
- `pause / resume / remove(approval_id template)` — pause/resume do owner; **remove/xóa recurring = R4** (phải qua card M4).
- `list_recurring()` — trạng thái tất cả template + lần chạy kế.

### 2.4. Tích hợp
- Watchdog gọi `create_due_instances()` mỗi chu kỳ (tick hiện có) — instance mới rơi vào work_queue chuẩn M2 → dispatcher M3 điều phối như task thường.
- Deadline của instance = next_run + grace (mặc định 1h) — quét expire_overdue vẫn đúng.

## 3. TaskFeedbackRecorder (`orchestration/task_feedback.py` — MỚI)

### 3.1. Luồng (DEOM §11: Task ID → Lessons → Reusable Procedure)
```
task → terminal (COMPLETED_*/FAILED/CANCELLED)
  → record_feedback(task):
      outcome + duration + retries + risk + agent + error (từ TaskRecord + transitions)
  → lưu data/task_feedback.db (bảng feedback + lessons)
  → FAILED/CANCELLED: tự sinh lesson hypothesis (nguyên nhân từ error_message,
    verification_status='candidate' — KHÔNG tự promote)
  → COMPLETED_VERIFIED: lesson 'thành công lặp lại' (candidate)
```
- KHÔNG BAO GIỜ tự promote candidate → fact (đúng R4/Q-4: chỉ verifier + owner).
- Wire: supervisor VERIFYING_RESULT/terminal transition gọi record_feedback (1 try/except — feedback lỗi không giết task).
- Trùng feedback (task_id + attempt) → bỏ qua (idempotent).

## 4. Nghiệm thu (tests bắt buộc)

1. Parse "hằng ngày 8h sáng" → daily 08:00 VN; "mỗi thứ 2 9h" → weekly weekday=0 09:00; "mỗi 30 phút" → interval 30; parse sai → ValueError.
2. create_due_instances: chưa đến giờ → 0; quá giờ → tạo đúng 1 instance có parent_task_id; quét lần 2 ngay → KHÔNG tạo nữa (chống double-run); next_run đúng chu kỳ kế.
3. Instance vào work_queue bình thường; template KHÔNG bị dispatcher chọn (lọc recurring).
4. pause → không tạo instance; resume → chạy lại; remove không card → ValueError.
5. record_feedback sau COMPLETED_VERIFIED → 1 dòng feedback + lesson candidate; sau FAILED → lesson hypothesis từ error; gọi 2 lần → vẫn 1 dòng (idempotent); feedback raise không giết task.
6. Regression FULL ≥ 3.166 PASS / 0 FAIL + commit + HANDOFF + mirror.

## 5. Biên an toàn

- Không ADD COLUMN, không migration, không đụng 578 records cũ (spec nằm trong progress_weight JSON).
- Learning chỉ sinh candidate — promote vẫn là đường Q-4 (owner + verifier).
- Remove recurring = R4 qua ApprovalCardService (M4) — đúng charter.
- Hoàn tác: xoá 2 module + revert commit; Task Scheduler Windows (mirror/backup) KHÔNG đụng.
