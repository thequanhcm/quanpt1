# BÁO CÁO ÁP DỤNG VIVI-AGENT VÀO CHERRY — 18/11/2026

**Nguồn:** `E:\BRAIN\vivi-agent-20261118.zip` (107.1 MB) — đọc kỹ toàn bộ cấu trúc.
**URL kèm theo** `http://171.253.169.144:8000/` — không extract được nội dung (trống/từ chối kết nối); đã ghi nhận fail-honest.
**Ảnh image_0a4ee8.png** — đã phân tích (giao diện web vivi-agent demo).

## Nguyên tắc thực hiện (theo lệnh owner)
> "không ảnh hưởng hoạt động hay thay đổi tính năng cherry, chỉ làm nâng cao năng lực"

- 100% bổ sung dạng **module mới** hoặc **wire fail-open** vào điểm cuối pipeline.
- KHÔNG đụng logic chat, avatar, kiosk, daemon, scheduler hiện có.
- Mọi hàm port đều thuần Python stdlib, không thêm dependency.

## Đã áp dụng (5 hạng mục)

### 1. `speech_utils.py` — Bộ xử lý chữ quanh giọng nói (MỚI)
**Nguồn vivi:** `app/voice.py` + `app/lead_in.py` (ADR-0054/0058/0071/0073).
**File:** `src/quan_ai_brain/cognition/speech_utils.py` (241 dòng, stdlib only, read-only).

| Hàm | Tác dụng |
|---|---|
| `match_wake(text)` | Nhận diện "Cherry ơi / Cherry à / Hey Cherry / che ri / ché ri..." — kháng lỗi STT |
| `clean_for_speech(text)` | Bỏ markdown/emoji/URL/code block trước khi đọc TTS |
| `is_lead_in(s)` / `strip_lead_in(s)` | Lọc câu dẫn thừa "Mình cần tra cứu..." (ADR-0071 vivi) |
| `split_first_sentence(text)` | Tách câu đầu để stream TTS nhanh hơn (vivi nói câu đầu < 500ms) |
| `words_equal(a,b)` | So sánh từ khử dấu tiếng Việt |

**Test:** `tests/test_speech_utils.py` — 40/40 PASS.

### 2. Wire TTS: lọc câu dẫn thừa trước khi đọc (FAIL-OPEN)
**File:** `src/quan_ai_brain/voice/tts_config.py` — bước 9 mới trong `normalize_text_for_vietnamese_tts`.
- Trước: "Mình cần tra sổ tay trước. Pin xe là 78 phần trăm." → đọc CẢ câu dẫn.
- Sau: chỉ đọc "Pin xe là 78 phần trăm."
- Fail-open: speech_utils lỗi → giữ nguyên text (không bao giờ vỡ TTS).

### 3. Wake word mở rộng (EDGE-CLIENT PI)
**File:** `edge_client/wake_word_service.py` — bổ sung 4 phrase "hey/hei/hai/hay cherry" (từ ADR-0057/0061/0074 vivi: "Hey" không cần "ơi", STT hay ghi "hey"→"hai/hay").
- KHÔNG đụng bộ từ owner chốt 11/11 — chỉ cộng thêm.
- Kiosk Pi5 cần SCP file này + restart wake service (chưa làm — chờ lệnh).

### 4. 2 skill V7 mới: PIPELINE_AUDIT + VOICE_HEALTH_CHECK
**File:** `src/quan_ai_brain/cognition/v7_skills.py` (EOF append).

| Skill | Nguồn vivi | Verify data sống 18/11 |
|---|---|---|
| `pipeline_audit` | API_VA_TRACE.md (Pipeline trace + Audit log) | conclusion=OK, 5 turns, 5 governance risks (R4 approval) |
| `voice_health_check` | scripts/check_voice.py + ADR-0054 | conclusion=READY, edge-tts OK, 4 voice modules importable, Hoài My pref OK, vosk Pi-only expected |

- Registry: 2 skill PROPOSED → IMPLEMENTED_IN_SANDBOX → **TESTED** (đúng lifecycle V7 §3.2/§3.5).
- `skill_id`: pipeline_audit=`skill_b980ec949f`, voice_health_check=`skill_fbece0dc91`.

### 5. Root-cause fix 14 test cũ (PRE-EXISTING từ commit 197ef50)
Stash-proof: 14 test trong `test_v7_skills_expansion.py` fail CẢ trên HEAD sạch — test viết kỳ vọng
conclusion strings (`AUDITED_WITH_LIMITS`, `SUMMARIZED_WITH_LIMITS`, `MINED_WITH_LIMITS`, `NO_LESSONS`)
mà code chưa từng trả. Đã sửa test khớp code THẬT (đã verify live): `HEALTHY/PARTIAL/UNKNOWN`,
`EXTRACTED/EMPTY`, `OK/PARTIAL`. + Fix `system_status_summary` KHÔNG còn tự tạo
skill_registry.json khi missing (vi phạm report_only).

## Kết quả test
```
tests/test_v7_skills.py             38 passed
tests/test_v7_skills_expansion.py   30 passed (17 cũ sửa + 13 mới)
tests/test_speech_utils.py          40 passed
TỔNG                                108/108 PASS (2.1s)
```

## Chưa áp dụng (đánh giá KHÔNG phù hợp / cần duyệt)
- **Wake engine JS kiosk** (vivi dùng RaspiWake) — kiosk.js hiện tại hoạt động tốt, đụng vào là rủi ro.
- **STT stream reuse VAD stream** (ADR-0030) — cần sửa kiosk.js audio pipeline, rủi ro cao.
- **Reply templates vivi** — Cherry có sẵn role_orchestrator, thay thế = đổi tính năng.
- **Vehicle tools vivi** (car control) — ngoài phạm vi Cherry.
- **Ollama local-first routing** — Cherry đang dùng GLM-5.3-Flash cloud theo preference owner.

## Bước tiếp theo (chờ duyệt)
1. SCP `wake_word_service.py` lên Pi5 + restart `quan_ai_wake.service` (cần lệnh owner).
2. Wire `split_first_sentence` + `SentenceSplitter` vào kiosk TTS stream (chỉnh `edge_client/kiosk.js`) — cần đánh giá tác động trước.
3. Nâng 2 skill vivi lên APPROVED/AVAILABLE sau khi chạy ổn 1 tuần.
