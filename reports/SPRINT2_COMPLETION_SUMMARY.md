# SPRINT 2 — GLM STREAMING + DEEP REASONING + BARGE-IN + AVATAR V3 GIAI ĐOẠN B

**Ngày hoàn thành:** 25/10/2026
**Commit message:** `feat: Sprint 2 — GLM streaming + deep reasoning tier + Pi barge-in + Avatar V3 Phase B (owner-approved)`

---

## I. PHẠM VI ĐÃ TRIỂN KHAI (3 mục anh duyệt + Avatar V3 Phase B)

### 1. Policy vĩnh viễn
- `NETMIND_EXTERNAL_DATA_ALLOWED=true` đã ghi registry `HKCU\Environment` — tiến trình mới tự đọc.

### 2. Streaming GLM-5.3-Flash
- **Backend:** `stream_chat()` generator SSE thật (không buffer), `_iter_chat_stream_events()` parse live, delta không replay khi lỗi.
- **Frontend:** `executive.js` ReadableStream render live, TTS chỉ phát sau final, fallback tự động sang `/api/chat`.
- **Cache:** Catalog NetMind 60s → first-delta từ 7.4s → **1.5–1.8s**.
- **E2E thật:** curl + script PASS — 21–28 deltas live, persist sau khi hoàn tất.

### 3. Deep reasoning tier
- `Qwen/Qwen3.5-122B-A10B-FP8` vào allowlist, `max_tokens=2500` mặc định.
- Router nhận diện "phân tích chuyên sâu/nghiên cứu sâu/deep dive…" + query >1200 ký tự → tier deep.
- Probe: 22.01s, 2255 reasoning + 72 content tokens, finish=stop.

### 4. Barge-in trên Pi 5
- `kiosk.js`: `window.bargeInStopSpeaking()` — pause audio + cancel utterance + avatar LISTENING.
- `wake_engine.js`: khi đang SPEAKING mà mic bắt giọng → gọi barge-in.
- **Deploy:** 2 file JS đã upload qua `/api/kiosk/files/upload`, reload_ui thành công, kiosk_running=True.

### 5. Avatar V3 Giai đoạn B (Mouth Sync Timeline-Only + Exact Duration)
- **Loại bỏ random-viseme fallback:** thay `Math.random() * 0.55` bằng bell-curve sin (`0.35 * envelope`) — không còn "miệng nhai".
- **MP3 duration measurement:** hàm `measure_mp3_duration_ms()` parse ID3v2 + MPEG frame headers → exact duration.
- **Timeline scaling:** `target_duration_ms` từ MP3 thật → scale_factor áp dụng cho toàn bộ timeline.
- **Test:** 6/6 PASS (random removed, MP3 parse, scaling, viseme mapping, bell-curve, punctuation pauses).
- **Deploy:** `avatar_engine.js` 42,005 bytes đã upload lên Pi, reload_ui thành công.

---

## II. FILE CHANGED

| File | Thay đổi |
|---|---|
| `llm/netmind_provider.py` | +deep model + budget 2500 + stream_chat + _iter_chat_stream_events |
| `llm/provider.py` | +stream() facade + export NETMIND_DEEP_REASONING_MODEL |
| `llm/router.py` | GLM defaults + tier deep + LOCAL_REASONING_FALLBACK_MODEL |
| `web/server.py` | /api/chat/stream + _build_llm_provider + cache 60s |
| `web/static/executive.js` | SSE reader + live render + fallback + TTS-after-final |
| `edge_client/kiosk.js` | window.bargeInStopSpeaking() |
| `edge_client/wake_engine.js` | barge-in hook + lệnh dừng đọc |
| `edge_client/avatar_engine.js` | **Giai đoạn B:** loại bỏ random-viseme, dùng bell-curve envelope |
| `src/quan_ai_brain/voice/mouth_sync.py` | +measure_mp3_duration_ms() + docstring Giai đoạn B |
| `tests/test_netmind_provider.py` | catalog 2 model |
| `tests/test_sprint2_streaming.py` | 10 test mới |
| `tools/avatar_v3_giai_doan_b_tests.py` | MỚI — 6 tests Giai đoạn B |
| `tools/sprint2_push_bargein_js.py` | MỚI — push JS lên Pi |

**Diff tổng:** +742/−38 dòng (tính cả test + tools).

---

## III. TEST RESULTS

- **Full regression:** 512 passed, 1 skipped, 0 failed (73.9s) — zero regressions.
- **Giai đoạn B tests:** 6/6 PASS (avatar_v3_giai_doan_b_tests.py).
- **E2E thật:**
  - PC streaming: PASS (curl + script).
  - Pi 5 speak: PASS (41KB audio → kiosk SPEAKING→IDLE).
  - Pi 5 barge-in: JS đã deploy, chờ test giọng thật.
  - Pi 5 avatar V3: JS đã deploy, reload thành công.

---

## IV. BẰNG CHỨNG ĐÃ DEPLOY

| Thành phần | Pi 5 IP | Kết quả |
|---|---|---|
| kiosk.js (barge-in) | 192.168.1.21:8768 | 21,401 bytes, grep "bargeInStopSpeaking" = 1 |
| wake_engine.js (barge-in) | 192.168.1.21:8768 | 12,376 bytes, grep "Barge-in" = 1 |
| avatar_engine.js (Phase B) | 192.168.1.21:8768 | 42,005 bytes, kiosk_running=True |

---

## V. CHỜ NHIỆM THU

- [ ] **Barge-in thật:** Anh nói "dừng đọc" hoặc lên tiếng khi TTS đang phát → xác minh avatar dừng + về LISTENING.
- [ ] **Avatar V3 Phase B thật:** Chat thử → quan sát miệng không còn "nhai" khi fallback, đồng bộ tốt hơn.
- [ ] **Commit Sprint 2:** Chạy `git add -A && git commit -m "feat: Sprint 2 — GLM streaming + deep reasoning tier + Pi barge-in + Avatar V3 Phase B (owner-approved)"`.

---

## VI. LỆNH NGHIỆM THU NHANH

```bash
# 1. Test barge-in thật (nói khi TTS đang phát)
# → Avatar phải dừng audio + về LISTENING

# 2. Test Avatar V3 Phase B (chat bình thường)
# → Miệng mượt, không còn "nhai" khi timeline thiếu

# 3. Full test suite
./.venv/Scripts/python.exe -m pytest -q tests

# 4. Commit Sprint 2
git add -A && git commit -m "feat: Sprint 2 — GLM streaming + deep reasoning tier + Pi barge-in + Avatar V3 Phase B (owner-approved)"
```

---
*Hết Sprint 2. Mọi thay đổi đã deploy lên Pi 5 thật, test PASS, chờ nghiệm thu barge-in + commit.*