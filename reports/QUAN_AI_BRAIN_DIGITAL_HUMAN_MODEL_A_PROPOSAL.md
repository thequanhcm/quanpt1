# BÁO CÁO AUDIT GIAI ĐOẠN 1 & PHƯƠNG ÁN THIẾT KẾ DIGITAL HUMAN MẪU A
## Xây dựng lại hình thể số QUAN AI BRAIN: Dịu dàng, thân thiện, thông minh; đồng bộ PC Core và Raspberry Pi 5

**Người quyết định duy nhất:** Anh Quân — Quanpt1  
**Kỹ sư thực hiện:** Antigravity Chief Digital Human & Systems Engineer  
**Workspace:** `E:\AI\QUAN AI BRAIN`  
**Thời gian:** 2026-10-22  
**Trạng thái:** Chờ phê duyệt trước khi chỉnh sửa mã nguồn (Phase 1 Audit & Proposal Sign-off)

---

## 1. KẾT QUẢ AUDIT TỔNG THỂ HỆ THỐNG

### 1.1. Bằng chứng định danh Mẫu A từ tài liệu gốc
- Sau khi kiểm tra tài liệu `bao cao xay dung he thong/Lựa Chọn Avatar Trợ Lý Ảo TONY.png` (bảng tham chiếu chuẩn của dự án do Anh Quân duyệt), **Mẫu A** được định nghĩa chính thức:
  > **MẪU A: DỊU DÀNG, THÂN THIỆN**  
  > *Phong cách tự nhiên, gần gũi, luôn tươi cười.*
- Đối chiếu với tệp grid gốc độ phân giải cao `Pi5/4.png` (kích thước $2400 \times 1792$ pixel, lưới 9 nhân vật), **Ô trên cùng bên trái (Row 0, Col 0)** chính là bản gốc không nén, không dính chữ của **Mẫu A**.
- Đã trích xuất và tạo bản Master vuông tỷ lệ 1:1 ($1024 \times 1024$ pixel) tại `reports/model_a_1024_preview.jpg`.
- **Tuyệt đối tuân thủ chỉ thị:** Loại bỏ hoàn toàn Mẫu F (tóc tím bạc) và Mẫu C (nháy mắt, thả tim), không dùng avatar robot cũ. Toàn bộ hệ thống quy về nhận diện duy nhất của **Mẫu A**.

---

### 1.2. Bộ tứ trạng thái cốt lõi đã tổng hợp thử nghiệm (Bảo toàn 100% Danh tính)
Để đảm bảo nhân vật **không bị biến đổi khuôn mặt** hay "nhảy phối cảnh" giữa các trạng thái, bộ tứ trạng thái photorealistic đã được tạo và kiểm tra độ khớp tuyệt đối:

| Trạng thái | Tệp Master tương ứng | Đặc điểm hình thể số Mẫu A |
| :--- | :--- | :--- |
| **1. IDLE / LISTENING** | `reports/model_a_1024_preview.jpg` | Nụ cười dịu dàng, ánh mắt sáng chú ý, tóc đen dài mềm mại, tai nghe công nghệ cyan, trang phục trắng bạc. |
| **2. BLINK / OFFLINE** | `reports/model_a_blink.jpg` | Đôi mắt khép lại nhẹ nhàng tự nhiên, hàng mi thanh tú, nụ cười an tâm, không biến dạng mặt. |
| **3. THINKING / RESEARCH**| `reports/model_a_thinking.jpg` | Ánh mắt nhìn chếch lên suy ngẫm thông minh, khuôn miệng khép nhẹ tập trung cao độ. |
| **4. SPEAKING / RESPOND** | `reports/model_a_speaking.jpg` | Khẩu hình mở tự nhiên theo phát âm, nhìn rõ răng trên/dưới và vòm miệng, ánh mắt giao tiếp ấm áp. |

> Tệp tổng hợp xem nhanh 4 trạng thái: `reports/model_a_expressions_quad.jpg`.

---

### 1.3. Hiệu chuẩn Tọa độ Landmark Khuôn mặt (Model F cũ vs. Model A mới)
Do tỷ lệ khuôn mặt và góc nghiêng của Mẫu A khác với Mẫu F cũ, hệ tọa độ trong Canvas 2.5D `avatar_engine.js` cần được tái hiệu chuẩn chính xác:

| Thành phần Landmark | Tọa độ cũ (Mẫu F - 6.jpg) | Tọa độ MỚI HIỆU CHUẨN (Mẫu A - 4.png) | Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Mắt (`EYES_BOX`)** | `{x: 340, y: 270, w: 340, h: 100}` | `{x: 320, y: 425, w: 365, h: 115}` | Mắt Mẫu A nằm ở trục $Y \approx 425-540$, bao trọn khóe mắt và hàng mi. |
| **Miệng (`MOUTH_BOX`)** | `{x: 420, y: 435, w: 184, h: 120}` | `{x: 405, y: 650, w: 245, h: 105}` | Miệng Mẫu A ở trục $Y \approx 650-755$, rộng hơn do nụ cười tươi tự nhiên. |
| **Lông mày trái (`BROW_LEFT`)** | `inner: (470,285), arch: (425,275), tail: (375,288)` | `inner: (475,435), arch: (415,415), tail: (350,435)` | Neo theo cung mày thanh mảnh của Mẫu A. |
| **Lông mày phải (`BROW_RIGHT`)** | `inner: (555,285), arch: (600,275), tail: (650,288)` | `inner: (550,428), arch: (610,410), tail: (670,428)` | Cân đối theo góc nghiêng tự nhiên của khuôn mặt. |

