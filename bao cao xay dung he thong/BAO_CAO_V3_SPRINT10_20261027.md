# BÁO CÁO V3 SPRINT 10 — EMAIL INTELLIGENCE LAYER (MOCK-MODE)

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT10 (PENDING_APPROVAL → APPROVED → consumed; duyệt bởi quanpt1 qua desktop chat "duyệt card Sprint 10")
**Điều kiện trung thực:** Vmail thật vẫn **BLOCKED** — chưa có bằng chứng mật khẩu SSO đã đổi; sprint thực hiện lớp Email Intelligence trên connector **mock** theo §IX master prompt Sprint 9 ("chưa đủ điều kiện thì phát triển interface + mock"). Email thật cần card riêng khi owner đổi pass + cấu hình credential an toàn.

## 1. Phạm vi đã duyệt và thực hiện
- (a) **Proposal builder** `src/quan_ai_brain/integration/email_intelligence.py` (308 dòng): sinh đề xuất xử lý 11 trường (goal/basis/conclusion/assumptions/recommended_action/alternatives/risks/action_scope/success_criteria/rollback/owner_decision_needed) — **deterministic**, không LLM; căn cứ từ phân loại Sprint 9 + kinh nghiệm liên quan (chỉ confirmed vào basis, candidates tách riêng, superseded loại).
- (b) **Nhiệm vụ ứng viên PENDING**: POST `/api/email/task/create` tạo task trong DurableTaskRegistry HIỆN CÓ, `PENDING` + `LEVEL_A` — **không tự thực thi**, có `source_email_id`/`related_task_id` metadata; idempotent theo email (lần 2 → cùng task, created=false).
- (c) **UI Workbench**: khu "Email Intelligence" trong tab 🧰 — xem đề xuất đầy đủ, nút tạo nhiệm vụ ứng viên (chống double-submit).
- Giữ nguyên Sprint 9: intake, VmailConnector BLOCKED, dedupe.

## 2. Ma trận năng lực (5 mức)
| Năng lực | Trạng thái |
|---|---|
| Proposal builder (mock email) | Đã có và hoạt động (15 test + smoke live) |
| Tạo nhiệm vụ ứng viên PENDING | Đã có và hoạt động (idempotent proven) |
| UI đề xuất email | Đã có và hoạt động (serve check) |
| Email thật (Vmail) | **Bị chặn** — chờ owner đổi SSO pass + credential an toàn |
| Tự thực thi nhiệm vụ từ email | **Chưa có** — đúng thiết kế an toàn (PENDING + approval) |

## 3. Kiểm chứng
- **Test Sprint 10: 15/15 pass** (`tests/test_v3_sprint10_email_intelligence.py`) — mock/tmppath 100%.
- **Full regression: 833 passed / 0 fail / 1 skipped** (817 → +16; chạy SAU khi sửa route GET/POST — số liệu cuối cùng).
- **Smoke thật live:** kill PID 20144 → watchdog respawn PID 10352 → `/api/email/proposals` 200 (1 đề xuất, vmail_status BLOCKED, assumptions ghi rõ nguồn mock/preview); `/api/email/task/create` tạo `task_95c288281a43` PENDING/LEVEL_A; gọi lần 2 idempotent; executive.html serve `wb-proposals-list`; workbench/tasks hiện task mới PENDING.
- **Lỗi thật bắt được trong smoke:** routes đặt nhầm trong do_POST (`/api/email/proposals` là GET) → 404 trên live → tách đúng do_GET/do_POST → re-test 15/15 + regression 833.

## 4. Giới hạn trung thực
- Toàn bộ email là **mock**; đề xuất sinh từ keyword, chưa semantic; chưa có luồng tự động email→nhiệm vụ theo lịch (cần thiết kế + duyệt riêng); Vmail BLOCKED.
- Task ứng viên không tự chạy — chỉ chờ duyệt qua Approval Center/NetChat (consume-once).

## 5. Next (đề xuất, chờ phê duyệt)
- Sprint 11 (Experience Memory consolidation) theo roadmap master prompt — cần card riêng.
- Kích hoạt Vmail thật: owner đổi mật khẩu SSO + card riêng "Real Email Connector".
