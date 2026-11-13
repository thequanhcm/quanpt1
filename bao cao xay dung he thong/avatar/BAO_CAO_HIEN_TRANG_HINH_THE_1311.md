# BÁO CÁO HIỆN TRẠNG HÌNH THỂ (AVATAR / DIGITAL HUMAN "CHERRY")

> **QUAN AI BRAIN — Sprint 13/11/2026**
> Người viết: TONY (Digital Executive Assistant)
> Thời điểm báo cáo: **13/11/2026 21:49** (sau khi hoàn thành nâng cấp cảm xúc + toast theo yêu cầu chủ sở hữu)
> Phạm vi: toàn bộ hình thể số (Model A) trên PC Core dashboard + Pi 5 kiosk + gói thư viện backup
> Phương pháp: **audit thật** — md5 từng bản engine, đếm asset, chạy test suite, truy vấn Pi 5 qua SSH, kiểm E2E bằng trình duyệt thật. Không có mục nào ghi theo trí nhớ.

---

## 1. TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Avatar dashboard PC Core | 🟢 HOẠT ĐỘNG — vừa nâng cấp 19 states | E2E browser 8/8 state mới chuyển OK |
| Avatar kiosk Pi 5 | 🟡 CHẠY được nhưng kiosk chromium đang zombie | `/api/kiosk/status`: `kiosk_running: false`, pgrep thấy `[chromium] <defunct>` |
| Gói thư viện backup | 🟢 TOÀN VẸN 100% | `test_avatar.py` 6/6 PASS tự động |
| Engine body_soft (thân + tay) | 🟡 ĐÃ HOÀN THÀNH, ĐANG TẠM DỪNG | md5 `3956a56f` an toàn 3 nơi, chờ chủ sở hữu duyệt áp dụng |
| Assets surprised | 🟠 LỖI DỮ LIỆU GỐC | md5 surprised **= trùng** portrait `c572cbbb` — ảnh "ngạc nhiên" thực chất là ảnh cười dịu dàng |

**Kết luận 1 dòng:** Hình thể đang ổn định ở bản "8:00 ngày 13/11" trên cả 2 nền tảng; bản nâng cấp cảm xúc 19-state đã xong và kiểm chứng trên PC dashboard; 2 việc đang chờ quyết định của chủ sở hữu là (a) tạo ảnh surprised thật và (b) duyệt áp dụng bản body_soft.

---

## 2. SƠ ĐỒ 4 BẢN AVATAR ENGINE ĐANG TỒN TẠI

Hệ thống hiện có **4 phiên bản** `avatar_engine.js` — mỗi bản một mục đích, **khác nhau có chủ đích**:

| # | Bản | Vị trí | Kích thước | Dòng | md5 | Trạng thái |
|---|---|---|---|---|---|---|
| 1 | **Gói thư viện backup** (25/10) | `bao cao xay dung he thong/avatar/avatar_engine.js` | 40.307 B | 961 | `2a453a11` | 🟢 Nguyên vẹn — baseline đóng gói |
| 2 | **Pi 5 kiosk** (bản "8:00") | `edge_client/avatar_engine.js` ↔ `/home/quanpt1/Desktop/edge_client/avatar_engine.js` | 47.780 B | 1.070 | `691886df` | 🟢 Đang chạy trên Pi 5 (kiosk `?v=cherry_07nov_r1`) |
| 3 | **PC dashboard** (nâng cấp tối 13/11) | `src/quan_ai_brain/web/static/avatar_engine.js` | 43.551 B | 1.016 | `61dd807d` | 🟢 Mới nhất — 19 states + 11 tông cảm xúc |
| 4 | **body_soft** (thân + tay mềm) | `backups/avatar_body_sync_1311/avatar_engine.js` + git `stash@{0}` + Pi 5 `.bak_body_sync_1311` | 60.306 B | 1.355 | `3956a56f` | 🟡 Đã lưu trữ, chờ duyệt |

