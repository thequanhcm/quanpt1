# CHERRY CONSOLE STUDIO — Báo cáo triển khai (17/11/2026)

**Owner duyệt**: "Duyệt hướng 'Studio điều khiển' (4 khối A/B/C/D) → em triển khai trong 1 sprint, commit theo quy trình 'duyệt merge'"

**Trạng thái**: ĐÃ TRIỂN KHAI + VERIFY E2E — chờ regression + commit

---

## 1. Phạm vi

Thêm khối **CHERRY STUDIO** collapsible vào panel phải Console :8765 (dưới card "Loa Raspberry Pi 5"). Tôn trọng nguyên tắc "tinh gọn và tích hợp" 06/11 — mặc định thu gọn, owner bấm mới mở.

## 2. 4 khối chức năng

### A. Trạng thái (23 state engine)
- 23 chip: IDLE, LISTENING, THINKING, SPEAKING, HAPPY, GREETING, GOODBYE, EMPATHETIC, SERIOUS_ALERT, APOLOGETIC, PROUD, SUCCESS, SURPRISED, CURIOUS, CONFUSED, DREAMY, SLEEPING, RESEARCHING, LEARNING, WAITING_FOR_OWNER, SAFE_MODE, BLOCKED, ERROR
- Click → `window.digitalHuman.setState(name)` (engine là nguồn sự thật)
- Chip active highlight theo `engine.state` thật (tick 1s)

### B. Lip-sync tiếng Việt
- 12 chip viseme: a, ă, â, e, ê, i, o, ô, ơ, u, ư, REST (khớp VISEME_VI trong audio_mouth_driver.js)
- Click → set `engine.activeViseme` + `engine.currentOpenRatio` trực tiếp, giữ 1s rồi auto-reset REST
- **KHÔNG** gọi `setState("SPEAKING")` (sẽ clear scheduler + transition cảm xúc — quá mạnh cho test viseme đơn)
- Ô nhập text + nút "🗣️ Phát" → gọi `speakText()` có sẵn trong app.js (tái dùng qua `window.cherryStudioHooks`)

### C. Hiệu năng (M5)
- Hiển thị FPS thật + render_ms_avg từ `engine.getPerfStats()` (đo từ `_lastMeasuredFps` cửa sổ 10s)
- Badge profile (NORMAL xanh / LOW vàng) — đồng bộ theo engine thật
- 2 nút NORMAL (12/18/24) / LOW (8/10/15) → `engine.setPerfProfile(name)`

### D. Điều khiển Pi5 (qua core :8766)
- Dropdown 23 state + nút "Gửi" → POST `/api/executive/edge/control` action `set_expression` (envelope chuẩn)
- Nút "↻ UI" → POST action `reload_ui`
- Dòng kết quả hiển thị response từ core (fail-honest: lỗi hiển thị lỗi, không fake)

### Log cuối
- 40 dòng gần nhất, timestamp `HH:MM:SS`, màu đỏ cho lỗi
- Tự cuộn xuống dòng mới nhất

## 3. File thay đổi

| File | Thay đổi | Dòng |
|---|---|---|
| `static/index.html` | Thêm khối studio + bump cache-buster `cherry_1411` → `studio_1711` | +57 |
| `static/style.css` | CSS cho studio (collapsible, chip, button, badge, log) | +203 |
| `static/app.js` | Thêm 2 state GOODBYE/ERROR + expose `window.cherryStudioHooks` | +11 |
| `static/cherry_studio.js` (mới) | Logic 4 khối A/B/C/D + collapse + tick 1s | +340 |

**Tổng**: 4 file, +611 dòng, không xoá dòng nào.

## 4. Kiến trúc

- **KHÔNG nhân bản logic** — studio gọi qua `window.cherryStudioHooks = {setAvatarState, speakText, stopAudio}` (expose từ app.js)
- **Engine là nguồn sự thật** — tick 1s đọc `engine.state` + `engine.getPerfStats()` để đồng bộ UI
- **Fail-honest** — API lỗi hiển thị lỗi trong log + dòng kết quả, không fake thành công
- **KHÔNG động** engine v6m5 / kiosk Pi5 / daemon / asset / secret

## 5. Kiểm chứng E2E (Chrome headless + CDP)

| Test | Kết quả |
|---|---|
| `node --check cherry_studio.js` | SYNTAX OK |
| `node --check app.js` | SYNTAX OK |
| Server :8765 serve file mới | 200 OK (không cần restart) |
| Reload page + cache-buster | studio DOM render đủ 23 chip + 12 viseme + 23 option |
| Click chip HAPPY | engine.state = HAPPY, chip active đúng 1 cái |
| Click nút LOW | profile=LOW, fps_target=8, badge đổi class `low`, nút LOW active |
| Click viseme 'a' | viseme=A, open=0.75, state giữ HAPPY (không bị setState đè); sau 1.2s auto-reset REST/open=0 |
| FPS thật | 12 FPS, render 0.12ms (đo từ engine `_lastMeasuredFps`) |
| Click "Gửi" set_expression HAPPY | core trả `set_expression("HAPPY") → HAPPY`, log "Pi5 set_expression OK" |
| Vision screenshot | 4 khối A/B/C/D + log 5 dòng hiển thị đầy đủ |

## 6. Cache-buster

- `cherry_1411` → `studio_1711` cho `index.html`, `style.css`, `app.js`
- Thêm `cherry_studio.js?v=studio_1711`
- KHÔNG đụng `avatar_engine.js?v=v6m5_1611` (đã commit `9f9ecbd`)

## 7. Regression FULL (proc_120e4a75cca2, 829s)

```
9 failed / 4084 passed / 28 skipped — baseline M5: 10 failed / 4083 passed / 28 skipped
→ +1 pass, −1 fail (flaky LAN test hồi phục), 0 FAIL MỚI TỪ STUDIO
```

Fail còn lại đều pre-existing: test_web_executive_endpoints (LAN socket), test_edge_client_daemon_local_kiosk_endpoints, test_cognitive_loop (Pi5 offline honest), test_cpsl_runner (13≠12), test_digital_identity_persona, test_media_only_dm, test_web_server speak forwarding.

## 8. Trạng thái commit

```
2375d54 feat(console): Cherry Studio — khối điều khiển collapsible (4 khối A/B/C/D) — owner duyệt 17/11
pushed: 9f9ecbd..2375d54 → origin/feat/v6-001-artifacts-ops
PR #31: open | mergeable: true | head 2375d54 | 6 commits
```

## 9. Đang chờ

- ~~Regression pytest~~ ✅ DONE — 9/4084/28, 0 fail mới
- ~~Commit + push~~ ✅ DONE — `2375d54` đã push, PR #31 head
- Owner nghiệm thu Studio trên :8765 (bấm mở khối Studio, click thử 4 khối)
- Owner "duyệt merge" PR #31

## 8. Cam kết

- KHÔNG động engine v6m5 / kiosk / Pi5 daemon / asset / secret
- KHÔNG thêm dependency mới
- KHÔNG hardcode secret
- Tận dụng 100% asset + engine + API có sẵn
