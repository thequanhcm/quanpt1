# M1 — VOICE HEALTH REPORT

**Người lập:** TONY · **Thời điểm đo:** 01/11/2026 ~11:00 giờ VN
**Nguồn:** `voice_collector.py` — probe import engine + provider health (không gọi API tốn tiền, không in key)

## Kết quả probe thật (server 8766, E2E)

| Thành phần | Kiểm tra | Kết quả | Trạng thái |
|---|---|---|---|
| STT engine | import faster-whisper | ok — v1.2.1 (small int8 theo cấu hình voice_stt.py) | ✅ NORMAL |
| LLM NetMind (GLM-5.3-Flash) | provider.health() | READY — key present trong server env; catalog reachable | ✅ NORMAL |
| LLM Ollama fallback | TCP 11434 + /api/status | online — 8 models (qwen2.5:7b dự phòng) | ✅ NORMAL |
| TTS engine | import edge_tts + TTS manager | ok — Edge-TTS ready; manager cấu hình đa giọng (HoaiMy/NamMinh + 10 MULTI_LANGUAGE) | ✅ NORMAL |

## Fallback status

- **LLM fallback chain**: NetMind GLM (chính) → Ollama qwen2.5:7b (dự phòng) → mock (test only, bị lọc [MOCK] khỏi memories). Router `fallback_mode=never` cho chat thường.
- **TTS fallback**: Edge-TTS (cloud) chính — retry ×2 khi 403. **Piper local fallback CHƯA CÀI** (Q-3 PENDING_OWNER) → khi Edge-TTS 403 dai dẳng, TTS giảm chất lượng/ im — đây là điểm yếu đã biết, ghi nhận trung thực.
- **STT**: faster-whisper local — không phụ thuộc mạng.

## Điểm chưa đủ dữ liệu (trung thực)

| Hạng mục | Trạng thái | Lý do |
|---|---|---|
| Voice round-trip latency đo liên tục | **UNKNOWN** | M1 không chủ động gọi hội thoại (tránh phát tiếng loa khi anh chưa bật); số liệu tham chiếu 4–9s từ phiên 09:15 |
| STT error rate thực chiến | **UNKNOWN** | cần loa BT bật + hội thoại thật mới đo được |
| TTS 403 frequency | **UNKNOWN** (đã có retry ×2) | cần theo dõi qua history dài hạn |

## Nhận định

1. Chuỗi voice pipeline **khỏi ở tầng cấu hình/engine**; các phép đo runtime (latency, error rate) cần buổi test hội thoại thật khi anh bật loa.
2. Rủi ro đã biết: Edge-TTS phụ thuộc cloud Viettel gateway — **Q-3 (Piper) là mitigation đúng**; nếu anh duyệt, em cài trong venv + tự chọn engine Edge→Piper.