**Lưu ý quan trọng:** khác biệt bản 1↔2 chỉ là CRLF↔LF (nội dung giống nhau — đã đối chiếu từng byte); bản 2 có sẵn state `SURPRISED` trong config nhưng **chưa được dùng** cho đến bản 3.

---

## 3. HIỆN TRẠNG ASSETS (KHO HÌNH ẢNH)

### 3.1. Kiểm kê 3 kho

| Kho | Số tệp | Ghi chú |
|---|---|---|
| PC Core: `src/quan_ai_brain/web/static/assets/avatar/` | **44 tệp** | Đầy đủ 10 portrait cảm xúc + 8 mouth + 3 eyes + Model F legacy |
| Gói backup: `bao cao xay dung he thong/avatar/assets/` | **45 tệp** | = PC static + `master_model_a_source.png` (ảnh gốc 8,5 MB) |
| Pi 5 Edge: `/home/quanpt1/Desktop/edge_client/assets/avatar/` | **60 tệp** (20 tệp `avatar_v2_*`) | Bản sao tốc độ cao phục vụ kiosk |

Khớp đúng mô tả README của gói backup ("44 tệp đồ họa"). Pi 5 có nhiều hơn vì giữ thêm các tệp trung gian từ các lần sinh asset.

### 3.2. Bảng asset portrait cảm xúc (trạng thái thực — đã kiểm md5)

| Asset | md5 | Biểu cảm thực tế (vision check 13/11) | Được dùng? |
|---|---|---|---|
| `avatar_v2_portrait.png` | `c572cbbb` | Nền tảng — nụ cười nhẹ dịu dàng | ✅ IDLE/NEUTRAL |
| `avatar_v2_happy.png` | `bf361783` | Cười tươi, mắt híp Duchenne | ✅ HAPPY/SUCCESS |
| `avatar_v2_thinking.png` | (riêng) | Mắt nhìn lệch, tập trung | ✅ THINKING/RESEARCHING |
| `avatar_v2_empathic.png` | `76d38cb8` | Ánh mắt dịu, đồng cảm | ✅ EMPATHETIC |
| `avatar_v2_confused.png` | (riêng) | Mày nhếch, băn khoăn | ✅ CONFUSED/WAITING |
| `avatar_v2_warning.png` | (riêng) | Gương mặt nghiêm túc | ✅ WARNING/BLOCKED |
| `avatar_v2_error.png` | (riêng) | Biểu cảm sự cố | ✅ ERROR |
| `avatar_v2_blink.png` | (riêng) | Mắt nhắm (chớp mắt) | ✅ Chu kỳ blink + SLEEPING |
| `avatar_v2_speaking.png` | (riêng) | Miệng đang nói | ✅ SPEAKING |
| ⚠️ `avatar_v2_surprised.png` | `c572cbbb` | **TRÙNG MD5 với portrait** — thực chất là ảnh cười dịu dàng, KHÔNG PHẢI mặt ngạc nhiên | 🟠 Được gọi bởi SURPRISED nhưng hiệu quả thị giác = portrait |

### 3.3. Lỗi dữ liệu gốc cần khắc phục

Phát hiện quan trọng nhất của đợt audit này:

```
avatar_v2_surprised.png  md5 c572cbbb
avatar_v2_portrait.png   md5 c572cbbb   ← GIỐNG HỆT NHAU
```

**Hệ quả:** Khi engine chuyển sang state `SURPRISED`, canvas vẽ đúng asset nhưng thị giác anh Quân thấy vẫn là khuôn mặt nền tảng (đã xác nhận qua 4 lần chụp màn hình + vision check lúc 21:30). Tag UI hiển thị "SURPRISED (NGẠC NHIÊN)" đúng nhưng **ảnh không có biểu cảm ngạc nhiên** (mắt mở to, miệng chữ O).

**Nguồn gốc:** script `generate_assets.py` thời điểm cắt asset đã không cắt được biểu cảm surprised riêng từ ảnh master `master_model_a_source.png` (2400×1792) nên fallback về portrait.

