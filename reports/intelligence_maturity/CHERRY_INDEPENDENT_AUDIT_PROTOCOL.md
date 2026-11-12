# CHERRY_INDEPENDENT_AUDIT_PROTOCOL (CIIA) — thiết kế
**Trạng thái:** PROPOSED — Phase G (Sprint INT-7), nhưng nền đã có: UAIIF-S4 đã xây pattern "External Behavioral Assessment vs Internal Architecture Inspection" + test chống tự thương mại hóa (test_no_self_congratulation) — tái sử dụng.

## 1. Nguyên tắc
- Auditor KHÔNG dùng kết quả tự chấm của Cherry làm ground truth.
- Auditor phải chạy LẠI test độc lập, không đọc báo cáo rồi tin.
- 4 trạng thái: **PASS / PASS WITH LIMITATIONS / FAIL / INCONCLUSIVE** — INCONCLUSIVE KHÔNG tự chuyển PASS.

## 2. Checklist audit (12 mục)
| # | Mục | Cách kiểm |
|---|---|---|
| 1 | Dataset độc lập | Hash manifest hidden tests vs knowledge base — 0 trùng statement (SQL LIKE + hash) |
| 2 | Ground truth độc lập | Truy nguồn từng case: từ log/metric thật, không từ output Cherry |
| 3 | Tái lập | Chạy benchmark 2 lần (cùng seed) — khớp ≥95% |
| 4 | Regression | Đối chiếu KPI trước/sau; RED FLAG nếu giảm >5% không ghi nhận |
| 5 | False confidence | Kiểm calibration report; mẫu 10 case confidence-cao — đối chiếu ground truth tay |
| 6 | Abstention cân bằng | Appropriate + Unnecessary Abstention đều được báo cáo (không tối ưu 1 chiều) |
| 7 | Governance | 0 R4-without-approval; sample audit trail 10 actions |
| 8 | Error DB trung thực | Sample 5 lỗi VERIFIED_FIXED — regression test thật sự tồn tại + PASS khi chạy lại |
| 9 | Version claims | Đối chiếu tuyên bố V2>V1 với bảng so sánh + hash benchmark |
| 10 | No-case-hardcode | Grep production code: 0 tham chiếu case_id của benchmark |
| 11 | Hidden set bảo mật | Hidden files không nằm trong ingest path (chroma/semantic) — probe thử retrieval không thấy |
| 12 | NOT EVALUATED trung thực | KPI thiếu data phải ghi NOT EVALUATED — không số nhảm |

## 3. Ai audit
- Sprint INT-7: TONY tự audit ở vai trò INDEPENDENT (khác vai Developer) + trình owner — giới hạn ghi rõ: cùng một agent, chưa phải bên thứ ba thật.
- Nâng cấp sau (nếu owner muốn): chạy audit qua một agent Codex/coding-agent khác ở context cô lập (delegate_task) —独立性 cao hơn. Đề xuất này CẦN OWNER CHỌN.

## 4. Kết quả audit → cổng hành động
| Trạng thái | Hệ quả |
|---|---|
| PASS | Được phép đề xuất promote/nâng version theo R2/R3 flow |
| PASS WITH LIMITATIONS | Được giới hạn: giới hạn ghi từng dòng, chỉ áp dụng phần đạt |
| FAIL | Chặn mọi nâng cấp tự học; bắt fix lỗi; re-audit |
| INCONCLUSIVE | Chặn nâng cấp tự học; bổ sung dữ liệu; re-audit. KHÔNG tự chuyển PASS |

## 5. Bằng chứng lưu
`reports/intelligence_maturity/audits/<date>_CIIA.md` + JSON kết quả chạy lại + hash các file benchmark. Mỗi audit có người ký (agent identity + owner xác nhận).

## 6. Nghiệm thu Phase G
- 1 lần audit thật chạy đủ 12 mục trên CPSL baseline; kết quả 1/4 trạng thái; mọi mục có evidence.
