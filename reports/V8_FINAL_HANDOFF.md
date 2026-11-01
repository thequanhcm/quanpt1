# V8 — IMPLEMENTATION REPORT & FINAL HANDOFF
**Ngày:** 27/10/2026 · Sprint: TASK-V8-CONV-ENGINE (APPROVED + consumed) · HEAD: `9ff4ca9` + thay đổi V8 chưa commit

## 1. Hiện trạng ban đầu
Xem `V8_VIETNAMESE_CONVERSATION_AUDIT.md` + `V8_BASELINE_RESULTS.md` (3/14 PASS): 2 luồng chat bất đối xứng — `/api/chat` đầy đủ 9 evidence points, `/api/chat/stream` (đường đi chính của dashboard + voice + NetChat) thiếu 5 lớp. LLM (GLM-5.3-Flash) không phải bottleneck.

## 2. Lỗi giao tiếp đã phát hiện
- **BUG-V8-1/2 (parity):** dạy "nhớ rằng..." qua dashboard/voice bị BỎ QUÊN (stream không có teach pipeline) → live verify: trước fix before=after=0 episode.
- **BUG-V8-3:** history 3 lượt — quá mỏng cho "làm tiếp", "sửa phần đó".
- **BUG-V8-4:** không có lớp chuẩn hóa đầu vào (filler "ừ ơi", khoảng trắng).
- **BUG-V8-5:** TTS đọc "R5" nguyên chữ, cắt cuối câu cụt.
- BUG-V8-6 (external gate) — xác minh KHÔNG phải bug, chỉ thiếu telemetry.

## 3. Module đã sửa / tái sử dụng
| Module | Hành động |
|---|---|
| `web/server.py` `_handle_api_chat_stream` | PATCH: +teach pipeline, +grounding facts, +TTNS, +Document RAG, +V7 chain, history 3→6, teach_note/progress_check vào final frame |
| `cognition/context_builder.py` | PATCH: +[CONVERSATION GUIDANCE] block (env kill-switch `QUAN_AI_BRAIN_V8_GUIDANCE_OFF`) |
| `cognition/vietnamese_conversation.py` | NEW 210 lines: RequestKind 8 loại, classify_request, normalize_vietnamese_input (không đụng mã kỹ thuật), build_guidance_block, should_inject_guidance |
| `voice/voice_pipeline.py` | PATCH: từ điển đọc R0-R5, cắt theo câu + ranh giới từ an toàn |
| `tools/v8_conversation_benchmark.py`, `tools/v8_live_smoke_teach_stream.py` | NEW: benchmark + live smoke SSE |
| `tests/test_v8_vietnamese_conversation.py` | NEW: 37 tests §VIII nhóm A-E |
| Governance | approval card TASK-V8-CONV-ENGINE APPROVED+consumed (chỉ thị owner = MASTER PROMPT V8) |

## 4. Cải tiến đã triển khai (P1→P5 theo plan)
1. **Parity 5 lớp** stream↔chat — LIVE_VERIFIED (teach persist + 4 evidence layers).
2. **Conversation guidance** — IMPLEMENTED + TESTED (37/37): classify 7 loại, block injected vào rendered_context (verify bằng test trên context thật, không chỉ viết prompt bỏ đó), context-dependent guidance ép dùng history + hỏi lại khi mơ hồ.
3. **Input normalization** — IMPLEMENTED + TESTED (filler sạch, mã kỹ thuật giữ nguyên tuyệt đối).
4. **History depth 3→6** — IMPLEMENTED (stream; chat giữ 3 vì non-stream là path phụ, đã có episodic retrieval bù).
5. **TTS reading layer** — IMPLEMENTED + TESTED (R5→"R năm", cắt theo câu, không cụt nghĩa).

## 5. Benchmark trước → sau
**3/14 → 15/15 PASS** (chi tiết `V8_VIETNAMESE_BENCHMARK.md`; raw JSON `V8_BENCHMARK_BASELINE.json` / `V8_BENCHMARK_AFTER.json`).

