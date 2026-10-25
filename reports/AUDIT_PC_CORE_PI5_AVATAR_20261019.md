# QUAN AI BRAIN — BÁO CÁO AUDIT HIỆN TRẠNG & ĐỀ XUẤT KIẾN TRÚC GIAI ĐOẠN 0
## PC CORE ↔ RASPBERRY PI 5 DIGITAL AVATAR
### Kết nối hai chiều — Đồng bộ trạng thái — Cảnh báo mất kết nối — Giọng nói và khẩu hình thời gian thực

- **Thời gian lập báo cáo:** 2026-10-19 19:40:00 (Local Time)
- **Hệ thống thẩm định:** Workspace `E:\AI\QUAN AI BRAIN`
- **Phiên bản Python:** Python 3.11.9 x64
- **Thiết bị chủ quản (PC Core):** Dell Precision 7550 — Windows 10/11 x64
- **Thiết bị ngoại vi thể chất (Edge Avatar):** Raspberry Pi 5 (4GB RAM) — Linux aarch64
- **Cơ sở dữ liệu kiểm tra:** 281/281 bài kiểm thử tự động đạt (PASS)
- **Tình trạng:** `GIAI ĐOẠN 0 HOÀN TẤT — CHƯA THAY ĐỔI MÃ NGUỒN — CHỜ PHÊ DUYỆT`

---

## 1. KIẾN TRÚC THỰC TẾ HIỆN TẠI (CURRENT AS-IS ARCHITECTURE)

Dự án hiện bao gồm 2 phân hệ chính hoạt động trên máy tính Dell Precision 7550 của Anh Quanpt1:

```
+-----------------------------------------------------------------------------------+
|               MÁY TÍNH TRUNG TÂM — PC CENTRAL BRAIN CORE (WINDOWS)                |
|                                                                                   |
|  [Cổng 11434]  Ollama Daemon (Mô hình qwen2.5:7b cục bộ)                          |
|  [Cổng 8765]   Web UI Chat & Memory Retrieval (BrainAPIHandler)                    |
|  [Cổng 8766]   Executive Consultation & Management Desk (Visual Cockpit Hero)      |
|                                                                                   |
|  [Lõi Tri Thức] SQLite WAL:                                                       |
|    - data/brain.db         : Bộ nhớ dài hạn 6 loại, truy xuất tiếng Việt có dấu   |
|    - data/tasks.db         : Sổ đăng ký nhiệm vụ bền vững (DurableTaskRegistry)    |
|    - data/governance.db    : Trạng thái STOP/FREEZE, single-use token, nonces     |
|    - data/consultations.db : Hộp thư tham vấn lãnh đạo trực tiếp                   |
|                                                                                   |
|  [Ràng Buộc An Toàn]                                                              |
|    - R5: Cấm tiệt đối (Hard-Blocked) — Không tồn tại cơ chế override              |
|    - R4: Phê duyệt Dual-Factor bắt buộc (Private Secret Code + SMS OTP)           |
|    - R0-R2: Safe Sandbox (Đọc file <=100KB, ghi file mới không ghi đè)            |
|    - InertProcessBackend: Cấm tuyệt đối spawn tiến trình production               |
+-----------------------------------------+-----------------------------------------+
                                          |
                        Mạng Wi-Fi LAN / HTTP Polling 2.0s
                                          |
+-----------------------------------------v-----------------------------------------+
|             RASPBERRY PI 5 (4GB RAM) — EDGE PHYSICAL EMBODIMENT                   |
|                                                                                   |
|  [Cổng 8768]   Local Kiosk HTTP Server (Serving kiosk.html, kiosk.css, kiosk.js)  |
|  [Daemon Nền]  EdgeClientDaemon (client_daemon.py & main.py)                      |
|  [Bảo Mật]     EdgeHMACAuth (Ký số HMAC-SHA256, Nonce dùng 1 lần, Drift <= 10s)   |
|  [Ngoại Vi]    ActuatorController (8 Relay Channels GPIO BCM, 6-DOF Servos)       |
|  [Cài Đặt]     setup_pi5.py / setup_pi5.sh (Hỏi PIN 888666 một lần duy nhất)      |
+-----------------------------------------------------------------------------------+
```

