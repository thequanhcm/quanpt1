# DEOM V4 — P9 DESIGN: MASTER SCENARIOS (Phần 13)

**Ngày:** 02/11/2026 02:40 · **Owner duyệt:** "anh duyệt" (02/11) · **Trạng thái:** IMPLEMENTED + TESTED

## 1. Nguyên tắc

3 kịch bản master tổng hợp nhiều năng lực (governance + task + state machine + recovery +
learning) chạy trên component thật, tmp_path, không LLM/network. Mỗi kịch bản = một "ngày
làm việc" của Digital Employee, kiểm chứng chuỗi hành vi đúng như DEOM yêu cầu.

## 2. Kịch bản

| # | Master scenario | Chuỗi kiểm chứng |
|---|---|---|
| MS1 | Ngày làm việc chuẩn: nhận goal → decompose → execute → verify → feedback → lesson candidate | L1+L2+L6 nối tiếp, lesson candidate, metrics đếm đúng |
| MS2 | Sự cố giữa chừng: step giữa FAILED → DAG chặn → task FAILED → lesson failure_cause → restart supervisor → không re-run sai (G-C) | fail-honest, không "chữa lành" ngầm |
| MS3 | Khủng hoảng + phục hồi: task đang chạy → supervisor "sập" → recover → OUTCOME_UNKNOWN → emergency STOP chặn task mới → hủy STOP → vận hành lại | an toàn tuyệt đối khi không chắc chắn |

## 3. Điểm kiểm chứng xuyên suốt

- Không tự nâng trạng thái xác minh; terminal không re-run (G-C).
- OUTCOME_UNKNOWN chỉ thoát bằng owner quyết định, không tự động re-execute.
- Emergency STOP/FREEZE tác động đúng tức thời lên lifecycle.
- Mọi lesson sinh ra luôn candidate.
