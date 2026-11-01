# QUAN AI BRAIN — THƯ VIỆN DIGITAL HUMAN AVATAR (MODEL A)
> **Gói thư viện đóng gói độc lập toàn bộ hoạt động, cử chỉ, biểu cảm và khẩu hình của Trợ lý số Tony (Digital Human Model A) để sao lưu (backup) và tái sử dụng.**

---

## 📌 1. Toàn bộ phần hiển thị Avatar trong hệ thống đang được lưu ở đâu?

Trong kiến trúc tổng thể của **QUAN AI BRAIN**, phần Avatar được phân bổ tại các vị trí chuyên biệt sau:

| Thành phần | Đường dẫn trong hệ thống | Chức năng |
| :--- | :--- | :--- |
| **Động cơ Canvas 2.5D (PC Core)** | `src/quan_ai_brain/web/static/avatar_engine.js` | Vẽ 60 FPS, tính toán vật lý nghiêng/gật đầu, chớp mắt kép, hòa trộn khẩu hình viền mờ (feathered alpha blending), bộ 12 trạng thái cảm xúc. |
| **Động cơ Canvas 2.5D (Pi 5 Edge)** | `edge_client/avatar_engine.js` | Bản engine đồng bộ cho màn hình cảm ứng Kiosk Raspberry Pi 5. |
| **Kho hình ảnh Assets (PC Core)** | `src/quan_ai_brain/web/static/assets/avatar/` | 44 tệp đồ họa: Master Portrait 1024x1024, các trạng thái biểu cảm (happy, thinking, blink, v.v.), lớp mắt và khẩu hình miệng alpha RGBA. |
| **Kho hình ảnh Assets (Pi 5 Edge)** | `edge_client/assets/avatar/` | Bản sao phục vụ hiển thị cục bộ tốc độ cao trên Pi 5. |
| **Ảnh tham chiếu Master gốc** | `Pi5/4.png` (Model A 2400x1792) & `Pi5/6.jpg` (Model F) | Nguồn hình ảnh gốc độ phân giải cao dùng để cắt trích xuất các biểu cảm. |
| **Động cơ Lip-Sync Python** | `src/quan_ai_brain/voice/mouth_sync.py` | Phân tích âm vị tiếng Việt, đo thời lượng MP3 thực tế và tạo dòng thời gian khẩu hình (Viseme Timeline). |
| **Giao diện tích hợp (Web Core)** | `src/quan_ai_brain/web/static/executive.html` & `index.html` | Tích hợp Avatar Canvas vào Bảng điều hành số trợ lý Tony trên PC. |
| **Giao diện tích hợp (Pi 5 Kiosk)** | `edge_client/kiosk.html`, `kiosk.js`, `kiosk.css` | Giao diện toàn màn hình chạm cảm ứng trên bàn làm việc của Anh Quân. |
| **Công cụ sinh Assets tự động** | `tools/generate_avatar_model_a_assets.py` | Script cắt tự động, feather viền và xuất đủ 44 tệp asset từ ảnh master. |
| **Kiểm thử chất lượng & an toàn** | `tests/test_digital_human_avatar_v2.py` & `tools/avatar_v3_giai_doan_b_tests.py` | Bộ kiểm thử tự động 13/13 tiêu chí về độ phân giải, kênh alpha, 12 trạng thái, bell-curve. |

---

## 📦 2. Cấu trúc thư mục gói Backup này (`bao cao xay dung he thong/avatar/`)

Thư viện đóng gói tại thư mục này được thiết kế **hoàn toàn khép kín, độc lập 100% (Zero-Dependency)**. Anh Quân có thể copy thư mục này sang bất kỳ máy tính, dự án web hoặc thiết bị nhúng nào khác:

