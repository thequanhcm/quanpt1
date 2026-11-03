# BÁO CÁO TỔNG HỢP HỆ THỐNG TONY (QUAN AI BRAIN)
**Thời điểm:** 02:00 — Chủ nhật, 02/11/2026 · **Người lập:** TONY (QUAN AI BRAIN) · **Chủ hệ thống:** Phạm Thế Quân (quanpt1)
**Lưu tại:** `D:\AI\AI Quanpt1 2026\BRAIN\bao cao xay dung he thong\11.2026`
**Phạm vi:** toàn bộ tiến triển từ báo cáo 12:30 ngày 01/11 đến nay (chiều + tối 01/11 → 02/11 00:05)

---

## 1. TÓM TẮT ĐIỀU HÀNH

TONY vận hành ổn định 24/7 trên cả 3 tầng. Trong phiên chiều–tối 01/11, hệ thống **bước sang giai đoạn GOVERNANCE-DEPTH mới**: hoàn tất chuỗi LLM-FALLBACK → PI5-SHOT → VN-LANG → PROV-CLEAN → **DEOM M0→M2** (kiến trúc nhân sự số One-Brain) → GIT/Q-1/Q-2/Q-5 → **ONE-CLICK chuyển máy** → Mirror F fix + đồng bộ 100%.

**Số liệu kiểm thử:** **3.071 PASS / 0 FAIL / 44 skipped** (161 test files, full regression 115s) — tăng +75 test so báo cáo 12:30.

**Số liệu hệ thống (02/11 00:05):**
- Brain DB: 100 MB · memories 2.235 · semantic 5.051 · knowledge_units 150 · quarantined 2.646 (by design)
- Tasks DB: 11,9 MB · 579 durable tasks · 5 transition records (schema mới M2)
- Server 8765+8766: **UP** (HTTP 200) · Pi5 kiosk: **ACTIVE** (up 16h43m) · journald persistent 57M

---

## 2. THÀNH TỰU PHIÊN CHIỀU–TỐI 01/11 (sau báo cáo 12:30)

### 2.1. LLM-FALLBACK ✅ (22:23) — không bao giờ cụt não
- Chuỗi dự phòng hoàn chỉnh: **NetMind GLM-5.3-Flash → qwen2.5:7b → llama3.1 → qwen2.5:3b → 1.5b → 0.5b → mistral → qwen → MOCK** (MOCK chỉ khi tất cả chết, kèm cảnh báo rõ "NO REAL LLM INFERENCE")
- Áp cho cả generate + stream (buffered events); chọn model CÓ THẬT trong Ollama lúc lỗi; minh bạch nguồn qua warning
- E2E 4 kịch bản: GLM sống / GLM chết→7b / Ollama chết hoàn toàn→MOCK / stream qua gateway chết; provider tests 46/46
- Bonus: sửa test flaky `test_entry_expired` (root cause PC reboot 22:01 → monkeypatch monotonic deterministic)

### 2.2. PI5-SHOT ✅ (19:25) — chụp đúng yêu cầu
- Intent `tony_pi_screenshot` có guard ngữ nghĩa: câu có "kiosk/pi" → chụp TFT Pi5 (wlopm --on → grim → scp → DM); không kèm → vẫn chụp PC
- E2E: ảnh kiosk 291KB verify đúng màn hình TONY

### 2.3. VN-LANG ✅ (19:36) — chuẩn hóa tiếng Việt
- Toàn bộ tin DM gửi owner chuẩn tiếng Việt (READY→SẴN SÀNG, RUNNING→ĐANG CHẠY, OFFLINE→MẤT KẾT NỐI, ONLINE→HOẠT ĐỘNG); giữ thuật ngữ quen (kiosk, Pi 5, Ollama, GLM); 6 test asserts

### 2.4. PROV-CLEAN ✅ (19:44) — metadata không rò vào lời nói
- `strip_provenance_artifacts` + rule 13: bỏ chữ "(nguồn: USER_PROVIDED)", "theo ghi nhớ Anh truyền đạt:" khỏi mọi câu trả lời

### 2.5. DEOM M0→M2 ✅ (20:00 → 23:10) — One Brain, One Memory, One Governance
**M0 (20:00):** audit 10 hạng mục trên nền hiện có — nền sẵn ~40%, 2 báo cáo GAP (`DEOM_M0_ACTUAL_STATE` + `GAP_ANALYSIS`)

