# TONY COGNITIVE EVOLUTION — M0 ACTUAL STATE AUDIT

**Thời điểm audit:** 01/11/2026, 09:20–09:45 (SE Asia Standard Time)
**Người thực hiện:** TONY (QUAN AI BRAIN) — theo chương trình TONY COGNITIVE EVOLUTION V1.0
**Phạm vi:** Toàn bộ workspace QUAN AI BRAIN, services PC + Pi5, dữ liệu, test, vận hành.
**Nguyên tắc:** Mọi thông tin dưới đây là kết quả đo/lặp trực tiếp tại thời điểm audit, KHÔNG lấy từ báo cáo cũ.

---

## 1. Điểm đã kiểm tra và bằng chứng

| # | Hạng mục | Phương pháp | Kết quả |
|---|----------|-------------|---------|
| 1 | Workspace thực tế | `ls E:\` | **E:\ KHÔNG tồn tại**. Workspace thật: `D:\AI\AI Quanpt1 2026\BRAIN` |
| 2 | Git | `git status` trong workspace | **KHÔNG phải git repository** (không .git, không branch, không commit) |
| 3 | Cấu trúc source | Walk `src/quan_ai_brain` | 34 module, **242 file .py, 83.118 dòng** |
| 4 | Test suite | `pytest --collect-only` | **2.958 tests collected** (151 file test) |
| 5 | Test suite | `pytest -q` đầy đủ | **2.914 passed, 44 skipped, 1 warning — 2:59** (exit 0) ✅ |
| 6 | Server 8766 | GET /api/status | ONLINE, ollama_online=true, 8 models Ollama |
| 7 | Server 8765 (GLM) | GET /api/status | ONLINE (NetMind provider, api_key_present=true, catalog_reachable=true) |
| 8 | Health API | GET /api/health | overall HEALTHY (4 components: core_server, ollama_daemon, brain_db, task_registry) |
| 9 | Pi5 services | ssh systemctl | quan_ai_edge, quan_ai_wake, quan_ai_kiosk_guard **cả 3 active** |
| 10 | Pi5 nhiệt/nguồn | vcgencmd | 57,6–58,2°C; throttled=0x0 (**không undervoltage hiện hành**) |
| 11 | Pi5 uptime | uptime | up 1:58 (boot 07:16:43 — KHÔNG reboot lạ trong phiên sáng nay) |
| 12 | Pi5 disk/RAM | df/free | 13% disk dùng; RAM 1.234/4.049 MB |
| 13 | Kiosk Pi5 | GET /api/kiosk/status | core_connected=true, kiosk_running=true, embodiment ACTIVE |
| 14 | Network PC↔Pi5 | edge telemetry | rtt_ms=30,18; packets_in=1471, packets_out=1757 |
| 15 | Loa BT SRS-XB33 | bluetoothctl | **Connected: no** (mất kết nối vật lý từ ~09:04, cần owner bật nguồn) |
| 16 | Memory DB | sqlite count | memories=2.004, semantic=1.842, episodes=2.548, **candidate_knowledge=4.284 (quarantine)**, knowledge_units=150, knowledge_relations=210, feedback=270 |
| 17 | Tasks DB | sqlite count | durable_tasks=578, durable_task_steps=1.029 |
| 18 | Knowledge Base | fs + db | knowledge_db=69,3 MB, kho_tai_lieu=1.778 files |
| 19 | Handoff | fs | HANDOFF_LATEST.md tồn tại; **mtime 31/10 18:38** (chưa cập nhật sau phiên 01/11) |
| 20 | Logs | fs mtime | responder heartbeat 09:18 (fresh), learning daemon 09:13–09:16, watchdog 08:48 |
| 21 | Windows services/tasks | Get-Service/ScheduledTask | Không service Windows; **3 scheduled tasks**: BACKUP_2AM, KHOI_DONG_LOGON, MORNING_REPORT_8AM (State=3=Ready) |
| 22 | journald Pi5 | config + fs | Storage=persistent ĐÃ cấu hình NHƯNG `/var/log/journal` rỗng (4,0K) → **ghi nhật ký vẫn VOLATILE** (mất lịch sử reboot) |

## 2. Baseline đối chiếu với báo cáo 01/11/2026

| Nội dung trong báo cáo | Kết quả audit thực tế | Đánh giá |
|---|---|---|
| Workspace `E:\AI\QUAN AI BRAIN` (master prompt) | `D:\AI\AI Quanpt1 2026\BRAIN` | **Sai trong prompt** — em dùng workspace thật |
| Server 8766 Executive | ONLINE | Khớp |
| Dashboard 8765 GLM | ONLINE | Khớp |
| Memory ~500 bản ghi | memories=2.004 + semantic=1.842 + episodes=2.548 | Báo cáo thấp hơn thực tế đáng kể |
| 2.914 pytest PASS | **2.914 passed, 44 skipped (2.958 collected)** | Khớp chính xác — đã chạy lại |
| Pi5 reboot bất thường | Boot 07:16 ổn định; nhưng **journald volatile → không tra cứu được lịch sử reboot cũ** | Nguyên nhân chưa xác định được do thiếu log bền vững |
| Edge-TTS 403 | Xác nhận còn flaky (gặp 09:00:37 trong E2E thoại) | Còn mở |
| R4 approval_verifier chưa cấu hình | Xác nhận: chỉ `clae/quarantine.py` có hook, default None → PermissionError; server KHÔNG inject; 4.284 candidates kẹt quarantine | Còn mở |
| Reply-thread NetChat | Gateway Bot NetChat bỏ root_id (API trả rỗng) — đã dùng prefix trích dẫn thay thế | Đã xử lý thay thế, còn giới hạn nền tảng |

## 3. Danh mục services/processes đang chạy (bằng chứng)

**PC (DESKTOP-SNMI929):**
- `start_dual_servers.py` (venv python) → serve 8766 + 8765
- `netchat_auto_responder.py` (heartbeat fresh 09:18)
- `learning_daemon.py` (log 09:13–09:16)
- watchdog (log 08:48)
- Scheduled tasks ×3 (backup 2AM, khởi động logon, báo cáo sáng 8AM)

**Pi5 (quanpt1@100.100.83.59):**
- `quan_ai_edge` (daemon kiosk + HTTP 8768) — active
- `quan_ai_wake` (wake word Vosk BT-first) — active
- `quan_ai_kiosk_guard` — active
- Wake record pw-record giữ mic BT thường trữ

## 4. Những gì KHÔNG kiểm tra được trong M0 (ghi nhận trung thực)

1. **Lịch sử reboot Pi5 31/10 20:32:13** — không còn log (journald volatile) → cần fix journald bền vững trước (xem GAP-02).
2. **Camera MJPEG stream chất lượng thực** — chỉ xác nhận camera_streaming=false ở trạng thái nghỉ.
3. **Nội dung credentials/key** — theo quy tắc an toàn tuyệt đối, chỉ kiểm tra tồn tại (api_key_present=true, len=25) — không đọc giá trị.
4. **Email/Outlook tích hợp** — có module `email_intake.db` (24 KB) nhưng chưa probe luồng thật trong M0.

---

*Kết thúc M0-AUDIT. Các gap chi tiết tại `TC_EVOLUTION_M0_GAP_ANALYSIS.md`.*
