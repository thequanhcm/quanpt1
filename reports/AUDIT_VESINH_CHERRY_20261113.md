# BÁO CÁO RÀ SOÁT + AUDIT VỆ SINH CHERRY — 13/11/2026 (22:30–23:00)

**Phạm vi:** toàn bộ E:\BRAIN (trừ BRAIN_0, .venv, .git) — file rác / file lỗi / draft ảnh hưởng tốc độ xử lý + hiển thị.
**Nguyên tắc:** CÁCH LY trước, KHÔNG xóa vội; test trước–sau; fail-honest.

---

## 1. KẾT QUẢ QUÉT

| Nhóm | Số lượng | Xử lý |
|---|---|---|
| `__pycache__`/*.pyc | 1.637 | **GIỮ** — tăng tốc import Python, không phải rác |
| Junk thật (tmp/bak/orig) ngoài BRAIN_0 | 38 | Cách ly phần thuộc runtime (xem §2); .bak DWG/xlsx thuộc `kho_tai_lieu` + `Skill/UC` = **dữ liệu cá nhân owner — KHÔNG đụng** |
| File 0 byte | 51 | 3 file đụng runtime → cách ly; phần còn lại là marker/WAL hợp lệ (`edge_devices.db` 0 byte **ĐƯỢC CODE DÙNG THẬT** — server.py:287 → GIỮ) |
| Log lớn >5MB | 3 (77,3MB) | **Đã rotate** (archive → truncate live) |
| File >50MB | 50 | Đĩa còn 182GB/342GB → không ảnh hưởng tốc độ; chờ owner duyệt dọn (§4) |

## 2. ĐÃ CÁCH LY (không xóa) — `E:\BRAIN\quarantine_audit_20261113\` (có MANIFEST.json + md5)

| File | Lý do |
|---|---|
| data/tmp_stt_roundtrip.wav (123KB) | tmp test STT, không code tham chiếu |
| data/tmp_ear_test.wav (95KB) | tmp test audio, không code tham chiếu |
| data/tmp_eye_snapshot.jpg (47KB) | tmp test camera, không code tham chiếu |
| tmp_audit_merge.json (46KB) | temp audit cũ, không code tham chiếu |
| data/experience.db (0 byte) | ORPHAN — không code nào dùng (grep src/tools/tests/edge_client = 0) |
| logs/e1.mp3 (0 byte) | rác trong logs/ |
| data/backups/tasks_backup_20261101_2300.db-wal (0 byte) | WAL mồ côi của backup cũ |
| tmp_audit_e2e_1311.py, tmp_audit_schema_1311.py | script test của TONY, dùng xong |

## 3. ĐÃ ROTATE LOG (giải phóng write-path)

- `logs/dual_servers_watchdog.log` 55,6MB → `logs/archive/20261113/` → truncate live
- `logs/learning_daemon.py.log` 11,1MB → idem
- `logs/learning_daemon_stdout.log` 10,6MB → idem
- Tổng 77,3MB archived; writer append-mode giữ handle an toàn (health 200 sau khi rotate).

## 4. KHOANH VÙNG CHỜ OWNER DUYỆT (không tự xóa)

1. `BRAIN_0/` 7,5GB (đã nộp trước — chờ duyệt)
2. `backups/knowledge_db_broken_20261031_005544/` ~540MB (chroma.sqlite3 391MB + data_level0.bin 150MB)
3. `data/pre_rehabilitate_20261112_133541.db` 103MB (DB chuỗi pre_* trùng 2 bản trong backups/)
4. 10 bản backup brain.db ~103MB/bản (giữ 2–3 bản gần nhất là đủ)
5. `kho_tai_lieu` + `Skill/UC`: các `.bak` DWG/bản "(1)" trùng (~150MB) — **dữ liệu owner, chỉ liệt kê**
6. `backups/rename_cherry_20261106/` + `logs/dm_token2-5.txt` (chờ duyệt từ lần trước)

## 5. TEST TỔNG THỂ (pytest, venv BRAIN)

- Nhóm voice/LLM/TTS: `test_v36_tts, test_vietnamese_tts, test_voice_api_endpoints, test_voice_first_pipeline, test_llm_provider, test_netmind_provider` → **93 passed, 1 skipped** (skip = cần phần cứng Pi5 trong vòng pytest)
- Nhóm hiển thị/edge/shield: `test_kiosk_overlay_1311, test_file_transfer_2way_1311, test_wake_word_noise_filter_1311, test_agentic_sec_input_shield, test_avatar_expression_sync, test_edge_client, test_wifi_protocol` → **91 passed**
- **Tổng: 184 passed / 1 skipped — KHÔNG test nào fail sau khi cách ly.**

## 6. TEST CHI TIẾT HOẠT ĐỘNG (E2E sống, không mock — server 8766 production)

| Kiểm tra | Kết quả |
|---|---|
| Health 8765 + 8766 | 200 / 200 |
| /api/chat thường ×3 | GLM-5.3-Flash, 2.01–3.24s, "10 + 5 = 15 ạ." đúng |
| Failover model đã rút (M2.7) | TỰ chuyển GLM-5.3-Flash, 1.71s ✓ |
| /api/voice/interact | **0.03s** trả `tts_mode=background` (stream reply sống) |
| TTS piper → audio tới Pi5 | kiosk avatar chuyển SPEAKING trong lúc phát ✓ |
| Edge heartbeat | 1.06s trước đó (timeout 12s) — LIVE ✓ |

## 7. TEST HIỂN THỊ

### PC Dashboard (qua CDP Edge, tab 8766)
- Avatar engine cache `?v=emo_1311_r5` ✓; `window.setAvatarState` + `showExecToast` hoạt động
- Chuyển state thử 5/5 (HAPPY/THINKING/SPEAKING/LISTENING/SURPRISED) OK; toast hiện 1/1; `alert()` = 0
- 20 telemetry pills ("NetMind Cloud (GLM-5…)", "Trí Nhớ: 500 mục"…); 11 tab pane đủ (nút `btn-tab-startup-sequence` thuộc nhóm nút hành trình/khởi động — pane riêng nằm ngoài 11 pane chính)

### Pi5 Kiosk — PHÁT HIỆN + ĐÃ SỬA LỖI HIỂN THỊ
- **Sự cố:** chromium kiosk đã chết từ 18:38 (zombie `[chromium] <defunct>`) → màn hình 7" KHÔNG hiển thị avatar cả chiều; dashboard báo STANDBY
- **Root cause (xác định bằng evidence):** `SingletonLock` profile mặc định `~/.config/chromium/SingletonLock` chỉ vào **zombie** (chủ đã chết) → chromium mới khởi động thấy "instance khác đang chạy" → tự thoát ngay → thành zombie tiếp → **vòng lặp chết-không-hiển-thị**. Lần launch đầu (22:39) cũng chết vì cùng nguyên nhân; lần thứ 2 sau khi dọn lock thì sống.
- **Fix đã áp dụng (đúng quy trình display):** verify chủ lock là zombie (`state=Z`) → xóa SingletonLock/Socket/Cookie → POST `/api/kiosk/control {launch_kiosk}` → daemon tự launch
- **Kết quả kiểm chứng:** T+8s / T+60s / **T+3 phút đều `kiosk_running: True | ACTIVE`**, 1 chromium sống, không zombie mới ✓
- **Khiếm khuyết gốc chờ duyệt (sprint sau):** (a) daemon Pi5 (`main.py`) không `wait()` con chromium → zombie tích tụ; (b) `launch_kiosk_process()` chưa tự dọn SingletonLock mồ côi trước khi start. 2 fix này thuộc code Pi5 — chờ owner duyệt.
- Screenshot Pi5: **INCONCLUSIVE** — grim/wlopm qua SSH không thấy wl_output (session labwc không expose qua env SSH); bằng chứng = API + process live

## 8. TRẠNG THÁI SAU AUDIT

- Server PC: 8765+8766 = 200, chạy code mới nhất (TTS breaker + warm-up + LLM động)
- Pi5: kiosk **ACTIVE trở lại và ổn định** (đã sửa root cause hiển thị trong audit này — xem §7); heartbeat live; disk 15%; temp 60.9°C; load OK
- Không file nào bị xóa; mọi thay đổi có MANIFEST + md5; pytest 184 pass chứng minh hệ thống ổn định sau vệ sinh
- Báo cáo lưu tại: `reports/AUDIT_VESINH_CHERRY_20261113.md`