---

## 2. SƠ ĐỒ ĐƯỜNG ĐI DỮ LIỆU ÂM THANH (AUDIO DATA PATH)

### 2.1. Hiện trạng (As-Is):
- **Phía PC:** Trình duyệt mở `executive.html` gọi Web Speech API cục bộ của Windows (`webkitSpeechRecognition` & `window.speechSynthesis`).
- **Phía Pi 5:** Trình duyệt Chromium mở `kiosk.html` cũng gọi Web Speech API cục bộ của Linux.
- **Kênh truyền giữa PC và Pi:** **CHƯA CÓ LUỒNG STREAM ÂM THANH NÀO**. Pi không truyền được âm thanh từ Mic vật lý về PC, và PC không stream được giọng nói tổng hợp sang Loa của Pi. Việc cử động miệng trên Pi hiện tại chỉ là giả lập nhịp hình sin (`Math.sin(time)`) khi cờ `avatar_state == "SPEAKING"`.

### 2.2. Kiến trúc chuẩn hóa mục tiêu (To-Be Target):
```
[Nguồn Micro 1: PC Mic]  ---> [PC Browser / PyAudio] ---+
                                                        |
[Nguồn Micro 2: Pi5 Mic] ---> [Pi VAD & Audio Chunk] ---+---> [PC CORE SPEECH INGESTION]
                                                                        |
                                                                        v
                                                               [Speech-to-Text / ASR]
                                                                        |
                                                                        v
                                                               [LLM qwen2.5:7b Suy Luận]
                                                                        |
                                                                        v
                                                          [Văn Bản Phản Hồi + Emotion Tag]
                                                                        |
                                                                        v
                                                          [Core TTS Engine + Waveform Gen]
                                                                        |
                                                                        +---> [Tạo Envelope / RMS Energy Timeline]
                                                                        |     (Mỗi frame 20ms: độ mở miệng 0.0 - 1.0)
                                                                        |
                                  +-------------------------------------+-------------------------------------+
                                  |                                                                           |
                                  v                                                                           v
                     [Phát Loa PC Core (Nội bộ)]                                            [Phát Loa Pi 5 Edge (Qua Wi-Fi)]
                                  |                                                                           |
                                  v                                                                           v
                   [Avatar PC Nhấp Nháy Khẩu Hình]                                           [Avatar Pi 5 Khẩu Hình Khớp Từng Frame]
```

---

## 3. SƠ ĐỒ ĐƯỜNG ĐI LỆNH ĐIỀU KHIỂN VÀ PHẢN HỒI KẾT QUẢ (COMMAND LIFECYCLE)

Vòng đời thực thi lệnh điều khiển từ xa tuân thủ nghiêm ngặt 10 bước:
```
[INPUT_RECEIVED]       : Nhận yêu cầu từ UI PC, Giọng nói hoặc Màn hình cảm ứng Pi 5
       |
       v
[AUTHENTICATED]        : Xác thực chữ ký số HMAC-SHA256, kiểm tra Nonce chống phát lại, độ trôi giờ <= 10s
       |
       v
[CORE_PROCESSED]       : Bộ não trung tâm PC lập kế hoạch DAG (TaskPlan), gán TaskID và IdempotencyKey duy nhất
       |
       v
[POLICY_CHECKED]       : Policy Engine kiểm định ranh giới (R0-R5)
       |                - R5: Chặn cứng tức thì (BLOCKED)
       |                - R4: Bắt buộc dừng chờ phê duyệt (APPROVAL_REQUIRED)
       |                - R0-R2: Cho phép chạy có kiểm soát trong Sandbox
       v
[APPROVAL_GATED]       : Nếu R4 -> Bắn vé tham vấn về Hộp thư PC Core, yêu cầu Anh Quanpt1 ký duyệt
       |
       v
[DISPATCHED]           : Gửi gói lệnh điều khiển kèm chữ ký xác thực từ PC Core tới Pi 5 Actuator
       |
       v
[ACKNOWLEDGED]         : Pi 5 xác nhận đã nhận lệnh thành công (ACK mạng)
       |
       v
[EXECUTION_VERIFIED]   : Pi 5 đọc lại cảm biến / trạng thái relay thực tế để xác minh hành động vật lý đã hoàn tất
       |
       v
[COMPLETED / FAILED]   : Gửi gói kết quả có chữ ký ngược về PC Core -> Ghi vào audit log & tasks.db
```