```text
bao cao xay dung he thong/avatar/
├── demo.html               # Studio giao diện kiểm thử trực quan tương tác (Chạy offline)
├── avatar_engine.js        # Động cơ JavaScript chính điều khiển Avatar (Model A Final V3)
├── avatar.css              # Stylesheet chứa biến màu 12 trạng thái, hiệu ứng hào quang Aura & Viewport
├── mouth_sync.py           # Module Python tính toán khẩu hình tiếng Việt & khớp độ dài audio
├── generate_assets.py      # Script tái tạo toàn bộ 44 assets từ ảnh gốc
├── test_avatar.py          # Script tự động kiểm tra tính toàn vẹn của thư viện (6/6 tests)
├── README.md               # Bản thuyết minh kiến trúc và hướng dẫn sử dụng chi tiết
├── avatar_backup.zip       # Tệp nén toàn bộ thư viện để anh lưu trữ 1 chạm
└── assets/                 # Thư mục chứa toàn bộ 44 tệp hình ảnh + Ảnh gốc Master 4K
    ├── avatar_v2_portrait.png    # Chân dung chính chuẩn 1024x1024
    ├── avatar_v2_blink.png       # Trạng thái chớp mắt
    ├── avatar_v2_happy.png       # Biểu cảm tươi vui, cười
    ├── avatar_v2_thinking.png    # Biểu cảm suy luận, tập trung
    ├── avatar_v2_speaking.png    # Trạng thái đang nói
    ├── avatar_v2_empathic.png    # Biểu cảm đồng cảm, lắng nghe
    ├── avatar_v2_confused.png    # Biểu cảm thắc mắc, băn khoăn
    ├── avatar_v2_surprised.png   # Biểu cảm ngạc nhiên
    ├── avatar_v2_warning.png     # Biểu cảm cảnh báo
    ├── avatar_v2_error.png       # Biểu cảm báo lỗi
    ├── mouth_v2_rest.png         # Khẩu hình nghỉ (RGBA alpha)
    ├── mouth_v2_speaking.png     # Khẩu hình nói thông thường (RGBA alpha)
    ├── mouth_v2_open_o.png       # Khẩu hình chữ O/U tròn miệng (RGBA alpha)
    ├── mouth_v2_happy.png        # Khẩu hình cười nói tươi vui (RGBA alpha)
    ├── eyes_open.png / eyes_closed.png / eyes_thinking.png
    ├── master_model_a_source.png # Ảnh gốc 2400x1792 Model A (Pi5/4.png)
    └── ... (đầy đủ các tệp phụ trợ và Model F legacy)
```

---

## 🧠 3. Các tính năng cốt lõi của Động cơ Avatar (`avatar_engine.js`)

1. **Vật lý cử chỉ sinh học (Biological Human Dynamics):**
   - **Gật đầu vi mô (Micro-Nodding):** Giật đầu nhẹ theo hàm cosine êm ái khi lắng nghe câu lệnh hoặc chào đón Anh Quân.
   - **Nghiêng đầu (Head Tilt Roll):** Nghiêng đầu tự nhiên từ `-2.2°` đến `+2.2°` khi suy nghĩ hoặc phản hồi thân thiện.
   - **Lắc hông/Chuyển trọng tâm (Yaw & Weight Shift):** Dao động ngang mềm mại `-3.5px` đến `+3.5px`.
   - **Nhịp thở vi mô (Micro-Breathing):** Dao động nâng hạ lồng ngực tự nhiên chu kỳ 3.5 giây.
   - **Chớp mắt sinh học (Biological Eye Blinking):**
     - Khoảng cách chớp ngẫu nhiên từ `3.2s` đến `6.0s`.
     - Cơ chế **Chớp mắt kép (Double-Blink)** với tỉ lệ `28%` giống hệt mắt người thật.
     - Thời gian chớp tiêu chuẩn `135ms` với viền mi mắt làm mềm.
   - **Đảo ánh nhìn (Saccades):** Mắt liếc góc trên bên trái khi suy nghĩ (`THINKING`), nhìn tập trung phía trước khi lắng nghe (`LISTENING`).
   - **Nụ cười Duchenne:** Mắt híp nhẹ tự nhiên và điểm sáng đồng tử (iris glint pulse) khi vui vẻ hoặc hoàn thành nhiệm vụ xuất sắc.

2. **Hòa trộn khẩu hình siêu mượt (Feathered Elliptical Alpha Blending):**
   - Áp dụng mặt nạ elip với gradient mờ viền (Radial Alpha Feathering).
   - Triệt tiêu 100% hiện tượng viền đen, răng cưa hoặc vệt hộp chữ nhật quanh miệng.
   - Khớp nối hoàn hảo với khuôn miệng gốc của Model A.

3. **Thuật toán Khẩu hình Bell-Curve (Avatar V3 Phase B):**
   - Loại bỏ hoàn toàn cơ chế giật ngẫu nhiên (`Math.random()`), thay thế bằng bao hình sin mịn (`0.35 * sin(π * phase)`).
   - Miệng mở khép mượt mà, triệt tiêu hiện tượng "nhai giật" (chewing artifacts) khi mất tín hiệu timeline.

