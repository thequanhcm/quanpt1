# SPRINT 15 — AUDIT REPORT (GIAI ĐOẠN A)

**Thời điểm:** 27/10/2026 18:52–19:05 GMT+7 · **Branch:** master · **HEAD:** `f6fa94f` (Sprint 15 đã commit)

## 1. HIỆN TRẠNG (xác minh live, không tin baseline)

### 1.1. Working tree & session song song
- **Thay đổi chưa commit:** `coordinator.py`, `models.py` (session song song)
- **File mới chưa commit:** `cognitive_state.py`, `test_cognitive_state.py`, `test_adversarial_cognition.py` (session song song)
- **HEAD commit:** `f6fa94f` — Sprint 15 Evidence Traceability ĐÃ commit (persist cognitive_state, API cognitive-state, passthrough warnings)

### 1.2. Task & Lesson live state
| Hạng mục | Số lượng | Ghi chú |
|----------|----------|---------|
| Task PENDING | **5** | Mỗi task có `idempotency_key` và `correlation_id` KHÁC NHAU → KHÔNG phải duplicate |
| Bài học candidate | **1** | `be444437...` — mới từ session song song |

**Phát hiện quan trọng:** 4 task cùng goal "Thu thập báo cáo năng lượng..." nhưng khác `correlation_id` → **HỢP LỆ** (có thể từ nhiều kênh/session). Không được archive/cancel theo master prompt.

### 1.3. Cognitive State integration
- **Đã tích hợp đầy đủ** trong `ExecutiveCoordinator.create_plan()`:
  - `CognitiveState` initialized với beliefs, contradictions, uncertainties
  - Retrieval memory → beliefs với verification_status (VERIFIED/OBSERVED/CANDIDATE/UNVERIFIED)
  - Adversarial detection → uncertainty flag
  - `cognitive_state` được attach vào `TaskPlan` (3 call-site)
- **API `/api/executive/tasks/cognitive-state`:** Đã implement (Sprint 15) — read-only, localhost-only

### 1.4. Test suite
- **Tổng:** 961 tests
- **PASS:** 959
- **FAIL:** 1 (`test_executive_api_tasks_full_lifecycle`)
- **SKIP:** 1 (Pi 5 hardware)

**Test fail:** `test_executive_api_tasks_full_lifecycle` — tạo task thành công (200, success=True) nhưng `list_tasks()` trả empty → **race condition/transaction isolation**.

## 2. NGUYÊN NHÂN GỐC (test fail)

**Bằng chứng:**
- POST `/api/executive/tasks/create` → 200, `success=True`, `task_id="task_..."`
- GET `/api/executive/tasks` → `active_tasks=[]` (empty)
- Test dùng tmp_path (test workspace) — server chạy độc lập

**Root cause:** `register_task()` INSERT vào SQLite nhưng **không commit** → transaction chưa visible khi `list_tasks()` đọc ngay sau đó.

**Kiểm chứng:**
- `task_registry.py`: `self._conn.execute(INSERT ...)` — không có `commit()`
- SQLite default: auto-commit disabled khi dùng transaction explicit
- Test tạo task → list ngay → chưa commit → empty

## 3. RỦI RO

| Rủi ro | Mức độ | Giảm thiểu |
|--------|--------|------------|
| Test fail che regression thật | Medium | Fix commit trong registry |
| Session song song tạo task trùng | Low | Idempotency key khác nhau → hợp lệ |
| Cognitive state chưa được owner review | Medium | Chờ audit V4 của session song song |

## 4. INCREMENT ĐỀ XUẤT

**Phạm vi nhỏ nhất:** Fix transaction commit trong `task_registry.register_task()` + verify test pass.

**File sửa:**
- `src/quan_ai_brain/orchestration/task_registry.py` — thêm `commit()` sau INSERT/UPDATE

**Không sửa:**
- 5 task PENDING (hợp lệ, khác correlation_id)
- 1 bài học candidate (chờ owner duyệt)
- Session song song files (không commit, không đụng)

**Lý do:** Test fail là regression — phải fix trước khi tiếp tục increment khác. Commit là fix an toàn, không side-effect.

## 5. TIẾN ĐỘ

- [x] Audit workspace, live state, test suite
- [x] Xác định root cause test fail
- [ ] Fix transaction commit trong task_registry
- [ ] Verify test pass
- [ ] Run full regression suite
- [ ] Live smoke (nếu cần)
- [ ] Viết implementation + test results report

---
*Audit bởi: QUAN AI BRAIN V3 Sprint 15 Agent · 27/10/2026 19:05 GMT+7*