**M1 (22:00):** 4 tài liệu thiết kế — 0 code (đúng nguyên tắc thiết kế trước):
- `DEOM_M1_OPERATING_MODEL.md` (65 dòng): mô hình vận hành
- `DEOM_M1_PERMISSION_MATRIX.md` (59 dòng): ma trận 13 quyền DEOM §5.1 × vai trò
- `DEOM_M1_TASK_LIFECYCLE.md` (89 dòng): vòng đời task bám schema thật
- `DEOM_M1_APPROVAL_DESIGN.md` (68 dòng): dựa approval_verifier Q-4 fail-closed

**M2 (23:05):** migration thật + verifier + NL intake:
- Backup `tasks.db` trước (578 records nguyên vẹn) → **ADD COLUMN an toàn +11 cột** (priority/deadline/parent/dependencies/required_tools/assigned_agents/permission_scope...)
- Bảng **`task_transitions`** (actor/time/reason/evidence — audit đầy đủ) + **+10 TaskStatus** (nhóm intake RECEIVED→UNDERSTANDING…, kết thúc COMPLETED_VERIFIED/PARTIALLY/UNVERIFIED/EXPIRED)
- **TaskVerifier fail-honest**: không bao giờ tự phong COMPLETED_VERIFIED khi không có bằng chứng
- **Work Queue** ORDER BY priority 4 bậc; **`nl_intake.py`** 172 dòng — nhận goal tiếng Việt, parse deadline giờ VN +07 ("5 chiều"=17:00; đã qua → mai 17:00)
- 3 API mới trên server (intake/transition-log/work-queue); watchdog thêm `check_task_deadlines()`
- Tests mới: 23 (lifecycle) + 14 (NL intake) = **37/37**; backbone 64/64; regression FULL 3.071/0

### 2.6. Rà soát việc dang dở + Q-1/Q-2/Q-5 ✅ (23:10) — blanket approval 01/11
- **Q-1 GIT ✅**: workspace thành git repo — `.gitignore` 59 dòng (secrets/DB/venv/cache), verify IGNORED (edge_hmac_secret, .env, brain.db), secret scan sạch, commit `e75d240` **1.692 files**. `Skill/SKILL_BAT_AI` (gitlink hệ thống anh em) assume-unchanged — không đụng
- **Q-2 JOURNALD PERSISTENT ✅ (Pi5)**: root cause là vendor conf Raspberry Pi (`40-rpi-volatile-storage.conf`) ép volatile → mask + drop-in `/etc/systemd/journald.conf.d/99-persistent.conf` → `/var/log/journal` **57MB** — chứng cứ reboot lạ 31/10 giờ được giữ
- **Q-5 BT POWER-SAVE ✅ (Pi5)**: FastConnectable=true + AutoEnable=true (main.conf persist) + `bluetoothctl power on`; SRS-XB33 giữ TẮT theo owner-ACK
- quarantined 2.646: ghi nhận by design, đợi lô promote kế qua verifier Q-4

### 2.7. GIT CONVENTIONAL-COMMITS + PR ✅ (theo yêu cầu owner)
- 5 commits chuẩn conventional trên nhánh `feat/deom-m1-m2-task-lifecycle`:
  1. `e75d240` — initial tracked state (Q-1)
  2. `9386a9d` — feat(orchestration): DEOM M2 task lifecycle
  3. `02cfa0d` — docs(status): Q-1/Q-2/Q-5 + M1/M2
  4. `7c0b5f0` — docs(pr): PR description
  5. `0bc7891` + `33462d9` — feat(setup) ONECLICK + docs(setup) hướng dẫn
- **Chưa push** — máy không có credential git host nào (SSH publickey denied, GCM non-interactive fail, 0 vault credentials, git.viettel.com.vn 000). Owner đã chọn phương án **commit cục bộ**; khi có repo + PAT/SSH key → push + mở PR trong 1 phút (mô tả PR sẵn tại `reports/PR_DESCRIPTION_DEOM_M1_M2.md`)

