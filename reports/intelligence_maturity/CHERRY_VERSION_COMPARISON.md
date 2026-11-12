# CHERRY_VERSION_COMPARISON — thiết kế so sánh phiên bản
**Trạng thái:** PROPOSED — Phase E. BASELINE V0 đã có (14 probes, 11/11) — version đầu tiên trong chuỗi.

## 1. Chuỗi phiên bản chuẩn
| Version | Ngày | Nội dung | Benchmark nào |
|---|---|---|---|
| BASELINE V0 | 11/11/2026 | 14 probes 8 nhóm, 9 PASS/3 FAIL/2 PARTIAL | Probe set P0 (file JSON) |
| COG V1 | (sau COG-0..1) | + trust engine + working memory + dedupe | P0 + CPSL mini (30 case) |
| COG V1.1 | (sau COG-2) | + retrieval 10.874 + hypothesis/causal | CPSL full |
| COG V2 | (sau COG-3..5) | + self-monitor + metacognition engine | CPSL full + CISC 12 KPI |

Quy tắc: mỗi version = 1 tag git + 1 file kết quả benchmark có sha256 + 1 entry trong bảng này. KHÔNG đổi benchmark giữa các version (hoặc nếu đổi phải chạy lại V cũ trên benchmark mới — đồng nhất so sánh).

## 2. Bảng so sánh bắt buộc (mỗi lần nâng version)
| Chiều | Nguồn |
|---|---|
| 12 KPI CISC (kể cả NOT EVALUATED) | CISC runs |
| Lỗi mới xuất hiện | Error DB diff |
| Lỗi cũ đã khắc phục | Error DB status=VERIFIED_FIXED |
| Regression (KPI giảm) | Version table |
| Chi phí: LLM calls, tokens, thời gian chạy benchmark | Runner logs |
| Độ trễ pipeline thật | /api/voice/interact timing + server logs |
| RAM/commit của servers | Get-CimInstance trước/sau |
| Độ ổn định (2 lần chạy benchmark khớp) | Runner repeat |
| Khả năng bài toán mới (OOD) | CPSL OOD split |

## 3. Quy tắc tuyên bố "V2 tốt hơn V1" (fail-honest)
Chỉ được tuyên bố khi ĐỒNG THỜI:
1. ≥1 KPI mục tiêu tăng có ý nghĩa (≥5 điểm % trên ≥30 case) với hidden tests.
2. 0 KPI khác giảm >5% (regression stability).
3. Chi phí (LLM calls/time/RAM) không tăng >2× không giải thích được.
4. CIIA của V2 không phải FAIL.
5. Không có governance violation mới.
Nếu chỉ 1-4 đạt một phần → tuyên bố "PASS WITH LIMITATIONS" kèm chi tiết, KHÔNG tuyên bố thắng thẳng.

## 4. Chống "tốt hơn vì có thêm module"
Bất kỳ tuyên bố nào phải trỏ về file benchmark (hash) + sample cases đọc được (CIIA đối chiếu ngẫu nhiên 10% cases). Số module mới thêm/số dòng code KHÔNG được xuất hiện trong bảng chính — chỉ ở phụ lục "diễn giải", không mang tính bằng chứng.

---
*Đã so sánh được ngay hôm nay: BASELINE V0 chỉ có 1 version — bảng so sánh đầy đủ bắt đầu từ COG V1.*
