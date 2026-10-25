# QUAN AI BRAIN — THIẾT KẾ GIAO DIỆN BIỂU CẢM VÀ BÀN ĐIỀU HÀNH THỊ GIÁC
## VISUAL COCKPIT & EXPRESSIVE FACE DESIGN SPECIFICATION

- **Dự án:** QUAN AI BRAIN — Digital Executive Assistant
- **Chủ nhân & Người phê chuẩn:** Quanpt1
- **Phạm vi áp dụng:**
  1. **PC Brain Cockpit:** Màn hình điều hành trung tâm tại `http://127.0.0.1:8766/`.
  2. **Raspberry Pi 5 Edge Kiosk:** Màn hình cảm ứng để bàn 5-7 inch.
- **Nguyên tắc thẩm mỹ & công nghệ:**
  - Thiết kế cao cấp (Premium Dark Mode, Glassmorphism, HSL Tailored Colors, Inter font).
  - Phản ánh trạng thái thực: **Không dùng animation giả lập** khi backend đang rảnh rỗi.
  - Hỗ trợ chế độ giảm chuyển động (Reduced Motion) và khả năng tiếp cận (Accessibility - A11y).

---

## 1. THIẾT KẾ DIGITAL AVATAR — EXPRESSIVE FACE (KHUÔN MẶT SỐ BIỂU CẢM)

Avatar của QUAN AI BRAIN (tên gọi trợ lý: **TONY**) được thiết kế dưới dạng hình học số học (Geometric Cybernetic Avatar) với đôi mắt phát sáng biểu cảm và vòng năng lượng trạng thái:

```
            ╭───────────────────────────────────╮
            │          QUAN AI BRAIN            │
            │                                   │
            │         ╭───╮       ╭───╮         │
            │         │ ◉ │       │ ◉ │         │  <─── Đôi mắt số biểu cảm
            │         ╰───╯       ╰───╯         │
            │                                   │
            │           ╭───────────╮           │  <─── Sóng âm dao động
            │           │  ▂ ▃ ▅ ▃  │           │       hoặc vạch trạng thái
            │           ╰───────────╯           │
            │                                   │
            │       [ ● STATE: LISTENING ]      │  <─── Huy hiệu trạng thái thực
            ╰───────────────────────────────────╯
```

### 1.1. Ma trận 11 trạng thái biểu cảm chuẩn mực

| Mã trạng thái | Màu sắc chủ đạo (HSL) | Biểu hiện của Mắt (Eyes) | Vòng năng lượng / Miệng | Ý nghĩa trạng thái |
|---|---|---|---|---|
| `IDLE` | Lam sẫm `#0ea5e9` | Mắt mở bình thường, chớp nhẹ mỗi 4 giây | Vòng hào quang thở nhẹ (Breathe glow 0.5Hz) | Trợ lý sẵn sàng, đang lắng nghe từ đánh thức |
| `LISTENING` | Lục lam sáng `#06b6d4` | Mắt mở to, đồng tử sáng rực rỡ | Vòng sóng âm phản hồi theo âm lượng micro | Đang nghe Quanpt1 nói sau khi nhận diện "Tony ơi" |
| `THINKING` | Tím thạch anh `#8b5cf6` | Mắt thu hẹp nhẹ, vệt sáng quét ngang | Các vòng bánh răng DAG xoay nhẹ | Đang gọi Ollama LLM và lập kế hoạch TaskPlan |
| `RESEARCHING` | Xanh ngọc `#10b981` | Mắt tập trung, biểu tượng kính lúp nhỏ | Radar quét tài liệu nội bộ và trích xuất tri thức | Đang tổng hợp hồ sơ nghiên cứu trong Learning Engine |
| `LEARNING` | Vàng kim `#f59e0b` | Mắt chớp nhịp nhanh, nạp dữ liệu | Vòng xoay phân tích tri thức cách ly (Quarantine) | Đang chạy chu trình tự học và sinh UpgradeProposal |
| `SPEAKING` | Xanh dương `#3b82f6` | Mắt sáng thân thiện, nhìn thẳng | Dải sóng âm thanh (Audio Waveform) dao động 60fps | Đang phát câu trả lời qua giọng nói TTS |
| `WAITING_FOR_OWNER`| Hổ phách `#f97316` | Mắt mở to nhìn chờ đợi, nhấp nháy chậm | Biểu tượng chuông tham vấn nhấp nháy 1Hz | Đang chờ Quanpt1 bấm duyệt đề xuất trên Port 8766 |
| `BLOCKED` | Đỏ thắm `#ef4444` | Mắt chéo nghiêm nghị, biểu tượng khiên chắn | Vòng bảo vệ khóa chặt ranh giới | Bị chặn bởi chính sách bảo vệ hoặc quy tắc R5 |
| `ERROR` | Đỏ cam `#dc2626` | Mắt tam giác cảnh báo | Dấu chấm than cảnh báo nhấp nháy | Gặp sự cố kết nối hoặc lỗi cú pháp |
| `SAFE_MODE` | Lam băng `#38bdf8` | Mắt đóng băng bảo vệ | Lớp tinh thể bao bọc | Hệ thống đang đóng băng theo lệnh FREEZE |
| `OFFLINE` | Xám tro `#64748b` | Mắt nhắm dạng đường kẻ ngang tĩnh | Vòng hào quang tắt | Mất kết nối mạng tới Brain Core |

