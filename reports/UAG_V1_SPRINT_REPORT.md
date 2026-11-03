# UAG_V1_SPRINT_REPORT.md — Universal Action Gateway V1.0 (02/11/2026)

## P0 Audit
`reports/UAG_V1_P0_AUDIT.md` — Pi5 REACHABLE nhưng **11 cổng đóng** (kênh thực thi
chưa có, chờ owner chạy script trên Pi); bảng đối chiếu 8 module ĐÃ CÓ/CÒN THIẾU.

## Sprint code (P0→P3+P5+P7 cốt lõi)

**File mới:** `src/quan_ai_brain/uaiif/uag.py` — KHÔNG tạo Cognitive Core/Memory/
Security mới; ghép QPIG + SENTINEL + ApprovalGovernor + Evidence có sẵn:

| Module §III | Hiện thực |
|---|---|
| M01 Device Discovery | `DeviceInventory` SQLite state machine DISCOVERED→REACHABLE→UNREACHABLE→RETIRED |
| M02 Adapter | kế thừa 7 adapter + AdapterGrant (không trùng lặp) |
| M03 QEP Engine | `QEPEnvelope` (schema qep/1.0, validate) + `QEPCommunicationEngine` (session, correlation, NOT_ACCESSIBLE fail-honest) |
| M04 Tool Registry | kế thừa 25 tool QPIG-V2 |
| M05 Action Engine | pipeline §IV **12 bước đủ** + timeout thật (ThreadPool) + retry CÓ GIỚI HẠN + idempotency |
| M06 SENTINEL | bước AUTHENTICATE bắt buộc; QUARANTINED chặn toàn bộ |
| M07 Approval | `AuthorityGovernor.consume_for_execution` — ticket quanpt1 một-lần, hết hạn, scope, 16 interventions, R5 không hạ |
| M08 Evidence | EvidenceStore 11 trường; evidence ghi ticket_id, directive, attempts |

**§V phân quyền:** AUTO = khảo sát/đọc/giao tiếp thông thường/isolation-REQUEST
(chỉ tạo card); tác động = bắt buộc ticket + intervention khớp mapping
`INTERVENTION_DIRECTIVES`; sai scope/hết hạn/reuse → refuse.
**§X:** không sửa Approval Gateway; rollback thật chỉ qua CSEF card R4.

## Kiểm thử §IX — 22/22 PASS (tests/test_uag_v1.py)

Đủ nhóm: Network · Agent API · MCP/A2A · Action Execution · Approval · Security ·
Recovery · timeout/retry · idempotency · mất kết nối (UNREACHABLE) · thiết bị không
phản hồi (timeout) · **agent giả mạo** (scope ticket khác mục tiêu + CONFLICT_PATTERNS
→ REFUSE_AND_REPORT_OWNER) · **phê duyệt hết hạn** (valid_until quá khứ → chặn).

## Demo luồng thực tế §XI (chạy thật trên WS)

[A] NETWORK_INSPECTION Pi5: REACHABLE 2ms, 12 bước đủ, evidence #2
[B] SUSPEND không ticket → **chặn tại CHECK_PERMISSION**
[C] SUSPEND có ticket quanpt1 `uag-demo-1` → executed, containment nhận
    (SUSPEND, edge_pi5, preapproved=True), evidence #3, ticket consumed=True (reuse chặn)
[D] QEP envelope → edge_pi5: **NOT_ACCESSIBLE** (kênh thật chưa có — fail-honest)

## Còn lại (từ P0 bảng thiếu)

- Pi5 thật: SSH/API mở + systemd UAG service = Release Candidate CSEF, chờ duyệt
- Multi-Agent Ops (P6), health-check tập trung: sau khi kênh Pi5 lên
- Card `appr_de50ca6a6a00` (sprint trước) + card sprint này chờ anh duyệt