4. **Bộ 12 Trạng thái Giao thức Điều hành Số:**
   - `IDLE` (Sẵn sàng - Cyan #00e5ff)
   - `LISTENING` (Lắng nghe - Xanh ngọc #06b6d4)
   - `THINKING` (Suy luận - Tím #a855f7)
   - `SPEAKING` (Đang nói - Xanh dương #38bdf8)
   - `HAPPY` (Vui vẻ - Xanh lá #10b981)
   - `EMPATHETIC` (Đồng cảm - Hồng #ec4899)
   - `CONFUSED` (Chưa rõ - Vàng #eab308)
   - `SUCCESS` (Thành công - Xanh ngọc lục bảo #34d399)
   - `WARNING` (Cảnh báo - Cam #f97316)
   - `OFFLINE` (Mất kết nối - Xám #64748b)
   - `ERROR` (Sự cố - Đỏ #ef4444)
   - `RECONNECTING` (Đang kết nối lại - Xanh lơ #0284c7)

---

## 📐 4. Hệ Tọa Độ Landmark Hiệu Chuẩn Model A

Mọi tọa độ tính toán trong `avatar_engine.js` đều được định chuẩn trên hệ không gian Master `1024 x 1024`:

```javascript
// Bounding box định vị mắt
this.EYES_BOX = { x: 320, y: 425, w: 365, h: 115 };

// Bounding box định vị miệng (khẩu hình viseme)
this.MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 };

// Điểm neo lông mày trái & phải
this.BROW_LEFT  = { innerX: 475, innerY: 435, archX: 415, archY: 415, tailX: 350, tailY: 435 };
this.BROW_RIGHT = { innerX: 550, innerY: 428, archX: 610, archY: 410, tailX: 670, tailY: 428 };
```

---

## 🚀 5. Hướng dẫn Khởi chạy & Kiểm thử

### Cách 1: Mở trực tiếp Studio Kiểm thử (`demo.html`)
1. Nhấp đúp chuột vào tệp `demo.html` để mở trong trình duyệt Chrome, Edge hoặc Firefox.
2. Tại đây Anh có thể:
   - Thử nghiệm chuyển đổi qua lại giữa **12 trạng thái cảm xúc**.
   - Bấm kích hoạt cử chỉ: **Gật đầu, Nghiêng đầu, Chớp mắt đơn, Chớp mắt kép**.
   - Nhập câu tiếng Việt bất kỳ và bấm **▶️ Mô phỏng nói** để kiểm tra đồng bộ khẩu hình.
   - Điều chỉnh thanh trượt vi biểu cảm (nhướng mày, híp mắt, nụ cười).

### Cách 2: Chạy kiểm tra tự động bằng Python
Mở terminal tại thư mục này và gõ:
```bash
python test_avatar.py
```
Kết quả hiển thị:
```text
==================================================
QUAN AI BRAIN — AVATAR MODEL A VERIFICATION SUITE
==================================================
[PASS] All core library files exist and non-empty.
[PASS] All 14 required expression and mouth assets verified.
[PASS] Master portrait is calibrated to 1024x1024 (1:1 ratio).
[PASS] Mouth layers have RGBA alpha channel for seamless feathering.
[PASS] avatar_engine.js 12-state protocol and Model A facial landmarks calibrated.
[PASS] mouth_sync.py generated valid Vietnamese phoneme timeline.
==================================================
[SUCCESS] ALL AVATAR VERIFICATION TESTS PASSED SUCCESSFULLY!
==================================================
```

---

## 💻 6. Hướng dẫn Tích hợp vào Dự án Mới

### Nhúng vào trang HTML:
```html
<link rel="stylesheet" href="./avatar.css">

<div class="avatar-viewport state-idle" id="my-avatar-viewport">
  <canvas id="my-avatar-canvas" width="720" height="720" class="avatar-canvas"></canvas>
</div>

<script src="./avatar_engine.js"></script>
<script>
  // Khởi tạo Avatar
  const avatar = new DigitalHumanAvatar("my-avatar-canvas", {
    basePath: "./assets",
    initialState: "IDLE",
    onStateChange: (state, config) => {
      document.getElementById("my-avatar-viewport").className = `avatar-viewport state-${state.toLowerCase()}`;
    }
  });

  // Chuyển trạng thái
  avatar.setState("LISTENING");

  // Kích hoạt nói theo timeline
  avatar.setTimeline(timelineData);

  // Hoặc kích hoạt nói nhanh với thời lượng
  avatar.startSpeaking(3500);

  // Kích hoạt gật đầu
  avatar.isNodding = true;
  avatar.nodStartTime = performance.now();
</script>
```

---
*Gói sao lưu hoàn tất vào lúc 20:15 - 25/10/2026. Đã kiểm thử an toàn và hoạt động độc lập.*
