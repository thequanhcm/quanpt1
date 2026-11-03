# TONY OWNER DECISION REGISTER — Sổ quyết định cần Quanpt1 (PHẦN XVII + XVIII)
**Cập nhật:** 01/11/2026 18:05 · Sau thực thi "DUYỆT TOÀN BỘ"

## Đã quyết định & hoàn tất (lưu vết)

| ID | Việc | Quyết định | Kết quả có bằng chứng |
|---|---|---|---|
| M6-B1 | Vá HMAC P0 | "DUYỆT M6-B1" | ✅ 15:50 — 6/6 tests, Pi synced, 0 fault/120s, regression 3.002 |
| Fix P0 responder | Lệnh xử lý dứt điểm lỗi chụp hình | ✅ | ✅ 16:13 — 0 router-error sau restart (E2E) |
| ACK loa TẮT | "Tiếp tục giữ tắt" | ✅ | ✅ sent=0 từ 16:10 — 4+ chu kỳ |
| Mirror F | Lệnh sao chép toàn bộ sang ổ mới | ✅ | ✅ 47.051 file/6,21 GB, verify 3 lớp, task 02:30 |
| WD-ON | Bật lại Watchdog | "duyệt toàn bộ" | ✅ 17:39 — watchdog sống độc lập, TỰ HỒI learning daemon E2E (bài test kill→recover thật) |
| BK-ON | Backup 2AM | "duyệt toàn bộ" | ✅ ĐÃ XÁC MINH: không hỏng — chạy đúng hằng ngày (lần cuối 01:59 result=0); báo cáo cũ nhầm thứ tự alphabet tên file UTC |
| Q-3 | Piper TTS | "DUYỆT Q-3" | ✅ 17:52 — E2E HTTP 200, WAV 125KB READY không phụ thuộc mạng; 88 voice tests |
| Q-4 | Approval verifier R4 | "DUYỆT Q-4" | ✅ 17:58 — fail-closed verifier 11 tests; 3.209 candidates promoted có audit trail chuẩn lifecycle; semantic 1.491→5.051 |
| M2 | Fix reflection.py | "duyệt toàn bộ" | ✅ 18:00 — 2 lỗi (schema + hard-code path bỏ qua injected store); E2E hypothesis quarantine 1 (trước 0) |
| CLEAN | Xoá .venv_broken_backup | "duyệt toàn bộ" | ✅ 18:02 — 50.043 files (~1,1 GB) đã xoá |
| M3 | Memory API consolidation | "DUYỆT M3" | ✅ 18:28 — `unified_memory.py` MemoryFacade 5 lớp + FactLevel FACT/OBSERVED/INFERENCE/QUARANTINED + sàng lọc fact_only push-down SQL; **21 tests PASS**; fix bug thật `MemoryService.add_memory` gọi method không tồn tại (chết im lặng từ đầu); promotion INFERENCE→FACT fail-closed qua R4 verifier |
| M4-P2 | Self-Q&A wired + self-model trung thực | "DUYỆT M4" | ✅ 18:40 — SelfQA wired vào DM (trước GLM); E2E "Em làm được gì?" → 7 năng lực sống; sửa 2 giới hạn SAI (sqlite3 stdlib + API key registry); M4-B CLO alert đã hoạt động (sent=1 DM thật); M4-D = Q-4 đã xong |
| M5-P2 | Barge-in G-23 + Multi-turn DM + fix GLM key | "DUYỆT M5" | ✅ 18:59 — wake_engine không abort mic khi SPEAKING + stopKioskSpeech; DM hiểu "nó/vậy" qua ConversationStateManager; **FIX P0 GLM rỗng** (key ở HKCU\Environment → fallback winreg) — GLM LIVE lại; regression 3.034/0 |
| CLO-UNSTICK | Mở kẹt CLO #7 + phòng tái diễn | "duyệt, hãy xử lý" | ✅ 19:14 — root cause: advance chỉ khi chat tạo task; #7→CONSOLIDATING + #8 RUNNING qua engine chuẩn; `check_clo_stall()` >24h wired watchdog |
| VN-LANG | Chuẩn hoá toàn bộ ngôn ngữ DM = tiếng Việt | "toàn bộ ngôn ngữ gửi cho anh đều được chuẩn hóa bằng ngôn ngữ tiếng việt" | ✅ 19:36 — 4 nguồn DM Việt hoá (command_center + responder greeting + morning_report + health_monitor CLO alert); helper `_vn`/`_vn_err`; 6 test assert đồng bộ; regression 3.034/0; DM demo thật ✅ |
| PROV-CLEAN | Bỏ "theo ghi nhớ anh truyền đạt" + "(nguồn: USER_PROVIDED)" khỏi lời trả lời | feedback image_d79379 | ✅ 19:44 — `strip_provenance_artifacts()` lọc metadata khỏi text trả lời + rule 13 system prompt cấm liệt kê nguồn; E2E "Em sinh ngày nào?" → "Em sinh ngày 20/10/2026 ạ." không leak ✅; regression 3.034/0 |
| DEOM M0 | AS-BUILT PRECHECK — kiểm toán hiện trạng cho Master Prompt V3.0 | MASTER PROMPT V3.0 | ✅ 20:00 — audit thật (policy.py R0–R5 đọc toàn bộ, 62/62 backbone tests, schema DB); nền sẵn ~40%; GAP matrix 16 thành phần + 7 CASE; `DEOM_M0_ACTUAL_STATE.md` + `DEOM_M0_GAP_ANALYSIS.md`; chờ duyệt M1 + duyệt migration R4 ở M2 |
| LLM-FALLBACK | Cài model dự phòng cho NetMind (runtime fallback) | "em cài đặt model dự phòng cho hệ thống netmind" | ✅ 22:23 — chuỗi GLM→qwen2.5:7b→llama3.1→3b→1.5b→0.5b→mistral→qwen→MOCK trong `provider.py` (cả generate + stream); E2E gateway chết → qwen2.5:7b thật (is_mock=False) ✅; regression 3.034/0 |
| Q-1 | git init + commit đầu | "rà soát… anh phê duyệt toàn bộ, làm luôn" | ✅ 22:35 — repo mới, commit `e75d240` 1.692 file; .gitignore chặn secret/DB/venv; verified sạch |
| Q-2 | Fix persistent journal Pi5 | cùng blanket approval | ✅ 22:40 — root cause vendor drop-in `40-rpi-volatile-storage.conf` ép volatile; mask + drop-in `/etc` → `/var/log/journal` 57M persistent; hoàn tác = xoá 2 file |
| Q-5 | Tắt BT power-save Pi5 | cùng blanket approval | ✅ 22:42 — FastConnectable+AutoEnable trong main.conf; bt active Powered yes; loa vẫn TẮT theo owner-ACK |
| DEOM M1 | 4 tài liệu thiết kế (0 code) | cùng blanket approval | ✅ 22:50 — Operating Model + Permission Matrix + Task Lifecycle + Approval Design trong `reports/DEOM_M1_*.md` |
| DEOM M2 | Schema expansion + transition log + verifier + NL intake (R4) | cùng blanket approval (backup trước) | ✅ 23:05 — +11 cột durable_tasks (578 records nguyên vẹn, backup 11,9MB), bảng task_transitions, +10 TaskStatus, TaskVerifier fail-honest, Work Queue 4 bậc, NL intake tiếng Việt giờ VN, 3 API, watchdog deadline guard; regression FULL 3.071/0; commit `dd73ae3` |
| PI5-SHOT | Chụp đúng màn hình kiosk Pi5 theo DM | feedback image_864dc0 | ✅ 19:25 — "chụp màn hình kiosk/pi" giờ chụp TFT Pi5 (grim + wlopm) gửi DM; "chụp màn hình" không kèm pi → vẫn PC; E2E ảnh 291KB verify đúng kiosk TONY |
| Audit V2 | Tổng kiểm toán 22 báo cáo | MASTER PROMPT V2.0 | ✅ 16:45 — 22/22 reports, scorecard Governance C3 |

**Regression cuối:** 3.034 PASS / 44 skipped / 0 FAIL · validate_and_report exit 0 · HANDOFF regen 19:44 (PROV-CLEAN).

## CÒN LẠI — chờ anh quyết (không thuộc phạm vi "duyệt toàn bộ" vừa rồi)

| # | ID | Việc | Vì sao cần | Thời gian | Nếu duyệt em làm ngay |
|---|---|---|---|---|---|
| 1 | **AUDIO** | USB mic/loa Pi5 | Voice chết phần cứng — CẦN MUA THIẾT BỊ, em không thể tự làm | 1h + thiết bị | Mua USB sound card + mic → "DUYỆT AUDIO" |
| 2 | Q-1 | git init | Track changes cho workspace | 30' | "DUYỆT Q-1" |
| 3 | Q-2/Q-5 | journald / BT power-save | Tối ưu phụ | 1h | "DUYỆT Q-2" |

**Quy tắc:** em KHÔNG tự thực hiện mục nào trong bảng chờ; nhắc lại tối đa 1 lần/ngày trong Morning Report (không spam).
