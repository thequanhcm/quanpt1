# V7.1 VOICE CONVERSATION UPGRADE — 27/10/2026

## Yêu cầu chủ nhân
Ảnh `image_c7d2ca.png`: (1) lỗi "NetChat send error: Unparseable NetChat response" trên dashboard; (2) "kiểm tra xử lý, nâng cấp để anh có thể trao đổi bằng lời thoại với trợ lý".

## Phần 1 — FIX lỗi NetChat send (LIVE VERIFIED)

### Root cause (audit-first, reproduce được)
`netchat_bot.py` (skill script) sau bước `--confirmed` in stdout theo thứ tự:
```
BOT: bot_quanpt1 (edojmne9d7gcxx8axu1mzas3pr)
TARGET: P Trợ lý Tony Pham [2 members]
{...JSON post object...}
```
`_parse_json_or_raise()` trong `src/quan_ai_brain/integration/netchat_bridge.py:65`
gọi `json.loads(toàn bộ stdout)` → JSONDecodeError →
`NetChatBridgeError("Unparseable NetChat response")` — dù **tin nhắn THẬT đã gửi
thành công** (post id có thật, xác minh 2 lần qua script trực tiếp).

### Fix
`_parse_json_or_raise()` (netchat_bridge.py:65): fallback quét từng dòng từ
dưới lên, `json.JSONDecoder().raw_decode()` dòng JSON hợp lệ đầu tiên.
Không đụng skill script (nằm ngoài workspace). Backward compatible.

### Bằng chứng
- Reproduce trước fix: `json.loads(whole) FAILS` / sau fix parse OK (in-process).
- LIVE: `POST /api/executive/netchat/send` (đúng path dashboard 8766) →
  `{"success": true, "post_id": "pfpsqaxt53fm5jttqpu6gz9z6o"}`.
- Test NetChat liên quan: 43/43 PASS.

## Phần 2 — NÂNG CẤP thoại: Chế độ hội thoại liên tục

### Audit trạng thái trước nâng cấp
Đã có sẵn (dashboard 8766):
- STT Web Speech API vi-VN (nút 🎙️ bấm-mỗi-lần) — executive.js:675
- Wake word rảnh tay "Tony ơi" + follow-up 20s — wake_engine.js (đầy đủ 9 state,
  AEC, chime, lệnh thoại)
- TTS edge-tts vi-VN-HoaiMyNeural server-side + fallback browser vi voice
- Multi-turn context: conversation_history limit=3 (server.py:1192)
- Pipeline thoại XiaoZhiVoicePipeline 9-state + mouth sync + sanitize (275 lines)

### Khoảng trống
Không có chế độ **nói liên tục không cần wake word** — anh phải bấm mic lại sau
mỗi câu trả lời, hoặc gọi "Tony ơi" trước mỗi câu.

### Triển khai (executive.js v4.1 + executive.html)
1. **Nút "💬 Hội thoại: BẬT/TẮT"** (`btn-conv-mode`) cạnh nút Đọc.
2. Vòng hội thoại: STT liên tục (tự re-arm) → `/api/chat/stream` → TTS đọc →
   **tự nghe tiếp** câu sau — không bấm mic, không wake word.
3. Đồng bộ lifecycle chính xác: đếm audio in-flight (`convTtsPlaying`), chỉ
   re-open mic SAU KHI đọc xong; chống loop chết (`isAwaitingReply` debounce,
   no-speech/aborted không phá vòng, leak self-heal 120s).
4. **Lệnh thoại "dừng hội thoại"** (hoặc "tắt hội thoại" / "stop conversation").
5. **FIX BUG THẬT kẹt THINKING/SPEAKING**: khi "🔇 Đọc: TẮT", `speakText()`
   `return` sớm → không ai gọi `notifySpeakingEnd()` → wake engine kẹt vĩnh
   viễn sau 1 tin nhắn (không AI gọi notifyThinking → onend không re-arm).
   Giờ: TTS tắt vẫn đóng chu kỳ speech → avatar IDLE + mic re-arm.
6. Xung đột wake-word vs conv-mode xử lý 2 chiều: bật conv → wake pause; tắt
   conv → wake resume nếu trước đó đang bật.

### Bằng chứng
- `node --check` executive.js + wake_engine.js: OK.
- Test voice hiện có: 25/25 PASS (voice_api 5 + voice_first_pipeline 11 +
  wake_word_config 9).
- Server phục vụ code mới (grep từ HTTP: 8 refs startConvListening, nút mới
  trong HTML); file tĩnh đọc trực tiếp từ disk, không cần restart.
- Regression full suite ×2 ĐỘC LẬP: **1071 passed / 0 failed / 1 skipped**
  (80.20s + 82.63s; skip cũ = test_vietnamese_tts.py:266 Pi5 chưa nối mạng —
  không đổi so với baseline V7 trước nâng cấp).

## Giới hạn trung thực (fail-honest)
- STT dùng Web Speech API (Google cloud STT phía trình duyệt) — KHÔNG phải
  offline. Offline STT cần Whisper/Vosk local — chưa làm (Cấp 3 đề xuất).
- Chưa test bằng giọng nói thật E2E (cần chủ nhân mở dashboard nói thử) —
  code path đã verify bằng syntax + unit test + live HTTP, nhưng "nghe - trả
  lời - nghe tiếp" thật sự cần người dùng thật với mic thật.
- Pi 5 edge client (mic phần cứng) đi path riêng `/api/executive/edge/audio/*`
  — không đổi trong increment này.

## Files changed
- `src/quan_ai_brain/integration/netchat_bridge.py` (fix parse)
- `src/quan_ai_brain/web/static/executive.js` (conv mode + speakText lifecycle + bug fix)
- `src/quan_ai_brain/web/static/executive.html` (nút mới + cache v4.1)
