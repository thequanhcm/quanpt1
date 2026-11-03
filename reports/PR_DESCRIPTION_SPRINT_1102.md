# PR: TONY Sprint 01/11→02/11 — DEOM M3–M6, Advanced Assurance, VN-LANG

> **Nhánh:** `feat/deom-m1-m2-task-lifecycle` → **Base:** `main`
> **27 commits conventional-commit** từ `e75d240` (initial state) đến `22afece`.

## Nội dung thay đổi (theo nhóm)

### feat(orchestration) — DEOM M3–M6: kiến trúc nhân sự số hoàn chỉnh
- `156f474` **M3** agent dispatcher + dependency manager (DAG, tránh xung đột tài nguyên)
- `e0d6135` **M4+M5** permission resolver + approval workflow (R4 card 12 trường) + goal decomposition deterministic tiếng Việt
- `170aa25` **M6** recurring task engine + task feedback recorder (KHÔNG ADD COLUMN — JSON extension)

### feat(governance) — V4 G-A: khoá hành động bằng fingerprint
- `4650a5c` action fingerprint binding cho R4 approval cards (sha256 card↔action, consume fail-closed, 1 lần)

### feat(orchestration) — G-C (ADV-003): state machine chống "sống lại"
- `910ed43` bảng ALLOWED_TRANSITIONS ở tầng `update_task_status`; trạng thái terminal (COMPLETED*, FAILED, CANCELLED, EXPIRED, OUTCOME_UNKNOWN, REJECTED) không quay lại RUNNING; `force=True` chỉ recovery nội bộ và ghi log

### test(advanced) — Advanced Assurance P0–P9
- `6996675` P0–P4: governance, red-team (P2 injection), chaos, concurrency; fix approval consume race (atomic F3)
- `54eed68` P5 learning metrics + 5 detector reward-hacking (report-only); **fix thật ADV-004: step FAILED không re-run ngầm**; P7 business scenarios L1–L6
- `fc655a0` P9 master scenarios MS1–MS3 (ngày làm việc / sự cố giữa chừng / khủng hoảng + recovery)

### feat(charter) + feat(alerts) — vận hành
- `d2309fb` TONY Digital Employee Charter tích hợp bằng code+test: 11 test nhận thức T1–T10 (T1 phát hiện decomposer match nhầm → R5 hard-block hoạt động đúng)
- `3016895` owner-ACK cả 2 loại cảnh báo đang hoạt động (ram_percent, pi5 connectivity) qua `data/alert_owner_ack.json` — ack rồi không DM lại, vẫn ghi DB audit

### feat(vn-lang) — chuẩn hoá tiếng Việt toàn bộ DM + hội thoại
- `5ccc293` 3 lớp chặn cuối: `netchat_bridge.send_message` (điểm chặn duy nhất mọi DM), `alert_engine`, `netchat_auto_responder`; rào NGÔN NGỮ bắt buộc trong system prompt cả 2 đường LLM (stream + non-stream); số liệu/tên riêng giữ nguyên
- `68d5c76` fix fatal-handler responder ghi file UTF-8 thay vì print cp1252

### docs + chore
- Chuỗi docs(status) ghi Handoff sau mỗi increment (cây bằng chứng: 3.111 → 3.323)
- `cadaec5` báo cáo tổng hợp 02/11 02:00; `22afece` snapshot runtime state
- `0bc7891`+`33462d9` ONECLICK_SETUP_NEW_PC.bat + hướng dẫn chuyển máy 1-click

## Kiểm định
- **Regression FULL: 3.323 PASS / 0 FAIL / 44 skipped** (250s) — từ 3.071 đầu sprint, +252 test
- tests/advanced: 101 test (governance, red-team, chaos, concurrency, learning, business, master, charter)
- `tools/validate_and_report.py` exit 0 · Mirror F:\BRAIN THÀNH CÔNG (SHA-256 từng khối) · secret scan sạch

## Trạng thái xác minh
Mọi commit có test đi kèm; KHÔNG tự nâng mức xác minh (ADV levels giữ nguyên do evidence); G-B scorecard + STRESS_TESTED (locust) còn backlog, KHÔNG khai báo hoàn thành.
