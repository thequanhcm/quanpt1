# CHERRY_INTELLIGENCE_MATURITY_DASHBOARD_SPEC — thiết kế dashboard
**Trạng thái:** PROPOSED — Phase E (Sprint INT-5). Read-only, tab mới trên server 8766 hiện có — KHÔNG server mới.

## 1. Phạm vi
Tab "Intelligence Maturity" hiển thị: 12 KPI CISC (từng KPI riêng, nhóm thiếu data = NOT EVALUATED), trend 7 lần benchmark gần nhất, trạng thái audit CIIA, danh sách lỗi OPEN từ Error DB, chi phí chạy benchmark gần nhất (LLM calls/thời gian). **KHÔNG có điểm tổng** (quy tắc Goodhart — CISC §1).

## 2. Nguồn dữ liệu
| Khối | Nguồn | Refresh |
|---|---|---|
| KPI | reports/intelligence_maturity/cisc_runs/*.json | khi chạy benchmark |
| Trend | lịch sử cisc_runs | mỗi lần chạy mới |
| Audit | audits/ + trạng thái 4 giá trị | khi có audit mới |
| Errors | data/cognitive/errors.db | 5 phút |
| Chi phí | runner logs | mỗi lần chạy |

## 3. API mới (R1 read-only)
- `GET /api/intelligence/scorecard` — 12 KPI + trend
- `GET /api/intelligence/audit-status`
- `GET /api/intelligence/errors?status=OPEN`
Không có POST — dashboard KHÔNG cho phép thay đổi gì (an toàn: người duyệt vẫn là owner qua chat/approval card).

## 4. UI nguyên tắc
- Dùng CSS vars của app (var(--foreground)…) — tách file static/intelligence_tab.js + phần trong executive.html.
- Mỗi KPI: tên + giá trị + dataset size + khoảng tin cậy (nếu có) + badge trạng thái (MEASURED / NOT EVALUATED).
- RED FLAG tự động: KPI giảm >5% giữa 2 lần chạy → highlight đỏ + cảnh báo.
- Pi5 offline → khối System Troubleshooting hiển thị "BLOCKED — Pi5 offline từ <timestamp>" thay vì số cũ.

## 5. Nghiệm thu
- Tab render đủ 12 KPI; NOT EVALUATED hiển thị đúng; 0 POST endpoint; audit status đúng 4 giá trị; khối BLOCKED khi Pi5 offline.

## 6. Rủi ro
- Dashboard cho cảm giác "đã hoàn thành" khi KPI còn NOT EVALUATED — chống bằng badge rõ + phần trăm coverage đo được hiển thị trên cùng.
