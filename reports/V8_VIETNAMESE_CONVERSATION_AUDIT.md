# V8 — VIETNAMESE CONVERSATION AUDIT
**Ngày:** 27/10/2026 · **HEAD:** `9ff4ca9` (feature/cognitive-state-integration) · **Baseline:** 1071 passed / 0 failed / 1 skipped (84.82s, chạy lại đầu sprint)
**Approval card:** TASK-V8-CONV-ENGINE — APPROVED + consumed (chỉ thị owner = MASTER PROMPT V8 desktop chat 27/10)

## 1. Đường đi hội thoại THỰC TẾ (đã đọc code, không suy đoán)

### 1.1 Text — hai luồng KHÔNG đồng nhất
| Thành phần | `/api/chat` (1085-1565) | `/api/chat/stream` (1566-1745) |
|---|---|---|
| Routing (LLMRouter fast/reasoning/deep) | ✅ | ✅ |
| Memory retrieval (top_k=5) + PromptContextBuilder | ✅ (max 6000) | ✅ (max 4000) |
| Session history (3 lượt gần nhất) | ✅ limit=3 | ✅ limit=3 |
| **Teaching pipeline** ("nhớ rằng...", "từ giờ...") | ✅ server.py:1164-1187 | ❌ **KHÔNG CÓ** |
| **Living Grounding Facts (BỘ SỰ THẬT SỐNG)** | ✅ 1211-1218 | ❌ **KHÔNG CÓ** |
| **External lookup** (tin tức, giá — Gemini+RSS) | ✅ gate `should_lookup_external` 1237 | ⚠️ gọi thẳng `collect_external_evidence` (tự gate bên trong — an toàn nhưng mất telemetry + không kiểm soát tier) |
| **TTNS lookup** (nhân sự/lịch họp nội bộ) | ✅ 1254-1280 | ❌ **KHÔNG CÓ** |
| **Document RAG** (quy trình/sổ tay nội bộ) | ✅ 1282-1303 | ❌ **KHÔNG CÓ** |
| OutputGuardrails sanitize + grounding analysis | ✅ | ✅ |
| Persist chat turn (Sprint 16 hygiene) | ✅ | ✅ |
| V7 progress chain | ✅ 1485-1507 | ❌ **KHÔNG CÓ** |
| Avatar expression sync | ✅ | ✅ |

**Dashboard 8766 (executive.js:507/588) + voice conversation + NetChat tab (3510) đều đi `stream` path** → anh đang nói chuyện qua luồng THIẾU 4-5 lớp năng lực.

### 1.2 Voice pipeline (đã tồn tại, V7.1 vừa nâng cấp)
- **STT:** Web Speech API vi-VN (trình duyệt) — `executive.js` + `wake_engine.js` (9-state, AEC, chime, follow-up 20s). Chế độ hội thoại liên tục (nút 💬) mới thêm 27/10.
- **Brain:** voice → text → `/api/chat/stream` → TTS.
- **TTS:** edge-tts `vi-VN-HoaiMyNeural` server-side (`/api/voice/tts-synthesize`) + fallback browser vi voice; `sanitize_for_spoken_vietnamese` (voice_pipeline.py:52-103): strip code/JSON/URL/markdown, giới hạn 350 ký tự.
- **XiaoZhiVoicePipeline** (voice_pipeline.py, 275 lines): 9-state machine, barge-in <10ms, correction patterns ("à nhầm", "ý anh là"), wake config, mouth sync.
- **Chưa có:** ASR reliability score (Web Speech API không trả confidence) → không thể "dùng độ tin cậy để hỏi lại" như §6.1 yêu cầu. ASR offline (Whisper/Vosk) chưa tích hợp.

### 1.3 Persona & context
- `DEFAULT_SYSTEM_INSTRUCTIONS` (context_builder.py:16-29): 11 quy tắc — có sẵn đúng hướng V8 (trả lời ngắn 2-5 câu, không hỏi lòng vòng, xưng Em/tại... nhưng viết dạng mệnh lệnh rời rạc).
- `ExecutivePersona` (executive_persona.py, 438 lines): 5 directives, xưng hô chuẩn, format_for_prompt().
- `[RECENT CONVERSATION HISTORY]` block: history chỉ 3 lượt, **chưa có cơ chế tách "dữ kiện đã xác nhận" vs "truy xuất dài hạn"** trong context (V8 §4.1).
- Session memory: episodes 1434 chat_turn, persist 2 chiều (query+reply), extract_user_facts tự động.

## 2. LỖI GIAO TIẾP ĐÃ PHÁT HIỆN (bằng chứng cụ thể)

### BUG-V8-1 (NGHIÊM TRỌNG — Parity): Stream path thiếu 4 lớp năng lực
Dashboard + voice + NetChat đều qua stream → anh dạy "nhớ rằng..." **bị bỏ quên**, câu hỏi nhân sự TTNS không tra cứu, hỏi quy trình nội bộ không RAG, hỏi tin tức mất telemetry. Đây là nguyên nhân số 1 của "quên ngữ cảnh / không nhớ điều đã dạy" trong hội thoại thật.

### BUG-V8-2: Teaching detect lệch phạt với giọng nói
Anh nói thoại "nhớ giúp em: họp 8h mai" → stream không có teach pipeline → im lặng. (Kết hợp BUG-V8-1.)

### BUG-V8-3: History depth 3 lượt — quá mỏng cho trao đổi nhiều lượt
`limit=3` (server.py:1192/1634) — câu "sửa phần đó" sau 4+ lượt/mở lại phiên là mất đối tượng. V8 §4.2 yêu cầu xử lý câu phụ thuộc.

### BUG-V8-4: Không có lớp chuẩn hóa đầu vào tiếng Việt không dấu
ASR trả text có thể mất dấu ("kiểm tra tien do"); `find_matching_skills` (V6) đã học bài này (không dấu không match), external_lookup patterns có cả 2 dạng, nhưng **chưa có module chuẩn hóa dùng chung**.

### BUG-V8-5: sanitize_for_spoken_vietnamese đọc sai số/mã
Chưa có từ điển đọc: "R5" đọc "R năm"? edge-tts đọc "8766" ổn nhưng "TASK-xxx", "8h30", "%" cần quy tắc. Đang strip thô 350 ký tự — có nguy cơ cắt giữa câu.

### BUG-V8-6 (đã xác minh KHÔNG phải bug): External gate trong stream
`collect_external_evidence` tự gọi `should_lookup_external` bên trong (external_lookup.py:332) — không tốn quota cho câu nội bộ. Chỉ thiếu telemetry (`_GLOBAL_EDGE_TELEMETRY["target_avatar_state"]` RESEARCHING có trong stream rồi).

## 3. Điểm MẠNH hiện có (không đập đi xây lại)
- Grounding analysis (VERIFIED/USER_PROVIDED/GENERAL_INFERENCE) — đúng triết lý fail-honest.
- Sprint 16 memory hygiene (không lưu system_prompt vào episodes).
- Router 3-tier + local fallback + mock-tagging nghiêm ngặt.
- V7 progress chain, CLO, TaskPipeline — evidence trail đầy đủ ở /api/chat.

## 4. Kết luận audit
Vấn đề KHÔNG nằm ở LLM (GLM-5.3-Flash tiếng Việt tốt) mà ở **đường đi bất đối xứng**: năng lực bị cài vào luồng cũ `/api/chat` trong khi toàn bộ giao tiếp thật đi `stream`. Ưu tiên sửa theo đúng thứ tự 1-10 của V8: parity trước, context/guidance sau, benchmark để chứng minh.
