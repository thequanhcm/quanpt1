# V9 — LOGICAL REASONING REPORT
**Ngày:** 28/10/2026 · Trạng thái: IMPLEMENTED + TESTED (live smoke qua API thật)

## 1. Bộ suy luận đã xây dựng (`src/quan_ai_brain/cognition/logical_reasoning.py`)

Quy trình 12 bước §V.1 cài đặt trong `LogicalReasoningEngine.answer_question()`:
(1) xác định câu hỏi → (2) truy xuất KU liên quan (token overlap + subject-head, tối đa 300 units quét / 20 trả về) → (3) thu thập bằng chứng → (4) dữ kiện nền → (5) giả định (`_assumptions`: tiền giả định trong câu hỏi, KU INFERRED đang dùng, mâu thuẫn đang bỏ qua) → (6) giả thuyết (tối đa 3 từ mâu thuẫn + 1 consistency) → (7)+(8) ủng hộ/phản bác với chống vòng tròn → (9) thiếu thông tin → (10) quyết định loại kết luận → (11) lưu steps + refs → (12) caller trình bày.

## 2. Phân loại 3 loại kết luận (đã TESTED)

| Loại | Điều kiện | Bằng chứng test |
|---|---|---|
| **A — trực tiếp** | Có KU `VERIFIED` khớp, không mâu thuẫn | test_conclusion_a_requires_verified ✅ |
| **B — suy luận** | Có KU liên quan (chưa VERIFIED), không mâu thuẫn; statement ghi rõ "chưa qua xác minh thật" | test_conclusion_b_records_reasoning_and_assumptions ✅ |
| **C — giả thuyết** | Có mâu thuẫn, hoặc không có tri thức liên quan | test_contradicted_knowledge_penalized ✅ |

INFERRED không bao giờ đủ điều kiện loại A — bảo vệ ở code path `_decide` (test_inferred_knowledge_never_treated_as_verified ✅).

## 3. Chống vòng tròn §V.3 (đã TESTED)
- `store.trace()` dùng visited-set — cycle không thể lặp vô hạn; `cycles_detected` báo nếu chuỗi bất thường.
- `_support_against()`: nhiều KU cùng `source_refs` gốc → nhóm thành **shared_origins** và **chỉ tính 1 bằng chứng độc lập** (test_shared_origin_counted_once ✅).
- KU suy luận có `derived_from` → truy vết ngược được chuỗi gốc (test_derived_chain_no_cycle ✅).

## 4. Phát hiện mâu thuẫn §V.4 (đã TESTED)
`analyze_contradiction(a, b)` trả về: quan hệ giữa hai KU, `same_scope`, phân loại **DIRECT** (cùng phạm vi — cần owner quyết) vs **CONTEXT_DIFFERENCE** (khác phạm vi — hệ thống giữ cả hai với phạm vi riêng), và `auto_resolution=None` **luôn** — hệ thống không tự chọn phía (test_contradiction_analysis_no_auto_resolution ✅).

## 5. Confidence (trung thực §IV.2)
`confidence_breakdown` trả: evidence_count, verified_count, contradiction_penalty (0.15/mâu thuẫn), shared_origins penalty (0.1/nhóm), aggregate kèm ghi chú "chỉ số khai báo, KHÔNG phải xác suất hiệu chuẩn". Không có bước nào tự sinh điểm LLM.

## 6. Giới hạn hiện tại (trung thực)
- Suy luận deterministic trên quan hệ + polarity — KHÔNG có chain reasoning đa bước phức tạp (ví dụ transitive A→B→C) ngoài trace DERIVED_FROM. Đủ theo phạm vi Slice 2; nâng cấp nếu chủ duyệt.
- Truy xuất từ khóa/thể hiện — chưa dùng BGE-M3 cho retrieve KU (đã có sẵn ở experience_semantic; có thể nối ở phiên sau).
- Kết luận loại A chỉ xuất hiện khi có KU VERIFIED — hiện có 72 memories VERIFIED nhưng chưa có KU nào VERIFIED trong knowledge_units (chỉ EXTRACTED). Đây là trạng thái trung thực: tri thức mới trích xuất chưa qua xác minh thật.
