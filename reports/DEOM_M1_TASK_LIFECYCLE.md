# DEOM M1 — TÀI LIỆU 3/4: TASK LIFECYCLE (Vòng đời task + schema mở rộng M2)

**Ngày:** 01/11/2026 · **Cơ sở:** schema thật `durable_tasks` (19 cột, 578 records) + TaskStatus hiện có · **Thiết kế cho M2 (R4 — đã duyệt blanket)**

---

## 1. Schema `durable_tasks` hiện tại (đọc thật từ tasks.db 01/11)

```
task_id, correlation_id, idempotency_key, goal, risk_level, autonomy_level, status,
acceptance_criteria_json, approved_scope_json, created_at_utc, updated_at_utc,
completed_at_utc, resource_budget_json, retry_count, max_retries, error_message,
evidence_refs_json, result_payload_json, checkpoint_data_json
```

## 2. Cột bổ sung (M2 — ADD COLUMN, nullable, không phá 578 records)

| Cột | Kiểu | Ý nghĩa DEOM |
|---|---|---|
| `priority` | INTEGER CHECK(1..5) | 1=Critical, 2=High, 3=Normal, 4=Low, 5=Background (§7.2) |
| `deadline_utc` | TEXT NULL | phát hiện quá hạn (CASE 2) |
| `parent_task_id` | TEXT NULL | task nhóm/milestone (CASE 5) |
| `dependencies_json` | TEXT NULL | danh sách task_id phải xong trước |
| `required_tools_json` | TEXT NULL | capability matching cho Dispatcher (M3) |
| `assigned_agents_json` | TEXT NULL | nhiều embodiment / agent |
| `permission_scope_json` | TEXT NULL | thu hẹp quyền trong lúc chạy task |
| `progress_weight_json` | TEXT NULL | weighted progress cho task phân rã |
| `source` | TEXT DEFAULT 'owner' | owner / proactive / learning / system |

Bảng mới **`task_transitions`** (transition log §4.4 — bắt buộc):

```sql
CREATE TABLE IF NOT EXISTS task_transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  from_status TEXT, to_status TEXT NOT NULL,
  actor TEXT NOT NULL,            -- 'tony' | 'owner' | 'system' | agent id
  reason TEXT, evidence_ref TEXT,
  at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_transitions_task ON task_transitions(task_id);
```

Bảng mới **`task_events`** (idempotency intake — chống duplicate giao việc NL).

## 3. Trạng thái vòng đời DEOM (mở rộng enum hiện có)

```
Hiện có (giữ): PENDING, IN_PROGRESS, WAITING_APPROVAL, APPROVED, COMPLETED,
               FAILED, CANCELLED, OUTCOME_UNKNOWN, BLOCKED
Thêm M2:       RECEIVED → UNDERSTANDING → ANALYZING → PLANNING → READY
               VERIFYING, NEEDS_INFORMATION, PAUSED, EXPIRED, REJECTED
Tách hoàn tất: COMPLETED → COMPLETED_VERIFIED | COMPLETED_PARTIALLY | COMPLETED_UNVERIFIED
```

**Luật chuyển (transition guard — cài cùng M2):**
- Chỉ chuyển hợp lệ theo bảng dưới; chuyển khác → từ chối + ghi log `actor=tony reason=invalid_transition`.
- `COMPLETED_VERIFIED` chỉ khi **Task Verifier** xác nhận mọi `acceptance_criteria_json` có bằng chứng trong `evidence_refs_json` (không có verifier → `COMPLETED_UNVERIFIED` + cảnh báo — fail-honest).
- `EXPIRED` tự động khi `deadline_utc < now` và chưa COMPLETED (check trong watchdog loop hiện có).
- `PAUSED`/`RESUME` nối Human Override supervisor (đã có states STOPPED/SAFE_MODE).

Bảng chuyển hợp lệ (rút gọn):
```
RECEIVED→UNDERSTANDING→ANALYZING→(NEEDS_INFORMATION↔ANALYZING)→PLANNING→READY
READY→WAITING_APPROVAL→(APPROVED|REJECTED)
APPROVED→IN_PROGRESS→(PAUSED↔IN_PROGRESS)→VERIFYING→COMPLETED_VERIFIED|COMPLETED_PARTIALLY
VERIFYING→FAILED→(retry≤max_retries→IN_PROGRESS|BLOCKED)
IN_PROGRESS→BLOCKED→(unblock→IN_PROGRESS|CANCELLED)
READY→EXPIRED (deadline); WAITING_APPROVAL→EXPIRED|CANCELLED
```

## 4. Work Queue 4 bậc (thiết kế M3, chạy trên registry không service mới)

- Hàng đợi = query `status=READY ORDER BY priority, deadline_utc NULLS LAST, created_at_utc`.
- 6 quy tắc ưu tiên DEOM §7.2: owner lệnh đứng đầu > safety/health > deadline > chuỗi phụ thuộc > độ tuổi > fairness.
- **Chống learning chiếm tài nguyên:** task `source=learning` chỉ chạy khi (a) không có task owner chờ, (b) resource_budget còn dư, (c) tối đa 1 learning task đồng thời.
- Scheduler định kỳ tái dùng watchdog loop (không thêm daemon).

## 5. Nghiệm thu M2 (R4 — migration thật)

1. Backup `tasks.db` → `data/backups/tasks_backup_<ts>.db` (sqlite backup API).
2. ADD COLUMN + 2 bảng mới trong 1 transaction; nếu lỗi → rollback toàn bộ.
3. Verify: 578 records nguyên vẹn + 19 cột cũ giữ giá trị + cột mới NULL/DEFAULT.
4. Regression FULL ≥ 3.034 PASS / 0 FAIL + 62/62 backbone tests.
5. HANDOFF + REGISTER ghi rõ hoàn tác = restore backup.

---
*TONY — DEOM M1 · Task Lifecycle thiết kế bám schema thật, không suy đoán.*