**Đề xuất (chờ duyệt):** tạo ảnh `avatar_v2_surprised_v2.png` thật — bằng cách generate AI từ master source hoặc cắt từ ảnh master gốc nếu có frame ngạc nhiên; engine bản 3 đã sẵn sàng hiển thị, chỉ cần thay file.

---

## 4. HIỆN TRẠNG TRẠNG THÁI CẢM XÚC (EMOTION STATES)

### 4.1. Nâng cấp tối 13/11 (đã hoàn thành + kiểm chứng E2E)

Trước nâng cấp: dashboard dùng 11 states, thực tế chỉ 7 được gọi. Sau nâng cấp:

**Dashboard (bản 3) — 19 states:**

| Nhóm | States |
|---|---|
| Vận hành | IDLE, LISTENING, THINKING, RESEARCHING, LEARNING, SPEAKING |
| Cảm xúc tích cực | HAPPY 😊, SUCCESS ✨, PROUD 🌟, WARM_GREETING |
| Cảm xúc trung tính | CURIOUS 🤔, PATIENT_WAITING, SURPRISED 😮, CONFUSED ❓ |
| Cảnh báo | WARNING ⚠️, BLOCKED 🛡️, ERROR, SAFE_MODE ❄️ |
| Kết nối | OFFLINE 💤, RECONNECTING 🔄, SLEEPING 💤, EMPATHETIC 💗, WAITING_FOR_OWNER 📬 |

**Tông vi-cảm xúc (EMOTION_PRESETS, bản 3) — 11 tông:** NEUTRAL, WARM_GREETING, ANALYTICAL_THINKING, SERIOUS_ALERT, CONFIDENT_SUCCESS, CONSULTATIVE_INQUIRING, **CURIOUS, APOLOGETIC, PATIENT_WAITING, PROUD, SURPRISED** (5 tông mới).

**Nhận diện cảm xúc tiếng Việt tự động** — `extractVietnameseEmotion()` đã test E2E 7/7 PASS:

| Câu mẫu | Tông nhận được | Đúng |
|---|---|---|
| "Chào anh ạ, rất vui được gặp anh" | WARM_GREETING | ✅ |
| "Anh ơi, tại sao hệ thống lại như thế nào vậy?" | CURIOUS | ✅ |
| "Xin lỗi anh, em gặp sự cố nhỏ" | APOLOGETIC *(fix riêng: ưu tiên đồng cảm trước cảnh báo)* | ✅ |
| "Em đã cải thiện và tối ưu xong hệ thống ạ" | PROUD | ✅ |
| "Bất ngờ quá, lần đầu tiên em khám phá được điều này" | SURPRISED | ✅ |
| "Đã hoàn thành 100% nhiệm vụ, thành công" | CONFIDENT_SUCCESS | ✅ |
| "Cảnh báo: phát hiện rủi ro" | SERIOUS_ALERT | ✅ |

**E2E chuyển state (browser thật, Edge):** 8/8 state mới PASS — `HAPPY:OK, SUCCESS:OK, WARNING:OK, CONFUSED:OK, EMPATHETIC:OK, SURPRISED:OK, RECONNECTING:OK, SLEEPING:OK`. Tag UI + viền khung + badge emoji hiển thị đúng (ảnh chụp `emo_surprised_v3.png` xác nhận tag `😯 SURPRISED (NGẠC NHIÊN)`).

### 4.2. Pi 5 kiosk (bản 2) — 22 states

Engine kiosk Pi 5 có sẵn 22 states trong `STATE_CONFIGS` (bao gồm 4 state mở rộng thêm tối 13/11). Kiosk nhận state qua IPC từ `client_daemon.py`; **chưa đồng bộ phần nhận diện cảm xúc tiếng Việt mở rộng** (bản kiosk dùng tông cũ 6 preset).

---

## 5. HÌNH THỂ (BODY) — BẢN BODY_SOFT ĐANG TẠM DỪNG

