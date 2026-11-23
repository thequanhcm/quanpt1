# BÁO CÁO AUDIT TOÀN HỆ THỐNG + ĐỒNG BỘ + CÁCH LY — 23/11/2026

**Yêu cầu owner:** "audit, rà soát toàn bộ cherry và Quan AI brain, có chức năng nào chồng chéo, hãy đồng bộ và thống nhất toàn hệ thống cho khoa học. các phần và hạng mục thừa hãy cách ly để đảm bảo hệ thống hoạt động ổn định 24/7. việc cách ly sau không ảnh hưởng đến các hoạt động của cherry và hệ sinh thái, tạo folder cho cách ly riêng các phần rác và các mục thừa không sử dụng."

**Phương pháp:** audit TRƯỚC — sửa SAU (quy tắc owner). Mọi item cách ly đều được
verify 3 lớp: (1) 0 tham chiếu trong code active, (2) không thuộc chuỗi Task
Scheduler 24/7, (3) không thuộc Pi5 sync whitelist. Move = không xóa gì —
trả lại được 100%.

---

## 1. CHUỖI SỐNG 24/7 HIỆN TẠI (KHÔNG ĐỘNG — verify còn nguyên sau cách ly)

Task Scheduler READY (4 task):
| Task | Chạy | Chu kỳ |
|---|---|---|
| QUAN_AI_BRAIN_BACKUP_2AM | `tools/run_backup_hidden.vbs` → `tools/backup_database.py` | 2AM hằng ngày |
| QUAN_AI_BRAIN_MORNING_REPORT_8AM | `tools/run_morning_report_hidden.vbs` → `tools/morning_report.py` | 8AM hằng ngày |
| QUAN_AI_BRAIN_PI5_FILE_SYNC_15MIN | `tools/run_pi5_sync_hidden.vbs` → `tools/pi5_edge_file_sync_guard.py` | 15 phút |
| QUAN_AI_BRAIN_PI5_MONITOR_5MIN | `tools/run_pi5_monitor_hidden.vbs` → `tools/pi5_monitor.py` | 5 phút |

Start/stop thủ công (đường DUY NHẤT theo owner 19/11):
- `KHOI_DONG_CHERRY.bat` (1 cửa sổ tổng: servers + NetChat + learning)
- `TAT_CHERRY.bat`
- Lệnh DM qua NetChat: `email hôm nay`, `lịch họp`, `status`...

**Kết quả verify sau cách ly:** 6 file wrapper + 2 BAT trên đều còn nguyên,
9 script lõi py_compile sạch, 24/24 test command center PASS, 24/24 test
office connector PASS, live smoke VoIP đọc được 14 lịch họp thật.

## 2. CHỒNG CHÉO PHÁT HIỆN + CÁCH XỬ LÝ

### 2.1. Ba đường khởi động chồng chéo (rủi ro nhầm lẫn cao nhất)
- `TONY_START.bat` (30/10) + `KHOI_DONG_24_7.bat` (24/7 auto) + `KHOI_DONG_CHERRY.bat` (19/11, manual) — **3 đường start cùng 1 hệ thống**.
- **Xử lý:** giữ đúng 1 đường = `KHOI_DONG_CHERRY.bat` / `TAT_CHERRY.bat` (ý owner mới nhất 19/11: manual-start, 1 cửa sổ). Cách ly 2 đường cũ + toàn bộ helpers (`_spawn_*.bat`, `khoi_dong_24_7_hidden.vbs`, `run_cherry_autonomous_*`).
- Task Scheduler `KHOI_DONG_LOGON` + `LIVENESS_30MIN` + `CHERRY_AUTONOMOUS` đã Disabled từ trước — không còn gì tham chiếu file bị cách ly khi chạy.

### 2.2. Email/VoIP: 3 module chồng chéo → 1 luồng thống nhất
- `integration/email_intake.py` (5 nhóm, gốc Sprint cũ) — vẫn là store nền, KHÔNG sửa.
- `office/email_connector.py` (10 nhóm + score, Sprint 1a) — tầng phân tích, tái dùng mail_reader.
- `tools/mail_reader.py` (SOAP) — connector DUY NHẤT gặp vmail.viettel.vn.
- **Xử lý:** thống nhất thành 1 chuỗi khoa học: `mail_reader (SOAP connector) → email_intake (store/dedupe) → office/email_connector (phân tích 10 nhóm) → netchat_command_center (giao diện DM)`. Không tạo connector thứ 2. Sprint 1 VMAIL (card TASK-VMAIL-S1) sẽ đóng gói chuỗi này thành class VmailConnector — KHÔNG viết lại I/O.
- **Wire mới (đồng bộ M7):** lệnh DM `lịch họp` / `lịch họp voip` / `lịch họp hôm nay` → `voffice_reader.py` (đọc lịch họp VoIP gián tiếp qua mail vofficeadmin, READONLY R2). Đặt TRƯỚC `email_today` để không bị nuốt. **Đã test thật: detect_intent 6/6 OK + live smoke 14 lịch họp thật.**

### 2.3. Engine avatar trùng 4 nơi — giữ đúng bản đang chạy
- `src/quan_ai_brain/web/static/avatar_engine.js` (md5 7dd792fb) — **bản chính web** (server.py serve từ đây).
- `edge_client/avatar_engine.js` (md5 db3c6de8) — **bản edge Pi5** (sync guard đồng bộ 5 file này).
- `edge_client/assets/avatar/` — **KHÔNG phải rác**: staging area upload asset → Pi5 (server.py L5241-5297). Đã loại khỏi danh sách cách ly.
- `bao cao xay dung he thong/avatar/avatar_engine.js` — bản lưu báo cáo (chấp nhận, thuộc hồ sơ).