---

## 4. BẢNG TRẠNG THÁI TỪNG CHỨC NĂNG (STATUS MATRIX)

| STT | Chức năng | Trạng thái hiện tại | Bằng chứng kiểm tra thực tế |
| :---: | :--- | :---: | :--- |
| 1 | Xác thực HMAC-SHA256 & Anti-Replay | **`VERIFIED`** | Đạt 8/8 unit tests tại `tests/test_edge_client.py`. Chặn thành công nonce cũ và payload bị sửa đổi. |
| 2 | Kịch bản ghép cặp 1 lần (PIN 888666) | **`VERIFIED (Test)` / `IMPLEMENTED_NOT_VERIFIED (Real Pi)`** | Test endpoint `/api/edge/pair` pass; chưa chạy trực tiếp trên bo mạch Pi 5 phần cứng thật của anh. |
| 3 | Bộ điều khiển Rơ-le 8 kênh & 6-DOF Servos | **`VERIFIED (Emulation)` / `IMPLEMENTED_NOT_VERIFIED (Hardware)`** | `actuators.py` pass unit test chế độ mô phỏng an toàn; chưa cắm dây vật lý vào header GPIO Pi 5. |
| 4 | **PC Core Tự Phát Hiện Pi 5 Mất Kết Nối** | **`MISSING`** | **LỖ HỔNG LỚN:** PC chỉ có API thụ động. Nếu Pi 5 tắt nguồn/mất Wi-Fi, PC vẫn giữ trạng thái cũ, không có watchdog chủ động phát hiện timeout! |
| 5 | **6 Loại Cảnh Báo Mất Mạng (A, B, C, D, E, F)** | **`MISSING`** | Chưa có module `EdgeConnectionMonitor` trên PC; chưa có giao diện cảnh báo âm thanh và pop-up trên PC Desk. |
| 6 | **Màn hình Pi 5 CHỈ hiển thị khuôn mặt** | **`IMPLEMENTED_NOT_VERIFIED (Conflict)`** | `kiosk.html` hiện tại vẫn còn chứa khung xem transcript chữ và 2 nút bấm cảm ứng ở dưới, chưa tuân thủ quy chuẩn "Face-Only". |
| 7 | **Đồng bộ Khẩu hình theo Năng lượng/Viseme** | **`MOCKED`** | `kiosk.js` hiện chỉ làm phập phồng miệng bằng hàm toán học `Math.sin(time)` khi có cờ `SPEAKING`, chưa khớp với âm thanh thực. |
| 8 | **Truyền Stream Âm Thanh 2 Chiều (PC ↔ Pi)** | **`MISSING`** | Chưa có socket streaming PCM Audio; Pi mic chưa truyền tiếng về PC Core, Core TTS chưa phát trực tiếp sang Loa Pi. |
| 9 | **Chống Chạy Lặp Lệnh (Idempotency Key)** | **`VERIFIED (Core Tasks)` / `MISSING (Edge RPC)`** | `DurableTaskRegistry` có idempotency, nhưng các lệnh gửi giữa Pi 5 và Core chưa gắn `command_id` có ACK 2 bước. |
| 10 | **Phân biệt 5 loại phiên bản & Gói phát hành ký số** | **`MISSING`** | Chưa có manifest kiểm tra hash SHA-256 gói phát hành; chưa có cơ chế staging và rollback tự động trên Pi 5. |

---

## 5. NHỮNG MÂU THUẪN VÀ NGUY CƠ BẢO MẬT PHÁT HIỆN TRONG AUDIT

1. **Nguy cơ mạng (Host Binding `0.0.0.0`):**
   - Hiện tại hàm `run_executive_server` đang bind cổng 8766 vào `0.0.0.0`. Điều này mở cổng ra toàn bộ các giao diện mạng (kể cả card mạng công cộng nếu có).
   - **Khắc phục:** Cần ràng buộc nghiêm ngặt chỉ lắng nghe trên IP Wi-Fi nội bộ (`192.168.1.17`) và `127.0.0.1`, cấm tuyệt đối mở ra WAN.
