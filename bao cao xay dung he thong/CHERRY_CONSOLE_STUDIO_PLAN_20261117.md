# CHERRY CONSOLE STUDIO — Đề xuất giao diện điều khiển trên :8765

**Ngày**: 17/11/2026
**Trạng thái**: ĐỀ XUẤT — chờ owner duyệt trước khi sửa
**Phạm vi**: Panel phải của `static/index.html` (Console :8765) — biến thành "Studio điều khiển" Cherry

---

## 1. Hiện trạng (đã verify qua CDP)

- Engine `window.digitalHuman` đang chạy thật trên :8765:
  - `loaded: true`, 18/18 asset `avatar_v3_*.png` (portrait 896×896)
  - `state: IDLE`, `fpsMeasured: 12`, `renderMsAvg: 0.16ms`
  - Head pose động: yaw -1.3°, pitch 0.6°, roll -0.3°
  - Viseme REST, blink/breath cycle chạy
- Canvas 480×480 (đã scale từ 896-space, head-pose warp 16 dải hoạt động đúng)
- Halo + tai nghe cyan + tóc nâu highlight xanh hiển thị đúng
- Ảnh owner chụp có thể là cache cũ (chưa bump `?v=v6m5_1611` hoặc reload trang)

## 2. Đề xuất: "Studio điều khiển" — 4 khối chức năng

### Khối A — Chọn trạng thái (22 state)
- 22 nút bấm nhỏ (chip) trong grid 4×6: IDLE, LISTENING, THINKING, SPEAKING, HAPPY, GREETING, GOODBYE, EXPLAINING, SERIOUS_ALERT, APOLOGETIC, PROUD, SUCCESS, SURPRISED, CONFUSED, FOCUSED, DREAMY, SLEEPING, NEUTRAL, FRIENDLY, ENERGETIC, CALM, CURIOUS
- Click → `window.digitalHuman.setState(name)` + log console
- Highlight nút đang active

### Khối B — Test viseme + lip-sync
- Dropdown 12 viseme tiếng Việt: A, Á, Ả, E, Ê, I, O, Ô, Ơ, U, Ư, REST
- Slider `openRatio` 0.0 → 1.0
- Nút "Test 1s" → animate openRatio 0→1→0 trong 1s
- Nút "Speak text" → gọi `speak("Xin chào anh Quân")` qua audio_mouth_driver

### Khối C — Perf profile (M5)
- Hiển thị FPS thật (đo từ engine `_lastMeasuredFps`)
- Hiển thị render_ms_avg
- 2 nút: "Set NORMAL" / "Set LOW" → `window.digitalHuman.setPerfProfile(...)`
- Hiển thị profile hiện tại (badge màu)

### Khối D — Điều khiển Pi5 (nếu online)
- Nút "Reload UI" → POST `http://192.168.1.21:8768/api/kiosk/control` action `reload_ui`
- Nút "Start kiosk" / "Stop kiosk"
- Hiển thị trạng thái Pi5 (online/offline + RTT)

## 3. File sẽ sửa

| File | Thay đổi | Dòng ước tính |
|---|---|---|
| `static/index.html` | Thêm 4 khối A/B/C/D vào panel phải (dưới canvas) | +120 |
| `static/style.css` | Style cho chip/button/slider/badge | +80 |
| `static/app.js` | Wire 4 khối → engine + Pi5 API | +90 |
| `static/cherry_studio.js` (mới) | Logic riêng cho studio (tách khỏi app.js) | +150 |

**Tổng**: ~440 dòng, không động engine, không động kiosk, không động Pi5.

## 4. Cache-buster

Bump `cherry_1411` → `cherry_studio_1711` cho 3 file: `index.html`, `style.css`, `app.js` + thêm `cherry_studio.js?v=cherry_studio_1711`.

## 5. Kiểm chứng

- `node --check` 2 file JS
- Mirror sang `edge_client/` (nếu cần kiosk dùng chung)
- Headless Chrome screenshot 8765 → verify 4 khối hiển thị
- CDP probe: click nút "HAPPY" → engine state đổi IDLE → HAPPY
- Regression: `pytest tests/ -q` (baseline 4083/10/28)

## 6. Cam kết

- KHÔNG động engine v6m5 (đã commit `9f9ecbd`)
- KHÔNG động kiosk Pi5
- KHÔNG động Pi5 daemon
- KHÔNG thêm dependency mới
- KHÔNG hardcode secret
- Tận dụng 100% asset + engine có sẵn

## 7. Đang chờ

- Owner duyệt hướng "Studio điều khiển" (4 khối A/B/C/D) HOẶC chọn hướng khác
- Nếu duyệt → em triển khai trong 1 sprint, commit theo quy trình "duyệt merge"