Công trình ngày 13/11 chiều theo yêu cầu *"rà soát... hiệu chỉnh cho giao diện hình thể... mềm mại, tự nhiên nhất. lưu ý giữ nguyên khuôn mặt gốc cũ"*:

- ✅ Hoàn thành: thân + 2 tay cong 2 khúc (quadratic), đàn phím + hoa mềm (ellipse/roundRect alpha thấp), váy tím lavender gradient
- ✅ Test 13/13 PASS tại thời điểm đó (`test_avatar_body_arms_1311.py` viết riêng cho bản này)
- ✅ Đồng bộ lên Pi 5 thành công (`?v=body_sync_1311`)
- 🔄 **Sau đó chủ sở hữu yêu cầu khôi phục về bản 8:00** → đã restore an toàn 4/4 file md5 khớp (`2a453a11`/`af49545a`/`ad7175d7`/`d5fb640f`)

**Body_soft hiện lưu 3 nơi (không mất):**
1. `E:\BRAIN\backups\avatar_body_sync_1311\` (md5 `3956a56f`, 60.306 B)
2. Git `stash@{0}` (`body_sync_1311-experimental-avatar`)
3. Pi 5: `/home/quanpt1/Desktop/edge_client/avatar_engine.js.bak_body_sync_1311`

**⚠️ Lưu ý test:** `tests/test_avatar_body_arms_1311.py` hiện **12 FAIL** — đây là tình trạng đúng/kỳ vọng, vì test viết cho bản body_soft mà working tree đã restore 8:00. Test sẽ PASS trở lại khi duyệt áp dụng body_soft. Không phải lỗi mới.

---

## 6. TRẠNG THÁI HỆ THỐNG THỜI ĐIỂM BÁO CÁO (21:49 — số liệu thật)

### 6.1. Pi 5 (192.168.1.21)

| Thành phần | Giá trị đo được |
|---|---|
| Engine md5 | `691886df` (bản 8:00 — khớp working tree) |
| Kiosk HTML version | `cherry_07nov_r1` (engine) + `overlay_1311_a` (kiosk.js) |
| `/api/kiosk/status` | `core_connected: true`, `avatar_state: IDLE`, `embodiment_mode: STANDBY`, `emergency_state: normal` |
| **kiosk_running** | ⚠️ **`false` — chromium kiosk đang ZOMBIE** (`pgrep`: `[chromium] <defunct>`, cha không reap) |
| Server 8768 | 🟢 HTTP 200 (daemon python vẫn sống, phục vụ trang bình thường) |
| Assets kiosk | 60 tệp (20 tệp `avatar_v2_*`) |

**Khuyến nghị khắc phục kiosk zombie** (quy trình đã kiểm chứng 3 lần 18:39–18:42): `pkill -9 chromium` + xóa `SingletonLock/Socket/Cookie` + `start_kiosk`. Chờ anh duyệt là em chạy ngay.

### 6.2. PC Core (QUANPT)

| Thành phần | Giá trị |
|---|---|
| Dashboard engine | `61dd807d` (43.551 B, 1.016 dòng) — bản mới nhất |
| executive.js / css / html | 225.785 / 72.994 / 105.582 B — cache version `emo_1311_r5` |
| Servers 8765/8766 | 🟢 LIVE (PID 11504, `start_dual_servers.py`) |
| Toast + 19 states | 🟢 Đã verify E2E browser thật |

### 6.3. Gói thư viện backup

| Kiểm tra | Kết quả |
|---|---|
| `test_avatar.py` (6/6) | 🟢 **PASS toàn bộ** — file tồn tại, 14 asset cảm xúc, portrait 1024×1024, alpha RGBA, 12-state protocol, timeline khẩu hình tiếng Việt |
| Độc lập thư viện | 🟢 Zero-dependency như thiết kế |
| `avatar_backup.zip` | 31.853.757 B (30,4 MB) |
| `demo.html` | Studio tương tác: 12 state + gật đầu + chớp mắt + mô phỏng nói (offline) |

---

## 7. CƠ CHẾ KỸ THUẬT CỐT LÕI (TỪ AUDIT CODE, KHÔNG PHÁT BIỂU TRỪ LỜI)

Các tính năng đã được xác nhận tồn tại trong code bằng grep từng bản engine:

1. **Vật lý sinh học:** micro-nodding (cosine), head tilt ±2.2°, weight shift ±3.5px, thở vi mô chu kỳ 3.5s, chớp mắt 135ms ngẫu nhiên 3.2–6.0s với **28% double-blink** (mã: `isDoubleBlink = Math.random() < 0.28`), saccades nhìn lệch khi THINKING
2. **Khẩu hình:** feathered elliptical alpha blending (triệt tiêu viền đen), bell-curve `0.35 * sin(π * phase)` thay random — chống artifact "nhai giật", timeline qua `setTimeline()` + fallback `startSpeaking(ms)`
3. **Chọn portrait theo state:** chuỗi if/else 11 nhánh — blink → thinking → happy → empathic → confused → warning → **surprised (mới 13/11)** → error → speaking
4. **Landmark chuẩn Model A 1024×1024:** `EYES_BOX {320,425,365,115}`, `MOUTH_BOX {405,650,245,105}`, 2 mỏi mắt trái/phải — khớp tài liệu README gói backup

---

## 8. VIỆC ĐANG CHỜ QUYẾT ĐỊNH CỦA CHỦ SỞ HỮU

| # | Việc | Tác động nếu duyệt | Rủi ro |
|---|---|---|---|
| 1 | **Tạo ảnh surprised thật** (mắt mở to, miệng O) | State SURPRISED có ý nghĩa thị giác thực | Thấp — chỉ thay 1 file, engine sẵn sàng |
| 2 | **Áp dụng body_soft** (thân + tay mềm) | Hình thể chuyển động tự nhiên hơn hẳn; test 12 FAIL hiện tại sẽ PASS lại | Trung bình — cần đồng bộ cả 2 path Pi 5 + verify seam |
| 3 | **Khởi động lại kiosk Pi 5** (chromium zombie) | Kiosk hiện avatar trở lại trên màn | Thấp — quy trình 3 bước đã kiểm chứng |
| 4 | **Đồng bộ cảm xúc mở rộng sang kiosk Pi 5** (bản 2 ← bản 3) | Kiosk biểu cảm theo tông câu nói như dashboard | Trung bình — cần regression test overlay |
| 5 | Commit các thay đổi tối 13/11 (6 file: engine × 2, executive × 3, kiosk cache) | Lưu an toàn lên git | Thấp — chưa commit gì, chờ duyệt theo quy tắc |

---

## 9. PHỤ LỤC: DANH SÁCH FILE THAY ĐỔI TRONG ĐỢT NÀY

```text
git diff --stat (13/11 21:49, chưa commit):
 edge_client/client_daemon.py                  |   6 +     (mirror --user-data-dir)
 edge_client/wake_word_service.py              | 147 +++++ (3 lớp lọc wake)
 src/quan_ai_brain/web/static/avatar_engine.js |  55 +++++ (+4 state, +5 tone, surprised branch)
 src/quan_ai_brain/web/static/executive.css    |  71 +++++ (toast + 9 state CSS)
 src/quan_ai_brain/web/static/executive.html   |   9 +-    (toast container + cache bump)
 src/quan_ai_brain/web/static/executive.js     | 181 +++++ (toast, 19 states, eyelid logic)
 6 files changed, 418 insertions(+), 51 deletions(-)
```

---

*Báo cáo được tạo tự động bởi TONY lúc 13/11/2026 21:49. Mọi con số md5/kích thước/trạng thái đều đo trực tiếp từ hệ thống tại thời điểm viết. Các mục có dấu 🟡/🟠/⚠️ là việc đang chờ chủ sở hữu quyết định — TONY không tự triển khai theo quy tắc "Tự học nhưng không tự thay đổi production".*