2. **Nguy cơ báo cáo sai sự thật khi Pi mất nguồn (False Positive Online):**
   - Biến `_GLOBAL_PAIRED_EDGE_DEVICES` trong `server.py` lưu trạng thái thiết bị trong bộ nhớ. Nếu Pi 5 bị rút nguồn, PC Core gọi `/api/executive/supervisor` vẫn trả về `"status": "ONLINE_PAIRED"`.
   - **Khắc phục:** Xây dựng `EdgeConnectionMonitor` chạy nền với chu kỳ kiểm tra 1.0s. Nếu quá 4.0s không nhận được heartbeat hợp lệ, PC lập tức chuyển trạng thái sang `DISCONNECTED` và kích hoạt **Cảnh Báo B**.
3. **Mâu thuẫn giao diện Kiosk Pi 5:**
   - Yêu cầu kiến trúc tại Mục VII quy định: *"Trên màn hình Pi 5, hiện tại CHỈ hiển thị khuôn mặt số có biểu cảm và hoạt ảnh miệng. Không hiển thị văn bản hội thoại, phụ đề, bảng điều khiển, nhật ký, nút chức năng hay đoạn trả lời chữ"*.
   - Hiện tại `kiosk.html` vẫn có header, transcript glance, consultation alert banner và touch buttons.
   - **Khắc phục:** Bổ sung cờ cấu hình `face_only_mode: true` (mặc định bật) trong `config.json` để ẩn toàn bộ thành phần chữ và nút bấm, tối ưu 100% diện tích màn hình cảm ứng hiển thị gương mặt Cybernetic TONY.
4. **Độ trễ truyền thông qua HTTP Polling:**
   - Polling 2.0s gây độ trễ từ 0 đến 2 giây cho việc đồng bộ trạng thái biểu cảm. Để đồng bộ giọng nói và khẩu hình thời gian thực (mouth sync), cần kênh truyền socket nhị phân hoặc HTTP SSE / WebSocket với độ trễ < 50ms.

---

## 6. NHỮNG MODULE CÓ THỂ TÁI SỬ DỤNG TỐI ĐA