### 2.4. Watchdog/monitor: 1 tầng duy nhất
- `tools/watchdog.py` (nền) + `monitoring/` (collectors + alert engine) + `pi5_monitor.py` (Pi5 riêng) — không trùng chức năng (PC health vs Pi5 vs network), giữ nguyên. Không daemon nào tự chạy nền ngoài Task Scheduler (đúng manual-start).

## 3. ĐÃ CÁCH LY — `E:\BRAIN\_QUARANTINE_20261123\` (11.88 GB, 37 item)

| Nhóm | Nội dung | Dung lượng | Lý do |
|---|---|---|---|
| tmp render avatar | `.tmp_motion_frames` (v8→v9.3 20-22/11) | 11.70 GB | tmp render preview đã xem xong, 0 refs, gitignore sẵn |
| trùng lặp | `Module 3` root | 5.3 MB | bản sao 100% của `kho_tai_lieu/.../Module 3` (38 files) |
| zip cũ | `vivi-agent-20261118.zip` | 112 MB | zip deploy 18/11 ở root |
| preview cũ | 10 file mp4 preview Pi5 v5-v9.3 | 54 MB | đã xem, giữ `Pi5/mẫu/` (27 files V3-candidate) NGUYÊN VẸN |
| start scripts cũ | TONY_START/STOP, KHOI_DONG_24_7 + hidden vbs, cherry_autonomous, 12 script tools/ cài-đặt-1-lần | ~0.1 MB | 3 đường start chồng chéo → còn 1; script cài đặt đã xong |
| bak engine | `avatar_engine.js.bak_v6cin_1411` | 0.1 MB | backup cũ 14/11 |
| tmp khác | `tmp_m5b`, `quarantine_audit_20261113`, `quarantine_cleanup` | 0.4 MB | tmp/quarantine cũ đã xử lý |

Manifest đầy đủ (`MANIFEST.json`): đường dẫn gốc → đích cách ly + lý do + kích
thước từng item — trả lại được 100% bằng move ngược.

**KHÔNG cách ly (verify kỹ):** `Pi5/mẫu/` (V3-candidate chờ owner xem), 6 wrapper
Task Scheduler, `edge_client/assets/avatar` (staging Pi5), `kho_tai_lieu/`,
`Skill/`, backups DB (backup_database.py tự giữ 30 bản), `data/` runtime.

## 4. TEST EVIDENCE
- `py_compile` 9 script lõi (console host, responder, mail_reader, voffice_reader, backup, morning report, pi5 sync guard, pi5 monitor, sync runner): exit 0.
- `pytest tests/test_netchat_command_center.py`: **24/24 PASS** (sau khi thêm voffice_meetings).
- `pytest tests/test_office_email_connector.py`: **24/24 PASS**.
- detect_intent smoke: 6/6 đúng intent (`lịch họp voip hôm nay`→voffice, `email hôm nay`→email, `duyệt`→approve...).
- Live smoke SOAP: `voffice_reader.py upcoming` → **14 lịch họp thật** (Đào tạo Kỹ sư AI 24/11, Họp định kỳ KV1 23/11 15h...).
- Chuỗi sống 24/7: 6 wrapper + 2 BAT tồn tại nguyên vẹn sau cách ly.

## 5. HIỆN TRẠNG SAU ĐỒNG BỘ
- 1 đường start duy nhất (manual): `KHOI_DONG_CHERRY.bat` / `TAT_CHERRY.bat`.
- 4 task nền duy nhất: backup 2AM / report 8AM / Pi5 sync 15' / Pi5 monitor 5'.
- Email: 1 connector SOAP → 1 store → 1 tầng phân tích → giao diện DM (`email hôm nay`, `lịch họp`).
- 11.88 GB rác nằm gọn `_QUARANTINE_20261123/`, gitignore, 0 ảnh hưởng runtime.
- Disk E: 185 GB free (move nội bộ ổ E — chưa giải phóng, chờ owner duyệt dọn hẳn).

## 6. ĐỀ XUẤT (chờ owner)
1. **"duyệt dọn"** → xóa hẳn `_QUARANTINE_20261123/` giải phóng 11.88 GB (manifest còn trong báo cáo này để tra cứu).
2. **"commit"** → commit các thay đổi đồng bộ (command_center wire voffice + .gitignore + báo cáo) theo lô đang chờ.
3. Card TASK-VMAIL-S1 (Sprint 1 VmailConnector) vẫn PENDING_APPROVAL — nối tiếp kế hoạch VMAIL.

## 7. KNOWN ISSUES (trung thực)
- Cách ly là move nội bộ ổ E: → chưa giải phóng dung lượng vật lý cho tới khi xóa hẳn.
- `email_intelligence.py` (331 dòng, 5 nơi import) cóOverlap nhẹ về vai trò với `office/email_connector.py` — giữ nguyên vì server.py dùng nó cho dashboard; Sprint 2 VMAIL sẽ thống nhất hợp nhất 1 tầng phân tích duy nhất khi có duyệt.
- 2 task Scheduler DISABLED (KHOI_DONG_LOGON, LIVENESS_30MIN, CHERRY_AUTONOMOUS) vẫn trỏ tới file đã cách ly — nếu owner muốn bật lại auto-start sẽ cần khôi phục file từ quarantine (manifest có sẵn đường dẫn).
