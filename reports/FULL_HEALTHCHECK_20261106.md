# FULL HEALTHCHECK TONY — 06/11/2026 21:00–21:15 (+07)

> Phạm vi: toàn bộ 4 lớp TONY sau khi merge PR #1/#8 và trước Sprint 1. Kết luận từng mục kèm bằng chứng thật.

## Lớp 1 — PC Cognitive Core (8765 + 8766)

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Servers 8765+8766 | ✅ UP (PID 4908, watchdog giám sát) | netstat LISTENING; /api/status 200 ×2 |
| LLM runtime | ✅ NetMind Cloud — zai-org/GLM-5.3-Flash, catalog reachable, api_key present | /api/status llm block |
| Chat E2E | ✅ 200, provider=netmind, is_mock=false | "báo cáo tình trạng" → trả lời thật 8.9s; "1+1" → 3.1s |
| Brain DB | ✅ HEALTHY (2.955 episodes, 5.051 semantic) | /api/health |
| Tab 10 Deep Memory | ✅ 200 — 150 tri thức thật | /api/memory/deep/stats sau restart |
| Health overall | ⚠️ DEGRADED — duy nhất ollama_daemon OFFLINE | Đúng known state: Ollama đã gỡ chủ đích, UI đã báo NetMind Cloud |
| Watchdog/Responder/Learning | ✅ 4 cặp process chạy (venv+py311 shim) | wmic inventory |

## Lớp 2 — Kênh DM NetChat

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Responder | ✅ PID 22648 sống, answered_ids=409 (tăng từ 406) | responder_state.json |
| stdout | ✅ sạch — không fatal pattern; dòng cuối "✅ Response sent!" | log 10.5KB |
| Confirm gate 2 bước | ✅ hoạt động (auto-confirm token trong log) | stdout |

## Lớp 3 — Voice Pipeline

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| 7 voice modules import | ✅ OK toàn bộ | python -c import |
| VoiceState | ✅ 9 trạng thái đầy đủ (không phải 3 như gap analysis viết trước — đã sửa) | VoiceState enum |
| /api/voice/interact (PTT) | ✅ 200 trong 0.6–0.7s, TTS audio thật 27.5KB + mouth_timeline | 3 câu test |
| /api/voice/tts-synthesize | ✅ 200, 14.4KB audio | sweep chốt |

## 🐛 BUG NGHIÊM TRỌNG TÌM THẤY + ĐÃ FIX (root cause "TONY ơi" im lặng)

- **Hiện tượng:** log edge Pi5 19:52–19:53: `POST lỗi (converse/tts-synthesize): Connection timed out` — hội thoại giọng nói Pi5→PC chết im lặng.
- **Root cause:** `client_daemon.py` **hardcode IP PC cũ `100.102.120.6`** ở 4 chỗ (voice_command, converse, tts-synthesize, hdmi_event) — IP Tailscale PC đã đổi thành `100.92.219.98`; kiosk/heartbeat dùng `config.json` nên vẫn sống, riêng voice loop bắn vào IP chết.
- **Fix:** thay 4 hằng bằng `_resolve_core_base_url()` đọc `config.json` (nguồn duy nhất, IP đổi tự theo) — commit kèm PR #9.
- **Minh chứng sau fix:** converse từ Pi5 → PC phản hồi **0.77s** với lỗi nghiệp vụ đúng (WAV test quá nhỏ) thay vì timeout; sha256 Pi5 = PC (`045741f4e07c6f65`); quan_ai_edge active.

## Lớp 4 — Pi5 Hình Thể

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| quan_ai_edge + bluetooth + BT-NAP | ✅ active | systemctl |
| selector + wifi-watchdog | ✅ oneshot theo timer 60s/90s — exit 0/SUCCESS là bình thường | list-timers |
| Kiosk | ✅ core_connected=True, avatar IDLE, core 100.92.219.98:8766 | /api/kiosk/status |
| Camera IMX708 | ✅ hardware detected, OFF (privacy đúng) | /api/kiosk/camera/status |
| Audio | ✅ Jieli UAC, mic ON, wake_word ON, −18dB READY, 16kHz | /api/kiosk/audio/status |
| Selector quyết định | ✅ MESH RTT 46ms (LAN null, BT null) | ~/.tony_channel_state.json |
| Edge log sau 19:53 | ✅ không còn lỗi | journalctl |

## Đánh giá "nói chuyện, giao tiếp, hoạt động trơn chu"

- **Nói chuyện (text):** ✅ trơn chu — chat 2 chiều qua GLM-5.3-Flash thật.
- **Giao tiếp DM:** ✅ 409/409 tin owner đã trả lời, confirm gate hoạt động.
- **Nói chuyện (giọng nói Pi5):** ✅ sau fix — đường converse Pi5→PC đã thông (trước đó chết âm thầm vì IP cũ); đang chờ owner thử "TONY ơi" thật để LIVE_VERIFIED hoàn chỉnh.
- **Hình thể:** ✅ kiosk + camera + mic READY; BT-PAN chờ pair.

## Việc còn mở

1. Owner test "TONY ơi" thật trên Pi5 → chốt LIVE_VERIFIED voice.
2. Pair TONY-PI5 (bấm Connect khi PIN khớp) → kênh BT thứ 3.
3. Sprint 1 (Voice Engine): AEC + đo latency + barge-in E2E — chờ duyệt.
