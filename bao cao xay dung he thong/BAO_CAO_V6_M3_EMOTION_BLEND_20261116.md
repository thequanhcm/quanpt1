# BÁO CÁO V6 P3/M3 — EMOTION BLEND MESH + HAPPY DUCHENNE (v6m3_1611)

**Ngày:** 16/11/2026 · **Task:** TASK-V6-M3 (card APPROVED + CONSUMED, auth `owner_desktop_chat_directive`)
**Chỉ thị owner:** "em triển khai M3"
**Nguồn thiết kế:** `docs/CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md` §4 P3 — *"Emotion blend mesh giữa 2 portrait (hết hard-cut) + HAPPY Duchenne"* (TEST 07/08 brief)

## 1. Audit nền (trước khi sửa — audit trước sửa sau)
- Crossfade 2 lớp `globalAlpha` 350ms **linear cứng** (v6emo 14/11) — hoạt động nhưng không theo engine
- `emotion_engine.js` (s3_1411) có `EmotionTransitionEngine` với duration/easing/intensity đầy đủ, NHƯNG `_emotionEngine.update()` **chưa từng được tick** trong frame loop → toàn bộ duration/easing preset chết code
- Micro-expression lerp factor cứng `0.08` mỗi frame — không đổi theo loại chuyển cảm xúc (alert phải nhanh, ngủ phải chậm)

## 2. Delivered
| Hạng mục | Nội dung | Bằng chứng |
|---|---|---|
| M3a | **Tick engine mỗi frame** + FADE duration lấy từ `transition.durationMs` (SERIOUS_ALERT 120ms → blend nhanh; SLEEPING 900ms → chậm) + easing `M3_EASING` (ease-in-out/ease-out/ease-in/linear khớp key preset) thay linear. Không transition → fallback 350ms (không hồi quy v6emo). Vẫn vẽ 2 lớp qua `_renderHeadPose` — kiến trúc crossfade giữ nguyên | harness M3a.1-10 (kèm runtime test preset 900/120ms) |
| M3b | **Micro-lerp theo easing×intensity**: `factor = ease(progress) × (0.12 + intensity×0.5)` clamp 0.02..0.6 — alert nhanh + mạnh, sleeping chậm + dịu; không transition → base 0.08 như cũ | harness M3b.1-5 |
| M3c | **HAPPY DUCHENNE (§4F "mắt hơi cong khi cười", không cường điệu)**: (1) SPEAKING tone tích cực — squint sync `0.30×smile×intensity` + smileBoost `0.45×smile×intensity` cùng nhịp khóe; (2) state vui KHÔNG nói (HAPPY/PROUD/SUCCESS/CONFIDENT_SUCCESS) — vẫn Duchenne + highlight 2 nét khóe, miệng nghỉ; (3) tone nghiêm → `_rigSmile=0` giữ nguyên | harness M3c.1-6 (runtime HAPPY + SERIOUS_ALERT) |

**Bug bắt được khi harness:** nhánh HAPPY đầu tiên đặt **sau** guard `state !== "SPEAKING"` → chết code (state HAPPY return trước khi tới). Đã chuyển lên trước guard + test runtime chốt.

## 3. Kiểm chứng
- **Harness riêng** `data/wire_v6m3_test.js`: **25/25 PASS** (M3a 10 + M3b 5 + M3c 6 + hooks 4) — có load `emotion_engine.js` THẬT vào sandbox (không mock)
- **Không hồi quy**: `wire_v6m12_test` 39/39 · `wire_v6rig_test` 24/24 · `wire_v6pose_test` 25/25
- **node --check** OK · mirror md5 `7b61fa26` khớp edge_client
- **Live smoke PC :8765**: engine serve md5 khớp, code M3 trong payload, cache-buster `v6m3_1611` ăn; headless console SẠCH; vision screenshot: avatar nguyên, **nụ cười Duchenne lan khóe mắt hiển thị đúng**, layout nguyên
- **Deploy Pi5**: backup `.bak_pre_m3` → scp engine + kiosk.html → md5 KHỚP 2/2 (`7b61fa26` / `6098c2d6`) → reload_ui OK → kiosk_running=True, state IDLE, embodiment ACTIVE; headless chromium: JS console SẠCH
- **Full regression pytest** nền `proc_63734b006a4c`: **4083 passed / 10 failed / 28 skipped (744.77s)** — 10 fail đều pre-existing baseline (emotion_sync cache-version + cognitive/cpsl/identity/media/edge_known + executive socket). Test `test_executive_edge_files_and_actions` (fail baseline) lần này PASS trong full-suite (flaky socket LAN), nhưng chạy RIÊNG vẫn fail, và A/B **stash HEAD sạch cũng fail riêng lẻ** → không phải fail mới của M3; 0 file Python sửa. Tổng: 0 fail mới, pass tăng +1 do flaky LAN thuận chiều

## 4. Không làm (trung thực — fail-honest)
- KHÔNG tạo portrait asset mới (blend trên 2 portrait có sẵn — giữ nhận diện Model A, verbatim owner)
- KHÔNG tạo engine thứ 2; KHÔNG đụng lớp tay (M4 PoC duyệt riêng); KHÔNG bật tóc động (owner tắt 14/11)
- **E2E động chưa chốt bằng mắt**: cần owner nhìn kiosk khi CHERRY chuyển cảm xúc (VD: nói chuyện có tone thành công → thấy mặt chuyển mượt ~300ms ease-in-out + mắt cong theo cười). Headless không thấy được chuyển động.

## 5. Files
- `edge_client/avatar_engine.js` + mirror (md5 `7b61fa26`): M3a/b/c + `M3_EASING` + `_lerpDuchenne` + tick engine
- `edge_client/kiosk.html` / `static/executive.html` / `static/index.html`: cache-buster `v6m3_1611`
- `data/wire_v6m3_test.js` (25 checks, load emotion_engine thật)
- `tools/submit_v6_m3_approval.py` (card TASK-V6-M3)
- Backup Pi5: `avatar_engine.js.bak_pre_m3`

## 6. Next (sau nghiệm thu owner)
- **M4**: cử chỉ tay procedural + GREETING/GOODBYE — PHẢI PoC duyệt riêng (bài học arms-1311)
- M5: tối ưu Pi5 PROFILE A + benchmark 60 phút 10 TEST brief
- Đề nghị owner nghiệm thu: nói 1 câu có tone vui ("Em hoàn thành rồi ạ!") → quan sát kiosk 20-30s: mặt chuyển mượt không nhảy, mắt cong khi cười
