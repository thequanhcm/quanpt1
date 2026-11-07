# PANEL TRẠNG THÁI SỐNG — MỞ RỘNG CHO CAMERA / TỰ HỌC / AUDIO (07/11/2026)

## Yêu cầu owner
"[ảnh image_771fe9] @url 8766 — hãy điều chỉnh cho toàn bộ các phần khác như camera, tự học ..... "
→ Áp cơ chế tab sáng/mờ (turn trước) xuống từng PANEL: chức năng đang bật → panel sáng; đang tắt → panel mờ + nút bớt tươi + badge trung tính.

## Nguyên nhân gốc (camera)
- Panel camera (card-remote-camera) có badge đỏ CAMERA OFF nhưng khung panel + nút chính vẫn tươi:
  1. không có class phản chiếu trạng thái trên card;
  2. nút "BẮT ĐẦU XEM" là `btn-primary` + inline gradient xanh luôn đậm;
  3. badge "CHỜ XÁC MINH" mặc định màu xanh (class badge-ready) ngay cả khi chưa chụp.

## Đã sửa
### 1. CSS (executive.css, cache bump r2 → r3)
- Thêm `.card.panel-off` (mờ 55%) — tái dùng ngôn ngữ `.tab-off` của turn trước.
- `.card.panel-off .btn-primary/.btn-outline` giảm bão hoà; rule `!important` đè inline gradient trên nút.
### 2. executive.js
- `loadCameraStatus()`: set/remove `.panel-off` theo `camera_enabled` (hoặc đang live); title tooltip theo trạng thái.
- `startLiveStream()/stopLiveStream()`: đổi nút BẮT ĐẦU XEM ↔ ĐANG LIVE (primary ↔ outline); DỪNG XEM sáng chỉ khi đang live; remove panel-off khi bật live.
- Badge "CHỜ XÁC MINH" → nền xám trung tính; chỉ xanh khi SHA-256 hợp lệ thật (capture verify).
- `loadAudioStatus()`: fetch lỗi → panel audio mờ; parse đúng.
- `loadLearningReports()`: 0 báo cáo → 2 card tự học mờ + tooltip hướng dẫn bấm "Kích Hoạt Chu Kỳ Tự Học Ngay".
### 3. executive.html
- Nút BẬT ĐẦU XEM: `btn-primary` → `btn-outline` (gradient inline giữ để khi camera BẬT nút vẫn nổi).
- **Deep-link `?tab=`**: `switchTab` ghi `?tab=tab-...` vào URL + DOMContentLoaded đọc `?tab=` mở thẳng tab (bookmark được, tiện owner xem đúng panel).

## Verify (bằng chứng ảnh, không tự suy diễn)
- `logs/dashboard_edge_tab_r3_full.png`: panel camera **mờ rõ** + badge CAMERA OFF; panel AUDIO bình thường (mic READY, WAKE: TẮT); badge "CHỜ XÁC MINH" **xám trung tính** ✓.
- `logs/dashboard_edge_tab_r3b.png`: 8 nút camera **mờ đồng nhất** — nút BẮT ĐẦU XEM không còn nền xanh đậm nổi bật ✓.
- Tab trạng thái (turn trước) vẫn nguyên: Đồng Bộ Pi 5 LIVE, Hình Thể ACTIVE...
- `node --check` executive.js OK; test tab+memory review: **33 passed**.
- Deep-link: `/?tab=tab-edge-sync` mở thẳng tab Đồng Bộ Pi 5 ✓ (2 ảnh trên chụp bằng URL này).

## Trạng thái chức năng hiện tại (thật, từ API)
- Camera: TẮT (config camera_enabled=false) — panel mờ đúng trạng thái.
- Mic: READY — panel audio sáng; wake word TẮT (badge phụ xám).
- Tự học: daemon 5' đang chạy 4 luồng — panel sẽ sáng khi loadLearningReports có reports.