### 2.8. ONE-CLICK CHUYỂN MÁY ✅ (00:00) — F:\BRAIN sẵn sàng làm "hộp di động"
- **`ONECLICK_SETUP_NEW_PC.bat`** — 8 bước tự cài trên máy mới: tìm Python 3.11 (winget fallback) → venv mới → deps → kiểm .env (không in secret) → SSH key → Ollama+models → 54 test sức khỏe → start scripts
- **E2E thật**: 7 PASS / 1 WARN (thiếu .env folder giả — đúng thiết kế) / 0 FAIL; trên đường làm bắt & sửa 4 bug cmd kinh điển
- **Mirror F FIX**: robocopy rc bit3 (extras dọn thừa-đích) là hành vi /MIR bình thường — trước đây false-alarm; giờ chỉ FAILED>0 mới là lỗi
- **F:\BRAIN đồng bộ 100%**: 14.939 file / 5,67 GB, SHA-256 từng nhóm khớp, 2 DB snapshot, 37/37 test chạy OK ngay trên mirror
- Hướng dẫn: `docs/ONECLICK_HUONGDAN.md` — 3 việc anh làm tay: Tailscale login, chép SSH key, dán NETMIND_API_KEY nếu WARN

---

## 3. KIẾN TRÚC HIỆN TẠI (điểm khác so báo cáo 12:30)

### 3.1. Nền tảng mới thêm (màu xanh = mới phiên này)
| Thành phần | File chính | Vai trò |
|---|---|---|
| 🟢 **LLM Fallback Chain** | `src/quan_ai_brain/llm/provider.py` | 8 bậc dự phòng local, cả generate + stream |
| 🟢 **Task Lifecycle DEOM M2** | `src/quan_ai_brain/orchestration/{models,task_registry,plan_orchestrator,nl_intake}.py` | Schema +11 cột, transitions audit, verifier fail-honest, queue priority, NL tiếng Việt |
| 🟢 **3 API quản trị task** | `src/quan_ai_brain/web/server.py` | intake / transition-log / work-queue |
| 🟢 **Watchdog deadline guard** | `tools/watchdog.py` | `check_task_deadlines()` → EXPIRED chuẩn, fail-honest |
| 🟢 **Git repo + conventional commits** | `.git/` | 5 commits, .gitignore chặn secrets/DB, branch feature chuẩn PR |
| 🟢 **ONE-CLICK bootstrap** | `ONECLICK_SETUP_NEW_PC.bat` + `docs/ONECLICK_HUONGDAN.md` | Chuyển máy 1 click, 8 bước tự cài + tự kiểm |
| 🟢 **Mirror F v2 (rc-fix)** | `tools/mirror_workspace_to_f.py` | Nhận đúng bitmask robocopy; verify 2 lớp + SHA-256 |

### 3.2. Giữ nguyên từ báo cáo 12:30 (tóm tắt)
- **Tầng não PC**: Server 8766 (GLM-5.3-Flash + fallback mới) + Dashboard 8765 + Responder NetChat (poll 2s, catch-up 12h) + Command Center ~30 intent + Voice STT faster-whisper + Watchdog 3 lớp + Learning daemon
- **Tầng giao tiếp**: DM NetChat duy nhất bot↔anh, chữ/giọng/ảnh/file, phản hồi ~2s, không mất tin
- **Tầng hình thể Pi5**: kiosk avatar + wake word 4 cụm + thoại 2 chiều + camera + TTS đa ngữ (Piper vi_VN local từ Q-3) + HDMI phê duyệt + nút STOP an toàn

---

## 4. ĐÁNH GIÁ ĐỊNH KỲ CẬP NHẬT

| Trục | Báo cáo 12:30 | Hiện tại 02:11 | Đánh giá |
|---|---|---|---|
| Nghe/Nói/Nhìn/Hiển thị | Đạt | Giữ nguyên + Screenshot Pi5 chuẩn yêu cầu | ✅ |
| Kênh lệnh DM | Đạt | + VN-LANG chuẩn hóa toàn bộ | ✅ |
| **Não LLM** | 1 model GLM (đứt = chết) | **Chain 8 bậc tự fallback** | ✅ **Đạt mới** |
| **Task/Governance** | tasks thô, không audit | **Lifecycle DEOM M2 + transitions + verifier fail-honest** | ✅ **Đạt mới** |
| **Provenance** | metadata rò vào lời nói | Strip sạch (PROV-CLEAN) | ✅ **Đạt mới** |
| **Version control** | Không có | Git repo + 5 commits conventional + PR-ready | ✅ **Đạt mới** |
| **Chuyển máy** | Không có (5,2GB thủ công) | **ONE-CLICK 8 bước E2E 7 PASS** | ✅ **Đạt mới** |
| **Mirror F** | rc=9 false-alarm | Fix + verify 100% (14.939 file) | ✅ **Đạt mới** |
| Ổn định 24/7 | Watchdog 3 lớp | Giữ nguyên + journald persistent (chứng cứ reboot) | ✅ |
| An toàn R4/R5 | Chờ cấu hình verifier | Giữ nguyên; quarantined by design | 🟡 |

