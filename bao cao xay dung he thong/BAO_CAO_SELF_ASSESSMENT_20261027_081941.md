# BÁO CÁO TỰ ĐÁNH GIÁ NĂNG LỰC — QUAN AI BRAIN

*Sinh lúc 2026-10-27T08:19:41.414207+00:00 bằng dữ liệu thật từ DB (Sprint 13 Continuous Improvement).*

## Ma trận năng lực (5 mức)

| Năng lực | Mức | Bằng chứng |
|---|---|---|
| tasks | Đã có và hoạt động | tasks.db durable_tasks @ 2026-10-27T08:19:41.414207+00:00 |
| approvals | Đã có và hoạt động | governance.db approval_cards @ 2026-10-27T08:19:41.414207+00:00 |
| experience | Đã có và hoạt động | brain.db memories/candidate_knowledge/semantic_memory @ 2026-10-27T08:19:41.414207+00:00 |
| email_intelligence | Có một phần | email_intake.db @ 2026-10-27T08:19:41.414207+00:00 — Vmail thật chờ owner đổi SSO pass |
| web_readonly | Đã có và hoạt động | integration/web_connector.py + smoke 27/10 (SSRF chặn, Bing search, VNE RSS 10 items) — commit cd626c0 |
| information_gaps | Chưa xác minh | information_gaps.db không đọc được |
| regression_tests | Đã có và hoạt động | BAO_CAO_V3_SPRINT12_20261027.md: - **Full regression: 893 passed / 0 fail / 1 skipped** (857 → +36 — bao gồm cả test Bing mới). |

## Số liệu chi tiết

### tasks
- total: 370
- completed: 2
- failed: 0
- cancelled: 161
- in_flight: 207
- success_rate_pct: 1.2
- evidence: tasks.db durable_tasks @ 2026-10-27T08:19:41.414207+00:00

### approvals
- cards_total: 12
- approved: 11
- rejected: 0
- decision_rate_pct: 0.0
- evidence: governance.db approval_cards @ 2026-10-27T08:19:41.414207+00:00

### experience
- lessons_total: 16
- lessons_confirmed: 1
- lessons_pending: 15
- quarantine_candidates: 786
- semantic_confirmed: 1841
- evidence: brain.db memories/candidate_knowledge/semantic_memory @ 2026-10-27T08:19:41.414207+00:00

### email_intelligence
- intake_emails: 3
- proposals: 1
- proposals_linked_task: 1
- vmail_real: Bị chặn
- evidence: email_intake.db @ 2026-10-27T08:19:41.414207+00:00 — Vmail thật chờ owner đổi SSO pass

### web_readonly
- evidence: integration/web_connector.py + smoke 27/10 (SSRF chặn, Bing search, VNE RSS 10 items) — commit cd626c0

### information_gaps
- reason: information_gaps.db không đọc được

### regression_tests
- evidence: BAO_CAO_V3_SPRINT12_20261027.md: - **Full regression: 893 passed / 0 fail / 1 skipped** (857 → +36 — bao gồm cả test Bing mới).

## Điểm cải tiến đề xuất (dựa trên số liệu)

- 15 bài học đang chờ anh duyệt — duyệt để dùng làm căn cứ mạnh cho đề xuất email.
- Vmail thật còn BLOCKED — đổi mật khẩu SSO + card 'Real Email Connector' để mở luồng email thật.
- 207 nhiệm vụ đang chờ/xử lý — cân nhắc duyệt hoặc huỷ task cũ.