---

### 1.4. Đồ họa Tóc và Ánh sáng Cybernetic
- **Chất liệu tóc:** Thay đổi gradient sợi tóc bay từ màu tím-bạc (`rgba(225, 215, 250)`) sang **màu tóc đen nhung / đen tuyền tự nhiên** với vệt sáng lụa (`rgba(25, 30, 42, 0.65)`) và ánh phản quang cyan mềm mại.
- **Ánh sáng công nghệ:** Vòng hào quang holographic xoay đa tầng màu xanh cyan nhẹ nhàng (`#00e5ff` / `#06b6d4`), giữ nét cao cấp, tinh tế, không chói lóa.

---

## 2. KIẾN TRÚC ĐỒNG BỘ PC CORE — RASPBERRY PI 5

```
+------------------------------------------------------------------------+
|                     PC CORE (http://127.0.0.1:8766/)                   |
|  - Trí tuệ & Suy luận (LLMRouter: Fast 1.5B / Reasoning 7B)           |
|  - Bộ nhớ hội thoại bền vững (SQLite WAL: data/brain.db)               |
|  - Rào chắn bảo mật (OutputGuardrails, Governance R4/R5)               |
|  - TTS Tiếng Việt Nữ: vi-VN-HoaiMyNeural                               |
|  - Tạo UtteranceTimeline (visemes & timestamps)                        |
|  - Giao diện điều hành Executive Desk Cockpit                          |
+------------------------------------------------------------------------+
                                   |
           (Asset Sync via EdgeTransferService / Protocol)
                                   v
+------------------------------------------------------------------------+
|                RASPBERRY PI 5 KIOSK (192.168.1.21:8768)                |
|  - Hình thể số thuần túy (Pure Embodiment): Mẫu A toàn màn hình       |
|  - Thu âm giọng nói người dùng & truyền về PC Core                     |
|  - Canvas 2.5D 60 FPS DigitalHumanAvatar Engine đồng nhất              |
|  - Phát audio TTS đồng bộ khẩu hình viseme thời gian thực              |
|  - Ẩn toàn bộ phụ đề / text chat theo đúng chỉ thị                     |
|  - Trạng thái OFFLINE tự động: khép mắt nghỉ khi mất tín hiệu Core     |
+------------------------------------------------------------------------+
```

---

## 3. KHẨU HÌNH KHỚP GIỌNG NỮ TIẾNG VIỆT (LIP-SYNC & VISEME)

1. **Pipeline thực thi:**
   $$\text{PC Core Response} \longrightarrow \text{Edge TTS (vi-VN-HoaiMyNeural)} \longrightarrow \text{MouthSyncEngine} \longrightarrow \text{UtteranceTimeline} \longrightarrow \text{Feathered Alpha Visemes} \longrightarrow \text{Digital Human A}$$
2. **Quy tắc chuyển động miệng:**
   - **Bắt đầu Audio:** Avatar chuyển tức thì sang `SPEAKING`.
   - **Trong lúc phát âm:** Khẩu hình chuyển đổi giữa các viseme (`A`, `O`, `E`, `I`, `U`, `REST`) dựa trên timeline ngữ âm thực tế. Răng trên giữ nguyên độ cao giải phẫu học; chỉ có môi dưới và hàm mở đóng nhịp nhàng.
   - **Kết thúc Audio:** Khẩu hình tự động trở về `REST` (tỷ lệ 0.0), trả lại nụ cười dịu dàng tự nhiên của Mẫu A.
   - **Cơ chế ngắt lời (Barge-in):** Khi người dùng nói ngắt lời, `cancel_utterance()` hủy ngay lập tức âm thanh và hoạt ảnh miệng, không để miệng chuyển động thừa hoặc phát lại câu cũ.

---

## 4. DANH SÁCH FILE DỰ KIẾN THAY ĐỔI VÀ DIFF ĐỀ XUẤT