## 6. Kiểm thử thực tế
- Unit V8: 37/37 PASS (0.36s).
- Full regression ×2 ĐỘC LẬP: **1108/0/1** (81.79s + 79.15s) — 1071 cũ + 37 mới = 1108 khớp tuyệt đối, 0 vỡ.
- Live: teach-via-stream persist thật (marker `V8-SMOKE-2710-1793119929`); server HEALTHY GLM-5.3-Flash.

## 7. Candidate (chưa áp dụng)
- Compact history (cắt reply >500 ký tự trong history block) — DESIGNED, chờ đánh giá tác động retrieval.
- Session_id client-side cho voice (hiện voice + text cùng session default — trộn ngữ cảnh, cần chủ quyết định).
- ASR confidence → hỏi lại thông minh: BLOCKED (Web Speech API không trả confidence; cần Whisper local = thêm dependency, cần chủ duyệt).

## 8. Giới hạn còn tồn tại
- Chất lượng "tự nhiên" của câu trả lời phụ thuộc LLM + guidance — NEEDS_LLM_EVAL độc lập (không có chấm tự động khách quan cho độ tự nhiên; benchmark đo cấu trúc, không đo văn phong).
- Voice E2E bằng giọng thật (nghe → trả lời → nghe tiếp) chưa test có người thật — cần anh nói thử dashboard.
- Voice/interact (Pi edge) vẫn đi role-router riêng — không thuộc 2 luồng chat chính, không parity trong sprint này (đúng thiết kế hiện có).

## 9. ASR/TTS chưa tích hợp / chưa xác minh
- ASR offline (Whisper/Vosk): CHƯA tích hợp — BLOCKED chờ thiết kế + duyệt dependency.
- ASR reliability score: KHÔNG CÓ (Web Speech API limitation) — không thể dùng độ tin cậy để hỏi lại tự động.
- Pi 5 kiosk voice: chưa nối mạng trong phiên test — UNVERIFIED (skip cũ giữ nguyên).

## 10. Trạng thái kích hoạt thực tế
| Thành phần | Trạng thái |
|---|---|
| Parity 5 lớp stream | **LIVE_VERIFIED** (server PID mới đang chạy) |
| Conversation guidance | **LIVE** (tự động với query tiếng Việt; kill-switch env) |
| Normalize input | **LIVE** (dùng trong guidance path) |
| TTS reading layer | **LIVE** (mọi lời đọc qua sanitize) |
| Benchmark + tests | **TESTED** (15/15 + 37/37 + regression 1108) |
| Compact history | DESIGNED |
| ASR offline / reliability | BLOCKED |
| Voice E2E giọng thật | CHỜ CHỦ NGHIỆM THỬ |

## Điều kiện nghiệm thu §X — đối chiếu
- [x] Đường đi hội thoại thực tế — audit + map
- [x] Nguyên nhân lỗi chính — 6 bug có bằng chứng
- [x] Lớp diễn đạt tiếng Việt — guidance + normalize
- [x] Duy trì ngữ cảnh — history 6 + guidance context-dependent
- [x] Quy tắc xử lý mơ hồ — hỏi lại 1 câu, không đoán đối tượng
- [x] Hạn chế lặp ý — guidance không lặp yêu cầu/kết luận
- [x] Benchmark tiếng Việt — 15 checks + 37 tests
- [x] Chạy trước và sau — 3/14 → 15/15
- [x] Hồi quy — 1108/0/1 (baseline 1071 + 37 mới, 0 vỡ)
- [x] Thuật ngữ kỹ thuật — test giữ nguyên TASK-123/8766/R5 khi cần
- [x] Không đủ dữ liệu — guidance fail-honest + test E
- [x] Voice pipeline thực tế — TTS layer live; ASR: trung thực là chưa có score
- [x] Giới hạn & quyền hạn không đổi — không đụng governance/R0-R5/approval
- [x] Báo cáo + ghi nhận chưa hoàn thành — chính file này