---

## 5. VIỆC DANG DỞ & LỘ TRÌNH (sau 02:11)

### 5.1. Chờ owner quyết/cung cấp
1. **AUDIO Pi5** — cần mua USB sound card + mic (em không thể tự làm)
2. **Push + PR git** — cần repo remote + PAT/SSH key; mọi thứ sẵn sàng 5 commits
3. **R4 approval_verifier cấu hình** — mở khóa 2.646 quarantined (đã có verifier fail-closed từ Q-4)

### 5.2. DEOM lộ trình (M0-M2 ✅ → còn 5 mốc)
| Milestone | Nội dung chính | Ước lượng |
|---|---|---|
| **M3 (tiếp theo, đề xuất)** | Agent Dispatcher + Dependency Manager: chọn agent theo năng lực kiểm chứng + workload + quyền; chống lệnh trái ngược; correlation ID; queue 4 bậc + 6 quy tắc ưu tiên DEOM §7.2 | 1 phiên |
| M4 | Permission Resolver hợp nhất (13 quyền × vai trò, nối RBAC + policy.py) + Approval Workflow đủ 12 trường §5.3, backend-enforced separation | 1–2 phiên |
| M5 | Task Decomposition tự động từ goal tiếng Việt (planner tự phân rã, không cần plan submit sẵn) | 1 phiên |
| M6 | Recurring task engine (định kỳ, deadline-driven) trong registry + Scheduler | 1 phiên |
| M7 | Voice/embodiment hoàn chỉnh + multi-agent | Sau AUDIO |

### 5.3. Việc nhỏ treo (không gấp)
- CriticalThinker: module có sẵn, chưa wire vào server/cognitive_loop (gộp được vào M3)
- Pi5 reboot 31/10 20:32 chưa rõ nguyên nhân (nghi nguồn 5V) — journald persistent giờ giữ chứng cứ nếu lặp lại
- Reply-thread NetChat: đợi gateway hỗ trợ root_id (đang dùng prefix trích dẫn, hoạt động tốt)

---

## 6. MINH BỘCH KIỂM CHỨNG (bằng chứng E2E phiên này)

| Hạng mục | Bằng chứng |
|---|---|
| LLM-FALLBACK | E2E 4 kịch bản + provider 46/46 + regression FULL 3.034/0 + stream E2E qua server thật |
| DEOM M2 | tests 37/37 + backbone 64/64 + FULL 3.071/0 (`reports/test_run_m2_full3.log`) + 578 records nguyên vẹn sau migration |
| Git | `git log` 5 commits + secret scan sạch + verify IGNORED secrets |
| Q-2 | `/var/log/journal` 57MB trên Pi5 (SSH) |
| Q-5 | bluetoothctl FastConnectable=true + main.conf persist |
| ONECLICK | Chạy thật folder giả: 7 PASS/0 FAIL, log `reports/ONECLICK_SETUP_LOG.txt` (trên folder test) |
| Mirror F | VERIFY-1 PASS + VERIFY-2 PASS + SHA-256 khớp (`logs/mirror_to_f.log` 23:59) |
| VN-LANG | 6 test asserts chuẩn hóa |
| PI5-SHOT | ảnh kiosk 291KB đúng màn TFT |

**Phương pháp:** Fail-honest tuyệt đối — mọi ✅ đều chạy thật, không có mục "đã code = đã xong".

---

*Báo cáo do TONY lập tự động lúc 02:11 ngày 02/11/2026 — dựa trên git log, DB thật, log regression, SSH Pi5, và bằng chứng E2E trong phiên. Báo cáo 12:30 ngày 01/11 là tiền đề trực tiếp.*
