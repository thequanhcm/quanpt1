# CHERRY — HƯỚNG DẪN SỬ DỤNG
**Phiên bản:** 18/11/2026 · **Soạn bởi:** TONY
**Dành cho:** Owner Phạm Thế Quân (quanpt1@viettel.com.vn)
**Áp dụng cho:** bản master `304d6eb` (PR #36 đã merge 18/11)

---

## MỤC LỤC

1. [Khởi động / Tắt hệ thống](#1-khởi-động--tắt-hệ-thống)
2. [Truy cập giao diện](#2-truy-cập-giao-diện)
3. [Hội thoại với Cherry](#3-hội-thoại-với-cherry)
4. [Hội thoại giọng nói trên Pi5](#4-hội-thoại-giọng-nói-trên-pi5)
5. [Dashboard Điều Hành (8766)](#5-dashboard-điều-hành-8766)
6. [Chạy V7 Skills](#6-chạy-v7-skills)
7. [Quản lý trí nhớ](#7-quản-lý-trí-nhớ)
8. [Quản lý tác vụ + tham vấn](#8-quản-lý-tác-vụ--tham-vấn)
9. [NetChat](#9-netchat)
10. [Camera + file trên Pi5](#10-camera--file-trên-pi5)
11. [Giám sát sức khỏe hệ thống](#11-giám-sát-sức-khỏe-hệ-thống)
12. [Tự học + tự chuẩn đoán](#12-tự-học--tự-chuẩn-đoán)
13. [Backup + báo cáo tự động](#13-backup--báo-cáo-tự-động)
14. [Xử lý sự cố thường gặp](#14-xử-lý-sự-cố-thường-gặp)
15. [Bảo mật — Owner cần biết](#15-bảo-mật--owner-cần-biết)

---

## 1. KHỞI ĐỘNG / TẮT HỆ THỐNG

### Khởi động đầy đủ 24/7

Chạy file (double-click hoặc Task Scheduler đã đặt):

```
E:\BRAIN\KHOI_DONG_24_7.bat
```

Launcher sẽ lần lượt:
| Bước | Thành phần | Ghi chú |
|---|---|---|
| 0/5 | Ollama (BGE-M3 embedding) | Chỉ dùng embedding, LLM không dùng |
| 1/5 | Dual Servers 8765 + 8766 | Server chính + executive |
| 2/5 | NetChat Auto-Responder | Bot "Trợ lý Tony Pham" |
| 3/5 | Learning Daemon | Tự học 5 phút/lần |
| 4/6 | Watchdog | Tự restart, cap 5/giờ |
| 5/6 | **Cherry Autonomous Mode** | Tự vận hành chủ động (mới 18/11) |
| 6/6 | Task Scheduler | Backup 2AM + report 8AM |

**Khởi động ẩn (không hiện cửa sổ):** `tools\khoi_dong_24_7_hidden.vbs` — đã fix CurrentDirectory=E:\BRAIN (18/11), chạy được từ Task Scheduler.

### Tắt toàn bộ

```
powershell -NoProfile -ExecutionPolicy Bypass -File E:\BRAIN\tools\stop_tony_services.ps1
```

Script dừng: dual servers, netchat, learning, watchdog, **cherry_autonomous** (đã thêm 18/11), ollama.

### Kiểm tra đang chạy

```
curl http://127.0.0.1:8765/api/health
```
→ `"success": true` + components với `verification_status: VERIFIED_LIVE`.

---

## 2. TRUY CẬP GIAO DIỆN

| Giao diện | URL | Dùng làm gì |
|---|---|---|
| **Chat Web** | http://127.0.0.1:8765/ | Hội thoại text với Cherry |
| **Dashboard Điều Hành** | http://127.0.0.1:8766/ | Quản trị toàn diện (11 tab) |
| **Health Dashboard** | http://127.0.0.1:8765/static/health_dashboard.html | Sức khỏe hệ thống |
| **Kiosk Pi5** | http://192.168.1.21:8768/ (máy trong LAN) | Màn hình avatar trên Pi5 |

**Lưu ý:** Dashboard Điều Hành là trang chính cho owner — mọi tab quản trị nằm ở đây.

---

## 3. HỘI THOẠI VỚI CHERRY

### 3.1. Qua Web Chat (8765)

Mở http://127.0.0.1:8765/ → gõ câu hỏi → Enter.

- Cherry trả lời bằng LLM GLM-5.3-Flash (~1,2s), tự ghi EPISODIC memory
- Cuối reply có thể thấy marker: 🧠 (skill memory) · 🔊 (voice) · 📜 (audit) — tức skill V7 đã tự chạy

### 3.2. Qua API (curl / script)

```
curl -X POST http://127.0.0.1:8765/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"Lịch hôm nay thế nào?\"}"
```

Các endpoint hội thoại:
- `POST /api/chat` — chat chính
- `GET /api/chat/history` — lịch sử
- `GET /api/chat/stream` — streaming

### 3.3. Qua NetChat (khi vắng máy)

Nhắn tin cho bot "Trợ lý Tony Pham" — xem §9.

---

## 4. HỘI THOẠI GIỌNG NÓI TRÊN PI5

### 4.1. Bật wake word

Pi5 chạy wake service tự động (qua `client_daemon.py`). Bộ từ đánh thức (owner chốt 11/11):

> **"Cherry ơi" · "Cherry" · "Cherry à"** (+ biến thể Vosk: cheri/ché ri/che ri/chè ri × ơi/oi/à/a)

Nói to, rõ, cách mic ~1m. Fuzzy match siết ≤2 lỗi → TV không kích hoạt được.

### 4.2. Quy trình nói chuyện

1. Nói "Cherry ơi" → đợi avatar chuyển LISTENING
2. Nói câu hỏi/câu lệnh
3. Cherry: STT → LLM → TTS giọng **Hoài My** → loa SRS-XB33 phát → avatar miệng nhấp nháy (SPEAKING)
4. Có thể **cắt lời** (barge-in) — nói to hơn là Cherry dừng nghe lại

### 4.3. Đổi giọng (nếu cần)

Kiểm tra giọng hiện có:
```
curl http://127.0.0.1:8765/api/voice/tts-voices
```
→ 2 giọng: HoaiMy (nữ, active) + NamMinh (nam). Theo quy ước owner: **thống nhất 1 giọng Hoài My**; lệnh verbatim "giọng nam" của anh là quyền tường minh để đổi.

Đổi cấu hình TTS: `GET/POST /api/voice/tts-config`.
Cấu hình wake: `GET/POST /api/voice/wake-config`.

### 4.4. Kiểm tra giọng nói nhanh

```
curl -X POST http://127.0.0.1:8765/api/voice/tts-synthesize ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Chào anh Quân\"}"
```
→ HTTP 200 + audio WAV. TTS đo thật: 681ms cho 150 ký tự.

---

## 5. DASHBOARD ĐIỀU HÀNH (8766)

Mở http://127.0.0.1:8766/ — 11 tab:

| Tab | Dùng khi nào |
|---|---|
| **Dialogue** | Chat với Cherry + xem trạng thái nhận thức |
| **Deep Memory** | Tìm kiếm trí nhớ chuyên sâu, timeline, units (V9) |
| **Consultation** | Gửi yêu cầu tham vấn / xem câu trả lời của Cherry |
| **Orchestration** | Kế hoạch đa lĩnh vực + giám sát ranh giới an toàn |
| **Workbench** | Việc đang làm (work-queue) + tasks |
| **Learning** | Báo cáo tự học + hồ sơ nâng cấp |
| **NetChat** | Kênh tin nhắn bot 24/7 |
| **Edge Sync** | Heartbeat PC↔Pi5, alerts, file transfers |
| **Pi5 Embodiment** | Avatar/audio/camera của Pi5 |
| **Intelligence** | Scorecard trí tuệ + audit |
| **Persona** | Hồ sơ bản sao số của anh |

---

## 6. CHẠY V7 SKILLS

### 6.1. 5 skill read-only qua API (whitelist)

```
curl http://127.0.0.1:8765/api/v7/skill/memory_health_audit
curl http://127.0.0.1:8765/api/v7/skill/lesson_mining?limit=20
curl http://127.0.0.1:8765/api/v7/skill/system_status_summary
curl http://127.0.0.1:8765/api/v7/skill/pipeline_audit?limit=10
curl http://127.0.0.1:8765/api/v7/skill/voice_health_check
```

Kết quả: `{"success": true, "skill": "<tên>", "result": {...}}`.
Skill không trong whitelist → HTTP 404 + danh sách skill có sẵn.

### 6.2. Qua chat tự nhiên

Trong `/api/chat`, hỏi các câu chứa trigger (ví dụ: "kiểm tra sức khỏe memory", "audit pipeline") → block V7 tự chạy + marker 🧠/🔊/📜 cuối reply.

### 6.3. Danh sách skill toàn bộ

```
curl http://127.0.0.1:8765/api/skills
```
→ 10 skill trong registry (lifecycle TESTED/AVAILABLE).

**Lưu ý kỷ luật:** skills chỉ **report_only** — KHÔNG tự ghi/gửi ngoài. Nâng lifecycle TESTED → APPROVED cần owner duyệt.

---

## 7. QUẢN LÝ TRÍ NHỚ

### 7.1. Tìm kiếm semantic

```
curl "http://127.0.0.1:8765/api/memory/semantic/search?q=deadline+báo+cáo"
curl http://127.0.0.1:8765/api/memory/semantic/stats
```

### 7.2. Trí nhớ chuyên sâu (Deep Memory V9)

| Endpoint | Chức năng |
|---|---|
| `GET /api/memory/deep/stats` | Thống kê tổng quan |
| `GET /api/memory/deep/timeline` | Timeline theo thời gian |
| `GET /api/memory/deep/units` | Danh sách knowledge units |
| `GET /api/memory/deep/questions` | Câu hỏi tự sinh |
| `POST /api/memory/deep/extract` | Trích xuất từ text |
| `POST /api/memory/deep/answer` | Trả lời từ trí nhớ |
| `POST /api/memory/deep/review` | Review |

### 7.3. Review session (duyệt memory)

```
POST /api/memory/review/start      → bắt đầu session review
GET  /api/memory/review/current    → finding hiện tại
POST /api/memory/review/respond    → chấp nhận/từ chối
POST /api/memory/review/confirm    → xác nhận thay đổi
POST /api/memory/review/undo       → hoàn tác
```

**Số liệu 18/11:** 3.157 memories (EPISODIC 3.135 · SEMANTIC 10 · PROCEDURAL 2 · PREFERENCE 3 · CANDIDATE 7); verification: OBSERVED 2.952 / UNVERIFIED 113 / VERIFIED 72 / USER_PROVIDED 13 / CANDIDATE 7.

---

## 8. QUẢN LÝ TÁC VỤ + THAM VẤN

### 8.1. Tasks

```
GET  /api/executive/tasks                  → danh sách task
POST /api/executive/tasks/create           → tạo task mới
GET  /api/executive/tasks/detail?id=...    → chi tiết
POST /api/executive/tasks/execute          → thực thi
POST /api/executive/tasks/cancel           → hủy
GET  /api/executive/tasks/cognitive-state  → trạng thái nhận thức của task
GET  /api/executive/tasks/transitions      → lịch sử chuyển trạng thái
```

### 8.2. Tham vấn (Consultations)

```
GET  /api/executive/consultations          → hộp thư tham vấn
POST /api/executive/consultations/create   → gửi câu hỏi
POST /api/executive/consultations/respond  → trả lời
```

### 8.3. Work-queue + todos

```
GET  /api/workbench/overview
GET  /api/workbench/tasks
GET  /api/todos      POST /api/todos/add      POST /api/todos/done
```

---

## 9. NETCHAT

Bot "Trợ lý Tony Pham" chạy 24/7 — anh nhắn tin từ điện thoại/máy khác qua NetChat.

**An toàn 2 bước (bắt buộc):** khi Cherry cần GỬI DM cho anh:
1. Bot gửi **preview** nội dung + hỏi xác nhận
2. Anh trả lời xác nhận → bot mới gửi thật với `--confirmed <token>`

**Không bao giờ tự gửi** — đây là luật cứng.

Quản trị:
```
GET  /api/executive/netchat/status     → trạng thái bot
GET  /api/executive/netchat/messages   → tin nhắn gần đây
POST /api/executive/netchat/send       → gửi qua bot (2-step gate)
POST /api/executive/netchat/command    → lệnh điều khiển
```

---

## 10. CAMERA + FILE TRÊN PI5

### 10.1. Camera

```
POST /api/executive/edge/camera/control   → camera_on / camera_off
GET  /api/executive/edge/camera/status
POST /api/executive/edge/camera/snapshot  → chụp 1 ảnh (47KB, 640×480)
GET  /api/executive/edge/camera/image     → lấy ảnh
GET  /api/executive/edge/camera/library   → thư viện ảnh
POST /api/executive/edge/camera/stream    → stream
```

### 10.2. File transfer (HMAC-signed)

```
POST /api/executive/edge/transfer/initiate
POST /api/executive/edge/transfer/chunk
POST /api/executive/edge/transfer/ack
GET  /api/executive/edge/transfer/status
GET  /api/executive/edge/files
POST /api/executive/edge/files/upload | /files/download | /files/sync-all
```

---

## 11. GIÁM SÁT SỨC KHỎE HỆ THỐNG

| Endpoint | Chức năng |
|---|---|
| `GET /api/health` | Tổng quan components (core/llm/db/edge) |
| `GET /api/health/history` | Lịch sử |
| `GET /api/health/machine` | CPU/RAM/disk |
| `GET /api/health/rca` | Phân tích nguyên nhân gốc |
| `GET /api/executive/edge/status` | Heartbeat Pi5 + alerts |
| `GET /api/executive/edge/pi5-stability` | Ổn định Pi5 |
| `GET /api/intelligence/scorecard` | Điểm trí tuệ |
| `GET /api/autonomic/status` | Hệ thần kinh tự động |
| `GET /api/autonomic/selftest` | Tự kiểm tra |

**Health hiện tại:** core_server HEALTHY; ollama DISABLED (theo owner); brain_db hoạt động — overall DEGRADED do Ollama tắt (đúng thiết kế, không phải lỗi).

---

## 12. TỰ HỌC + TỰ CHUẨN ĐOÁN

### 12.1. Learning daemon (5 phút/chu kỳ)

```
GET  /api/learning/status    → đang chạy/nghỉ, số facts
POST /api/learning/pause     → tạm dừng
POST /api/learning/resume    → tiếp tục
POST /api/learning/trigger   → chạy ngay 1 chu kỳ
GET  /api/executive/learning/reports → báo cáo
```

### 12.2. Watchdog (cap 5 lần/giờ)

Tự chạy nền — phát hiện: FED mất kết nối, CLO session stall >24h, NetChat stale, learning chết. **Chỉ báo + log, không tự sửa** (an toàn). Kết quả xem qua `/api/autonomic/status` + tab Learning.

### 12.3. Cherry Autonomous Mode (mới 18/11)

Chạy nền `tools/cherry_autonomous.py` — tự vận hành chủ động. Đã vào launcher bước 5/6 + stop script.

---

## 13. BACKUP + BÁO CÁO TỰ ĐỘNG

| Việc | Thời gian | Cơ chế |
|---|---|---|
| Backup | 2AM hằng ngày | Task Scheduler `QUAN_AI_BRAIN_BACKUP_2AM` |
| Report sáng | 8AM hằng ngày | Task Scheduler |

Kiểm tra lịch: `schtasks /query | findstr QUAN_AI` (PowerShell) hoặc xem Task Scheduler GUI.

---

## 14. XỬ LÝ SỰ CỐ THƯỜNG GẶP

### 14.1. Pi5 không kết nối

1. Kiểm tra `GET /api/executive/edge/status` → state?
2. Pi5 có **auto-discovery**: PC đổi IP → 45s sau tự tìm lại. Đợi 1 phút.
3. Vẫn offline → kiểm tra vật lý: nguồn Pi5, đèn LED, WiFi router
4. DHCP: nên đặt **DHCP reservation** cho PC + Pi5 trên router (IP hiện nhảy .9→.13→.11→.24)

### 14.2. Cherry nghe nhầm TV

Đã fix: fuzzy ≤2 lỗi + 19/19 TV noise bị từ chối. Nếu còn: kiểm tra `/api/voice/wake-config`, thu hẹp threshold. Memory nhiễm TV → dùng memory review (§7.3) để gỡ.

### 14.3. Server không phản hồi

1. `curl http://127.0.0.1:8765/api/health` → lỗi?
2. Chạy lại `KHOI_DONG_24_7.bat` (idempotent — có `ensure_single_instance` chống double-start)
3. Watchdog sẽ tự restart trong cap 5 lần/giờ

### 14.4. Task Scheduler không chạy .bat/.vbs

**Đã fix 18/11 (commit `76f69e1`):** VBS giờ set `CurrentDirectory = E:\BRAIN` trước khi Run. Nếu vẫn lỗi: kiểm tra Task Scheduler → task → Action → Start in = `E:\BRAIN`.

### 14.5. Lỗi "skill không trong whitelist"

Skill chỉ có 5 cái qua HTTP (§6.1). Skill khác (EMAIL_ANALYSIS...) chạy nội bộ qua chat/consultation, không có HTTP endpoint — đúng thiết kế an toàn.

### 14.6. Kết quả pytest có fail

9 fail đều **PRE-EXISTING** (stash-verified 18/11, commit `8e600b4`): HTML cache version, edge kiosk endpoints, cognitive_loop health, cpsl_runner, digital_identity, media_only_dm, web_server speak_audio, executive_edge_startup (TimeoutError). Không liên quan chức năng chính. Báo cáo đầy đủ: `reports/HANDOFF_LATEST.md`.

---

## 15. BẢO MẬT — OWNER CẦN BIẾT

1. **HMAC signing:** mọi POST từ Pi5 qua 8766 phải HMAC-sign; sai key → 401
2. **Không đọc secret:** hệ thống không mở .env/credentials; log có redact
3. **R4 approval:** hành động nhạy cảm cần duyệt qua `approval_cards` (bảng v2)
4. **R5 hard-block:** không có hard-coded credentials — không thể override
5. **2-step NetChat gate:** không DM owner tự do
6. **Quarantine:** tri thức lạ không tự vào memory chính
7. **Lệnh owner:** "duyệt merge" = merge PR qua API; "duyệt toàn bộ" = làm hết mục duyệt; "duyệt để làm" = làm ngay

---

## PHỤ LỤC — FILE QUAN TRỌNG

| File | Vai trò |
|---|---|
| `E:\BRAIN\KHOI_DONG_24_7.bat` | Khởi động 24/7 |
| `E:\BRAIN\tools\stop_tony_services.ps1` | Tắt toàn bộ |
| `E:\BRAIN\tools\khoi_dong_24_7_hidden.vbs` | Khởi động ẩn (Task Scheduler) |
| `E:\BRAIN\tools\cherry_autonomous.py` | Autonomous Mode |
| `E:\BRAIN\tools\learning_daemon.py` | Tự học |
| `E:\BRAIN\tools\watchdog.py` | Tự chuẩn đoán |
| `E:\BRAIN\tools\memory_review.py` | Review trí nhớ |
| `E:\BRAIN\data\brain.db` | Trí nhớ chính (SQLite) |
| `E:\BRAIN\data\knowledge_db\chroma.sqlite3` | Vector store |
| `E:\BRAIN\data\skill_registry.json` | V7 skill registry |
| `E:\BRAIN\data\tts_preference.json` | Giọng Hoài My |
| `E:\BRAIN\reports\HANDOFF_LATEST.md` | Handoff mới nhất |
| `E:\BRAIN\bao cao xay dung he thong\11.2026\` | Thư mục tài liệu này |

---

*Hướng dẫn kết thúc. Fail-honest: mọi endpoint/URL/con số đã probe thật 18/11/2026 trên bản master 304d6eb.*
