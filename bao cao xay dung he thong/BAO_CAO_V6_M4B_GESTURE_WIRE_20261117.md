# BÁO CÁO V6 M4B — TAY PROCEDURAL 2D (WIRE)

**Ngày:** 17/11/2026
**Sprint:** V6-001 / M4b
**Trạng thái:** ✅ WIRE XONG — chờ owner nghiệm thu bằng mắt

---

## 1. Owner duyệt
- Duyệt PoC M4b v9 (`data/_poc_arms_sheet.png`) → wire vào production
- Cam kết verbatim: "toggle + chỉ chạy state phù hợp + geometry verbatim PoC v9"

## 2. Trạng thái trước M4b
- M4a GOODBYE đã wire (commit `9f9ecbd`)
- M4b PoC v9 đạt vision (3 gesture phân biệt rõ) — CHƯA wire
- Engine v6m5 đang chạy ổn định trên Pi5 (FPS 12 IDLE / 20 SPEAKING)

## 3. Kiến trúc M4b wire

### 3.1 Toggle (4 method mới)
```js
setHandsEnabled(bool)   // bật/tắt tay (mặc định true)
getHandsEnabled()       // đọc trạng thái
setHandsGesture(name)   // wave | palm | rest (mặc định auto theo state)
getHandsGesture()       // đọc gesture hiện tại
```

### 3.2 Gate state
Tay chỉ chạy khi `state ∈ {IDLE, GREETING, EXPLAINING}` — KHÔNG vẽ khi SPEAKING/HAPPY/THINKING/LISTENING/GOODBYE (tránh xung đột với viseme + emotion blend).

### 3.3 Auto-gesture theo state
- `GREETING` → wave (ngón dang + tilt lớn)
- `EXPLAINING` → palm (ngón khép khối tròn)
- `IDLE` → rest (ngón cong xuống + chìm gần hết)

### 3.4 Sample màu da
`_sampleHandsSkinTone()` đọc pixel từ portrait 896-space (vùng cổ 448,802) → fallback `[236,188,180]` nếu portrait chưa load.

### 3.5 Geometry verbatim PoC v9
- Tay nhô **18-32px** từ mép dưới
- Ngón dài `fl*1.0`, mảnh **2.6**, spacing **10**
- Cổ tay thắt eo
- KHÔNG warp dải ảnh (tránh barcode glitch)
- Portrait BUST-crop → tay chỉ nhô mép dưới

## 4. File thay đổi
| File | +/− | Mô tả |
|---|---|---|
| `edge_client/avatar_engine.js` | +166 | 4 method toggle + sample + render + 2 state fallback |
| `edge_client/avatar_protocol.js` | +4 | 2 state GREETING + EXPLAINING |
| `edge_client/kiosk.html` | +2/−2 | bump cache-buster v6m5_1611 → v6m4b_1711 |
| `src/quan_ai_brain/web/static/avatar_engine.js` | +166 | mirror |
| `src/quan_ai_brain/web/static/avatar_protocol.js` | +4 | mirror |
| `src/quan_ai_brain/web/static/index.html` | +2/−2 | mirror |
| `src/quan_ai_brain/web/static/executive.html` | +2/−2 | mirror |
| `src/quan_ai_brain/web/static/kiosk.html` | +2/−2 | mirror |

**Tổng:** 8 files, +342/−14

## 5. Verify E2E

### 5.1 Harness `data/wire_v6m4b_test.js`
**32/32 PASS** (state + toggle + gate + sample + 3 gesture)

### 5.2 CDP probe trên :8765
```
state=GREETING  → gesture=wave
state=EXPLAINING → gesture=palm
state=IDLE       → gesture=rest
toggle off → enabled=false
toggle on  → enabled=true
skin_sampled=true, skin_tone=[194,149,164] (sample thật từ portrait)
```

### 5.3 Vision screenshot
- `m4b_greeting.png`: tay nhô giữa mép dưới, ngón dang (wave) ✅
- `m4b_explaining.png`: tay khép khối tròn (palm) ✅
- 3 gesture phân biệt rõ theo vision

## 6. Kiểm tra trước commit
- `node --check` 2 file: SYNTAX OK
- md5 PC+mirror khớp: engine `6ae998fc` → mới, protocol `099b23c7`
- Secret-scan: **CLEAN** (0 match)
- Regression FULL: **9/4084/28** (baseline M5, 0 fail mới)

## 7. Commit + PR
- Commit `0c3adc7` 8 files +342/−14 đã push
- PR #32 mở: https://github.com/thequanhcm/quanpt1/pull/32
- Head `0c3adc7`, 1 commit, chờ "duyệt merge"

## 8. Cam kết giữ vững
- ✅ KHÔNG đổi khuôn mặt qua animation (giữ verbatim)
- ✅ KHÔNG sao chép danh tính từ video (chỉ học chuyển động)
- ✅ KHÔNG warp dải ảnh (tránh barcode glitch)
- ✅ KHÔNG thêm dependency mới
- ✅ KHÔNG động engine v6m5 / kiosk / Pi5 daemon / asset / secret
- ✅ Tay chỉ chạy khi state phù hợp (gate _render)
- ✅ Toggle cho phép owner tắt nếu style mismatch

## 9. Đang chờ
1. **Owner nghiệm thu bằng mắt** trên :8765 — click chip GREETING/EXPLAINING/IDLE trong Studio
2. **"duyệt merge" PR #32** (1 commit, head `0c3adc7`)
3. **Pi5 sync kiosk.html md5 mới** khi WiFi hồi (ping 100% loss 17/11)
4. **M6** — chờ brief gốc 10 TEST hoặc owner duyệt tiêu chí runtime stability 24h
