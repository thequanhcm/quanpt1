# V8 — BASELINE RESULTS (TRƯỚC KHI NÂNG CẤP)
**Ngày:** 27/10/2026 · Chạy `tools/v8_conversation_benchmark.py baseline` tại HEAD `9ff4ca9` (code V7.1 chưa commit giữ nguyên)
**Kết quả:** **PASS 3/14 — FAIL 11** · Chi tiết máy đọc: `V8_BENCHMARK_BASELINE.json`

## A — Parity stream vs non-stream (0/6 PASS)
| Lớp năng lực | /api/chat | /api/chat/stream |
|---|---|---|
| Teaching pipeline | ✅ 2 refs | ❌ 0 refs |
| Grounding facts (BỘ SỰ THẬT SỐNG) | ✅ 2 refs | ❌ 0 refs |
| TTNS lookup | ✅ 2 refs | ❌ 0 refs |
| Document RAG | ✅ 2 refs | ❌ 0 refs |
| V7 progress chain | ✅ 1 ref | ❌ 0 refs |
| History depth ≥6 | — | ❌ limit=3 |

## B — Lớp tiếng Việt (2/6 PASS)
- ❌ Module chuẩn hóa đầu vào: chưa tồn tại (ImportError)
- ❌ Phân loại 7 loại yêu cầu §3.2: chưa tồn tại
- ❌ [CONVERSATION GUIDANCE] trong rendered_context: chưa wire
- ✅ Context gốc không bị phá (backward baseline)
- ❌ TTS từ điển đọc mã: "R5", "TASK-123" giữ nguyên chữ → đọc máy móc
- ✅ Không cắt giữa câu (hiện trạng chấp nhận được)
- ✅ Đọc số/quy mô ổn (edge-tts tự xử lý 1071)

## C — Live behavioral (0/1)
- ❌ **Dạy qua stream KHÔNG persist** (before=0, after=0, reply_ok=False do HTTPTransport error — stream hiện trả SSE, benchmark POST thuần chưa parse frame; ĐỒNG THỜI code thực tế xác nhận KHÔNG có detect_teaching trong stream handler — bug thật bằng 2 bằng chứng độc lập: grep code + live test)

## Kết luận baseline
Trợ lý thật sự đang **mất 5 lớp năng lực** trên luồng hội thoại chính (dashboard/voice/NetChat). Số 11/14 FAIL là hiện trạng trung thực TRƯỚC nâng cấp — dùng làm mốc so sánh bắt buộc cho V8_REGRESSION_RESULTS.
