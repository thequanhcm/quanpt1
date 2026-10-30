# V8 — IMPLEMENTATION REPORT
**Ngày:** 27/10/2026 · Bổ sung chi tiết kỹ thuật cho V8_FINAL_HANDOFF.md

## Kiến trúc sau V8

```
INPUT (dashboard 💬/🎙️/voice, NetChat)
        │
        ▼
POST /api/chat/stream  ──────────────┐
  1. LLMRouter (fast/reasoning/deep) │
  2. V8 PARITY LỚP (mới — P1):       │
     ├ teach pipeline ("nhớ rằng")   │ ← LIVE_VERIFIED (smoke marker persist)
     ├ grounding facts (BỘ SỰ THẬT)  │
     ├ TTNS lookup (nhân sự họp)     │
     ├ Document RAG (tài liệu)       │
     ├ V7 progress chain             │
     └ history depth 6 (trước: 3)    │
        │                            ▼
        ▼                    POST /api/chat
PromptContextBuilder.build()  (giữ nguyên + 1 block mới)
  + [CONVERSATION GUIDANCE] ← V8 P2 (classify 7 loại §3.2 → quy tắc
    độ dài/xưng hô/không lặp/không bịa/hỏi lại khi mơ hồ; kill-switch env)
        │
        ▼
LLM (GLM-5.3-Flash) → OutputGuardrails → persist (Sprint 16 hygiene)
        │
        ▼
OUTPUT: text bubble + speakText → TTS reading layer (V8 P5:
        R0-R5 đọc tự nhiên, cắt theo câu) → edge-tts vi-VN
```

## Vấn đề thiết kế đã cân nhắc (trung thực về trade-off)
1. **Tại sao guidance inject vào prompt thay vì hậu chỉnh sửa reply?**
   Hậu chỉnh sửa câu chữ của LLM dễ phá nghĩa (đặc biệt thuật ngữ). V8 §III yêu cầu "không hy sinh độ chính xác để đổi câu chữ bóng bẩy" → chỉ ĐỊNH HƯỚNG LLM trước khi viết.
2. **Tại sao normalize không thêm dấu cho text không dấu?**
   V8 §6.1: "Không được tự sửa tên riêng hoặc mã kỹ thuật theo suy đoán" — thêm dấu tự động có nguy cơ sai nghĩa tên riêng. Normalize chỉ làm sạch filler an toàn.
3. **Tại sao chat non-stream giữ limit=3?**
   Path phụ (fallback + NetChat); stream là đường chính. Nâng cả 2 làm tăng token không cần thiết khi episodic retrieval đã bù. Có thể nâng sau nếu benchmark chỉ ra nhu cầu.
4. **Rủi ro guidance xung đột system prompt gốc?**
   Block được thêm CUỐI (sau [USER REQUEST]) — không ghi đè quy tắc governance; kill-switch env để tắt ngay không cần deploy lại.

## Bằng chứng commit-sẵn-sàng
- `git status`: server.py, context_builder.py, voice_pipeline.py, vietnamese_conversation.py (NEW), test_v8_vietnamese_conversation.py (NEW), benchmark + smoke tools (NEW), 7 báo cáo V8 (NEW).
- Giữ nguyên thay đổi V7.1 chưa commit (netchat_bridge.py, executive.js/html) theo nguyên tắc preserve working tree.
