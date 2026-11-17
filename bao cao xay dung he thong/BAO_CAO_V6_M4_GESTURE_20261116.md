# BÁO CÁO V6 M4 — CỬ CHỈ TAY + GOODBYE (16/11/2026)

## Tóm tắt
- **M4a (đã wire + deploy)**: state GOODBYE — gật chào 2 nhịp + lean-back + auto về IDLE 2.5s; trigger khi kết thúc phát thoại tone tích cực.
- **M4b (PoC chờ owner duyệt)**: bàn tay procedural 2D — sample màu da từ portrait, 3 gesture (wave/palm/rest) phân biệt rõ, file độc lập KHÔNG wire.

## M4a — GOODBYE (đã wire)
### Thay đổi
| File | Nội dung |
|---|---|
| `edge_client/avatar_protocol.js` | Thêm GOODBYE vào STATE_CONFIGS (aura #94a3b8, haloSpeed 0.04, eyes open, smile closed, symbol 👋, defaultTone GOODBYE) |
| `edge_client/avatar_engine.js` | (1) GOODBYE trong STATE_CONFIGS fallback; (2) animation GOODBYE trong update loop: pitch sin 2 chu kỳ 0.85Hz biên 4.5° + lean-back scale 0.985 + auto về IDLE 2.5s; (3) method `playGoodbye()`; (4) wire lean-back vào chest transform |
| `edge_client/kiosk.js` | Hook `audio.onended`: nếu tone tích cực (CONFIDENT_SUCCESS/HAPPY/PROUD/SUCCESS) → `playGoodbye()`; ngược lại → IDLE như cũ |

### Kiểm chứng
- `node --check` OK 3 file
- Mirror PC sync md5: kiosk.js `2943060f`, engine `f8ae49c2`
- Chưa deploy Pi5 (chờ owner duyệt M4a + M4b cùng lúc)

## M4b — PoC tay procedural (CHỜ DUYỆT)
### File
- `data/cherry_poc_arms.html` — file độc lập, KHÔNG wire
- `data/poc_arms/` — bản sao + 3 variant (wave/palm/rest)
- `data/_poc_arms_sheet.png` — contact sheet 3 gesture

### Đặc tính kỹ thuật
- **Bàn tay procedural 2D** (path + gradient màu da sample từ portrait tại vùng cằm/má dưới)
- **Cẳng tay**: thắt eo cổ tay (anatomy), vào khung từ mép dưới
- **Bàn tay**: trapezium mềm + 4 ngón tách rời (wave) / 1 khối tròn (palm) / 4 ngón cong xuống (rest) + ngón cái (wave/palm)
- **Biên độ**: 18-32px từ mép dưới (≤6% khung) — đúng nguyên tắc "cử chỉ nhỏ"
- **Feather đáy**: gradient alpha 0→0.7 trong 22px — tay hoà vào mép khung
- **Toggle**: nút "Tay: BẬT/TẮT" — tắt tức thì
- **3 gesture phân biệt rõ**:
  - **Wave** (GREETING): ngón dang + tilt 0.12 rad (7°) + sway 6px
  - **Palm** (EXPLAINING): ngón khép thành 1 khối tròn + raise cao hơn wave
  - **Rest** (IDLE): ngón cong xuống + tay chìm gần hết dưới mép

### Bài học từ quá trình làm PoC
1. **Warp dải ảnh (v1-v3)**: tạo barcode/scanline — KHÔNG dùng
2. **Bàn tay procedural (v4-v9)**: sạch, đúng tỷ lệ, sample màu da
3. **3 gesture trùng nhau ở ảnh tĩnh** (lần đầu): do raise quá nhỏ + tilt quá nhỏ — đã sửa bằng cách phân biệt rõ silhouette (dang/khép/cong)
4. **Nhãn card hardcode "WAVE"**: bug cosmetic — đã sửa bind theo gesture

### Kiểm chứng
- `node --check` OK
- Vision verify 3 gesture phân biệt rõ bằng hình (contact sheet)
- File độc lập, KHÔNG ảnh hưởng production

## Chờ owner duyệt
1. **M4a GOODBYE**: duyệt → deploy Pi5 + commit
2. **M4b tay procedural**: duyệt → wire vào avatar_engine.js (M4b production) với toggle + chỉ chạy khi state phù hợp (GREETING/EXPLAINING/IDLE)
3. Nếu KHÔNG duyệt M4b → đề xuất hướng khác (3D VRM, sprite chibi chuẩn, hoặc bỏ tay)

## Rủi ro đã biết
- **Style mismatch**: tay clip-art phẳng vs portrait semi-real chi tiết — có thể bị cảm giác "dán sticker" ở kiosk thật
- **Wave vs Palm khó phân biệt** ở kích thước 18-32px khi nhìn đơn lẻ (chỉ rõ khi đặt cạnh nhau)
- **Chưa test motion**: ảnh tĩnh không chứng minh chuyển động mượt — cần owner xem kiosk thật

## Files tham chiếu
- `data/cherry_poc_arms.html` — PoC chính
- `data/poc_arms/cherry_poc_wave.html`, `cherry_poc_palm.html`, `cherry_poc_rest.html` — 3 variant
- `data/_poc_arms_sheet.png` — contact sheet
- `data/_poc_arms_wave9.png` — ảnh đơn lẻ wave (vision verify đạt)
- `edge_client/avatar_engine.js` (md5 `f8ae49c2`) — M4a GOODBYE
- `edge_client/avatar_protocol.js` — M4a GOODBYE config
- `edge_client/kiosk.js` (md5 `2943060f`) — M4a trigger
