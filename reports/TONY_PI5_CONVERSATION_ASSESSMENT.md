# TONY PI5 CONVERSATION ASSESSMENT — Hội thoại giống người trên Pi5
**Cập nhật:** 01/11/2026 16:45 · PHẦN VIII

## 8.1. Ngôn ngữ

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| Tiếng Việt tự nhiên | ✅ | toàn bộ DM + dashboard tiếng Việt |
| Xưng hô đúng văn hoá | ✅ | "em"/"anh Quân" cố định |
| Giải thích / phản biện | ✅ | báo cáo root-cause có lý lẽ |
| Thuật ngữ chuyên ngành | ✅ | HMAC, fail-closed, mirror… |
| Nói ngắn / phân tích sâu | ✅ | DM ≤600 ký tự vs báo cáo đầy đủ |
| Không lặp máy móc | ✅ | biến thể theo ngữ cảnh |

## 8.2. Hội thoại

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| Context continuity | ✅ | conversation_state TTL 10' + per-channel |
| Multi-turn | ✅ | M5 27/27 |
| End-of-turn detection | ⚠️ | logic có; cần bài test voice thật |
| Interruption / barge-in | ⚠️ Cấp 1 | thiết kế; chưa verify phần cứng |
| Listening/Speaking/Waiting state | ✅ | kiosk state machine |
| Session recovery | ✅ | seen-state 248 ID + catch-up 12h (chứng minh lại 16:13) |

**Không phản hồi sớm khi chủ nhân nói nhiều phần:** logic catch-up + seen SAU khi gửi đã xử lý ở kênh văn bản; kênh voice cần mic thật để verify — NOT_VERIFIED.

## 8.3. Voice Pipeline

| Bước | Trạng thái | Bằng chứng |
|---|---|---|
| Wake word (4 cụm) | ✅ code | daemon voice |
| Microphone | ❌ không gắn (alsa_cards=0) | kiểm tra 31/10 |
| STT (faster-whisper) | ✅ code | test suite |
| LLM | ✅ GLM live | |
| TTS | ⚠️ Edge-TTS 403 flaky → **Q-3 Piper đã duyệt, hàng đợi** | G-33 |
| Speaker | ❌ loa BT giữ TẮT theo quyết định owner (ACK 16:10) | alert_owner_ack.json |
| Fallback | ⚠️ chờ Q-3 | |
| Latency | ⚠️ UNKNOWN voice; chat RTT ~6,8s | |
| Audio session | ✅ | lệnh "nghe từ pi" action audio sạch (31/10) |

**Bài kiểm thử tiếng Việt thật qua voice: NOT_VERIFIED** — không có mic/loa active. Đúng nguyên tắc: không đòi Cấp 2 khi phần cứng chưa có.

## 8.4. Personality

| Yếu tố | Bằng chứng |
|---|---|
| Phong cách ổn định | ✅ mọi kênh cùng persona |
| Biết lắng nghe | ✅ seen-after-send, không trả tin cũ trùng |
| Có quan điểm / phản biện | ✅ nhận xét trong báo cáo |
| Biết cảnh báo | ✅ alert engine + CLO-stall |
| Biết thừa nhận sai | ✅ "lần vá đầu sai chỗ đã xóa sạch, viết lại" |
| Biết nói thiếu dữ liệu | ✅ UNKNOWN policy |

## Điểm Pi5 Conversation: **CẤP 1 (kênh voice — chờ AUDIO + Q-3) nhưng kênh văn bản NetChat = CẤP 2 (làm việc thật cả ngày hôm nay).** Hai lệnh chờ duyệt quyết định điểm số: AUDIO (mic/loa USB) + Q-3 (Piper).
