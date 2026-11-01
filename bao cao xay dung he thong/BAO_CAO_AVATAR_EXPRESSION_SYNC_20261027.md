# BÁO CÁO: Biểu cảm avatar đồng bộ theo hội thoại (PC ↔ Pi 5)

**Mã báo cáo:** RPT-QAB-AVATAR-EXPRESSION-SYNC-20261027
**Thời điểm:** 27/10/2026 ~02:20 ICT
**Yêu cầu chủ sở hữu:** "thiết lập để thay đổi trạng thái biểu cảm khi anh chat, hỏi đáp, tùy theo các câu hỏi, hoặc trạng thái trợ lý suy nghĩ..... đồng bộ cùng hiển thị trên giao diện Pi5 về trạng thái biểu cảm khi giao tiếp, chat, tương tác"

## 1. Kiến trúc phát hiện & hoàn thiện

Chuỗi điều khiển biểu cảm Pi 5 đã có sẵn (kiosk daemon 8768 + kiosk.js) nhưng **chat PC chưa nối vào**:

```
PC chat (/api/chat hoặc /api/chat/stream)
  → 2.55 push_avatar_thinking()        → Pi5: THINKING (kèm "Đang suy nghĩ...")
  → 2.6  nếu câu hỏi thời sự:
         push_avatar_expression("RESEARCHING") → Pi5: RESEARCHING ("Đang tra cứu thông tin ngoài...")
  → LLM trả lời
  → 4.5  push_avatar_speech(reply)     → Pi5: SPEAKING + hiển thị lời thoại
         (sau duration_ms: PC đặt IDLE vào telemetry; daemon Pi tự reset kiosk)
  → nếu LLM lỗi: BLOCKED (🛡️ trên mặt)
```

Kênh đẩy: `_send_edge_request` → `POST http://192.168.1.21:8768/api/kiosk/control` `{action:"set_expression"|"speak", state, transcript}` — đúng API kiosk daemon đã có. kiosk.js poll `/api/kiosk/status` mỗi 1s → đổi biểu cảm mặt (SVG lông mày/miệng, CSS, ký hiệu 📬🛡️⚠️❄️).

## 2. Bug quan trọng đã bắt trong lúc test E2E

**Heartbeat Pi 5 định kỳ pull `target_avatar_state` + `transcript` từ PC** (`/api/executive/edge/heartbeat` → daemon `_process_core_heartbeat_response` apply về máy). Push đầu tiên hoạt động nhưng **vài giây sau bị heartbeat ĐÈ ngược bằng state/transcript CŨ** trong `_GLOBAL_EDGE_TELEMETRY`.

**Fix tận gốc:** `push_avatar_expression`/`push_avatar_speech` cập nhật `_GLOBAL_EDGE_TELEMETRY` cùng lúc; speech hẹn giờ đặt IDLE vào telemetry sau khi đọc xong — heartbeat và push giờ cùng nguồn sự thật.

## 3. E2E kiểm chứng trên Pi 5 thật (LAN 192.168.1.21)

| Thời điểm | avatar_state | transcript |
|---|---|---|
| T+2.5s (đang tra cứu) | **RESEARCHING** | "Đang tra cứu thông tin ngoài..." |
| Sau chat +0.5s | **SPEAKING** | câu trả lời thời tiết mới (báo chí 26/10) |
| Sau chat +16s | **IDLE** | (giữ transcript, hết đọc) |

Câu hỏi thường (không tra cứu): THINKING → SPEAKING → IDLE tương tự.

## 4. Test & commit

- **11 test mới** (`tests/test_avatar_expression_sync.py`): action/endpoint đúng, cắt transcript 300/text 600 chars, offline → False không raise, telemetry đồng bộ, auto-reset IDLE, **STATE_CONFIG khớp kiosk.js** (đọc edge_client.tar.gz — chặn lỗi đẩy state kiosk không hiểu).
- Full regression: **684 passed**, 2 skipped (Pi hardware), 1 fail cũ đã biết (Ollama OFFLINE).
- Mọi push fire-and-forget timeout ≤3s — Pi 5 offline không ảnh hưởng tốc độ chat.

## 5. Trạng thái

Đã test E2E thật trên Pi 5. Còn lại (đề xuất Sprint sau): nối biểu cảm cho kênh NetChat (responder đi qua /api/chat 8765 nên đã được phủ sẵn — xác nhận thêm khi kênh rảnh), voice pipeline barge-in có thể cần THINKING→LISTENING.