1. **`edge_client/auth.py` (`EdgeHMACAuth`):** Rất chuẩn, thực hiện xác thực HMAC-SHA256 đối xứng, tự sinh nonce ngẫu nhiên 32 hex, kiểm tra thời gian UTC chống phát lại.
2. **`edge_client/actuators.py` (`ActuatorController`):** Đã phân bổ sẵn 8 kênh rơ-le và 6 khớp servo, có cơ chế ngắt an toàn phần cứng `emergency_all_stop()` và chế độ safe emulation.
3. **`src/quan_ai_brain/voice/state_machine.py` (`VoiceStateMachine`):** Máy trạng thái 9 nấc (`STANDBY`, `WAKE_DETECTED`, `LISTENING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, v.v.) tuân thủ chuẩn chuyển đổi trạng thái hợp lệ.
4. **SVG Digital Avatar TONY (`tony_avatar.svg` & `kiosk.html`):** Thiết kế SVG Cybernetic chuẩn mực, có mí mắt cử động tự nhiên và khẩu hình morphing, rất dễ tích hợp bộ nội suy năng lượng âm thanh.
5. **`src/quan_ai_brain/governance/state_store.py`:** Lưu trữ trạng thái STOP/FREEZE bền vững xuyên suốt các lần khởi động.

---

## 7. DANH SÁCH FILE DỰ KIẾN THAY ĐỔI & TẠO MỚI (PHASE A ĐỀ XUẤT)

### Các file tạo mới:
1. `src/quan_ai_brain/web/edge_monitor.py`:
   - Lớp `EdgeConnectionMonitor` chạy nền trên PC Core.
   - Quản lý 9 trạng thái kết nối (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `DEGRADED`, `SYNCING`, `READY`, `RECOVERING`, `AUTH_FAILED`, `STOPPED`).
   - Tự động phát hiện Pi mất kết nối và kích hoạt 6 loại cảnh báo (A, B, C, D, E, F) trên PC.
2. `src/quan_ai_brain/voice/mouth_sync.py`:
   - Phân tích biên độ âm thanh (RMS Energy Envelope) theo từng frame 20ms.
   - Ánh xạ mức năng lượng `[0.0 - 1.0]` thành độ mở/khép miệng của SVG Avatar.
   - Quản lý `utterance_id` và token hủy (`cancel_utterance`) để ngắt khẩu hình ngay lập tức khi người dùng ngắt lời.
3. `tests/test_edge_monitor.py`:
   - Kiểm thử độc lập toàn diện 6 kịch bản cảnh báo A-F và 9 trạng thái kết nối của `EdgeConnectionMonitor`.
4. `tests/test_mouth_sync.py`:
   - Kiểm thử thuật toán phân tích năng lượng âm thanh, đồng bộ timeline và ngắt lời.

### Các file hiện có cần cập nhật:
1. `src/quan_ai_brain/web/server.py`:
   - Tích hợp `EdgeConnectionMonitor` vào tiến trình Executive Server.
   - Thêm API `GET /api/executive/edge-alerts` và websocket/SSE endpoint cho cảnh báo tức thì.
   - Ràng buộc an toàn IP lắng nghe (chỉ bind LAN IP nội bộ và Loopback).
2. `src/quan_ai_brain/web/static/executive.html` & `executive.js`:
   - Thêm Widget Cảnh báo mất kết nối Pi 5 chuyên biệt trên Hero Visual Cockpit:
     - Đèn cảnh báo nhấp nháy đỏ khi mất Pi 5.
     - Phát âm báo cảnh báo trên loa PC khi mất kết nối đột ngột (Alert B).
     - Ghi nhận lịch sử sự cố kết nối không bị xóa khi phục hồi.
3. `edge_client/config.py` & `edge_client/config.json`:
   - Thêm các trường theo dõi phiên bản: `core_version`, `edge_client_version`, `protocol_version`, `avatar_version`, `config_schema_version`.
   - Thêm cờ `face_only_mode: true` (chỉ hiển thị khuôn mặt).
   - Thêm `update_policy: "notify_only"`.
4. `edge_client/kiosk.html`, `kiosk.css`, `kiosk.js`:
   - Tối ưu chế độ **Face-Only**: Ẩn thanh header và khung chữ khi `face_only_mode == true`.
   - Tích hợp bộ điều khiển khẩu hình theo timeline năng lượng âm thanh (Mouth Synced to Speech Energy).
5. `edge_client/client_daemon.py`:
   - Nâng cấp tần suất gửi heartbeat (1.0s), gửi kèm chỉ số chất lượng mạng (RTT ms, packet loss).
   - Tiếp nhận gói `utterance_envelope` từ PC Core để điều khiển khẩu hình Avatar.
6. `docs/PROJECT_STATUS.md` & `edge_client/README.md`: Cập nhật tài liệu kỹ thuật đồng bộ.

---

## 8. DIFF DỰ KIẾN MINH HỌA (PREVIEW DIFF)

### Minh họa 1: `EdgeConnectionMonitor` trên PC Core (`src/quan_ai_brain/web/edge_monitor.py`)
```python
class EdgeAlertCode(str, Enum):
    ALERT_A_UNPAIRED = "ALERT_A_PI5_NOT_CONNECTED"
    ALERT_B_SUDDEN_DISCONNECT = "ALERT_B_PI5_SUDDEN_DISCONNECT"
    ALERT_C_CHANNEL_DEGRADED = "ALERT_C_CHANNEL_DEGRADED"
    ALERT_D_SYNC_FAILED = "ALERT_D_SYNC_FAILED"
    ALERT_E_RECOVERED = "ALERT_E_PI5_RECOVERED"
    ALERT_F_SECURITY_FAULT = "ALERT_F_SECURITY_OR_AUTH_FAULT"

class EdgeConnectionMonitor:
    def __init__(self, timeout_sec: float = 4.0):
        self.state = EdgeConnectionState.DISCONNECTED
        self.timeout_sec = timeout_sec
        self.last_heartbeat_utc: datetime | None = None
        self.active_alerts: list[dict[str, Any]] = []

    def poll_check(self) -> None:
        """Called every second by PC watchdog thread."""
        now = datetime.now(timezone.utc)
        if self.last_heartbeat_utc is None:
            self._set_alert(EdgeAlertCode.ALERT_A_UNPAIRED, "RASPBERRY PI 5 — CHƯA KẾT NỐI")
            return
        elapsed = (now - self.last_heartbeat_utc).total_seconds()
        if elapsed > self.timeout_sec and self.state == EdgeConnectionState.CONNECTED:
            self.state = EdgeConnectionState.DISCONNECTED
            self._set_alert(EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT, "CẢNH BÁO: MẤT KẾT NỐI RASPBERRY PI 5")
```

### Minh họa 2: Khẩu hình Face-Only trên Pi 5 (`edge_client/kiosk.js`)
```javascript
function applyFaceOnlyMode(enabled) {
  const header = document.querySelector(".kiosk-header");
  const transcript = document.querySelector(".micro-transcript");
  const actionWrap = document.querySelector(".kiosk-action-wrap");
  if (enabled) {
    if (header) header.style.display = "none";
    if (transcript) transcript.style.display = "none";
    if (actionWrap) actionWrap.style.display = "none";
    document.querySelector(".avatar-card").classList.add("pure-face-mode");
  }
}
```

---

## 9. KẾ HOẠCH KIỂM THỬ VÀ TIÊU CHÍ NGHIỆM THU (TEST PLAN)

### Giai đoạn B: Kiểm thử Core cục bộ (Không cần Pi thật)
1. **Test Parser & Schema:** Kiểm tra cấu trúc thông điệp, timestamp UTC, và token định danh.
2. **Test 6 Kịch Bản Cảnh Báo:**
   - [x] Pi chưa từng kết nối -> Kích hoạt Cảnh báo A.
   - [x] Pi đang gửi heartbeat thì đột ngột ngừng quá 4s -> Kích hoạt Cảnh báo B (`CẢNH BÁO: MẤT KẾT NỐI RASPBERRY PI 5`).
   - [x] Gián đoạn kênh hoặc mất gói tin vượt ngưỡng -> Kích hoạt Cảnh báo C.
   - [x] Quá thời gian đồng bộ phiên -> Kích hoạt Cảnh báo D.
   - [x] Khôi phục thành công -> Kích hoạt Cảnh báo E (`RASPBERRY PI 5 ĐÃ KHÔI PHỤC KẾT NỐI`).
   - [x] Sai chữ ký HMAC / sai PIN -> Kích hoạt Cảnh báo F (`LỖI BẢO MẬT`).
3. **Test Khẩu hình Speech Envelope:** Kiểm tra thuật toán bóc tách năng lượng âm thanh tạo ra độ mở miệng tỷ lệ thuận với âm lượng và về `0.0` ngay khi hết âm hoặc bị ngắt lời.

### Giai đoạn C: Tích hợp qua Wi-Fi riêng
- Kiểm tra kết nối từ Pi 5 tới PC IP `192.168.1.17:8766`.
- Xác nhận PC lập tức phát cảnh báo trên màn hình và loa khi rút cáp mạng Pi hoặc ngắt nguồn Pi.

---

## 10. TUYÊN BỐ DỪNG SAU GIAI ĐOẠN 0 (AUDIT ONLY)

Theo đúng điều khoản chỉ đạo của Anh tại **Mục II (Yêu cầu bắt buộc)**:
- Em **chưa chỉnh sửa bất kỳ dòng mã nguồn nào** trong `src/` hoặc `edge_client/`.
- Em **chưa thay đổi cấu hình đang chạy** và **chưa bật cơ chế tự động cập nhật**.
- Trạng thái git được giữ nguyên vẹn 100%, không mất dữ liệu.
- Em trân trọng kính trình bản Báo cáo Audit Hiện Trạng & Phương Án Kiến Trúc trên đây để Anh Quanpt1 xem xét và phê duyệt trước khi chuyển sang bước triển khai mã nguồn!