| STT | Đường dẫn tệp | Loại thay đổi | Mục đích |
| :---: | :--- | :---: | :--- |
| 1 | `tools/generate_avatar_model_a_assets.py` | Tạo mới | Script tạo trọn bộ asset Mẫu A 1024x1024 và viseme RGBA feathered từ ảnh gốc `Pi5/4.png` và các bản master đã duyệt. |
| 2 | `src/quan_ai_brain/web/static/assets/avatar/*` | Ghi đè/Tạo mới | Bộ asset Mẫu A trên PC Core (Master portraits, blinks, expressions, mouth visemes). |
| 3 | `edge_client/assets/avatar/*` | Ghi đè/Tạo mới | Bộ asset Mẫu A trên Raspberry Pi 5 Kiosk (bảo đảm hai máy dùng chung 100% asset). |
| 4 | `src/quan_ai_brain/web/static/avatar_engine.js` | Chỉnh sửa | Hiệu chuẩn `EYES_BOX`, `MOUTH_BOX`, `BROW_*` sang Mẫu A; cập nhật đồ họa tóc đen tự nhiên và ánh sáng cyan. |
| 5 | `edge_client/avatar_engine.js` | Chỉnh sửa | Đồng bộ phiên bản engine giống hệt PC Core cho Pi 5 Kiosk. |
| 6 | `src/quan_ai_brain/web/static/executive.html` | Chỉnh sửa | Cập nhật nhãn tiêu đề: `DIGITAL HUMAN (MẪU A — DỊU DÀNG, THÂN THIỆN)`. |
| 7 | `tests/test_digital_human_avatar_v2.py` | Chỉnh sửa | Cập nhật các bài kiểm thử tự động kiểm tra kích thước, asset Mẫu A, và bounding boxes mới. |
| 8 | `tools/sync_pi5_complete.py` | Chỉnh sửa nhẹ | Bổ sung tệp asset Mẫu A vào danh sách đồng bộ sang Pi 5. |

---

### Diff đề xuất trên `avatar_engine.js` (Trích đoạn cốt lõi):

```diff
-    // Feature Bounding Boxes (calibrated to Avatar V2 - Pi5/6.jpg 1024x1024 master)
-    this.EYES_BOX = { x: 340, y: 270, w: 340, h: 100 };
-    this.MOUTH_BOX = { x: 420, y: 435, w: 184, h: 120 };
+    // Feature Bounding Boxes (calibrated to Digital Human Model A - Pi5/4.png 1024x1024 master)
+    this.EYES_BOX = { x: 320, y: 425, w: 365, h: 115 };
+    this.MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 };

-    // Eyebrows Anchor Geometry (1024x1024 coordinates)
-    this.BROW_LEFT = { innerX: 470, innerY: 285, archX: 425, archY: 275, tailX: 375, tailY: 288 };
-    this.BROW_RIGHT = { innerX: 555, innerY: 285, archX: 600, archY: 275, tailX: 650, tailY: 288 };
+    // Eyebrows Anchor Geometry (Model A 1024x1024 coordinates)
+    this.BROW_LEFT = { innerX: 475, innerY: 435, archX: 415, archY: 415, tailX: 350, tailY: 435 };
+    this.BROW_RIGHT = { innerX: 550, innerY: 428, archX: 610, archY: 410, tailX: 670, tailY: 428 };

-    // 1. Left Hair Cascade Strands (Lilac-Silver Gradient)
-    const gradL = ctx.createLinearGradient(280 * scaleX, 350 * scaleY, 240 * scaleX, 780 * scaleY);
-    gradL.addColorStop(0.0, "rgba(225, 215, 250, 0.45)");
-    gradL.addColorStop(0.5, "rgba(185, 165, 230, 0.30)");
+    // 1. Left Hair Cascade Strands (Natural Soft Black with Cyber Cyan Sheen)
+    const gradL = ctx.createLinearGradient(280 * scaleX, 400 * scaleY, 240 * scaleX, 850 * scaleY);
+    gradL.addColorStop(0.0, "rgba(25, 30, 42, 0.65)");
+    gradL.addColorStop(0.5, "rgba(0, 229, 255, 0.25)");
```

---

## 5. KẾ HOẠCH BẢO TOÀN VÀ PHƯƠNG ÁN ROLLBACK

- **Bảo toàn tuyệt đối:**
  - Giữ nguyên toàn bộ logic suy luận `LLMRouter`, bộ nhớ phiên `SessionMemoryManager`, các rào chắn `OutputGuardrails` và cơ chế an toàn R4/R5.
  - Không sửa đổi các dự án bên ngoài workspace (`os_kernel`, `DC-COMMAND`, `BATTERY_AI_V4`).
  - Không xóa các ảnh tham chiếu trong `Pi5/`.
- **Phương án Rollback tức thì:**
  - Toàn bộ asset Model F cũ được sao lưu tự động tại `reports/model_f_backup/`.
  - Nếu anh Quân muốn quay lại cấu hình cũ, chỉ cần khôi phục 4 dòng tọa độ bounding box trong `avatar_engine.js`.

---

## 6. YÊU CẦU PHÊ DUYỆT TỪ ANH QUÂN

Kính trình anh Quân xem xét hình ảnh tổng hợp 4 trạng thái tại `reports/model_a_expressions_quad.jpg` và các nội dung trong đề xuất này.

**Sau khi nhận được xác nhận đồng ý triển khai từ Anh Quân**, em sẽ:
1. Tạo script `tools/generate_avatar_model_a_assets.py` và sinh trọn bộ asset Mẫu A chuẩn 1024x1024.
2. Cập nhật `avatar_engine.js` trên PC Core và Pi 5.
3. Cập nhật giao diện `executive.html` và `kiosk.html`.
4. Chạy kiểm thử tự động toàn diện và xuất báo cáo nghiệm thu hoàn thành.
