# BÁO CÁO BATCH REVIEW & ARCHIVE + ROOT CAUSE FIX — 27/10/2026

**Phạm vi được chủ nhân duyệt (phiên chat):**
1. APPROVED skill `TASK_PROGRESS_AUDIT` — transition TESTED → APPROVED → AVAILABLE (có reason).
2. Batch review/archive các task PENDING cùng goal "Thu thập báo cáo năng lượng trung tâm dữ liệu".

## 1. SKILL LIFECYCLE (skill_956691fa41)

| Transition | Reason |
|-----------|--------|
| TESTED → **APPROVED** | "Chủ nhân duyệt trực tiếp qua phiên chat 27/10/2026" |
| APPROVED → **AVAILABLE** | "Chủ nhân duyệt kích hoạt ngay sau APPROVED — evidence đã có (smoke V6 + units + live API)" |

Verify: `find_matching_skills('kiểm tra tiến độ')` → `[('TASK_PROGRESS_AUDIT', 'AVAILABLE')]` ✓

## 2. ROOT CAUSE (điều tra trước khi archive — audit first)

**Nguồn gốc task trùng lặp KHÔNG phải lỗi producer nghiệp vụ:**

1. `tools/learning_daemon.py:150` — daemon học liên tục chạy **pytest full suite mỗi cycle ~201s** (nguồn "Ingests ALL test results").
2. `tests/test_web_server.py::test_web_server_api_plan_with_durable_task` — spin server thật bằng `BrainAPIHandler`; `_find_workspace_root()` resolve về workspace production → POST `/api/plan` ghi **1 task thật vào `data/tasks.db` mỗi lần chạy suite**.
3. Cùng cơ chế: `tests/test_web_executive_endpoints.py:145` (goal "Kiểm toán hiệu năng hệ thống và bảo mật dữ liệu điều hành").

**Bằng chứng định lượng:** 294 task 'năng lượng' từ 20/10; biểu đồ theo giờ khớp chu kỳ daemon (~18 cycle/giờ → 11–23 task/giờ, đỉnh 148 task 27/10). idempotency_key khác nhau từng task (mỗi lần = 1 plan mới) → idempotency không chặn được.

**Daemon đang chạy 2 process song song** (PID 7724 venv, PID 15200 system python) — KHÔNG dừng (ngoài thẩm quyền; chủ quyết định).

## 3. ARCHIVE (danh sách ID lấy tươi ngay trước UPDATE, không WHERE goal loạt)

- **41/41 task PENDING cùng goal 'năng lượng' → archived** (41 = 36 cũ + 5 mới sinh ra trong lúc điều tra).
- Verify đọc lại: PENDING cùng goal = **0**; tổng archived cùng goal = 47 (gồm 3 + 2 task trước đó).
- Toàn DB còn **9 PENDING** — 8 là 'Kiểm toán hiệu năng' (ngoài phạm vi, chưa đụng), 1 khác.

## 4. FIX ROOT CAUSE (small diff, fail-closed)

- `src/quan_ai_brain/web/server.py` — `_find_workspace_root()` thêm env override `QUAN_AI_BRAIN_WORKSPACE`: chỉ nhận khi directory tồn tại (fail-closed), không ảnh hưởng production (env không set).
- `tests/test_web_server.py` + `tests/test_web_executive_endpoints.py` — fixture set env về tmp workspace; fixture executive copy read-only assets avatar sang test workspace (test edge files cần ≥20 file).
- **Verified:** chạy 6/6 + 14/14 test → PENDING DB **trước = sau = 9** (trước fix: +1 task mỗi lần chạy suite).

## 5. REGRESSION SAU FIX

**1033 passed / 0 failed / 1 skipped** (81.50s) — giữ nguyên 1033, fix chỉ đổi nơi ghi của test.

## 6. VIỆC CÒN MỞ (chờ chủ)

1. 8 task PENDING 'Kiểm toán hiệu năng' — cùng cơ chế test-induced, đề xuất archive tương tự (cần duyệt).
2. Daemon chạy 2 process song song — nên giữ 1 (cần duyệt để dừng PID 15200 hoặc 7724).
3. Từ nay daemon vẫn chạy pytest mỗi ~3.5 phút — nhưng suite đã sạch, không còn sinh task rác.

---
*QUAN AI BRAIN Agent · Master Prompt V6 · 27/10/2026 ~23:15 GMT+7*