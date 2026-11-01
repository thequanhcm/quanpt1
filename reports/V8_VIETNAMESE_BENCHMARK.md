# V8 — VIETNAMESE BENCHMARK
**Ngày:** 27/10/2026 · Công cụ: `tools/v8_conversation_benchmark.py` (baseline/after) + `tests/test_v8_vietnamese_conversation.py` (37 unit tests)

## Thiết kế benchmark (đúng §VIII)
- **Nhóm A — Parity cấu trúc:** 5 lớp evidence (teach/grounding/TTNS/RAG/V7-chain) phải có mặt ở CẢ 2 luồng chat; depth history.
- **Nhóm B — Lớp tiếng Việt:** normalize (filler/mã kỹ thuật), classify 7 loại §3.2, guidance block trong rendered_context, backward-compat, kill-switch.
- **Nhóm C — Live behavioral:** dạy qua stream → persist thật vào brain.db (SSE parse chuẩn, không curl).
- **Nhóm D (unit tests):** hội thoại giọng nói — từ điển đọc mã, không cắt giữa câu, strip code.
- **Nhóm E (unit tests):** độ tin cậy — fail-honest cues, guardrails còn hoạt động, không tự chế dấu tiếng Việt.

**Chấm điểm khách quan:** PASS/FAIL theo tiêu chí xác định trước (grep code structure, pytest assertions, DB persist check). KHÔNG dùng LLM tự chấm. Các chất lượng "tự nhiên" cần đánh giá độc lập → ghi NEEDS_LLM_EVAL trong handoff (trung thực).

## Kết quả TRƯỚC → SAU
| Metric | Baseline | After | Δ |
|---|---|---|---|
| Benchmark tổng | **3/14 PASS** | **15/15 PASS** | +12 |
| Nhóm A parity | 0/6 | 6/6 | +6 |
| Nhóm B tiếng Việt | 2/6 | 7/7 | +5 |
| Nhóm C live | 0/1 | 1/1 | +1 |
| Unit tests V8 | — (chưa có) | 37/37 PASS | NEW |
| Full regression | 1071/0/1 | chạy lại (xem REGRESSION_RESULTS) | giám sát |

Chi tiết từng check (bằng chứng raw): `V8_BENCHMARK_BASELINE.json` · `V8_BENCHMARK_AFTER.json`

## Baseline ghi nhận trung thực
3 PASS trong baseline = những gì ĐÃ ĐÚNG từ trước (context gốc không vỡ, TTS không cắt giữa câu, đọc số ổn). 11 FAIL là nguyên nhân thực của "trợ lý quên, trả lời dài dòng, thiếu tự nhiên" — không phải do LLM.

## Kịch bản §VIII chưa phủ (trung thực)
- Case hội thoại D "người dùng ngắt lời thật" — cần mic + người nói thật (chờ chủ).
- Case B "khôi phục nhiệm vụ sau khi mở lại phiên" — session_id hiện do client giữ; benchmark chỉ verify history depth, chưa verify cross-session recall E2E.
- Nhóm C "yêu cầu vượt quyền hạn" — đã có PolicyEngine + approval cards (test riêng), không nhân bản vào benchmark để tránh trùng lặp test governance.
