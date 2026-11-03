# V8 — DIALOGUE PIPELINE MAP
**Ngày:** 27/10/2026 — sơ đồ đường đi hội thoại thực tế, đối chiếu code `9ff4ca9` + V7.1

```
┌────────────────────────── INPUT LAYER ──────────────────────────┐
│                                                                  │
│  Bàn phím (dashboard 8766, tab Hội Thoại)                        │
│    executive.js sendDialogueMessage() → POST /api/chat/stream    │
│    (fallback: POST /api/chat khi stream lỗi — executive.js:588)  │
│                                                                  │
│  Giọng nói (V7.1 — hội thoại liên tục / wake word / nút 🎙️)     │
│    Web Speech API vi-VN (STT cloud trình duyệt)                  │
│    wake_engine.js 9-state + AEC + chime + lệnh thoại             │
│    → fill #dialogue-input → sendDialogueMessage() → STREAM       │
│                                                                  │
│  NetChat (kênh 'Trợ lý Tony Pham' 24/7)                          │
│    responder bot → POST /api/chat (KHÔNG phải stream)            │
│                                                                  │
│  Voice interact API (Pi 5 edge / debug)                          │
│    POST /api/voice/interact → XiaoZhiVoicePipeline → role router │
│    (LUỒNG RIÊNG — KHÔNG qua LLM chat pipeline!)                  │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌────────────────────────── ROUTING ──────────────────────────────┐
│ LLMRouter.route(): explicit > deep > reasoning > fast            │
│ fast/reasoning = NetMind GLM-5.3-Flash · deep = Qwen3.5-122B     │
│ offline → LOCAL_REASONING_FALLBACK (qwen2.5:7b) → mock (tagged)  │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌────────────────────── CONTEXT BUILD ────────────────────────────┐
│ MemoryStore(brain.db)                                            │
│  ├ CognitiveRetriever.retrieve(top_k=5, max 4000/6000 chars)     │
│  ├ SessionMemoryManager.get_recent_session_history(limit=3)      │
│  │   ⚠ mỏng — BUG-V8-3                                          │
│  └ PromptContextBuilder.build():                                 │
│     [SYSTEM INSTRUCTIONS 11 quy tắc]                             │
│     [PERSONA 5 directives — xưng Em/gọi Anh]                     │
│     [CAPABILITIES — khi query hỏi năng lực]                      │
│     [COGNITIVE EVIDENCE — V5, optional]                          │
│     [APPROVED/VERIFIED MEMORY] [USER-PROVIDED] [PROCEDURES]      │
│     [PREFERENCES] [EPISODIC] [SOURCE AUDIT]                      │
│     [RECENT CONVERSATION HISTORY — 3 lượt]                       │
│     [USER REQUEST]                                               │
│                                                                  │
│  Sau đó system_instructions được GHÉP THÊM (chỉ /api/chat đủ):   │
│  ├ BỘ SỰ THẬT SỐNG (grounding_facts — probe thật)  ← stream THIẾU│
│  ├ EVIDENCE EXTERNAL (Gemini/RSS — câu thời sự)    ← stream OK*  │
│  ├ EVIDENCE TTNS (nhân sự/lịch họp)                ← stream THIẾU│
│  └ DOCUMENT RAG (kho tài liệu nội bộ)              ← stream THIẾU│
│  * stream gọi collect_external_evidence trực tiếp (tự gate)      │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌────────────────────── LLM GENERATION ───────────────────────────┐
│ /api/chat:    provider.generate(req) — block, đủ 1 khối          │
│ /api/chat/stream: provider.stream(req) — SSE delta từng token    │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌────────────────────── POST-PROCESSING ──────────────────────────┐
│ OutputGuardrails.sanitize (redact credential/script/path)        │
│ OutputGuardrails.analyze_grounding (VERIFIED/USER/INFERENCE)     │
│ persist_chat_turn (episodes + episodic memory + extract_facts)   │
│ teach_note ghép TRƯỚC reply (chỉ /api/chat có)     ← stream THIẾU│
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌────────────────────── OUTPUT LAYER ─────────────────────────────┐
│ Text: SSE delta → bubble dashboard                               │
│ Voice: speakText(finalText) → /api/voice/tts-synthesize          │
│   edge-tts vi-VN-HoaiMyNeural → Audio() → loa PC                 │
│   fallback: browser speechSynthesis (bắt buộc voice vi)          │
│ Avatar: push_avatar_speech(duration_ms=len*90 capped 15s) → Pi 5 │
└──────────────────────────────────────────────────────────────────┘
```

## Bảng trách nhiệm từng file (đã đọc toàn bộ)
| File | Vai trò | Trạng thái |
|---|---|---|
| web/server.py | 2 luồng chat + evidence wiring | stream thiếu parity (BUG-V8-1) |
| cognition/context_builder.py | 305 lines — build prompt có provenance | đủ, cần thêm [CONVERSATION GUIDANCE] |
| cognition/executive_persona.py | persona + directives | đủ |
| cognition/session_memory.py | persist + history 188 lines | depth=3 mỏng |
| cognition/teach_pipeline.py | detect_teaching 15 prefix | chỉ wire ở /api/chat |
| core/guardrails.py | sanitize + grounding 142 lines | đủ |
| llm/router.py | 3-tier 176 lines | đủ |
| tools/external_lookup.py | 2 tầng Gemini/RSS, fail-closed | đủ (cả 2 luồng) |
| voice/voice_pipeline.py | XiaoZhi pipeline + sanitize | đủ, cần từ điển đọc |
| web/static/wake_engine.js | 362 lines wake + follow-up | đủ (V7.1) |
| web/static/executive.js | dashboard + voice loop (v4.1) | đủ (V7.1) |