---

## 2. GIAO DIỆN BÀN ĐIỀU HÀNH TRÊN PC (EXECUTIVE DESK — PORT 8766)

Giao diện trên PC được tối ưu hóa cho màn hình lớn (Desktop / Laptop) với bố cục 6 khu vực chức năng khoa học:

### 2.1. Header Bar (Thanh trạng thái hệ thống)
- **Logo & Danh tính trợ lý:** `QUAN AI BRAIN — DIGITAL EXECUTIVE DESK`.
- **Trạng thái Brain Core:** Huy hiệu xanh `ONLINE (127.0.0.1:8766)` kèm PID tiến trình thực.
- **Model LLM:** `qwen2.5:7b (Local Ollama)` kèm chỉ số probe TCP socket `<=50ms`.
- **Trí nhớ dài hạn:** `SQLite WAL (brain.db: 65KB, 3 candidates)`.
- **Thiết bị Edge đã ghép cặp:** `01 Active (Raspberry Pi 5 Desk)`.
- **Thời gian đồng bộ:** Đồng hồ UTC & Giờ địa phương cập nhật từng giây.

### 2.2. Khu vực trung tâm: Digital Avatar & Active Task Focus
- **Avatar 3D/SVG:** Biểu cảm thời gian thực của TONY theo 11 trạng thái ở Mục 1.
- **Nhiệm vụ đang xử lý (Current Focus):**
  - Task ID, Mục tiêu, Cấp độ tự chủ (`LEVEL_A`, `LEVEL_B`, `LEVEL_C`, `LEVEL_D`).
  - Thanh tiến trình thực hiện từng bước của kế hoạch DAG.
- **Microphone & Voice Controls:** Nút bật/tắt chế độ rảnh tay, danh sách 10 từ đánh thức ("Tony ơi", "Hi TONY",...), thanh đo âm lượng đầu vào trực quan.

### 2.3. Khu vực Quản lý Vận hành (Operational Activity Stream)
- Bảng hiển thị từ `DurableTaskRegistry` (`data/tasks.db`):
  - Danh sách nhiệm vụ đang chờ (`PENDING`).
  - Nhiệm vụ đã hoàn thành kèm bằng chứng (`evidence_refs`).
  - Nhiệm vụ thất bại hoặc phục hồi sự cố (`OUTCOME_UNKNOWN`).
  - Nút bấm thêm nhiệm vụ mới trực tiếp từ giao diện.

### 2.4. Khu vực Trung tâm Tự học (Learning Cockpit)
- Theo dõi các chu kỳ tự học từ `PeriodicLearningReporter` (`data/learning_reports.db`):
  - Số kỳ học gần nhất, thời gian hoàn thành.
  - Vấn đề nghiên cứu & Tri thức mới trong Vùng cách ly (`CANDIDATE`).
  - Điểm tự tin (Confidence score: ví dụ `92.5%`).
  - Trạng thái kiểm thử hồi quy (`Regression: ALL_PASSED`).
  - Nút bấm *"Kích Hoạt Chu Kỳ Học Mới"* (gọi API có xác thực).

### 2.5. Hộp thư Tham vấn & Quyết định (Consultation Inbox)
- Danh sách các vé nâng cấp từ `ConsultationStore` (`data/consultations.db`):
  - Phân loại rõ ràng: Đề xuất mới, Đang chờ duyệt, Đã duyệt, Đã từ chối.
  - Hiển thị trực tiếp Unified Diff, kết quả test before/after, rủi ro và kế hoạch rollback.
  - Nút bấm **[PHÊ DUYỆT]**, **[TỪ CHỐI]**, hoặc **[CHỈ ĐẠO THÊM]** dành riêng cho Quanpt1.

