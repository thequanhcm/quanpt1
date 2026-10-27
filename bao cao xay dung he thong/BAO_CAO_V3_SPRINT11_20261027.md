# BÁO CÁO V3 SPRINT 11 — EXPERIENCE MEMORY (CONSOLIDATION & LESSONS LEARNED)

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT11 (PENDING_APPROVAL → APPROVED → consumed; duyệt bởi quanpt1 qua desktop chat "em triển khai Sprint 11 (Experience Memory")
**Theo roadmap §XIV master prompt Sprint 9:** Sprint 11 = Experience Memory.

## 1. Phạm vi đã duyệt và thực hiện
- (a) **`memory/experience_consolidation.py`**: `extract_candidate_lesson()` — task COMPLETED/FAILED → lesson CANDIDATE (EPISODIC + UNVERIFIED + lifecycle QUARANTINED) vào MemoryStore HIỆN CÓ + episode audit trail; **idempotent theo task_id** (1 task = 1 lesson, lặp → no-op trung thực); `promote_lesson()` — chỉ owner (approval_verified=True bắt buộc, không có → PermissionError) → supersede thành VERIFIED + active; `list_lessons()` tách candidates/confirmed.
- (b) **API (localhost-only, fail-closed):** GET `/api/experience/lessons` (list), POST `/api/experience/consolidate` (task_id + outcome COMPLETED/FAILED, đọc goal từ tasks.db), POST `/api/experience/lessons/promote` (**bắt buộc `owner_confirm=DUYET`** — thiếu/sai → 403; 404 lesson không tồn tại; 409 không promote được).
- (c) **UI Workbench:** khu "📚 Kinh nghiệm (Experience Memory)" — ứng viên 🟡 CHƯA duyệt vs đã duyệt ✅ tách rõ, nút duyệt có confirm + chống double-submit.
- (d) **Hook execute:** `_handle_api_executive_task_execute` tự sinh lesson candidate khi task kết thúc COMPLETED/FAILED — **fail-closed** (lỗi consolidation chỉ ghi reason, không phá response execute).

## 2. Ma trận năng lực
| Năng lực | Trạng thái |
|---|---|
| Capture lesson từ task kết thúc | Đã có và hoạt động (24 test + smoke live) |
| Quarantine lesson ứng viên | Đã có và hoạt động (idempotent proven) |
| Owner promote → kinh nghiệm xác nhận | Đã có và hoạt động (403 chặn không-confirm proven) |
| Lesson phục vụ đề xuất (retrieval S9) | Đã có và hoạt động (sau promote vào confirmed) |
| Tự promote / learning tự duyệt | **Không có — đúng thiết kế** (Learning is not deployment) |

## 3. Kiểm chứng
- **Test Sprint 11: 24/24 pass** — bao gồm: candidate KHÔNG rò vào retrieval trước promote (an toàn hơn yêu cầu §VII.2 tối thiểu); sau promote → vào `confirmed` của `find_similar_experiences`.
- **Full regression: 857 passed / 0 fail / 1 skipped** (833 → +24).
- **Smoke thật live:** kill PID 10352 → watchdog respawn PID 7012 → lessons list 200; consolidate từ task thật `task_95c288281a43` → created; lặp lại → idempotent "đã tồn tại"; promote thiếu confirm → **403**; promote `owner_confirm=DUYET` → VERIFIED+active; lessons cuối `{candidates: 2, confirmed: 1}`; executive serve `wb-lessons-list`.
- Lỗi thật bắt được khi test: `TaskPriority` không tồn tại trong models (dùng đúng signature `register_task`); FakeHandler `type(cls)` immutable — sửa theo class name.

## 4. Giới hạn trung thực
- Lesson sinh từ goal/result_summary của task — **không LLM**, chất lượng phụ thuộc mô tả task.
- Consolidate qua API là **thủ công** (gọi tay hoặc hook execute); chưa có job tự động quét task mới kết thúc (cần thiết kế + duyệt riêng nếu muốn).
- 2 lesson candidates có sẵn trong smoke là từ các task COMPLETED trước đó qua hook mới — trung thực ghi nhận, không phải dữ liệu mẫu.

## 5. Next (đề xuất, chờ phê duyệt)
- Sprint 12 (Web & Internal Application Workflows) theo roadmap — cần card riêng; kết hợp Read-only browser connector.
- Tự động quét task kết thúc → consolidate định kỳ (job nhỏ, cần duyệt).
