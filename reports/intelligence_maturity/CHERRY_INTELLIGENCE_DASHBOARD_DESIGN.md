# CHERRY INTELLIGENCE MATURITY DASHBOARD — DESIGN DOC (Phase 1)

**Trạng thái:** Phase 1 hoàn thành (12/11/2026) — Design + mockup tĩnh. CHƯA đụng server 8766, chưa có API thật, mockup dùng dữ liệu MINH HỌA có nhãn rõ.
**Tiền đề:** Phase 0 (System Discovery) đã duyệt; spec `CHERRY_INTELLIGENCE_MATURITY_DASHBOARD_SPEC.md`; scorecard CISC 12 KPI.

## 1. Nguyên tắc bất biến (từ master prompt + spec)

1. **KHÔNG điểm tổng** — 12 KPI hiển thị riêng biệt (chống Goodhart).
2. **N/A — INSUFFICIENT** khi thiếu data; **NOT EVALUATED** khi chưa có benchmark; không tô hồng thứ chưa đo.
3. **INCONCLUSIVE không tự thành PASS** — badge trạng thái bắt buộc 4 giá trị: MEASURED / NOT EVALUATED / BLOCKED / AUDIT REQUIRED.
4. **Benchmark chạy trên DB copy snapshot** — không benchmark DB live.
5. **0 POST endpoint** — dashboard read-only; người duyệt là owner qua chat/approval card.
6. **RED FLAG tự động:** KPI giảm >5% giữa 2 lần chạy liên tiếp → highlight + cảnh báo.
7. Pi5 offline → khối System Troubleshooting hiện **BLOCKED — Pi5 offline từ <timestamp>**, không hiện số cũ.

## 2. Kiến trúc (map vào hiện trạng thật — Phase 0)

```
server.py (8766, đã có) ──► static/executive.html  (thêm 1 section + nav tab)
                        ──► static/intelligence_tab.js + intelligence_tab.css (MỚI, file riêng)
                        ──► 3 API read-only (Phase 3):
                              GET /api/intelligence/scorecard   → 12 KPI + trend
                              GET /api/intelligence/audit-status → 4 giá trị audit
                              GET /api/intelligence/errors?status=OPEN
Nguồn: reports/intelligence_maturity/cisc_runs/*.json (tương lai)
       + data/cognitive/errors.db (Error DB Phase D)
       + audits/ (CIIA)
```

Tái sử dụng: server.py (152 routes đã có), executive.html/js (append-only section), Evaluation Harness (`learning/evaluation.py`), Error DB (Phase D), CIIA audit protocol.

**Không tạo:** server mới, DB mới ngoài kpi_store ADD-ONLY, POST endpoint, điểm tổng, tự đánh giá.

## 3. Bố cục 6 khu vực (master prompt §III.2)

| Khu vực | Nội dung | Nguồn Phase 3 | Trạng thái data hiện tại |
|---|---|---|---|
| A. Intelligence Overview | 12 KPI tóm tắt + coverage % + trạng thái đánh giá (BASELINE NOT ESTABLISHED…) | cisc_runs/*.json | CHƯA CÓ baseline CISC — hiển thị đúng N/A |
| B. Benchmark History | trend 7 lần chạy gần nhất (bảng + sparkline) | cisc_runs history | CHƯA CÓ — trống có nhãn |
| C. Audit Status (CIIA) | 4 giá trị: PASS / FAIL / INCONCLUSIVE / NOT RUN + link báo cáo audit | audits/ | NOT RUN |
| D. Error DB (OPEN) | danh sách lỗi OPEN + chu trình tự sửa 10 bước | data/cognitive/errors.db | Error DB Phase D chưa dựng — hiển thị trống có nhãn |
| E. Version Comparison | BASELINE V0 → COG V1: 12 KPI side-by-side + chi phí | version_comparisons | CHƯA CÓ |
| F. System Troubleshooting | trạng thái edge/Pi5/camera; Pi5 offline → BLOCKED | edge telemetry 8766 | CÓ THẬT (edge telemetry API sẵn) |

## 4. Mockup tĩnh — file

- `reports/intelligence_maturity/mockups/intelligence_dashboard_mockup.html` — standalone, dùng CSS vars của app (`--foreground`, `--muted-foreground`, `--accent`, `--border`, `--card`) → dark/light tự theo theme app; dữ liệu MINH HỌA nhãn "MOCKUP — DỮ LIỆU MINH HỌA" banner đỏ trên cùng.
- 12 KPI đúng tên CISC §2; 9/12 NOT EVALUATED đúng thực trạng baseline V0; 3 KPI đo được sớm (KPI3 50%, KPI11 PASS, KPI12 0 violations) hiển thị như baseline V0 preview.
- RED FLAG demo: KPI3 giảm >5% → highlight đỏ (minh họa cơ chế).

## 5. Phase tiếp theo (chờ owner duyệt từng phase)

| Phase | Nội dung | Rủi ro |
|---|---|---|
| 2 Data | kpi_store.py (ADD-ONLY migration có backup) + kpi_engine.py + tests | R2 |
| 3 Impl | intelligence_tab.js/css + executive.html append + 3 API + restart + verify | R2-R3 |
| 4 Baseline | benchmark_runner + CPSL mini 30 case + baseline report | R2 |
| 5 Audit | CIIA audit dashboard | R2 |