### 2.6. Bảng Quản trị An toàn (Safety & Emergency Panel)
- **Nút STOP KHẨN CẤP (Nút Đỏ Lớn):** Lập tức kích hoạt lệnh dừng toàn bộ công cụ trong 0.1 giây.
- **Nút FREEZE:** Đóng băng hệ thống về chế độ an toàn chỉ đọc.
- **Trạng thái ranh giới:** Xác nhận R5 bị khóa cứng, R4 yêu cầu chữ ký số HMAC-SHA256.

---

## 3. GIAO DIỆN EDGE RASPBERRY PI 5 (EDGE KIOSK INTERFACE)

Thiết kế tối giản, tối ưu cho màn hình cảm ứng để bàn nhỏ (5 inch hoặc 7 inch), ưu tiên tương tác giọng nói:

```
┌───────────────────────────────────────────────────────────┐
│ 🖧 CORE: ONLINE (192.168.1.50)         🔒 SAFE: NORMAL    │
├───────────────────────────────────────────────────────────┤
│                                                           │
│                       ╭───╮   ╭───╮                       │
│                       │ ◉ │   │ ◉ │                       │
│                       ╰───╯   ╰───╯                       │
│                                                           │
│                         ▂ ▃ ▅ ▃                           │
│                                                           │
│                   "Chào Anh Quanpt1!                      │
│                Em đang sẵn sàng hỗ trợ."                  │
│                                                           │
├───────────────────────────────────────────────────────────┤
│ [🎤 TONY ƠI...]      [📋 VIỆC CẦN DUYỆT: 01]     [🛑 STOP]│
└───────────────────────────────────────────────────────────┘
```

1. **Hiển thị Avatar toàn màn hình:** Đôi mắt số chiếm 60% diện tích màn hình để người dùng dễ dàng nhận biết trạng thái từ xa.
2. **Hộp thoại ngắn gọn (Micro Transcript):** Chỉ hiển thị 1 câu Quanpt1 vừa nói và 1 câu trả lời gần nhất của Brain.
3. **Chỉ báo kết nối Core:** Nếu mất kết nối Wi-Fi tới máy tính, viền màn hình chuyển sang màu xám nhấp nháy kèm dòng chữ: *"Mất kết nối Brain Core"*.
4. **Huy hiệu công việc cần duyệt:** Nếu có vé tham vấn R4 mới trên PC, màn hình Pi 5 hiển thị một thông báo màu vàng: *"Có 1 đề xuất cần Anh duyệt trên PC"*.
5. **Nút bấm cảm ứng STOP:** Cho phép Quanpt1 chạm tay dừng ngay lập tức mọi tác vụ đang chạy trên PC từ xa.

---

## 4. MÔ HÌNH DỮ LIỆU ĐỒNG BỘ THỜI GIAN THỰC (CORE-TO-EDGE STATE MODEL)

Tất cả các thành phần UI (PC và Raspberry Pi 5) đều nhận cùng một gói trạng thái JSON qua WebSocket hoặc REST polling:

```json
{
  "protocol_version": "1.0",
  "timestamp_utc": "2026-10-19T11:42:00.123456Z",
  "core_status": "ONLINE",
  "system_uptime_sec": 43200,
  "active_model": "qwen2.5:7b",
  "supervisor_state": "READY",
  "voice_state": "LISTENING",
  "current_task": {
    "task_id": "task_9f8a12bc",
    "goal": "Tra cứu kiến trúc chỉ mục SQLite",
    "risk_level": "R0",
    "autonomy_level": "LEVEL_A",
    "step_current": 2,
    "step_total": 3
  },
  "learning_status": {
    "cycle_number": 2,
    "last_cycle_at": "2026-10-19T09:25:54Z",
    "quarantined_candidates_count": 3,
    "proposals_pending_review": 1
  },
  "governance": {
    "emergency_state": "normal",
    "pending_consultations_count": 3,
    "r5_status": "HARD_BLOCKED"
  },
  "edge_client": {
    "device_id": "EDGE-PI5-DESK",
    "authenticated": true,
    "last_ping_latency_ms": 2.4
  }
}
```

### Nguyên tắc chống dữ liệu ảo (Anti-Stale Rule)
- Mỗi gói trạng thái có trường `timestamp_utc`.
- Nếu UI không nhận được gói trạng thái mới trong vòng **5 giây**:
  - Huy hiệu trạng thái chuyển từ màu xanh (Online) sang màu cam (Cảnh báo mất tín hiệu).
  - Sau **10 giây**: Chuyển sang màu xám (Offline) và ngừng mọi animation.
  - **Tuyệt đối không giữ màu xanh khi dữ liệu đã quá hạn.**
