# QUAN AI BRAIN — DIGITAL HUMAN AVATAR V2 PROPOSAL & AUDIT REPORT
**Dự Án:** QUAN AI BRAIN — Executive Assistant & Physical Embodiment  
**Chủ Sở Hữu & Phê Duyệt:** Anh Quanpt1  
**Tài Liệu Tham Chiếu Trực Quan:** `Pi5/6.jpg` (Chân dung Nữ Trợ Lý Cybernetic Tóc Tím Bạc, Nụ Cười Tự Nhiên)  
**Thời Điểm Khảo Sát:** 2026-10-21 21:26:00 (Local Time)  
**Trạng Thái Hệ Thống Hiện Tại:** 383 PASSED / 1 SKIPPED / 0 FAILED  

---

## I. TỔNG QUAN & MỤC TIÊU NÂNG CẤP AVATAR V2

Theo chỉ đạo của Anh Quân trong **ANTIGRAVITY MASTER PROMPT — QUAN AI BRAIN DIGITAL HUMAN AVATAR V2**:
1. **Chuẩn Tham Chiếu Trực Quan Chính Thức:** Sử dụng bức ảnh do Anh Quân cung cấp tại [Pi5/6.jpg](file:///E:/AI/QUAN%20AI%20BRAIN/Pi5/6.jpg) làm nhân vật chuẩn duy nhất:
   - Khuôn mặt nữ trẻ trung, thân thiện, nụ cười rạng rỡ tự nhiên.
   - Mái tóc dài màu tím ánh bạc mềm mại với kẹp tóc pha lê và vầng sáng thiên hà xanh tím.
   - Trang phục cybernetic màu trắng bạc với viền LED cyan tương lai, phong thái cao cấp, hiện đại, tinh tế.
   - **Tuyệt đối không tự ý thay thế** bằng robot, nhân vật hoạt hình hoặc khuôn mặt khác.
2. **Nâng Cấp Thành Digital Human Sống Động:** Không chỉ là ảnh tĩnh, mà được động hóa toàn diện thành Thực Thể Số có khả năng chớp mắt sinh học, lắc đầu vi mô, biểu cảm theo ngữ cảnh và cử động môi (Mouth-Sync) khớp từng âm tiết với giọng đọc nữ tiếng Việt tự nhiên (`vi-VN-HoaiMyNeural`).
3. **Bảo Tồn Nguyên Vẹn Hệ Thống:** Mọi năng lực cốt lõi (Governance, Memory WAL, Task Orchestration, Voice First, Edge Connectivity) giữ nguyên tính toàn vẹn 100%.

---

## II. KẾT QUẢ AUDIT TRƯỚC KHI SỬA ĐỔI (PHASE 0 AUDIT)

### 1. Phân Tích Hình Ảnh Tham Chiếu `Pi5/6.jpg`
- **Đường dẫn tệp gốc:** `E:\AI\QUAN AI BRAIN\Pi5\6.jpg` *(Được bảo vệ nguyên vẹn, không chỉnh sửa hoặc di chuyển file gốc)*.
- **Kích thước gốc:** `1448 x 1086` px (Tỉ lệ 1.33:1 / 4:3), Dung lượng: `503.0 KB`.
- **Tọa độ hình thể & Điểm mốc khuôn mặt (Facial Landmarks):**
  - **Tâm khuôn mặt:** Nằm chính xác tại trung tâm ngang $X = 724$, $Y \approx 450$.
  - **Khung mắt (Eye Axis):** Đường mắt nằm tại $Y \approx 360 - 410$. Khoảng cách hai đồng tử $\approx 205$ px.
  - **Khung miệng (Mouth Axis):** Miệng tươi cười tự nhiên tại $X = 724$, $Y \approx 510 - 565$, độ rộng khuôn miệng $\approx 180$ px.
  - **Trang phục Cybernetic:** Cổ áo viền pha lê LED cyan tại $Y \approx 670 - 760$, ngực và vai áo trắng bạc giáp công nghệ tại $Y \approx 760 - 1086$.
  - **Đánh giá hình học:** Bố cục cực kỳ lý tưởng để tạo khung vuông $1024 \times 1024$ (Crop $X = 181 \to 1267$, $Y = 0 \to 1086$) mà không bị méo tỉ lệ, khuôn mặt nằm trọn vẹn ở 1/3 trên khung hình.

### 2. Trạng Thái Git & Working Tree
- **Commit hiện tại:** `9243d12` (*docs: update handoff report with 17 passed tests and clean git tree*).
- **Bộ kiểm thử tự động:** `383 PASSED, 1 SKIPPED, 0 FAILED` (100% tests cốt lõi đạt chuẩn).
- **Tất cả các tệp hiện có:** Giữ nguyên vẹn, không chạy git reset, git clean hoặc ghi đè tùy tiện.

### 3. Bản Đồ Luồng Dữ Liệu Thực Tế (Data Flow Architecture Map)

```
[Người Dùng / Anh Quân]
   │  Gọi "Hi TONY" (Mic USB Pi 5 hoặc PC)
   ▼
[Raspberry Pi 5 Kiosk] (wake_engine.js)
   │  Phát chuông ting... (440Hz -> 880Hz)
   │  Chuyển gương mặt sang LISTENING
   │  Thu âm lệnh: "Báo cáo tình hình hệ thống"
   ▼
[PC Core Backend] (server.py: POST /api/voice/interact)
   │  Chuyển Avatar sang THINKING
   │  Tra cứu trí nhớ dài hạn (data/brain.db: Episodic/Semantic Memory)
   │  Sinh câu trả lời điều hành tôn trọng Owner Consent & Policy R0-R5
   ▼
[Vietnamese Female TTS & Mouth-Sync Engine]
   │  1. edge-tts (tts_config.py: vi-VN-HoaiMyNeural) -> MP3 Audio Buffer Base64
   │  2. MouthSyncEngine (mouth_sync.py) -> Sinh UtteranceTimeline (50ms frames)
   │     Visemes: REST (đóng), A (mở rộng), O (tròn môi), E (mỉm bè), I, U
   ▼
[Phát Đồng Thời Hai Thiết Bị (Bi-directional Sync)]
   ├──> PC Core (Virtual Screen 127.0.0.1:8766):
   │      - Canvas DigitalHumanAvatar V2 hiển thị gương mặt tóc tím bạc
   │      - Web Audio API phát MP3
   │      - Cử động môi và chớp mắt đồng bộ theo timeline
   │
   └──> Raspberry Pi 5 (192.168.1.21:8768):
          - Loa USB phát âm thanh thật qua ALSA/WirePlumber
          - Màn hình 7" DSI toàn màn hình (kiosk.html) hiển thị Avatar V2
          - Thuần hình thể Digital Human (KHÔNG hiển thị chữ hội thoại)
          - Kết thúc câu thoại: miệng tự động khép về nụ cười tự nhiên (IDLE)
```

---

## III. QUY CHUẨN THIẾT KẾ DIGITAL HUMAN AVATAR V2

### 1. Giữ Đúng Nhận Diện Nhân Vật Từ `Pi5/6.jpg`
- **Gương mặt:** Giữ nguyên nét đẹp thanh tú, ánh nhìn ấm áp, nụ cười tươi rạng rỡ của bức ảnh `6.jpg`.
- **Mái tóc:** Tím ánh bạc dài óng ả, các lọn tóc mai uốn nhẹ hai bên má, kẹp tóc tinh thể công nghệ.
- **Trang phục:** Bộ giáp cybernetic trắng bạc bóng mờ với các rãnh LED phát quang màu xanh cyan.
- **Hiệu ứng ánh sáng:** Giữ vầng hào quang công nghệ xanh tím dịu nhẹ phía sau, sao trời lấp lánh nhẹ nhàng, không gây chói mắt.
- **Nguyên tắc bất khả xâm phạm:** Không thêm logo, nhãn chữ hay giao diện che khuất khuôn mặt và khẩu hình nhân vật.

### 2. Tối Ưu Màn Hình PC Cockpit (`http://127.0.0.1:8766/`)
- Tích hợp trực tiếp vào khung hiển thị ảo `#virtual-kiosk-screen` trên `executive.html`.
- Canvas $720 \times 720$ hoặc $1024 \times 1024$, khuôn mặt luôn là tâm điểm ánh nhìn.
- Hỗ trợ responsive cho mọi kích thước cửa sổ trình duyệt máy tính.

### 3. Tối Ưu Màn Hình Cảm Ứng 7" DSI Trên Raspberry Pi 5 (`1280x720`)
- **Thuần Hình Thể (Pure Digital Human Body):** Tuân thủ chỉ đạo của Anh Quân: **Tuyệt đối không hiển thị khung chat, không hiện chữ hội thoại trên màn hình Pi 5**.
- Toàn màn hình chỉ dành riêng cho cô trợ lý AI với chuyển động sống động.
- Trực quan hóa trạng thái mạng và dịch vụ bằng chỉ báo ánh sáng viền tinh tế (Aura Border Glow & Cybernetic Status Halo):
  - Xanh Cyan: Sẵn sàng (`IDLE`) / Lắng nghe (`LISTENING`).
  - Tím Nebula: Đang suy nghĩ (`THINKING`) / Nghiên cứu (`RESEARCHING`).
  - Xanh Lam Nhạt: Đang nói chuyện (`SPEAKING`).
  - Xanh Lục Ngọc: Thành công (`SUCCESS`) / Vui vẻ (`HAPPY`).
  - Hổ Phách: Chờ phê duyệt (`WAITING_FOR_OWNER`).
  - Đỏ Ruby: Cảnh báo (`WARNING`) / Bị chặn (`BLOCKED`).
  - Xám Đục: Mất kết nối (`OFFLINE`) / Đang kết nối lại (`RECONNECTING`).
  - Đỏ Nhấp Nháy Chậm: Lỗi âm thanh / dịch vụ (`ERROR`).

---

## IV. BỘ ĐIỀU KHIỂN 12 TRẠNG THÁI BIỂU CẢM & HOẠT ẢNH

Hệ thống sẽ chuẩn hóa bộ điều khiển trạng thái thống nhất gồm **12 trạng thái chính thức**:

| STT | Mã Trạng Thái | Ý Nghĩa Thực Tế | Biểu Cảm & Chuyển Động Avatar V2 |
| :---: | :--- | :--- | :--- |
| 1 | `IDLE` | Sẵn sàng chờ lệnh | Nụ cười tươi tự nhiên từ `6.jpg`, chớp mắt 3-6s, thở ngực nhẹ nhàng, lắc đầu vi mô. |
| 2 | `LISTENING` | Đang lắng nghe | Mắt hướng thẳng vào Anh Quân, nghiêng đầu 1.8° chú ý, hào quang cyan đập nhịp theo giọng nói. |
| 3 | `THINKING` | Đang suy luận/phân tích | Mắt liếc nhẹ lên trái, đầu nghiêng nhẹ, lông mày tập trung, hào quang tím galaxy. |
| 4 | `SPEAKING` | Đang phát âm thanh | Khẩu hình cử động chuyển tiếp mượt mà theo từng âm tiết, đồng bộ 100% với Loa USB. |
| 5 | `HAPPY` | Vui vẻ / Hài lòng | Mắt cười Duchenne rạng rỡ, nụ cười tươi bừng sáng, điểm sáng con ngươi lấp lánh. |
| 6 | `EMPATHETIC` | Dịu dàng / Đồng cảm | Đầu nghiêng dịu, ánh mắt thấu hiểu, nụ cười nhẹ nhàng, hỗ trợ tâm lý tối đa. |
| 7 | `CONFUSED` | Chưa hiểu rõ / Cần hỏi lại | Một bên lông mày nhướng nhẹ, đầu nghiêng dò hỏi, mắt mở to thăm dò chỉ thị. |
| 8 | `SUCCESS` | Nhiệm vụ đã xác minh | Nụ cười rạng ngời, gật đầu xác nhận nhẹ, hào quang xanh lục bảo tỏa sáng. |
| 9 | `WARNING` | Cảnh báo rủi ro / Policy | Gương mặt nghiêm túc, mắt nhìn thẳng cảnh giác, hào quang chuyển đỏ cam. |
| 10 | `OFFLINE` | Mất kết nối PC Core | Mắt nhắm nhẹ, sắc diện chuyển mờ xám lạnh, hào quang tắt. |
| 11 | `ERROR` | Lỗi dịch vụ / Âm thanh | Ánh mắt áy náy nghiêm túc, chỉ báo sự cố đỏ dịu, không làm biến dạng mặt nhân vật. |
| 12 | `RECONNECTING` | Đang khôi phục kết nối | Mắt mở hé, hào quang xanh lam xoay tròn tìm kiếm tín hiệu PC Core. |

---

## V. CÔNG NGHỆ KHẨU HÌNH ĐỒNG BỘ GIỌNG NÓI (MOUTH-SYNC V2)

### 1. Chuẩn Bị Tài Sản Khẩu Hình Khớp Tông Màu `Pi5/6.jpg`
Để tránh hoàn toàn hiện tượng lệch màu hoặc viền hộp hình chữ nhật:
- Cắt và trích xuất trực tiếp vùng môi và răng nguyên bản từ `Pi5/6.jpg`.
- Tạo các biến thể khẩu hình đồng bộ màu da và sắc son hồng tự nhiên:
  - `mouth_v2_rest.png`: Khuôn miệng mỉm cười khép tự nhiên (trạng thái nghỉ/nghe/nghĩ).
  - `mouth_v2_speaking.png`: Khẩu hình nói thông dụng hé răng tự nhiên.
  - `mouth_v2_open_a.png`: Mở rộng cho các nguyên âm /a/, /ă/, /â/.
  - `mouth_v2_open_o.png`: Môi tròn cho các nguyên âm /o/, /ô/, /ơ/, /u/.
  - `mouth_v2_open_e.png`: Môi bè cho /e/, /ê/, /i/.

### 2. Thuật Toán Hòa Trộn Mềm (Feathered Alpha Blending)
- Sử dụng mặt nạ hình elip viền mờ (Feathered Elliptical Gradient Mask) bao quanh khóe miệng.
- Bán kính chuyển tiếp mềm 15-20 pixel giúp chuyển động môi hòa tan 100% vào làn da của bức ảnh gốc `6.jpg`, hoàn toàn không có đường cắt hay vết ghép.
- **Quy tắc dứt điểm:** Khi âm thanh vừa dứt (hoặc khi người dùng ngắt lời), `currentOpenRatio` lập tức hồi quy về `0.0`, chuyển về `mouth_v2_rest.png`. Không bao giờ để miệng há khi im lặng.

---

## VI. DANH SÁCH TỆP THAY ĐỔI & DIFF DỰ KIẾN

### 1. Tạo Tài Sản Mới (Assets Creation)
| Tệp Tin | Mục Đích Sử Dụng |
| :--- | :--- |
| `src/quan_ai_brain/web/static/assets/avatar/avatar_v2_portrait.png` | Master Portrait 1:1 ($1024 \times 1024$) chuẩn nét từ `Pi5/6.jpg` |
| `src/quan_ai_brain/web/static/assets/avatar/avatar_v2_blink.png` | Portrait với mắt khép tự nhiên |
| `src/quan_ai_brain/web/static/assets/avatar/avatar_v2_thinking.png` | Portrait với ánh nhìn suy luận |
| `src/quan_ai_brain/web/static/assets/avatar/avatar_v2_happy.png` | Portrait nụ cười rạng rỡ |
| `src/quan_ai_brain/web/static/assets/avatar/mouth_v2_rest.png` | Khẩu hình nghỉ |
| `src/quan_ai_brain/web/static/assets/avatar/mouth_v2_speaking.png` | Khẩu hình nói chung |
| `src/quan_ai_brain/web/static/assets/avatar/mouth_v2_open_o.png` | Khẩu hình tròn môi |
| `edge_client/assets/avatar/*` | Đồng bộ các tệp tương ứng sang Pi 5 |

### 2. File Sửa Đổi & Diff Dự Kiến

#### A. `src/quan_ai_brain/web/static/avatar_engine.js` & `edge_client/avatar_engine.js`
```diff
--- a/avatar_engine.js
+++ b/avatar_engine.js
@@ -42,12 +42,12 @@ class DigitalHumanAvatar {
     this.height = this.canvas.height || 720;
 
-    // Feature Bounding Boxes (normalized relative to 1024x1024 master)
-    this.EYES_BOX = { x: 320, y: 310, w: 370, h: 110 };
-    this.MOUTH_BOX = { x: 420, y: 500, w: 184, h: 120 };
+    // Feature Bounding Boxes calibrated to Avatar V2 (Pi5/6.jpg - 1024x1024 space)
+    this.EYES_BOX = { x: 335, y: 275, w: 355, h: 100 };
+    this.MOUTH_BOX = { x: 425, y: 455, w: 175, h: 95 };
 
@@ -140,14 +140,24 @@ class DigitalHumanAvatar {
     // State configurations (Standard 12-State Protocol)
     this.STATE_CONFIGS = {
       IDLE: { name: "IDLE (SẴN SÀNG)", auraColor: "#00e5ff", haloSpeed: 0.025, defaultTone: "WARM_GREETING" },
       LISTENING: { name: "LISTENING (LẮNG NGHE)", auraColor: "#06b6d4", haloSpeed: 0.055, defaultTone: "WARM_GREETING" },
       THINKING: { name: "THINKING (SUY LUẬN)", auraColor: "#a855f7", haloSpeed: 0.075, defaultTone: "ANALYTICAL_THINKING" },
       SPEAKING: { name: "SPEAKING (ĐANG NÓI)", auraColor: "#38bdf8", haloSpeed: 0.07, defaultTone: "WARM_GREETING" },
       HAPPY: { name: "HAPPY (VUI VẺ)", auraColor: "#10b981", haloSpeed: 0.06, defaultTone: "CONFIDENT_SUCCESS" },
+      EMPATHETIC: { name: "EMPATHETIC (ĐỒNG CẢM)", auraColor: "#ec4899", haloSpeed: 0.03, defaultTone: "WARM_GREETING" },
+      CONFUSED: { name: "CONFUSED (CHƯA RÕ)", auraColor: "#eab308", haloSpeed: 0.04, defaultTone: "CONSULTATIVE_INQUIRING" },
+      SUCCESS: { name: "SUCCESS (THÀNH CÔNG)", auraColor: "#10b981", haloSpeed: 0.08, defaultTone: "CONFIDENT_SUCCESS" },
+      WARNING: { name: "WARNING (CẢNH BÁO)", auraColor: "#f97316", haloSpeed: 0.03, defaultTone: "SERIOUS_ALERT" },
+      OFFLINE: { name: "OFFLINE (MẤT KẾT NỐI)", auraColor: "#475569", haloSpeed: 0.0, defaultTone: "NEUTRAL" },
+      ERROR: { name: "ERROR (SỰ CỐ)", auraColor: "#ef4444", haloSpeed: 0.02, defaultTone: "SERIOUS_ALERT" },
+      RECONNECTING: { name: "RECONNECTING (KẾT NỐI LẠI)", auraColor: "#0284c7", haloSpeed: 0.09, defaultTone: "NEUTRAL" },
     };
```

#### B. `edge_client/kiosk.html` & `edge_client/kiosk.js`
- Đảm bảo màn hình Pi 5 là Kiosk thuần chân dung Digital Human, xóa sạch phần overlay chữ văn bản nếu còn sót lại, giữ vững nguyên tắc: **Pi 5 là hình thể, không hiển thị chat log**.
- Bổ sung hiệu ứng viền màn hình (Edge Aura Glow) tương ứng với 12 trạng thái trên.

#### C. `src/quan_ai_brain/web/server.py`
- Mở rộng hàm `_handle_api_edge_sync_all_assets` để tự động đẩy toàn bộ asset `avatar_v2_*` sang Pi 5 khi có lệnh đồng bộ.

---

## VII. KẾ HOẠCH BÀN GIAO & DUYỆT CỦA ANH QUÂN

Theo đúng quy trình kỷ luật kỹ thuật của dự án:
1. **Bước 1 (Đã hoàn thành):** Trình bày Báo cáo Audit & Phương án chi tiết này lên Anh Quân.
2. **Bước 2 (Sau khi Anh Quân duyệt):** Tiến hành tạo bộ assets chuẩn V2 từ `Pi5/6.jpg` và cập nhật mã nguồn PC.
3. **Bước 3:** Hoàn thiện TTS tiếng Việt và kiểm thử đồng bộ khẩu hình.
4. **Bước 4:** Đồng bộ toàn diện sang Raspberry Pi 5 qua Wi-Fi API.
5. **Bước 5:** Chạy toàn bộ 383+ tests hồi quy và viết báo cáo nghiệm thu hoàn tất.

Kính trình Anh **Quanpt1** xem xét và cho ý kiến phê duyệt phương án trên để em bắt đầu triển khai Giai đoạn 2!
