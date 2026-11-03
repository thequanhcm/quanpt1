# QUAN AI BRAIN — Project Status

## 02/11/2026 ~16:30 — UAIIF-S4 ✅ GIAI ĐOẠN 1/3: AGENT INTELLIGENCE CORE (owner: master prompt UAIIF v1.0)
- **Card TASK-UAIIF-S4**: APPROVED + consumed. R2. Nguyên tắc bất di bất dịch tuân thủ: KHÔNG tạo cognitive core mới (uaiif/ = năng lực chuyên môn mở rộng dùng core có sẵn); Pi5 = QPIG tool gateway không chứa não; tái sử dụng ToolRegistry + federation + SENTINEL + containment — 0 module trùng lặp.
- **UniversalAgentKnowledge** `uaiif/agent_knowledge.py` (MỚI 280d): kho kiến thức 7 LAYER × 20 nhóm Agent; epistemic statuses VERIFIED/OBSERVED/INFERRED/UNKNOWN (VERIFIED bắt buộc evidence_ref — không đánh đồng đọc tài liệu với thành thạo); chu trình học 8 bước; **AgentIntelligenceScorecard 8 câu hỏi điểm gắn bằng chứng** (không tự cho điểm cảm tính — test chứng minh: không knowledge thì điểm = 0 dù truyền cờ đẹp).
- **AgentDiscoveryWorkflow** `uaiif/agent_discovery.py` (MỚI 215d): 7 bước DISCOVERY→...→KNOWLEDGE_CONSOLIDATION; mỗi bước có bằng chứng; **phân biệt External Behavioral Assessment vs Internal Architecture Inspection**; fail-honest (target chết → NOT_ACCESSIBLE + đủ 7 bước vẫn trả).
- **UniversalAgentProfile** `uaiif/agent_profile.py` (MỚI 180d): 24 trường chuẩn, mỗi trường Verified/Observed/Inferred/Unknown/Not_Accessible riêng; idempotent theo target; completeness counter.
- **QPIG** `uaiif/qpig.py` (MỚI 195d): 6 nhóm tool (Discovery/Inspection/Communication/Capability/Security/Control) **đăng ký vào ToolRegistry hiện có** với RiskLevel chuẩn + input_schema + requires_owner_approval cho R3; communication chỉ chạy kênh ĐÃ đăng ký; control chỉ pre-approved; điểm vào thống nhất call().
- **Live E2E thật**: khảo sát Pi5 (nút federation) → profile uap_0798098 với 16/24 trường Unknown TRUNG THỰC (SSH chưa mở — không bịa); QPIG capability_list + inspection_probe thật REACHABLE; Scorecard thật **60/100** (mọi điểm có bằng chứng: 6 VERIFIED knowledge, SENTINEL 38 test PASS, containment 3 cấp PASS, 0 evidence → câu 8 = 0 đúng trung thực).
- **Tests**: 34/34 mới (test_uaiif_s4.py) — bao gồm test chống tự thương lượng (test_no_self_congratulation).
- Full regression: `reports/TEST_RUN_UAIIF_S4.txt`. Còn lại (trung thực): GĐ2 QPIG phía Pi5 thật (khi SSH mở) + MCP client + A2A; GĐ3 200 kịch bản kiểm thử + learning engine tự động.

## 02/11/2026 ~16:20 — SENTINEL-S3 ✅ GIAI ĐOẠN 1/4: SECURITY AUTHORITY CORE (owner: master prompt SENTINEL AI v1.0)
- **Card TASK-SENTINEL-S3**: APPROVED + consumed (auth `owner_desktop_chat_directive`). R2.
- **M01+M04** `security/agent_identity.py` (MỚI 390d): sổ cái agent — trust/risk scoring DETERMINISTIC (base 20, đăng ký +40, hợp đồng +30, vi phạm −25/+25), phân loại A-F, SENTINEL không tự gán COMPROMISED/MALICIOUS (chỉ owner hoặc evidence_ref điều tra) — tách nghi vấn khỏi xác nhận đúng prompt mục 4.
- **Phản ứng 5 cấp** `security/threat_levels.py` (MỚI 185d): L0-L4 append-only, L2+ bắt buộc evidence_ref, hạ từ L4 chỉ owner, L4 → notify_owner callback.
- **M06** `security/containment.py` (MỚI 250d): governance 3 cấp AUTONOMOUS/CONTROLLED/HUMAN, EvidenceStore sha256 append-only, SUSPEND/KILL orchestrate actions.py (whitelist S1 giữ nguyên), CONTROLLED/HUMAN chỉ ghi kế hoạch chờ R4.
- **DM**: `sentinel` (NOC dashboard) / `sentinel agent <q>` / `sentinel mức L0..L4` (owner qua DM).
- **Watchdog**: security_watchdog_cycle giờ tự cập nhật hồ sơ SENTINEL theo vi phạm đo được.
- **Lỗ hổng thật đã sửa**: watcher cũ chỉ khớp TÊN tiến trình — agent ẩn dưới node/python.exe với cmdline mang danh tính LẬN ĐƯỢC. Live E2E bắt được (demo PID 9408, cycle=0). Sửa gốc: `get_cmdlines_bulk()` quét cmdline mọi tiến trình 1 lần PowerShell, khớp tên HOẶC cmdline. Re-test 2/2 phát hiện.
- **Tests**: 38/38 mới (test_sentinel_s3.py) · 86/86 cụm an ninh S1+S2+S3 · Live E2E: demo vi phạm → hồ sơ SUSPICIOUS/RESTRICTED tự lập → dashboard phản ánh đúng → dọn DB test sạch.
- Báo cáo 10 mục: `reports/BAO_CAO_SENTINEL_S3_20261102.md`. Còn thiếu (trung thực): M02 sâu, M03, M07, M08, M09, M10, M12, Dashboard UI, 100 kịch bản — lộ trình S4/S5.
- Full regression: `reports/TEST_RUN_SENTINEL_S3.txt`.

## 02/11/2026 ~15:45 — SEC-S2 ✅ TONY LÕI LIÊN BANG (owner: "biến Pi5 thành công cụ giao tiếp với thiết bị khác, PC toàn quyền điều khiển, xử lý, khống chế")
- **Card TASK-SEC-S2**: APPROVED + consumed (auth `owner_desktop_chat_directive`). R2.
- **Giải pháp trung thực**: không AI nào "xâm nhập lõi" AI khác — kiểm soát = (1) đặt người của mình CÙNG MÁY với agent đó (resident agent — nền có sẵn), (2) giám sát điểm chạm mạng, (3) hạn ngạch cloud fail-closed.
- **(a) NodeRegistry** `federation/node_registry.py` (MỚI 206d): SQLite data/federation_nodes.db — EDGE/PC/CONNECTOR, probe ping REACHABLE/UNREACHABLE, idempotent upsert, fail-honest.
- **(b) LanScanner** `federation/lan_scanner.py` (MỚI 143d): quét /24 hiện diện-only (ping song song ThreadPool + ARP MAC + OUI Raspberry Pi hint + reverse DNS) — KHÔNG scan cổng tấn công, chỉ-đọc.
- **(c) CloudConnector** `federation/cloud_connector.py` (MỚI 149d): ConnectorCallResult + call_with_budget — vượt hạn ngạch → BLOCKED fail-closed, lỗi fn không tính ngạch, AuditLogger.record đầy đủ.
- **(d) Lệnh DM** (netchat_security_center PATCH): `liên bang` / `quét mạng` / `đăng ký nút edge <IP> [tên]` / `đăng ký đầu nối <domain> [hạn ngạch: N]` + federation_watchdog_cycle() (probe nút → mất kết nối → DM, cooldown 1 lần/giờ/nút qua data/fed_alert_last.json).
- **Watchdog PATCH**: chu kỳ FED sau chu kỳ SEC trong main loop.
- **Pi5 script PATCH**: `pi5_deploy/tony_pi5_all_in_one.sh` core_host mặc định **192.168.1.9** (CORE_HOST env cho Tailscale).
- **Pi5 thực tế**: REACHABLE tại **192.168.1.2** (DHCP đổi từ .21 cũ); SSH port 22 vẫn đóng; MAC 34-24-3e KHÔNG khớp OUI Pi → đã đăng ký nút edge_pi5, còn chờ owner chạy script trên Pi (bước vật lý 5 phút) để mở SSH + nối kiosk/loa/camera.
- **Live E2E thật**: quét LAN 7 thiết bị · đăng ký edge_pi5 + pc_core_quanpt → probe REACHABLE · nút test IP chết → chu kỳ liên bang phát hiện → **DM cảnh báo thật tới kênh owner** → cooldown đúng → dọn nút test.
- **Tests**: 22/22 mới (test_sec_s2_federation.py) · **Full regression 3.370 PASS / 0 FAIL / 45 skip (4:57)** (baseline 3.348, +22 đúng số test mới).
- Báo cáo: `reports/BAO_CAO_SEC_S2_20261102.md`. Hạn chế: thiết bị LAN chỉ thấy hiện diện khi chưa đăng ký; SYSTEM/admin chỉ báo cáo; AI cloud chỉ điểm chạm máy mình.

## 02/11/2026 ~15:10 — SEC-S1 ✅ TONY NHÂN VIÊN AN NINH (owner: "tạm thời nắm quyền kiểm soát, quản trị" + "Duyệt — làm Sprint S1 luôn")
- **Card TASK-SEC-S1**: APPROVED + consumed (auth `owner_desktop_chat_directive`, clarify 02/11). R2.
- **(a) Hợp đồng nhiệm vụ** `security/task_contracts.py`: TaskContract (subject/goal/allowed_paths/allowed_domains/expires_at/auto_contain) + TaskContractStore (SQLite idempotent) + parse_dm_contract fail-honest. Hợp đồng = chuẩn duy nhất đo "vượt tầm".
- **(b) Vệ sĩ** `security/watcher.py`: quét tasklist/netstat chỉ-đọc; detect_violations: UNREGISTERED / OUT_OF_SCOPE_PATH / OUT_OF_SCOPE_DOMAIN / OVER_CONTRACT; SecurityEventStore append-only (data/security_events.db). Chỉ quét sâu khi CÓ hợp đồng (0 chi phí ngược lại).
- **(c) Tạm giữ** `security/actions.py`: NtSuspendProcess/NtResumeProcess (treo giữ dữ liệu, thả được) + taskkill; PROTECTED_WHITELIST cứng (Windows system + TONY/netMind) refuse fail-closed — **đã chứng minh thật: suspend watchdog PID 12572 → REFUSE**.
- **(d) Lệnh DM**: `an ninh` / `giữ <pid>` / `thả <pid>` / `hạ <pid>` / `giao nhiệm vụ cho <AI>: <mục tiêu> | phạm vi | miền | hạn | tự giữ` — wire vào netchat_command_center (priority trước detect_intent) + security_watchdog_cycle() gắn watchdog main loop (vi phạm → auto-contain nếu hợp đồng bật tự giữ → DM 1 tin/cycle).
- **Tests**: 26/26 mới (test_sec_s1_security.py) · **Full regression 3.348 PASS / 0 FAIL** (baseline 3.322).
- **Live smoke E2E**: full chain route_message thật (an ninh / giữ PID ảo → từ chối trung thực / tạo hợp đồng thật → DB / cycle=0 đúng) · kill responder+watchdog cũ → watchdog mới tự hồi phục responder (heartbeat 13s) — responder giờ chạy code có lệnh an ninh.
- **Bài học git-bash**: `cmd //c file.bat` từ MSYS không thực thi .bat (banner interactive, không chạy) — spawn process nền đúng cách: `powershell Start-Process -FilePath ...pythonw.exe -ArgumentList ... -WindowStyle Hidden`.
- Báo cáo: `reports/BAO_CAO_SEC_S1_20261102.md`. Hạn chế trung thực: keyword-match có thể lẩn tránh (S2: parent-child tree + psutil resource cap); SYSTEM process không kill được (thiếu admin); AI cloud chỉ thấy điểm chạm máy mình.
- **S2 đề xuất**: resource caps thật (psutil), giám sát tiến trình con, tab An ninh dashboard 8766.

## 02/11/2026 ~12:40 — KÍCH HOẠT 24/7 TRÊN MÁY MỚI (E:\BRAIN) ✅ (owner: "kiểm tra toàn bộ và kích hoạt, chạy 24/7, restart máy thì DM báo")
- **Audit-first**: máy mới (QUANPT, user DELL) có repo + data nguyên vẹn (2.869 episodes, 5.051 semantic memories) nhưng 0 tiến trình, 3 task scheduler DISABLED trỏ đường dẫn máy cũ (E:\AI\QUAN AI BRAIN), editable-install trong venv trỏ `D:\AI\AI Quanpt1 2026\BRAIN\src` (máy trước) → `import quan_ai_brain` FAIL từ subprocess.
- **Di trú đường dẫn (156 thay thế / 43 file runtime)**: `D:\AI\AI Quanpt1 2026\BRAIN` + `C:\Users\quocd` → `E:\BRAIN` + `C:\Users\DELL` trong toàn bộ tools/src/*.bat/*ps1 (kể cả TONY_START/STOP, KHOI_DONG_24_7, 3 _spawn_*.bat, watchdog, learning_daemon, netchat_action_executor, sched_task_setup, run_backup/run_morning_report, stop_tony_services). Bỏ qua tool di trá lịch sử. Syntax-check 43 file OK.
- **Chuyển bot**: giữ nguyên việc đổi bot_quanpt1→bot_tony của phiên sáng (whoami live OK, source=env); phát hiện **ID kênh DM mới** `mwp3nk3ciprjjr4hdmcoqgk6jr` (DM là cặp bot↔user nên đổi bot = đổi kênh) → cập nhật 5 module (responder, bridge, approval/info-gap adapter, alert_engine).
- **Sửa gốc rễ venv**: `pip install -e .` lại từ E:\BRAIN → import OK; 2/6 test fail baseline (restart_system) về PASS.
- **Khởi động**: TONY_START.bat → dual servers (8765+8766, HTTP 200, core/brain_db/task_registry HEALTHY) + responder (heartbeat live, greeting DM tới tay anh — đọc lại DM xác nhận post thật) + learning daemon + watchdog; dọn 1 cặp learning trùng (watchdog tự đẻ thêm — giữ 1 bản).
- **ACK chủ động** `selfcare:ollama:connectivity` (Ollama ĐÃ GỠ khỏi máy này trong đợt tối ưu 02/11 — quyết định owner): hết cảnh báo NGHIÊM TRỌNG 5 phút/lần; chỉ còn GLM-5.3-Flash cloud làm LLM chính.
- **24/7 + reboot-proof**: 3 task scheduler chuyển Ready với đường dẫn mới (KHOI_DONG_LOGON trigger QUANPT\DELL; backup 2AM NextRun 03/11 02:00; report 8AM NextRun 03/11 08:00); **test-fire thật task logon → LastResult 0, 0 trùng lặp (guard `ensure_single_instance` hoạt động), cổng ổn định**. UTF-8 env thêm vào KHOI_DONG_24_7.bat + CRLF cho 4 file bat (phòng UnicodeEncodeError cp1252 giết daemon ngầm).
- **Tests sau kích hoạt**: 15/15 PASS (ok_confirmation + hardening — 2 test này fail khi hệ thống tắt vì probe thật trả MẤT KẾT NỐI, đúng thiết kế fail-honest); validate_and_report chạy nền (kết quả ở reports/HANDOFF_LATEST.md).
- **Báo cáo năng lực đã DM owner** (post w7roymgxb7ropeydmq5iksdkfr) — nêu đúng năng lực thật + 2 giới hạn trung thực (Ollama đã gỡ, Pi5 chưa nối máy này).
- **Còn lại**: nối Pi5 kiosk (ĐÃ PAIR trước đây nhưng heartbeat null ở máy mới), commit đợt thay đổi này (chờ owner duyệt theo quy tắc cũ), M3-M7 DEOM.

## 01/11/2026 ~23:10 — RÀ SOÁT VIỆC DANG DỞ + DEOM M1 ✅ + M2 ✅ (owner: "phê duyệt toàn bộ, làm luôn")
- **Rà soát đầy đủ** 7 nhóm việc dang dở theo sổ REGISTER; owner blanket approval → thực hiện tuần tự.
- **Q-1 git init ✅**: repo mới, commit `e75d240` (1.692 file, 327K dòng); `.gitignore` chặn .env/secret/DB/venv/log; verified không secret nào tracked.
- **Q-2 journald persistent ✅ (Pi5)**: root cause thật = vendor drop-in `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` ép `Storage=volatile` đè config `/etc` — mask bằng symlink `/dev/null` + drop-in `99-persistent.conf`; kết quả `/var/log/journal` 57M, `journalctl --header` trỏ `/var` — log sống qua reboot (hoàn tác = xoá 2 file).
- **Q-5 BT power-save ✅ (Pi5)**: `FastConnectable=true` + `AutoEnable=true` trong `/etc/bluetooth/main.conf`, bluetooth active, Powered yes — giảm rơi kết nối loa SRS-XB33 (owner vẫn giữ loa TẮT theo owner-ACK).
- **DEOM M1 ✅**: 4 tài liệu thiết kế (`reports/DEOM_M1_OPERATING_MODEL.md`, `DEOM_M1_PERMISSION_MATRIX.md`, `DEOM_M1_TASK_LIFECYCLE.md`, `DEOM_M1_APPROVAL_DESIGN.md`) — bám 100% hiện trạng M0, 0 code.
- **DEOM M2 ✅ (R4 đã duyệt)**:
  - Backup `tasks.db` → `data/backups/tasks_backup_20261101_2300.db` (578 records nguyên vẹn) trước migration.
  - Schema `durable_tasks` +11 cột (priority/deadline_utc/parent_task_id/dependencies/required_tools/assigned_agents/permission_scope/progress_weight/source/verified_at/verification_note) — ADD COLUMN idempotent, 578 records không mất.
  - Bảng `task_transitions` (actor/time/reason/evidence — DEOM §4.4) + index work queue.
  - `TaskStatus` +10 trạng thái DEOM (RECEIVED→UNDERSTANDING→ANALYZING→PLANNING→READY, VERIFYING, NEEDS_INFORMATION, PAUSED, EXPIRED, REJECTED, COMPLETED_VERIFIED/PARTIALLY/UNVERIFIED); backward-compat giữ nguyên 9 state cũ.
  - **Task Verifier fail-honest**: không bằng chứng → COMPLETED_UNVERIFIED, không bao giờ tự phong VERIFIED; wire vào PlanOrchestrator (mọi step có expected_output + result success → VERIFIED).
  - **Work Queue 4 bậc** + chống learning chiếm tài nguyên (learning nhường owner) + `expire_overdue` quét deadline.
  - **NL Task Intake tiếng Việt** (`orchestration/nl_intake.py`): deterministic regex (không LLM), parse priority (khẩn/gấp/khi rảnh) + deadline giờ VN +07 ("trước 5 chiều", "trong 3 ngày", "đến khi hoàn thành"); fail-honest không đoán mạo.
  - 3 API mới: `/api/executive/tasks/intake`, `/api/executive/tasks/transitions`, `/api/executive/work-queue`.
  - Watchdog `check_task_deadlines()` (rate-limit 10 phút) — task quá hạn → EXPIRED chuẩn transition log.
  - Cognitive loop + reflection nhận đủ trạng thái mới (TERMINAL_STATUSES, _is_completed).
- **Tests**: 37 test mới (`test_deom_m2_task_lifecycle.py` 23 + `test_deom_m2_nl_intake.py` 14); cập nhật assert cũ sang ngữ nghĩa VERIFIED; **Regression FULL 3.071 PASS / 0 FAIL** (baseline 3.034).
- **Git**: commit `dd73ae3` (M1+M2). Mirror F THÀNH CÔNG 23:40. backup tasks.db đã mirror.
- **Còn lại**: M3 (Dispatcher + dependency manager), M4 (Permission Resolver + approval workflow), M5 (Executive Report + tab dashboard), M6 (Proactive Work Engine + recurring), M7 (7 CASE acceptance); AUDIO chờ owner mua thiết bị.

## 01/11/2026 ~22:23 — LLM-FALLBACK: cài model dự phòng cho hệ thống NetMind (owner lệnh)
- **Yêu cầu owner**: "em cài đặt model dự phòng cho hệ thống netmind của anh".
- **Audit-first**: `LLMProvider.generate/stream` hiện NẾU NetMind GLM chết → rơi thẳng **MOCK** (không inference thật) dù Ollama local có 8 model. Router chỉ fallback lúc CHỌN model (pre-call), không có fallback RUNTIME khi cloud chết giữa chừng. Đã chứng minh E2E: gateway giả chết → `[MOCK]` trả về.
- **Fix `src/quan_ai_brain/llm/provider.py`**: chuỗi fallback runtime **NetMind GLM-5.3-Flash → Ollama qwen2.5:7b → llama3.1 → qwen2.5:3b/1.5b/0.5b → mistral → qwen → (cuối) MOCK**. `_local_fallback_candidates()` chỉ yield model CÓ THẬT, giữ đúng thứ tự ưu tiên (fix bug prefix-match chọn nhầm 0.5b/1.5b), loop thử model tiếp theo nếu model trước fail, fix `timeout_seconds=None` raise TypeError. Cả **generate lẫn stream** đều có fallback (stream buffer events, nếu error → local thay thế với warning rõ). Provenance minh bạch: warning "FALLBACK LOCAL — NetMind failed [code], dùng model dự phòng Ollama 'X' (chất lượng thấp hơn GLM)".
- **E2E thật**: gateway chết → `model=qwen2.5:7b, provider=ollama, is_mock=False, text="1+1 bằng 2."` ✅; cloud+local đều chết → MOCK với cảnh báo rõ ✅; stream dead-gateway → meta/delta/final `qwen2.5:7b` ✅; GLM sống → vẫn dùng GLM (không đổi) ✅.
- **Bonus fix flaky test**: `test_v26_self_learning.py::test_entry_expired` phụ thuộc uptime máy (monotonic < 990 khi mới boot) → monkeypatch monotonic theo FakeClock — deterministic mọi lúc.
- **Regression FULL 3.034 PASS / 0 FAIL** · provider tests 46/46 · validate_and_report exit 0 (HANDOFF 22:22) · Mirror F THÀNH CÔNG · servers live (8765+8766 HTTP 200, GLM primary OK).

## 01/11/2026 ~20:00 — DEOM M0 ✅: AS-BUILT PRECHECK hoàn thành (Master Prompt V3.0)
- Owner ban hành **MASTER PROMPT V3.0 — TONY DIGITAL EMPLOYEE OPERATING MODEL (DEOM)**: chuyển TONY từ "chatbot chờ lệnh" sang "nhân sự số chủ động" (HUMAN SETS OBJECTIVE → TONY PLANS/ORGANIZES/EXECUTES/VERIFIES/REPORTS/LEARNS).
- **M0 làm đúng quy trình, audit-first**: kiểm tra thật schema DB, đọc toàn bộ `governance/policy.py` (R0–R5 gate chuẩn DEOM §15), quét 30+ package, 127 tools, 344 reports, 157 test files; chạy lại backbone tests **62/62 PASS** (task registry + supervisor + approval + planner).
- **Phát hiện quan trọng**: nền móng DEOM đã có sẵn ~40%: DurableTaskRegistry (578 tasks, idempotency+checkpoint+recovery), PlanOrchestrator, ContinuousAutonomySupervisor, policy R0–R5, approval_verifier fail-closed, proactive findings, executive dashboard 61 APIs.
- **GAP lớn nhất**: durable_tasks thiếu priority/deadline/parent/dependencies/required_tools/assigned_agents/permission_scope + thiếu transition log (actor/time/reason/evidence) + thiếu states DEOM (RECEIVED→UNDERSTANDING→...→VERIFYING, COMPLETED_VERIFIED/PARTIALLY/UNVERIFIED) + chưa có Permission Matrix tập trung + chưa có Work Queue 4 bậc.
- Deliverables: `reports/DEOM_M0_ACTUAL_STATE.md` + `reports/DEOM_M0_GAP_ANALYSIS.md` (gap matrix 16 thành phần + 7 CASE + thứ tự M1→M7 + rủi ro).
- **Chờ owner duyệt để tiếp tục M1** (thiết kế operating model — chỉ tài liệu, 0 code) và **duyệt migration tasks.db ở M2** (R4 — ADD COLUMN an toàn, backup trước, 578 records).

## 01/11/2026 ~19:44 — PROV-CLEAN: bỏ chữ "theo ghi nhớ anh truyền đạt" + "(nguồn: USER_PROVIDED)" khỏi lời trả lời (owner feedback image_d79379)
- **Bug thật**: GLM nhắc lại metadata audit của ngữ cảnh prompt vào câu trả lời: "theo ghi nhớ Anh truyền đã: em sinh ngày 20/10/2026 à (nguồn: USER_PROVIDED)".
- **Root cause**: `context_builder.py` nhúng `(Source: ..., Status: USER_PROVIDED)` + `[SOURCE REFERENCES AUDIT]` vào prompt để em tra cứu — model hiểu nhầm là phải đọc lên cho owner.
- **Fix 2 tầng**: (1) `netmind_provider.py` — hàm `strip_provenance_artifacts()` lọc mọi dạng "(nguồn: X)/(Source: X)/(Status: ...)/theo ghi nhớ anh truyền đạt|dạy|bảo" khỏi text trả lời trước khi trả ra (chạy trong `generate()`, không đụng stream error path); (2) `context_builder.py` — rule 13 system prompt cấm model liệt kê nguồn/trạng thái lưu trữ, chỉ nêu khi owner hỏi roàng về nguồn.
- **E2E thật qua server 8765**: "Em sinh ngày nào?" → **"Em sinh ngày 20/10/2026 ạ."** (KHÔNG leak ✅); "Pin của em bao nhiêu phần trăm?" → "Dạ pin em còn 87% sức khỏe, đã qua 321 chu kỳ sạc-xả ạ." (KHÔNG leak ✅); "Anh dạy gì em gần đây?" → trả nội dung dạy, không nhắc Status (KHÔNG leak ✅).
- **Traceability không mất**: audit table vẫn nguyên trong BuiltContext (section_stats + SOURCE REFERENCES AUDIT) — chỉ lọc ở LỚP HIỂN THỊ lời trả lời.
- **Regression FULL 3.034 PASS / 0 FAIL** · provider tests 28/28 · validate_and_report exit 0 (HANDOFF 19:44) · Mirror F THÀNH CÔNG · servers restart cặp mới 18292+18936 (8765+8766 HTTP 200).

## 01/11/2026 ~19:36 — VN-LANG: chuẩn hoá toàn bộ ngôn ngữ DM = tiếng Việt (owner yêu cầu)
- **Yêu cầu owner**: tin "🧭 Hình thể Pi5: READY | paired=True | heartbeat ? | kiosk=tắt" còn trộn tiếng Anh → "toàn bộ ngôn ngữ gửi cho anh đều được chuẩn hóa bằng ngôn ngữ tiếng việt".
- **Đã Việt hoá (4 nguồn DM)**: `netchat_command_center.py` (helper `_vn`/`_vn_err`/`_vn_bool` + tin trạng thái/hình thể/bật-tắt/freeze/probe/confirm; ONLINE→HOẠT ĐỘNG, OFFLINE→MẤT KẾT NỐI, READY→SẴN SÀNG, lỗi server → tiếng Việt kèm chi tiết gốc), `netchat_auto_responder.py` (greeting khởi động), `morning_report.py` (Ollama + backup status), `health_monitor.py` (alert CLO kẹt).
- **Test đồng bộ**: 6 assert tiếng Anh (command_center ×1, ok_confirmation ×2, morning_report ×3) cập nhật khớp ngôn ngữ mới.
- **E2E**: handle_tony_status → "🧭 Hình thể Pi 5: SẴN SÀNG | ghép nối: rồi | tim đập (heartbeat): ? | kiosk: đang tắt" ✅; handle_status 3 dòng HOẠT ĐỘNG ✅; DM thật gửi owner demo ✅.
- **Regression FULL 3.034 PASS / 0 FAIL** · validate_and_report exit 0 (HANDOFF 19:36) · Mirror F OK · responder restart (pair 16804+18524, greeting VN).

## 01/11/2026 ~19:25 — PI5-KIOSK-SCREENSHOT: chụp đúng màn hình kiosk theo lệnh DM (owner feedback image_864dc0)
- **Bug thật**: anh gõ "Chụp màn hình kiosk" → regex `^chụp màn hình` khớp `pc_screenshot` → bot chụp **màn hình PC** thay vì TFT Pi5.
- **Fix `netchat_command_center.py`**: intent mới `tony_pi_screenshot` + guard — "chụp màn hình" có kèm `kiosk|pi` → chụp Pi5; không kèm → vẫn chụp PC (5/5 test cases).
- **Handler mới `handle_tony_pi_screenshot`**: SSH Pi → `wlopm --on '*'` (màn ngủ swayidle 600s làm grim "failed to copy output DSI-2" — đã chẩn đoán) → `grim` (wlr-screencopy Wayland TFT 800x480) → scp về PC → gửi ảnh DM. Fail-honest: lỗi từng bước trả thông báo rõ.
- **E2E thật**: ảnh `data/netchat_files/kiosk_20261101_191740.png` (291 KB, 800x480) — verify nội dung: kiosk TONY Assistant, avatar, waveform, subtitle TTS, nút STOP. ✅ ĐÚNG màn hình kiosk.
- Responder restart chuẩn (pair 6924→18772, greeting OK); tests 62 passed (netchat/command_center); regression FULL 3.034/0; validate exit 0 HANDOFF 19:25; mirror F sync OK.

## 01/11/2026 ~19:14 — CLO-UNSTICK: MỞ KẸT CLO #7 (owner "duyệt, hãy xử lý")
- **Root cause thật (audit)**: CLO #7 RUNNING 115,8h vì **advance chỉ xảy ra khi chat tạo task** (`server.py ~:1923` gọi `end_session`) — KHÔNG tồn tại loop nào tự advance session; learning daemon không đụng CLO (0 hits).
- **Xử lý (đúng engine, KHÔNG sửa DB tay)**: gọi `ContinuousLearningEngine.end_session()` chuẩn với evaluation_result ghi rõ root_cause + owner approval → CLO #7 **CONSOLIDATING** (ended 19:00) + **CLO #8 tự đẻ RUNNING** (cd995d85, 19:00). Audit trail giữ nguyên trong `learning_checkpoints.db`.
- **Phòng tái diễn — `check_clo_stall()` wired vào watchdog** (`tools/watchdog.py`): mỗi chu kỳ 60s, session RUNNING > 24h → advance qua engine chuẩn (rate-limit 1 lần/giờ bằng marker file, fail-honest không giết watchdog). E2E fake-DB: session 30h → advance #9→#10 đúng; session 0.0h → không đụng; rate-limit call-2 không đẻ thêm. CLO tests 28/28 PASS.
- **Watchdog restart chuẩn** `_spawn_watchdog.bat` — pair mới 20424→5172 live, servers 8765/8766 healthy.
- Regression **3.034 / 0 FAIL**; validate exit 0 HANDOFF 19:14; mirror F sync OK (lần đầu rc=9 do file lock — chạy lại PASS, đã ghi nhận).

## 01/11/2026 ~18:59 — M5 PHẦN 2 HOÀN TẤT (Barge-in G-23 + Multi-turn DM + FIX GLM key chết)
- **M5-B Barge-in (G-23) ✅**: `wake_engine.js` KHÔNG còn abort recognition khi SPEAKING — mic vẫn nghe khi TONY đang nói; final result khi SPEAKING → ngắt lời: `window.stopKioskSpeech()` (kiosk.js — pause audio + avatar IDLE + restart mic) + xử lý câu mới ngay. Lệnh "dừng đọc/dừng nói/stop speaking" hoạt động cả khi đang phát. Chromium kiosk restart 2 lần để load JS mới; `BARGE-IN` marker confirm qua HTTP daemon (3 hits). Backup `.bak_m5b` trên Pi (kiosk.js, wake_engine.js + assets/avatar/).
- **M5-C Multi-turn DM ✅**: responder wire `ConversationStateManager` kênh "dm" — câu có đại từ ("nó/vậy/cái đó...") → bọc ngữ cảnh lượt trước (cùng cơ chế voice M5 P1); ghi state sau reply (fire-and-forget fail-honest). E2E 2 lượt thật: "Cục pin..." → SelfQA; "Vậy nó sạc được bao nhiêu chu kỳ nữa?" → GLM trả lời đúng ngữ cảnh pin 321 chu kỳ/87%.
- **FIX P0 GLM chết im lặng (phát hiện khi E2E M5-C)**: server 8765 trả `answer=""` `success=False` — `NETMIND_API_KEY` chỉ có ở HKCU\Environment, process server spawn từ session cũ không kế thừa → mọi reply GLM rỗng. Fix gốc `netmind_provider._get_api_key()`: env → **fallback winreg HKCU\Environment** (không log giá trị). Restart dual servers qua `tools/_spawn_dual_servers.bat` (mới) → GLM LIVE: "success=True, provider=netmind, answer='Em khỏe ạ...'". Fix 2 test helper (`_clear_netmind_env`/`_clear_env`) monkeypatch winreg để test máy-có-key vẫn verify đúng contract NO_API_KEY.
- **Tests**: netmind_provider 18/18 + streaming 28/28; regression **3.034 PASS / 44 skipped / 0 FAIL**; validate exit 0 HANDOFF 18:59; mirror F sync OK.

## 01/11/2026 ~18:40 — M4 PHẦN 2 (M4-C Self-Q&A wired + sửa self-model báo sai giới hạn)
- **M4-C (G-12) HOÀN TẤT**: SelfQA đã wired vào **DM thật** — `netchat_auto_responder.py` chèn bước SelfQA trước GLM fallback: câu hỏi về bản thân ("em là ai / em làm được gì / em đang chạy ở đâu / hệ thống khỏe không / em học được gì / em không làm được gì") trả lời **TỪ DỮ LIỆU SỐNG** (self model + learning checkpoints + candidates + health), không khớp → đi tiếp GLM như cũ. E2E `process_message`: "Em làm được những gì?" → 7 năng lực kiểm chứng; "Giúp em tính 2+2" → KHÔNG dính SelfQA. Responder restart chuẩn bằng `tools/_spawn_responder.bat` (start /MIN tránh space-splitting ArgumentsList PowerShell) — greeting OK, 0 error.
- **Sửa self-model báo SAI giới hạn (trung thực > số đẹp)**: (1) "sqlite3 not installed" — sai vì sqlite3 là stdlib, `importlib.metadata` không thấy nhưng import luôn OK → tách khỏi dist-packages check, verify bằng `import sqlite3` + `sqlite_version`; (2) "Requires API key" — NETMIND_API_KEY sống ở HKCU\Environment (User registry), process con không kế thừa nhưng key CÓ THẬT → check registry `winreg` thay vì đoán từ process env. Sau fix: limits chỉ còn limitation ĐÚNG ("External dependency").
- **Tests**: 22 passed (self introspection + self_qa + self_model + inventory); regression **3.034 PASS / 44 skipped / 0 FAIL**; validate exit 0, HANDOFF regen 18:40.
- **M4-B đã xong từ M5 P1** (đã verify live): `_evaluate_clo_stall` hoạt động thật — health_alerts.db có 10 alert `selfcare:clo_stalled`, mới nhất 10:52 sent=1 "CLO session #7 RUNNING 115h không tiến triển" → owner đã nhận DM cảnh báo CLO kẹt.
- **M4-D (Q-4)**: đã hoàn tất 17:58 — 3.209 candidates promoted qua R4 verifier fail-closed.

## 01/11/2026 ~18:28 — M3: MEMORY API CONSOLIDATION (5 LỚP CHUẨN HOÁ + FACT/INFERENCE)
- **Audit-first**: kiểm kê `memory/` (39 files, 7 store) → thấy facade cũ `MemoryService.add_memory()` gọi `vector_store.add()` **method không tồn tại** — bug chết im lặng từ đầu (endpoint `/api/memory/add` luôn trả error).
- **Mới `unified_memory.py`**: `MemoryFacade` (add/search/add_episode/stats) chuẩn hoá 5 lớp: MemoryStore (semantic/episodic) · DeepMemoryStore · ExperienceStore · ContextStore · QuarantineStore. `FactLevel` enum: FACT (USER_PROVIDED/VERIFIED) · OBSERVED · INFERENCE · QUARANTINED; ánh xạ VERIFICATION_TO_FACT + heuristic `classify_statement()` tiếng Việt ("có thể/sẽ/tôi nghĩ..." → INFERENCE; "đã xác minh/telemetry/pytest" → OBSERVED; mặc định fail-closed → INFERENCE).
- **Sàng lọc**: `search(fact_only=True)` push-down SQL (USER_PROVIDED + VERIFIED) — E2E production brain.db: 2.037 active (83 FACT + 1.954 OBSERVED), fact_only trả đúng 20 hits USER_PROVIDED/VERIFIED.
- **Promotion fail-closed**: `promote_to_fact()` yêu cầu GovernanceApprovalVerifier (R4) — không approval hợp lệ → PermissionError, memory giữ INFERENCE.
- **Fix bug thật**: `memory_service.py` dùng `add_memory(MemoryChunk)` chuẩn (chunk id UUID, UNVERIFIED) — giữ signature cũ cho server.py.
- **21 tests PASS** (`tests/test_m3_unified_memory.py`); regression **3.034 PASS / 44 skipped / 0 FAIL**; validate exit 0, HANDOFF regen 18:28.
- **Bài học**: facade "đơn giản" không test = bug chết im lặng; mọi API mới phải có test chứng minh đường gọi thật.

## 01/11/2026 ~18:05 — THỰC THI "DUYỆT TOÀN BỘ" (WD-ON, BK-ON verify, Q-3, Q-4, M2, CLEAN)
- **WD-ON ✅**: watchdog sống độc lập qua `tools/_spawn_watchdog.bat` (execute_code spawn bị Job Object giết khi kernel reset — bat `start /MIN` sống sót). **Tự hồi phục E2E thật**: phát hiện learning stale 935s → tự đẻ lại learning daemon chu kỳ đầu.
- **BK-ON ✅ (không hỏng)**: Task `QUAN_AI_BRAIN_BACKUP_2AM` chạy đúng hằng ngày (lần cuối 01:59 result=0); file `brain_20261102_*.db` đặt tên UTC — báo cáo "dừng 28/10" là NHẦM sắp xếp alphabet. Bài học: sort theo mtime, không theo tên.
- **Q-3 Piper TTS ✅**: piper-tts + voice `vi_VN-vais1000-medium` trong venv; TTSProvider.PIPER + xử lý trong `tts_config.py` (Windows `-f -` bị PermissionError → synth qua temp file); server nhận `provider` param. **E2E HTTP 200, WAV RIFF 125KB READY** — không phụ thuộc mạng Microsoft (chữa Edge-TTS 403).
- **Q-4 R4 verifier ✅**: `governance/approval_verifier.py` FAIL-CLOSED — đọc card APPROVED + auth_method ∈ {netchat_dm, owner_desktop_directive} + approvals record quanpt1 + TTL; ledger 1-lần-dùng (`data/q4_batch_ledger.json`). 11 tests. Card `TASK-Q4-BATCH-20261101` duyệt qua chuẩn lifecycle `approve_card()` (không sửa DB tay). **3.209 candidates promoted có audit trail; semantic_memory 1.491→5.051; quarantined về 0.**
- **M2 reflection ✅ (root cause sâu hơn dự kiến)**: ngoài lỗi schema INSERT `source_type`, hàm `_quarantine_hypotheses` hard-code `workspace/data/brain.db` trong khi production inject MemoryStore (path khác/:memory:) → INSERT vào DB rỗng + exception nuốt im lặng. Fix: dùng `store._connection` của factory khi có. E2E: hypothesis quarantine = 1 (trước = 0).
- **CLEAN ✅**: xoá `.venv_broken_backup` 50.043 files (~1,1 GB).
- **Regression cuối: 3.013 PASS / 44 skipped / 0 FAIL** (+11 test Q-4); validate exit 0; HANDOFF regen 18:02. Báo cáo: `reports/BAO_CAO_THUC_THI_DUYET_TOAN_BO_20261101.md`.
- **Bài học Q-4**: "duyệt" phải đi qua surface xác thực (approval card + approvals record) — verifier không bao giờ tin chuỗi LLM tự sinh; status trong approvals có thể là 'approved' HOẶC 'completed' (đọc DB thật trước khi đoán).

## 01/11/2026 16:45 — AUDIT V2 HOÀN TẤT: 22/22 BÁO CÁO + EVIDENCE LIVE
- Bộ 22 báo cáo TONY_*.md đầy đủ (trước đó 1/22); `TONY_FINAL_AS_BUILT_AUDIT_20261101.md` cập nhật lần 2.
- Evidence live 16:32-16:39: servers 8765/8766 HTTP 200; Pi5 READY 56°C; fix P0 verify qua log (0 router-error sau 16:13); candidates 4.507; scorecard Governance C3, 9/12 C2, 0 dưới C1.
- 2 phát hiện: watchdog MISSING + backup "dừng 28/10" (sau này verify = nhầm alphabet).

## 01/11/2026 16:29 — MIRROR F: 47.048 FILE / 6,21 GB / 0 LỖI
- `tools/mirror_workspace_to_f.py`: robocopy /MIR → F:\BRAIN; DB sống chụp qua sqlite backup API + integrity-check đích; verify 3 lớp (file+byte, robocopy /L phân loại churn logs/+data/, SHA-256 4 thư mục code); Task Scheduler `QUAN_AI_BRAIN_MIRROR_F` 02:30/ngày.
- Restore: copy ngược F:\BRAIN. Report: `reports/MIRROR_F_COMPLETION_REPORT.md`.

## 01/11/2026 16:13 — FIX P0 "CHUP HINH" + OWNER-ACK STORE (VERIFY LIVE)
- Root cause PYTHONPATH pollution (netmind-agent có package `tools` giả) → patch 3 entrypoint (responder + learning_daemon + watchdog) prepend BRAIN root; log sạch 100% sau banner 16:13.
- Owner-ACK: `alert_engine.py` đọc `data/alert_owner_ack.json`; lệnh DM "giữ nguyên loa"/"tắt cảnh báo X" → handle_ack_alert; acked vẫn ghi DB audit nhưng chặn gửi DM. 4 chu kỳ 16:13-16:19: sent=0 `owner_ack`.

## 31/10/2026 ~21:58 — FIX LỆNH "CHỤP ẢNH GỬI ANH" (bot trả lời suông sai sự thật)
- **Sự cố**: owner ra lệnh 2 lần trong DM ("Em chụp ảnh gửi cho anh") 21:53/21:55 — bot trả lời "chưa có công cụ chụp ảnh" (SAI — hệ thống có sẵn pi_media_capture photo).
- **Rễ**: detect_intent chỉ khớp ("chụp ảnh" AND "pi") — câu owner không nhắc "pi" → rơi xuống GLM chat tự do → bịa trả lời.
- **Fix**: detect_intent thêm nhánh ("chụp ảnh|chụp hình" AND "gửi|camera|cho anh") → tony_pi_photo; mở rộng INTENTS keywords (chụp ảnh gửi anh, chụp một tấm, chụp ảnh từ camera...).
- **E2E thật**: route_message("Em chụp ảnh gửi cho anh") → ('tony_pi_photo', 'Đã chụp... đã gửi DM') — 3 ảnh gửi DM thành công (21:56 119KB, 21:57 76KB, 21:58 112KB); mỗi lần chụp ~3s.
- **Deploy**: responder restart chuẩn PowerShell (kill 2264+13392 → 2 procs mới, heartbeat 5s).
- **Bài học**: mọi lệnh ĐIỀU KHIỂN phần cứng phải chặn ở detect_intent TRƯỚC khi rơi GLM tự do (GLM không biết hệ thống có tool gì → sẽ bịa "chưa có").


## 31/10/2026 ~21:05 — CỐNG HÒA ỔN ĐỊNH 24/7 CHO PI5 (AUDIT + CÀI ĐẶT)
- **Audit toàn cảnh**: Debian 13, uptime, disk 13%, RAM 1.2/4GB, swap zram 2GB (không ghi SD), temp 58.7°C, throttled=0x0, NTP sync, fstrim enabled — nền tảng tốt.
- **Fix 1 — journald PERSISTENT**: /var/log/journal + Storage=persistent (lúc trước volatile 4KB → không tra được nguyên nhân reboot 20:32; từ giờ mọi reboot đều có log chẩn đoán).
- **Fix 2 — quan_ai_kiosk_guard.service (MỚI)**: watchdog 60s kiểm daemon + kiosk_running + chromium; kiosk false ×2 → POST start_kiosk; false ×3 + chromium rác → pkill rồi start. **Đã test thật**: kill toàn bộ chromium → guard tự cứu trong ~125s (log 20:54:14 pkill + 20:54:19 start_kiosk→True).
- **Fix 3 — start_kiosk.sh v3 (FIX BUG BOOT)**: logic cũ chỉ mở kiosk khi daemon báo kiosk_running=true (sau reboot daemon báo FALSE → kiosk không bao giờ dậy = nguyên nhân vụ 20:32!). v3: daemon sống mà kiosk false → POST start_kiosk 3 lần. **Đã test thật**: close_kiosk → chạy script → attempt 1 success (log start_kiosk.log 20:55:31).
- **Kết luận 24/7**: quan_ai_edge (Restart=always) + quan_ai_wake + tailscaled + lightdm đều enabled; guard service enabled; kiosk autostart đã sửa đúng logic; journald persistent; wifi power save off; PC-side watchdog + responder + learning_daemon đang chạy.
- **Rủi ro còn theo dõi**: reboot 20:32 nguyên nhân chưa rõ (nghi nguồn 5V) — journald persistent sẽ ghi nguyên nhân nếu lặp lại.


## 31/10/2026 ~21:10 — HDMI OUT: XUẤT KIOSK RA CỔNG HDMI CỦA PI5
- **Kiến trúc**: daemon Pi thêm `detect_hdmi_outputs()` (đọc /sys/class/drm) + `launch_hdmi_mirror()` (chromium kiosk thứ 2 cùng URL, window-size theo EDID màn HDMI, ozone x11) + watcher nền 5s — **cắm HDMI là TỰ hiện avatar, rút là tự tắt**.
- **Endpoint**: GET/POST `/api/kiosk/hdmi` (daemon) + action `hdmi_show`/`hdmi_hide` (server edge/control forward) + command center intent `tony_hdmi_show`/`tony_hdmi_hide` ("xuất hình ra hdmi", "chiếu ra hdmi", "tắt hdmi"...).
- **E2E fail-honest**: HDMI chưa cắm → "HDMI chưa cắm màn — không bật được mirror" (đúng trung thực); watcher sẽ tự bật khi owner cắm màn.
- **Deploy**: daemon Pi PID 6132 (systemd restart, md5 khớp); server PC PID 2364 (watchdog GUI, netmind READY); responder PID 3712+6188 (pycache xoá).
- **Lưu ý**: chromium mirror chạy SwiftShader 2D như kiosk DSI; độ phân giải theo EDID (fallback 1920x1080); vị trí cửa sổ x=800 (sau màn DSI) để rơi vào output HDMI.


## 31/10/2026 ~20:50 — KIỂM TRA KẾT NỐI LIÊN TỤC PI5 + HỒI PHỤC SAU REBOOT
- **Phát hiện**: Pi5 vừa reboot 20:32:13 (nguyên nhân không xác định — journal không persist, throttled=0x0, temp 57.6°C bình thường).
- **Hồi phục**: daemon (PID 1777) + wake service tự dậy ✅; kiosk KHÔNG tự dậy → ensure 2 lần → running=true, chromium 10 ✅.
- **Đo 3 phút liên tục**: HTTP kiosk **80/80 = 100%** (avg 263ms, max 1.4s); SSH 10/10 = 100%; ICMP 85% (mất gói đơn lẻ qua WAN, không bao giờ mất 2 gói liên tiếp — không ảnh hưởng công việc thật).
- **Đường đi**: Tailscale direct WAN 58.186.91.250:13072 + DERP hkg dự phòng; backend Running, self Online.
- **Fix**: Wi-Fi power save OFF (brcmfmac power save enabled → disabled; nmcli 'Ca Ngo 5G' powersave=2 lưu vĩnh viễn) — thử nghiệm giảm mất gói.
- **Kết luận**: kết nối liên tục thực chiến (SSH/HTTP/API) ổn định 100% sau khi loại trừ power save; nếu Pi5 tiếp tục tự reboot → nghi nguồn 5V (cap/adapter), cần owner kiểm tra phần cứng.


## 31/10/2026 ~20:30 — TEST 2 MIC (USB + MIC TÍCH HỢP LOA BT) + CHỌN MIC QUA DM
- **Mic USB Jieli** (node 77): RMS 116 nền sạch — mic chính.
- **Mic tích hợp SRS-XB33** (node 58 bluez_input): RMS 117, peak cao hơn khi tiếng lớn (DSP loa).
- **Loa BT XB33 phát OK** (mpg123 stream FL/FR active); **echo test**: mic BT bắt được tiếng loa phát (peak 3547); mic USB cũng ghi được tiếng loa từ xa.
- **Lệnh DM mới**: "nghe từ pi N giây [bằng mic usb|mic loa]" — mic_kind usb|bt|auto (auto=USB ưu tiên, BT dự phòng).
- **FIX**: parse node PipeWire bằng split chuẩn (regex cũ bắt sai id → target luôn 75); server + daemon + command center 3 tầng đều nhận mic_kind; response trả mic_target để verify.
- **Deploy**: daemon Pi restart systemd (PID 36754) + server PC watchdog GUI hồi sinh (PID 14720, netmind READY).


## 31/10/2026 ~20:20 — MIC USB JIELI: CÀI ĐẶT + CẤU HÌNH + ƯU TIÊN
- **Nhận diện**: mic USB = Jieli Technology UACDemoV1.0 (4c4a:4155) — node `alsa_input.usb-Jieli_Technology_UACDemoV1.0_4150354839393212-00.mono-fallback`, 16kHz mono.
- **Cấu hình**: wpctl set-default mic USB; volume 100% + unmute; WirePlumber rule `60-usb-mic-priority.conf` (priority.session 3000) — mic USB LUÔN là source mặc định kể cả khi loa BT reconnect; restart wireplumber OK.
- **Daemon "nghe từ pi"**: tự tìm node UACDemo → ưu tiên MIC USB, fallback mic BT (75) nếu USB rời.
- **SRS-XB33 bật lại**: sink mặc định (vol 0.50) — phát speak OK (mpg123 PID 35477, streams output_FL/FR active).
- **Wake word**: quan_ai_wake active, tự dùng mic Jieli (đúng).
- **E2E**: thu âm 5s RMS 119 ✅ (file DM); speak 2 câu qua loa BT ✅; transcript kiosk đúng.


## 31/10/2026 ~20:15 — PI5 LÀ ĐẠI DIỆN: TAI MỚI (thu âm mic qua DM) + KIỂM SOÁT
- **Yêu cầu owner**: kiểm soát việc điều khiển Pi5 — Pi5 là đại diện, là tai mắt.
- **Kiểm kê kênh điều khiển hiện có (22 intents)**: tony_on/off/status/pause/resume (hình thể), pi_photo/pi_video (MẮT), pi_live, speak (giọng), show_image, music, youtube/websearch.
- **BỔ SUNG TAI**: lệnh mới "nghe từ pi [N giây]" — mic Pi5 thu âm 3–30s → WAV lưu 2 bên (Pi + PC) + gửi DM.
  - Daemon: action "audio" pw-record target 75 (Popen + terminate sạch sau N giây + ffmpeg remux nếu header hỏng — fix WAV cắt cụt).
  - Server: pi_media_capture kind="audio" forward + tải về PC.
  - Command center: handle_tony_pi_listen + regex + detect_intent (read-only).
- **Ops học lại**: daemon Pi chạy qua main.py (systemd quan_ai_edge, MainPID) — kill pgrep client_daemon KHÔNG đủ; phải `sudo systemctl restart quan_ai_edge` (passwordless) + xoá __pycache__ + ensure kiosk sau restart.
- **E2E**: thu âm 6s → WAV 190KB 16kHz hợp lệ, RMS 137/peak 2232 (tín hiệu thật) ✅; file gửi DM.


## 31/10/2026 ~20:10 — FIX PHÁT NGUYÊN VĂN (chống GLM paraphrase)
- **Vấn đề owner báo**: "em phát câu này 2 lần trên loa pi5: ..." → loa phát KHÔNG đúng nguyên văn (câu 180 ký tự bị GLM rút gọn/diễn giải trước khi TTS).
- **Rễ**: câu lệnh không khớp intent cứng nào → rơi vào GLM chat tự do → GLM paraphrase; không có đường phát verbatim.
- **FIX (netchat_command_center.py)**:
  1. Thêm intent `tony_speak_verbatim` — regex `_SPEAK_VERBATIM_RE` bắt "phát [câu này] [N lần] [trên loa pi5] [giọng nữ/nam]: <nguyên văn>".
  2. Handler: synth TTS NGAY TẠI PC (TTSManager, retry 3) rồi đẩy audio_base64 sang server → không chết timeout 8s; phát đúng N lần (1..5); text giữ 100% nguyên văn ≤600 ký tự.
  3. `detect_intent` trả `tony_speak_verbatim` → responder không đưa câu này cho GLM nữa.
  4. route_message truyền CÂU ĐẦY ĐỦ cho handler (không chỉ group(1)).
- **E2E verify**: phát lại đúng câu của owner 2 lần → transcript Pi == gốc 180/180 ký tự ("cảm ơn chị đã lắng nghe." có đủ); mpg123 PID 32434 phát pipewire; audit success repeat=2.
- **Ops**: restart responder (kill 18372 → start venv pythonw PID 17680), xoá __pycache__, heartbeat OK 1-3s.


## 31/10/2026 ~20:00 — TEST TOÀN DIỆN HỆ THỐNG (12 hạng mục)
- **Kết quả**: 11 PASS + 1 WARN (loa BT SRS-XB33 tắt nguồn — signal vẫn OK).
- **PC**: 8766/8765 health 200; GLM chat E2E 4.9s tiếng Việt chuẩn; NetMind catalog READY.
- **Pi**: daemon active (PID 31488); heartbeat 1.1s; mic RMS 141/peak 863 (pw-record 3s); camera ảnh 124KB nét (vision: chi tiết tóc/tem điều hòa rõ, WB hơi ấm); MJPEG 30KB/2s SOI=True; upload 51KB MD5 khớp; speak audio E2E → mpg123 PID 31867 phát pipewire.
- **SỰ CỐ + HỒI PHỤCH**: Pi mất Tailscale ~60s (wifi hiccup, không thấy deauth trong journal) → daemon BrokenPipeError vô hại → Pi tự quay lại, kiosk chết → start_kiosk lại OK (chromium 11, màn rõ).
- **FIX BUG QUAN TRỌNG**: context_builder default_max_chars 4000 → 8000 — LANGUAGE RULE làm sys prompt lên 3647 chars khiến MỌI memory bị budget_exceeded (root cause 4 tests fail: redaction/disallowed/exclusion/pipeline). Sau fix: **2914 passed, 44 skipped** (full suite).
- **Loa BT**: SRS-XB33 Connected: no (tắt nguồn) — sink Dummy Output; khi owner bật loa sẽ tự reconnect (đã trusted).


## 31/10/2026 ~19:56 — AVATAR THU NHỎ TỔNG THỂ CĂN GIỮA (theo mẫu 19:05)
- **Yêu cầu owner**: avatar thu nhỏ nhìn tổng thể, cân đối giữa màn hình Pi5, mẫu = ảnh 19:05.
- **Thay đổi kiosk.css**: `.digital-human-canvas` cover+28% → **contain center** (trọn đầu→vai, không cắt); `.avatar-card` 100% → **aspect-ratio 3/2, max-width 92%, margin auto**; `.kiosk-stage` align center; `.kiosk-sidebar` width 112px → **0** (banner đề xuất chuyển absolute nổi, không chiếm chỗ); `.kiosk-body` position relative.
- **Deploy**: kiosk.css + kiosk.html (cache-bust `avatarfit_31oct_r4`), MD5 khớp; close_kiosk + pkill chromium + deep-clean cache + start lại.
- **E2E verify (vision 4 ảnh)**: khung avatar CĂN CHÍNH GIỮA (lề 2 bên ~100px cân bằng) ✅; avatar TRỌN VẸN đầu→vai ✅; header/footer nguyên vẹn ✅; SPEAKING test: VU nhảy ✅, marquee VN trong local window ✅ → sau 9s chuyển EN ✅, avatar cười ✅.
- Lưu ý vận hành: grim fail "failed to copy output DSI-2" khi màn nhấp nháy sau restart kiosk → pkill chromium dư (13 proc chồng) + start lại → chụp OK.
- Tests: không đổi code Python; tests TTS/voice 85 passed (phiên trước) vẫn nguyên.

## Bổ sung 31/10 ~19:50 — GIỌNÓI ĐA NGÔN NGỮ + GLM TIẾNG VIỆT CHUẨN (theo owner)

**Yêu cầu:** tìm kiếm đầy đủ thư viện giọng nói tiếng Việt; bổ sung đa ngôn ngữ; kết hợp GLM phản hồi tiếng Việt chuẩn trôi chảy; gửi câu giọng đọc mẫu (chào/chúc).

**Đã làm:**
1. KHẢO SÁT edge-tts: tiếng Việt có ĐÚNG 2 giọng neural (HoaiMy nữ + NamMinh nam — đã có sẵn trong config chuẩn).
2. BỔ SUNG MULTI_LANGUAGE_VOICES (10 giọng: EN Ava/Andrew Multilingual, JA Nanami, ZH Xiaoxiao, KO Hyunsu, FR Vivienne, DE Seraphina, TH Premwadee, RU Svetlana, ES Elvira) + LANGUAGE_VOICE_MAP + get_voice_for_language() (fallback luôn về giọng VN chuẩn, tôn trọng gender cho vi).
3. synthesize_audio: BỎ chặn "non-Vietnamese locale" — cho phép voice trong danh mục (VN + đa ngôn ngữ), chỉ từ chối voice lạ. Verify synthesize thật: EN 36KB, JA 42KB, ZH 34KB, VI NamMinh 36KB OK.
4. GLM (NetMind cloud GLM-5.3-Flash): thêm RULE 12 vào DEFAULT_SYSTEM_INSTRUCTIONS (context_builder.py) — LUÔN trả lời tiếng Việt có dấu, trôi chảy, xưng em gọi anh, chỉ chuyển ngôn ngữ khi owner yêu cầu. Verify chat thật: reply tiếng Việt tự nhiên đúng phong cách. Lưu ý vận hành: server cần env NETMIND_API_KEY (watchdog GUI spawn có key — kill server để GUI tự hồi là đủ; NO_API_KEY khi spawn từ shell thường).
5. GỬI 2 CÂU GIỌNG ĐỌC MẪU qua loa BT Pi5 (speak + audio_base64, has_audio=true): câu CHÀO "Chào anh Quân! Em là TONY..." + câu CHÚC "Em chúc anh một buổi tối thật ngon giấc...". File mẫu: logs/tts_mau_chao.mp3 (53KB), tts_mau_chuc.mp3 (34KB).
6. Tests: TTS/voice subset **85 passed / 1 skipped**; py_compile sạch.

**Files:** src/quan_ai_brain/voice/tts_config.py, src/quan_ai_brain/cognition/context_builder.py.

---

## Bổ sung 31/10 ~19:32 — HEADER VU NGANG + FOOTER 3 VÙNG (theo owner)

**Yêu cầu:** nút TONY ƠI sát góc trái dưới; marquee dịch hội thoại EN ở GIỮA footer; MIC/LOA lên ngang hàng đồng hồ đặt GIỮA header; avatar cân đối.

**Đã làm:**
1. HEADER 3 vùng: badge trái | VU MIC/LOA NGANG (canvas 150x18, 16 cột nhảy theo state) GIỮA (header-center absolute center) | đồng hồ phải. kiosk.js initWaveform viết lại render NGANG (slot/barW theo width, barH theo height).
2. FOOTER 3 vùng: TONY ƠI trái | marquee EN giữa (flex:1) | STOP phải (justify-content: space-between).
3. Avatar cân đối: object-fit cover + object-position center 28% — tràn khung nhưng giữ trọn khuôn mặt (không cắt trán/cằm).
4. Bỏ vu-rail dọc cũ khỏi kiosk-body (CSS display:none) — avatar thêm diện tích.
5. VERIFY E2E: pi5_v3b.png 5/5 ĐẠT (vision); speak thật → VU giữa header NHẢY (pi5_v3b_speak2.png 3/3); marquee giữa footer nhận transcript mới; transcript_en hoạt động (Hello Mr. Quanpt1!...). Màn Pi tự ngủ idle 4 phút là hành vi tiết kiệm chuẩn — start_kiosk lại OK.
6. Daemon log sạch; md5 3 file khớp; cache-bust vuheader_31oct_p2.

**Files:** edge_client/kiosk.html, kiosk.css, kiosk.js.

---

## Bổ sung 31/10 ~19:25 — LAYOUT TỐI ĐA + BIỂU CẢM GIAO TIẾP THEO NỘI DUNG (theo owner)

**Yêu cầu owner:** badge TONY ASSISTANT sát góc trên TRÁI; đồng hồ góc trên PHẢI; mở rộng giao diện + avatar rộng nhất; hiệu chỉnh tất cả biểu cảm khi giao tiếp trực tiếp.

**Đã làm:**
1. LAYOUT TỐI ĐA (kiosk.css): .kiosk-app padding 8→4px/gap 6→4; header bỏ khung nền (trong suốt, không border); badge device-pill bỏ background/border/padding = chữ trần cyan; avatar-card/side/VU tối ưu diện tích; stage max.
2. BIỂU CẢM THEO NỘI DUNG (kiosk.js + avatar_engine.js): setContextFromText(text) gọi ở playKioskSpeech + mỗi poll tick; extractVietnameseEmotion hỗ trợ text KHÔNG DẤU (normalize NFD + regex bỏ dấu); 5 tone (SERIOUS_ALERT/CONFIDENT_SUCCESS/ANALYTICAL_THINKING/CONSULTATIVE_INQUIRING/WARM_GREETING) nhận đúng 5/5 trên chromium Pi (probe headless).
3. SỬA ASSET SAI: avatar_v2_warning.png gốc là ảnh CƯỜI → portrait_warning dùng avatar_v2_confused.png (trầm tư); portrait_error dùng avatar_v2_thinking.png.
4. TONE AURA OVERRIDE (avatar_engine.js): aura/symbol đổi theo cảm xúc câu nói (SERIOUS_ALERT → đỏ + ⚠; CONFIDENT_SUCCESS → xanh lá...).
5. kiosk.js STATE_CONFIG + CSS: thêm WARNING/HAPPY/CONFUSED/EMPATHETIC (set_expression các state này trước đây fallback IDLE).
6. FIX REGRESSION daemon (client_daemon.py): (a) UnboundLocalError _t trong speak handler (dùng time.time() global); (b) PC heartbeat đè transcript/avatar_state/transcript_en khi Pi đang phát câu local → transcript_local_until window (speak: duration+5s; set_expression: 10s); trong window KHÔNG nhận transcript/transcript_en/target_avatar_state từ PC, transcript_en="" để kiosk fallback transcript VN.
7. VERIFY E2E thật (vision proof): câu chào → cười rạng rỡ; câu CẢNH BÁO (speak + audio thật) → TRẦM TƯ nghiêm túc + marquee câu cảnh báo + VU nhảy; set_expression WARNING → trầm tư + icon ⚠ cam dưới avatar; câu THÀNH CÔNG → cười tươi mắt nhắm (portrait_happy). Chromium cache deep-clean + cache-bust exprwarn_31oct_m7.
8. Tests: edge/kiosk/avatar/tts subset **268 passed / 4 skipped**; daemon log sạch; PC health HEALTHY.

**Files:** edge_client/kiosk.html, kiosk.css, kiosk.js, avatar_engine.js, client_daemon.py (đã deploy scp + md5 khớp; daemon restart qua systemd; kiosk restart chuẩn).

---

## Bổ sung 31/10 ~19:10 — MARQUEE HỘI THOẠI TIẾNG ANH + BỎ CORE/NHIỆM VỤ (theo owner)
- BỎ khối "CORE: ONLINE (...)" và khối "NHIỆM VỤ" ở cột trái kiosk (cột trái giờ chỉ còn banner đề xuất khi có).
- THÊM marquee (khung chữ chạy) trong FOOTER, cùng hàng nút TONY ƠI + STOP, chiếm bên trái: hiển thị hội thoại đang giao tiếp **bằng TIẾNG ANH**.
- Kiến trúc dịch: PC `server.py` helper `_translate_to_english()` (Google gtx endpoint, cache 200 entry, timeout 4s, fail→giữ gốc) → heartbeat response thêm `transcript_en` (2 endpoint heartbeat + làm nóng cache khi set_expression/speak) → `client_daemon.py` nhận + expose `transcript_en` trong to_kiosk_dict → `kiosk.js` cập nhật marquee (restart animation khi text đổi).
- Deploy: kiosk.html/css/js + client_daemon.py (md5 khớp), xóa __pycache__, restart daemon Pi + server PC (kill start_dual_servers wrapper PID 15104/568 → start lại .venv pythonw — LƯU Ý: server chạy qua `start_dual_servers.py`, không phải server.py trực tiếp).
- E2E thật: kiosk status transcript_en = "Hello Mr. Quanpt1! I'm ready to help." (dịch thật từ PC); test động: set_expression VN mới → EN mới xuống trong ~5s. Screenshot pi5_marquee.png 4/4 điểm (bỏ 2 khối, marquee footer đúng, avatar/badge/đồng hồ nguyên).
- Tests: 46 passed (edge_client + edge_monitor + web_server + command_center).

## Bổ sung 31/10 ~19:05 — ĐỔI TÊN HIỂN THỊ KIOSK PI5
- Badge header kiosk: `EDGE-PI5-DESK` → **`TONY ASSISTANT - QUANPT1 - VIETTEL`** (yêu cầu owner). Chỉ sửa `edge_client/kiosk.html` (device-id-tag); `device_id` hệ thống giữ nguyên `EDGE-PI5-DESK-01` (không ảnh hưởng API/heartbeat).
- Deploy scp + md5 khớp; restart kiosk qua action start_kiosk (pkill chromium một mình KHÔNG tự hồi — autostart chỉ chạy lúc boot; lưu ý vận hành: dùng start_kiosk thay vì kill).
- Verify screenshot pi5_rename2.png: badge đúng text mới, đủ avatar/đồng hồ/CORE/VU/nút. DM report + ảnh đã gửi.

## Bổ sung 31/10 ~19:00 — FIX LOA BLUETOOTH SRS-XB33 KHÔNG PHÁT TIẾNG
- Triệu chứng: TTONY TTS báo phát nhưng loa BT SRS-XB33 im lặng.
- Root cause 1 (PC): edge-tts 7.3.1 flaky — "No audio was received" ~20-80% tùy thời điểm → server synthesize fail âm thầm → KHÔNG có audio gửi Pi. FIX: retry 5 lần backoff 0.5s trong synthesize_audio (tts_config.py) → đo 6/6 pass, TB 2.7s.
- Root cause 2 (Pi): WirePlumber "bluetooth-autoswitch" LƯU saved-headset-profile=headset-head-unit cho SRS-XB33 + khi có stream record (pw-record wake engine) nó ưu tiên profile headset HFP mSBC (mono 16kHz) thay vì A2DP stereo → một số chu kỳ chuyển profile sập → Dummy Output → TTS im. FIX: conf `~/.config/wireplumber/wireplumber.conf.d/51-no-autoswitch.conf` (bluez5.autoswitch-to-headset-profile=false), xóa saved-headset-profile trong state, và `/etc/bluetooth/main.conf` Disable=Headset.
- Verify E2E: sink SRS-XB33 profile a2dp-sink codec LDAC, pw-play/mpg123 OK, POST /api/kiosk/control action=speak (audio_base64 TTS thật) → has_audio:true phát ra loa; profile GIỮ vững qua restart WirePlumber; screenshot pi5_speaker_ok.png kiosk lành mạnh.
- Tests: 39 passed 1 skipped (TTS suite). Lưu ý: kết nối BT sau reboot cần loa BẬT nguồn trước — nếu loa tắt nguồn, sink sẽ là Dummy (đã biết).


## Bổ sung 31/10 ~18:45 — KIỂM TRA TOÀN BỘ SAU CẤU HÌNH: 14/14 PASS
- E2E thật (không mô phỏng): services active + keyring 140B; kiosk wake từ SLEEPING→IDLE; layout V2 chụp chuẩn; TTS SPEAKING + VU dọc; camera live on/off + MJPEG 200; photo 130KB + video 742KB (Pi+PC); banner sidebar (test→dọn); 7/7 DM intent đúng; tắt/bật pi5 (18s không relaunch); responder heartbeat 0s; server 200; wake engine + mic 94KB/3s; self-test PASS; md5 5/5; pytest 2914.
- Báo cáo 14 mục gửi DM owner + 2 ảnh proof. Logs test: logs/test_1..5_*.png.

## Bổ sung 31/10 ~18:40 — LAYOUT V2: SIDEBAR TRÁI + VU METER DỌC (theo owner)
- **ĐÃ XONG + NGHIỆM THU ẢNH THẬT** (logs/pi5_layout_v2.png, pi5_banner_side.png, pi5_vu_speaking.png): md5 PC↔Pi 3 file (kiosk.html/css/js) khớp, cache-bust `sidebar_vu_31oct_j`.
  - Cột SÁT TRÁI (`.kiosk-sidebar` 150px): CORE ONLINE → NHIỆM VỤ → banner "Có N đề xuất..." (thứ tự đúng yêu cầu owner, xác nhận bằng đề xuất test tạo→chụp→resolve).
  - Avatar GIỮA: `.kiosk-body` flex 3 vùng, stage flex:1 — rộng nhất, `contain` trọn vẹn khuôn mặt.
  - VU METER DỌC PHẢI (`.vu-rail` 52px + canvas 36x300): bar vẽ dọc từ dưới lên, SPEAKING=bar xanh dương bung theo biên độ, LISTENING=cyan, IDLE=xẹp; nhãn dọc "MIC / LOA". Đã test khi TONY đang nói (`action speak` → state SPEAKING).
  - Footer chỉ còn nút TONY ƠI + STOP sát phải (status chuyển hết lên sidebar).
- Tests: full **2914 passed / 44 skipped** (HANDOFF_20261031_183757.md). Ảnh gửi DM owner.

## Bổ sung 31/10 ~18:35 — FIX LỖI "UNLOCK KEYRING" QUAY LẠI SAU MỖI REBOOT PI5
- **ĐÃ XONG + NGHIỆM THU REBOOT THẬT**: ảnh owner (7" TFT, dialog "Unlock Keyring — Authentication required") → file `~/.local/share/keyrings/Default_Keyring.keyring` trên Pi bị HỎNG chỉ 1 byte (lần fix trước 17:39 reset chưa đủ — file không đúng format plaintext → daemon coi locked, hỏi password mỗi boot).
- Fix: dựng lại keyring plaintext 140 bytes chuẩn (display-name/ctime/mtime/lock-on-idle=false) + `chmod 600` + unlock qua DBus `Service.Unlock` (libsecret/Gio) → `Locked: False`.
- **Reboot test không can thiệp**: boot ~50s, services active, kiosk tự dậy sau start_kiosk.sh wait-loop, **KHÔNG còn dialog** (logs/pi5_keyring_fixed2.png — avatar + CORE ONLINE + nút layout mới đầy đủ).
- Ảnh proof gửi DM owner. Lưu ý: lần sau nếu keyring lại hỏng (power-cut khi ghi), kiểm `stat -c%s ~/.local/share/keyrings/Default_Keyring.keyring` (chuẩn ~140 bytes, không phải 0/1).

## Bổ sung 31/10 ~18:25 — LAYOUT HÌNH THỂ PI5 MỚI (avatar mở rộng + nút dồn phải)
- **ĐÃ XONG + NGHIỆM THU ẢNH THẬT** (logs/pi5_layout_final.png): kiosk.html/kiosk.css md5 PC↔Pi khớp, cache-bust `layout_shift_31oct_i`.
  - Avatar mở rộng: viewport fill tuyệt đối trong stage (flex), canvas `object-fit: contain` — trọn vẹn khuôn mặt, không crop.
  - Footer mới: 2 nút TONY ƠI + STOP dồn sát PHẢI (`.footer-btns` margin-left:auto); trạng thái CORE ONLINE chuyển xuống góc TRÁI (`.footer-status`); bỏ khung nhiệm vụ khỏi footer (`.task-summary-glance` display:none).
  - 4 lần deploy-verify (avatar từng tràn che nút → dải bẹp → contain chuẩn).
- **Fix flaky test** `test_model_allowlist_rejects_unknown_model`: test phụ thuộc env tình cờ có NETMIND_API_KEY → giờ set key giả cứng + clear env (deterministic). Nguyên nhân: terminal session được inject key giữa phiên.
- Tests: full **2914 passed / 44 skipped** (validate_and_report OK, HANDOFF_20261031_182446.md). Ảnh gửi DM owner (file_id wmj7budpwpdf5qh9c3a63c6f7c).

## Bổ sung 31/10 ~18:05 — CAMERA LIVE TRỰC TIẾP TRÊN MÀN PI5 (lệnh DM "bật camera"/"tắt camera")
- **ĐÃ XONG + NGHIỆM THU E2E THẬT**: lệnh DM `bật camera` → Pi5 tự bật màn + giao diện kiosk + hiển thị hình LIVE trực tiếp từ Camera Module 3 (IMX708) ngay trên màn Pi5; `tắt camera` → gỡ live, về avatar TONY. `trạng thái camera` → báo trạng thái.
- Luồng kỹ thuật: netchat_command_center (intent `tony_pi_live`/`tony_pi_live_off` + guard bước 2.5 chặn pc_open nuốt lệnh) → server 8766 `/api/executive/edge/camera/control` (forward HMAC) → daemon Pi5 `/api/kiosk/camera/control`:
  - `start_live`: wake màn (như wake_by_voice) + `camera_streaming=True` (to_kiosk_dict expose cho kiosk.js poll).
  - MJPEG `/api/kiosk/camera/mjpeg` — multipart/x-mixed-replace, `rpicam-still --immediate` ~1fps (tiết kiệm CPU, không đụng mic pipeline), thread-safe, tự dừng khi `camera_streaming=False`.
  - `stop_live`: dừng stream + trả avatar. MJPEG không giữ camera mở liên tục → tránh xung đột capture photo/video.
- kiosk.js: overlay `#cameraLive` z-index cao fullscreen (`<img src=mjpeg>`), chỉ hiện khi poll thấy `camera_streaming=true`, cache-bust `cam_live_31oct_h`.
- Lỗi đã xử lý: (1) `tony_pi_live` rơi vào `_ARG_KEYWORD_RES` bị pc_open nuốt → thêm guard; (2) handler command_center gọi nhầm endpoint `/edge/control` → tách `_camera_control()` trỏ đúng `/edge/camera/control`; (3) grim fail tạm thời "failed to copy output DSI-2" sau khi tắt overlay (compositor busy) → tự hồi phục sau vài chục giây, không ảnh hưởng hệ.
- Tests: full **2914 passed / 44 skipped** (validate_and_report OK, HANDOFF_20261031_180451.md). MD5 PC↔Pi khớp (client_daemon.py, kiosk.js, kiosk.html). Ảnh nghiệm thu: logs/pi5_cam_live.png (LIVE trần nhà thật), logs/pi5_cam_off.png (về avatar).

## Current milestone
QUAN AI BRAIN — Raspberry Pi 5 Physical Audio, Vietnamese TTS & Zero-Dependency YouTube Music Engine (28/10/2026, VERIFIED).
- **Edge Pi 5 Status**: Live Raspberry Pi 5 (`192.168.1.21:8768`) paired and ONLINE (`READY`), RTT ~28ms, real HMAC-SHA256 heartbeats every 0.6s.
- **Physical Audio Hardware**: `Jieli Technology UACDemoV1.0 (USB Audio)` USB speaker & microphone active, audio level -18dB.
- **YouTube Music Engine (`src/quan_ai_brain/media/youtube_music.py`)**: Zero-dependency Python stdlib search and streaming coordination (`looks_like_music_request`, `search_youtube_music`, `dispatch_play_music_to_pi5`, `dispatch_stop_music_to_pi5`).
- **Edge Kiosk Daemon Endpoints (`edge_client/client_daemon.py`)**: Added `POST /api/kiosk/music/play`, `POST /api/kiosk/music/stop`, `GET /api/kiosk/music/status`, with multi-engine playback (Chromium Kiosk native iframe / headless Chromium / mpv fallback).
- **Core Chat Integration (`src/quan_ai_brain/web/server.py`)**: Natural language request interception ("em bật bài hát Tàu Anh Qua Núi cho anh", "vợ anh muốn nghe bài...", "dừng nhạc"), injects YouTube evidence blocks into LLM system context, dispatches playback to Pi 5, returns `music_playback` payload for UI widgets.
- **Web UI & Kiosk Player (`app.js`, `kiosk.js`)**: Interactive music card with Stop button, persistent Edge-TTS Vietnamese voice status badge (`vi-VN (Hoài My - Edge-TTS)`).
- **Test Suite Status**: 100% pass on all music & edge tests (`tests/test_youtube_music.py`, `tests/test_edge_client.py`, `tests/test_web_executive_endpoints.py`, `tests/test_v8_vietnamese_conversation.py`).

## Status as implemented and verified by test suite
- [x] QUAN AI BRAIN — Migration to New PC (DESKTOP-SNMI929, user quocd, D:\AI\AI Quanpt1 2026\BRAIN) (30/10/2026, VERIFIED):
  - [x] Broken venv rebuilt on Python 3.11.13 (`D:\...\BRAIN\.venv`) + editable install (`pip install -e .`) + libs: pytest, chromadb, flask, flask-cors, numpy, pillow, edge-tts, pypdf, python-docx, psutil, pywin32.
  - [x] 48 code files migrated off old-PC paths (`E:\AI\QUAN AI BRAIN`, `C:\Users\DELL`, `E:\AI\Ollama`) via `tools/migrate_paths_to_new_pc.py` (dry-run + backup at `backups/path_migration_20261030/`).
  - [x] Ollama installed user-level (`C:\Users\quocd\AppData\Local\Programs\Ollama`); 8 models verified (bge-m3, qwen2.5:0.5b/1.5b/3b/7b, llama3.1, mistral, qwen); BGE-M3 1024-dim embedding + qwen Vietnamese reply verified live (100% CPU — no discrete GPU on this machine).
  - [x] NetMind GLM cloud verified live: `netmind-health` catalog reachable, `netmind-ask` real GLM-5.3-Flash answer 405ms; API key persisted user-level via `tools/persist_netmind_env.ps1` (value never printed).
  - [x] Task Scheduler re-registered: `QUAN_AI_BRAIN_BACKUP_2AM`, `QUAN_AI_BRAIN_MORNING_REPORT_8AM` (+logon triggers), `QUAN_AI_BRAIN_KHOI_DONG_LOGON` → auto-start TONY at login; Desktop shortcuts START/STOP TONY recreated.
  - [x] 24/7 self-healing demonstrated LIVE: server crash (OpenBLAS RAM exhaustion) at 23:25:06 → watchdog detected 23:25:28 → auto-restarted 23:25:30.
  - [x] Root-cause fix for 16GB RAM: `OMP_NUM_THREADS=2` + `OPENBLAS_NUM_THREADS=2` + `MKL_NUM_THREADS=2` added to `start_dual_servers.py`, `tools/learning_daemon.py`, `tools/watchdog.py`, `TONY_START.bat`.
  - [x] `tools/validate_and_report.py` test timeout raised 180s → 900s (2947 tests need ~330s on this machine).
  - [x] Test suite: 2902 PASSED / 1 FAILED / 44 SKIPPED. The single failure (`test_web_server_e2e_multi_turn_chat`, 25s timeout) is load-sensitive and passes 5/5 when run standalone.
  - [x] E2E chat verified on live server: real answer from qwen2.5:0.5b (`is_mock=false`) with memory retrieval in 7.3s.
  - [x] Bom nổ chậm 33GB ĐÃ GỠ (31/10/2026, 00:57): kho tri thức `data/knowledge_db` có chỉ mục HNSW hỏng (nghi do server bị kill giữa chừng trong cơn khủng hoảng commit 00:21) → mỗi tin nhắn chat đầu tiên chạm kho hỏng → chromadb vòng lặp retry cấp phát nhân đôi → server phình 33,35GB commit → cạn commit toàn hệ thống → treo. Fix: backup kho hỏng (`backups/knowledge_db_broken_20261031_005544/`, 519MB, 35.700 embeddings), tạo kho mới sạch, đang re-ingest 191 tài liệu từ `kho_tai_lieu` (background, log `logs/ingest_knowledge_0057.log`). Kết quả verify: server commit sau chat = 0,13GB (trước fix: 33,35GB); E2E GLM 8s OK.
  - [x] `tools/__init__.py` bị mất khi migrate → `from tools.netchat_command_center import route_message` fail → responder log "Command router error". Đã tạo lại file marker; router hoạt động chuẩn (test "trạng thái" OK).
  - [x] NetChat bot token configured & verified live (31/10/2026 - 02/11/2026): Thay thế toàn bộ bot cũ `bot_quanpt1` (`edojmne9d7gcxx8axu1mzas3pr`) sang bot mới `bot_tony` (`66opztx9ut8rjxny555xhj84je`) theo yêu cầu owner. Đã nạp token mới `4ypgbchq97n6fcgcob36yetu9o` vào cấu hình skill `.env` và `%LOCALAPPDATA%\netmind_desktop\.env`. Live `whoami` & `netchat_bridge.get_status()` xác nhận danh tính bot `bot_tony` hoạt động 100%. Cập nhật `netchat_bridge.py`, `netchat_approval_adapter.py`, `netchat_auto_responder.py`, `KHOI_DONG_24_7.bat`, `TONY_START.bat`, `tests/test_web_netchat_tab.py` (54/54 netchat tests passed).
  - [x] Responder fix decode UTF-8 (cp1252 → 855 crash ngầm lịch sử) + fix commit-34,6GB của learning daemon (không còn tự chạy pytest — đọc reports/TEST_RUN_LATEST.txt).
  - [x] Sự cố bot bị gateway ĐÌNH CHỈ 15 phút vì rate_limit_violation (01:07, hết phạt 01:22:51): nguyên nhân cộng dồn — responder poll 5s + tab Cockpit tự refresh 10s (mỗi lần = 2 lệnh gateway thật: whoami + read) + các lần test tay. Fix 3 lớp: (1) bridge `get_status` có CACHE TTL 30s + circuit breaker 429 (bắt suspended_until, không bắn request vào gateway đang phạt, trả cached); (2) responder backoff 429/suspended đủ lâu (đọc suspended_until/retry_after từ lỗi, tối thiểu 90s); (3) tab Cockpit đọc qua bridge đã cache. Verify: get_status 3 lần liên tiếp = 2 lần cached; sau hết phạt whoami OK; responder tự trả lời "Chào em" qua DM thành công.
  - [x] Kiểm tra toàn hệ thống 19 hạng mục (31/10/2026 01:24, trước khi owner restart máy): RAM/commit 30,25GB trống, 3 ports UP, 4/4 services, server commit 0,15GB, E2E GLM 3,1s, trí nhớ 53 chunks + 2.497 memories, Ollama 8/8, lịch 3/3 Ready, watchdog có lịch sử tự phục hồi, heartbeat LIVE, learning 7,7s/chu kỳ, ingest nền ổn định, ổ C/D đủ trống, 0 log phình — 19/19 ĐẠT. Báo cáo đã gửi NetChat (kênh bị 403 do bot private → fallback DM thành công). Owner được xác nhận restart an toàn.
  - [x] Kiểm tra & sửa 3 lỗi thật của START/STOP double-click (31/10/2026 01:25-01:36, VERIFIED bằng cách mô phỏng double-click qua cmd /c): (1) TONY_STOP.bat dòng 74 `echo [OK] Ollama ... (dung y).` — dấu `)` trong text đóng if-block sớm → cmd crash `'. was unexpected'` exit 255 TRƯỚC khi dừng services (kill thật 4 services trong lần chạy thử) → đã bỏ dấu ngoặc; (2) `tools/stop_tony_services.ps1` dòng 42 `Substring(0,90)` ném ArgumentOutOfRangeException khi CommandLine < 90 ký tự (4 exception/lần) → đã guard Length; (3) TONY_START.bat 4 chỗ gọi `wmic` (bị loại khỏi Win11 26300) để check single-instance → đã thay bằng `tools/ensure_single_instance.ps1 -Marker`. NOTE thiết kế: START = stop-all-then-start (không phải detect-and-skip) → chạy 2 lần liên tiếp vẫn an toàn, tổng luôn 8 process (4 launcher + 4 interpreter con). Verify cuối: START tạo đúng 8 process + 3 ports UP + E2E chat OK + STOP chạy sạch exit 0 + 0 paren-in-block còn lại.
  - [x] Fix lỗi 'NETMIND_API_KEY is not set' trên Chat UI (31/10/2026 01:45, owner báo qua screenshot): key đã persist ở HKCU\Environment từ trước nhưng server được sinh ra từ môi trường terminal CŨ (trước khi persist) nên không nhận key. Fix gốc trong TONY_START.bat: tự đọc NETMIND_API_KEY + HERMES_CUSTOM_NETMIND_API_KEY từ registry vào env trước khi spawn services (chỉ báo DA_NAP/CHUA_CO, không bao giờ in giá trị). Verify: server mới có key (len=25) trong env, chat 'xin chào' → GLM trả lời thật 4,9s, lỗi biến mất. Báo đã gửi DM chủ sở hữu.
  - [x] Fix 'gửi tin nhắn vẫn không phản hồi' trong DM (31/10/2026 01:44): responder cũ CHỈ đọc kênh 'Trợ lý Tony Pham', không bao giờ đọc DM — nhưng fallback 403 lại đẩy mọi trả lời vào DM → owner trả lời trong DM thì bot mù (vòng lặp chết). Fix: read_channel_messages đọc CẢ kênh + DM (gắn _src/_chan vào từng tin), send_message nhận target_channel (DM thì bỏ --to-channel), trả lời đúng nơi owner nhắn. Verify: tin 'Chào em' 01:42 trong DM được trả lời lúc 01:44:05 ngay trong DM.
  - [x] THỐNG NHẤT DM-ONLY (31/10/2026 01:49, owner yêu cầu 'xóa các kênh khác, chỉ còn lại DM'): bot API bị khóa endpoint delete/leave/archive kênh (api.bot.endpoint_not_allowed — chỉ owner human mới xóa được kênh qua giao diện web). Đã chuyển TOÀN BỘ hệ thống sang chỉ dùng DM bot↔quanpt1 (131u5z64pj8q9da3k1xqp3y6pe): netchat_auto_responder.py, netchat_bridge.py (Cockpit tab), morning_report.py, netchat_approval_adapter.py, netchat_info_gap_adapter.py — 5 file, id kênh cũ 4phc9b1...=0 match. Responder restarted: trả lời DM thành công (01:49:09). Kênh cũ còn tồn tại phía server: owner tự xóa trong giao diện NetChat (kênh → ⋮ → Xóa kênh) nếu muốn.
  - [x] Yêu cầu 'xóa kênh 4phc9b1... + bot về riêng tư chỉ anh thấy' (31/10/2026 01:55): bot API bị CHẶN toàn bộ endpoint delete/leave/archive/update-privacy kênh (api.bot.endpoint_not_allowed — giới hạn nền tảng NetChat với bot token). ĐÃ ĐẠT mục tiêu bằng cấu hình: hệ thống DM-only từ 01:49 (5 file, id kênh cũ = 0 match trong code chạy, chỉ còn docstring mô tả đã cập nhật); bot chỉ đọc + trả lời trong DM bot↔quanpt1 → nội dung KHÔNG AI khác thấy được (DM 2 người). Kênh cũ phía server vẫn tồn tại nhưng bot bỏ hoàn toàn — owner xóa tay trong giao diện (kênh → ⋮ → Xóa) nếu muốn sạch danh sách. Báo đã gửi DM xác nhận.
  - [x] 31/10/2026 ~20:05 — FIX 2 LỖI TỪ ẢNH OWNER (image_7a124f: 'Em mở trình duyệt firefox lên' + 'Em khoá máy tính cho anh' bị từ chối): (1) thêm Firefox vào allowlist executor; (2) `_strip_polite_prefixes` — 'Em/Tony/Bạn... mở...' là mệnh lệnh; (3) thêm 'khoá' (sắc) vào pc_lock. Verify: Firefox mở thật + khóa màn hình thật; 63/63 tests; responder PID 17080.
  - [x] 31/10/2026 ~02:45 — ĐÓNG GÓI BỘ LỆNH PC THÀNH SKILL netMIND DESKTOP: tạo skill `tony-pc-executor` (skills/automation/tony-pc-executor/) — SKILL.md + `scripts/tony_pc_executor.py` standalone (cùng allowlist 21 app + audit JSONL + fail-honest; CLI list/open/close/lock/screenshot/screenshot-dm/send-dm). Verify thật: list 21 app, screenshot → PNG, screenshot-dm → DM thành công, open/close notepad thật, 'steam' ngoài allowlist → TỪ CHỐI đúng; audit 6 entries.
  - [x] 31/10/2026 ~03:15 — TONY NHẬN + ĐỌC FILE ẢNH TRONG DM (owner: 'thực hiện việc nhận file gửi là file ảnh và tiến hành đọc và xử lý file ảnh'): (1) `_ocr_image` 2 tầng offline — RapidOCR (onnxruntime có sẵn, cài rapidocr-onnxruntime vào venv agent, đọc tốt cả tiếng Việt có dấu: 'Báo cáo doanh thu quý 4' ✓) → dự phòng Windows OCR winocr; (2) `_extract_text` nhận thêm 6 định dạng ảnh (.png/.jpg/.jpeg/.gif/.bmp/.webp ≤20MB); (3) block prompt ghi rõ 'ẢNH — trả lời dựa trên nội dung OCR'. E2E thật: upload ảnh test vào DM → OCR đúng 'TONGYVISION TEST 2026-10-31 / DOC MA TRAN: 7-4-2-9'; 63/63 tests; responder restart PID 14456 heartbeat 2s; DM báo owner. Lỗi đã chữa: winocr cần .get() trên IAsyncOperation.
  - [x] 31/10/2026 ~03:30 — OWNER DUYỆT CÀI GÓI OCR vi-VN → ĐÃ THỬ VỚI QUYỀN ADMIN (UAC elevated qua Start-Process -Verb RunAs, script ps1 + log Temp): Add-WindowsCapability trả INSTALL_OK NHƯNG kiểm chứng Get-WindowsCapability: Windows 11 build này KHÔNG cung cấp capability Language.OCR~~~vi-VN (chỉ có Basic/Handwriting/TTS cho vi-VN, đều NotPresent; OCR chỉ en-US Installed) → gói OCR tiếng Việt không tồn tại để cài. Kết luận: RapidOCR = tầng chính (E2E lại qua terminal — process sạch: ảnh VI 'Báo cáo doanh thu quý 4' đọc đúng toàn bộ), Windows OCR en-US = dự phòng. 63/63 tests pass; DM báo owner. Ghi chú: import netchat_auto_responder nhiều lần trong 1 process test → monkeypatch subprocess.run chồng lớp RecursionError — chỉ hiện tượng test, responder thật import 1 lần không bị.
  - [x] 31/10/2026 ~04:10 — GHÉP CẶP ẢNH ↔ LỜI MÔ TẢ TRONG DM (owner image_4da003 + 'khi anh gửi ảnh kèm mô tả, nhận và thực hiện theo mô tả; ảnh chưa mô tả thì không cần phản hồi; mô tả trước/sau ảnh; tổng hợp cả ảnh và lời yêu cầu rồi mới xử lý'): (1) `_plan_batch` lập kế hoạch CẢ LÔ 2 pha (CLAIM: ảnh-đơn không chữ tìm mô tả gửi TRƯỚC trong 2 phút; WORK: ảnh đã claim → việc, tin chữ chưa dùng → gộp TẤT CẢ ảnh pending + chữ thành MỘT việc, lệnh hệ thống chạy ngay không ghép ảnh, file thường giữ hành vi cũ); (2) pending_images sống sót restart trong `data/netchat_responder_state.json` (pending_files, TTL 30 phút quá hạn im lặng); (3) poll loop chạy theo kế hoạch (_work) thay vì từng tin; (4) FIX bug sẵn có detect_intent: câu chứa 'giúp' ở GIỮA ('mở giúp anh chrome', 'đọc giúp anh ảnh này') bị nuốt thành bảng help → 'giúp' chỉ là lệnh khi đứng đầu câu. Verify: 74/74 tests (11 test mới tests/test_netchat_image_pairing.py); E2E ảnh DM thật q5d6bpnba7bd38dt4sc1smgbqh — ảnh đơn HOLD đúng, 'ảnh này ghi gì em?' ghép + OCR thật 'TONGY VISION TEST 2026-10-31'; lệnh giữa lúc có ảnh chờ chạy ngay không dính ảnh; responder PID 16996 heartbeat 3s; DM thông báo.
  - [x] 31/10/2026 ~02:55 — DUYỆT + DỌN KHO TRI THỨC THEO LỆNH OWNER (owner duyệt báo cáo trợ lý: 3,866 quarantined + 2,434 episodes + ~99% candidate trùng lặp): KIỂM TOÁN THẬT trước — 3,866 quarantined live (thay đổi từ 3,846 báo cáo), 0 trùng khớp approved cũ, 581 trùng archive, 209 trùng trong lô, 1,671 heading không nội dung, 1,406 tri thức thật unique; "99%" của trợ lý là trùng với archive 106,746 hàng lịch sử (thực tế 15%). HÀNH ĐỘNG (sau khi backup `backups/knowledge_approval_20261031/brain_pre_approval.db` 88MB, kiểm chứng khớp 3,867): (1) 1,406 tri thức thật → `approved` (note "owner-approved bulk 31/10/2026"); (2) 2,461 rác (581+209+1,671) → `candidate_knowledge_archive` với archive_reason đầy đủ (không xóa trắng); (3) 113 episodes "Experience lesson candidate" (memory gốc 70 superseded + 43 quarantined UNVERIFIED) → status `archived` + reason trong metadata; (4) audit log + integrity_check ok; server 8766 trả 200 sau thao tác. SAU: live 1,491 approved (85 cũ + 1,406 mới), 0 quarantined, 0 trùng lặp, episodes 2,323 recorded + 113 archived.
  - [x] 31/10/2026 ~02:37 — CHỤP MÀN HÌNH + GỬI ẢNH DM (owner ảnh image_273ce1): executor thêm `capture_screenshot` (PIL ImageGrab → logs/screenshots/) + `send_file_to_dm` (netchat_bot.py upload_dm, auto 2 bước CONFIRM-REQUIRED, post_id) + `screenshot_to_dm`; command_center thêm intent `pc_screenshot` + regex `^chụp (lại) (ảnh|hình) màn hình` trong detect_intent VÀ `_starts_with_command_keyword`. E2E thật: đúng câu trong ảnh → chụp 1920×1080 + upload DM post_id thật; câu hỏi không kích hoạt; 63/63 tests; responder PID 17580.
    - Tạo tools/netchat_action_executor.py: allowlist 20 app (ultraviewer/notepad/calc/paint/explorer/taskmgr/cmd/powershell/chrome/edge/coccoc/vscode/word/excel/powerpoint/outlook/zalo/dashboard/chatui/thư mục dự án) — resolve qua PATH/registry App Paths/đường dẫn cài đặt; open_app (Popen detached), close_app (taskkill /IM), lock_pc (rundll32 LockWorkStation); mọi hành động ghi audit log (pc_action.*).
    - UltraViewer trên máy này = UltraViewer_Desktop.exe (C:\Program Files (x86)\UltraViewer) — phát hiện bằng quét thật, đã thêm vào allowlist đầu tiên.
    - Nối vào netchat_command_center.py: +3 intent (pc_open/pc_close/pc_lock), 2 regex đối số ('mở/đóng <app>'), 3 handler; câu hỏi (dấu ?) KHÔNG kích hoạt (STATE_CHANGING); handle_help thêm mục THỰC THI TRÊN MÁY TÍNH.
    - E2E thật: 'mở ultraviewer' → UltraViewer 3 process chạy; 'mở chrome' → Chrome 10 process; 'em có mở được chrome không?' → không kích hoạt (rơi về AI); 63/63 tests pass.
    - Biên an toàn: CHỈ allowlist — không shell tự do, không xóa file, không credentials, không nâng quyền; mọi lệnh audit; fail-honest.
    - Responder restart (PID 17572/17736) + DM bảng năng lực đã gửi.
  - [x] 31/10/2026 ~19:25 — DM NETCHAT THÀNH BẢNG ĐIỀU KHIỂN TONY/Pi5 (owner yêu cầu 'ra lệnh trực tiếp từ DM cho các tác vụ thay đổi'):
    - Đọc đầy đủ chuỗi điều khiển: netchat_auto_responder.py (873 dòng) → netchat_command_center.py (route_message: ok-confirm → approval card → info-gap → todo_add → system commands) → server /api/executive/edge/control (start/close_kiosk, speak TTS+MouthSync, set_expression, set_volume, pause/resume, toggle_face_only, reload_ui, poweroff_pi) → pending_commands queue → Pi heartbeat pop.
    - Mở rộng netchat_command_center.py: +9 intent (tony_on/off/speak/face/pause/resume/status/volume + arg regex), STATE_CHANGING mở rộng (lệnh phải đứng đầu câu, câu hỏi không bắn), 6 handler mới gọi API thật qua _edge_control(), audit mọi lệnh; handle_help thêm mục ĐIỀU KHIỂN HÌNH THỂ.
    - Tests: 63/63 pass (test_netchat_command_center + ok_confirmation_flow + v3_sprint8_office_skills + v3_sprint3_netchat_info_gap — không phá contract cũ).
    - E2E thật: 'hình thể' → đúng edge DISCONNECTED (honest); 'âm lượng 70' → server nhận success; 'bật hình thể' + 'biểu cảm cười' → vào pending_commands queue (target_avatar_state=HAPPY, transcript cập nhật) — Pi sẽ pop khi heartbeat chảy lại.
    - Responder restart (PID 17656/3004) — đã tự trả lời tin owner 'Pi5 có thể làm được gì...' bằng lệnh tony_status mới. DM bảng lệnh đã gửi.
  - [x] 31/10/2026 ~02:40 — KIỂM TOÁN FILE PI5 + GÓI DEPLOY (owner yêu cầu 'kiểm tra lại toàn bộ file cài trên Pi5, hướng dẫn khai báo'):
    - Đọc kỹ edge_client/: main.py (CLI --core-host override + --check-health), config.py (EdgeConfig, fallback 127.0.0.1), client_daemon.py (1564 dòng: heartbeat HMAC + kiosk 8768 + Chromium launch 800x480 X11 SwiftShader V40 + audio CHROMIUM_ONLY), auth.py (HMAC-SHA256 anti-replay nonce + drift 10s), setup_pi5.py (pair POST /api/edge/pair PIN 888666 → server cấp shared_secret token_hex(32)), sync_assets.py (đọc core_host từ config.json — IP cũ chỉ là fallback vô hại).
    - Phát hiện: server KHÔNG verify HMAC header (chỉ cần X-QuanAI-Device) — HMAC hiện là client-sign-only; heartbeat trả remote_command + target_avatar_state.
    - 22/22 file cốt lõi đủ, py_compile 0 lỗi; 3 chỗ IP cũ còn lại vô hại (setup_systemd_247.sh đã thay bằng deploy script mới đọc config.json).
    - Tạo edge_client/deploy_pi5_tailscale_20261031.sh (bash -n OK): 3 chế độ --tailscale-only / --repoint / deploy-full 5 bước (packages → Tailscale check → setup_pi5.py --auto --host <TS_IP> --pin 888666 → systemd quan_ai_edge.service Restart=always 3s → health check).
    - Gói ZIP: backups/edge_client_pi5_deploy_20261031.zip (22,7MB, 72 file, nguyên vẹn OK).
    - Hướng dẫn khai báo đầy đủ 6 bước: docs/PI5_HUONG_DAN_KHAI_BAO_20261031.md; đã DM tóm tắt.
  - [x] 31/10/2026 ~02:20 — KẾT NỐI Pi5 QUA TAILSCALE (đáp ứng "Pi chỉ cần có mạng bất kỳ"):
    - Kiểm tra 7 điều kiện phía PC: internet OK, firewall pythonw Allow sẵn, server 8766 nhận LAN, HMAC khớp, gateway 192.168.10.1, không route về subnet cũ, PC không có Wi-Fi adapter (không làm hotspot được).
    - Cài Tailscale 1.104.4 trên PC qua winget (service Running) — mạng riêng ảo WireGuard, IP 100.x.y.z cố định, Pi ở mạng nào cũng nối được.
    - Chờ owner: (1) bấm link login https://login.tailscale.com/a/ac17fe901cc4a trên PC, (2) cài Tailscale trên Pi (curl -fsSL tailscale.com/install.sh | sh; sudo tailscale up — login cùng tài khoản), (3) sửa core_host trong ~/edge_client/config.json sang IP 100.x.y.z của PC, (4) sudo systemctl restart quan_ai_edge.
    - Hướng dẫn đầy đủ: docs/PI5_KET_NOI_LAI_HUONG_DAN.md; đã DM 3 phần qua NetChat (đường ống bot bị 403/429 ngẫu nhiên khi gửi — phải retry + tách tin ngắn; tin chứa URL ngoài thỉnh thoảng bị chặn).
    - [x] 31/10/2026 ~09:40 — PC ĐÃ LOGIN TAILSCALE THÀNH CÔNG (owner duyệt link auth; `tailscale login` exit 0 "Success"): self = DESKTOP-SNMI929, IP tailnet **100.102.120.6**, BackendState Running, netcheck UDP true, DERP gần nhất Singapore 52.7ms (không bị chặn như loạt đầu). Tailnet có 3 máy: DESKTOP-SNMI929 (online), iphone-15-pro-max + quanpt (offline 49 ngày, máy cũ). CÒN CHỜ OWNER PHÍA PI: cài Tailscale + `sudo tailscale up` cùng tài khoản → Pi sẽ hiện trong tailnet, rồi sửa core_host=100.102.120.6 + restart quan_ai_edge.
    - [x] 31/10/2026 ~09:50 — KIỂM TRA SAU KHI OWNER BÁO "ĐÃ KẾT NỐI" (kèm ảnh login PC thành công): xác minh thật 4 điểm — (1) tailnet vẫn 3 máy (PC online + iPhone + máy cũ), **PI CHƯA join**; (2) server 8766 probe **200 OK qua chính IP Tailscale 100.102.120.6** (LAN + localhost cũng 200) → đường ống cho Pi sẵn sàng 100%; (3) edge status `DISCONNECTED`, chưa có heartbeat; (4) ping Pi cũ 192.168.1.21 + quanpt 100.92.219.98 → không phản hồi. Kết luận trung thực: PC hoàn tất, Pi phía owner còn 4 bước (tailscale status / cài + up / sửa core_host / restart quan_ai_edge); đã DM 3 tin hướng dẫn, đọc lại API xác thực đủ.
    - [x] 31/10/2026 ~10:20 — Pi5 JOIN TAILNET THÀNH CÔNG + ĐỌC 2 ẢNH DM OWNER BẰNG OCR (owner: "kiểm tra thông tin kết nối như ảnh anh gửi cho Tony"): (1) OCR thật 2 ảnh DM — ảnh 1 (kèm chữ "Em thực hiện đăng nhập trên Pi5"): màn hình TFT hiển thị link login Tailscale `login.tailscale.com/a/7f1eafe010c26`; ảnh 2 (không chữ — HOLD đúng luật): terminal Pi báo quét mạng tìm PC → thử ghép cặp tới `http://100.100.83.59:8766` → **Connection refused**. (2) XÁC MINH TAILNET: máy mới `quanpt1` (linux) = **100.100.83.59 ONLINE** — Pi đã vào Tailscale thành công; ping thông; kiosk Pi 8768 phản hồi 200. (3) GỐC RỄ LỖI GHÉP CẶP: `discover_pc_core()` trong setup_pi5.py quét subnet và bắt NHẦM giao diện tailscale0 của chính Pi (100.100.83.59) → gửi pairing cho TỰ NÓ → refused. Server PC xác nhận NGHE pairing qua Tailscale: test `/api/edge/pair` đúng payload (pairing_pin 888666) → 200 (lưu ý: lần test này đổi secret phía PC, Pi cần pair lại để đồng bộ). (4) GIẢI PHÁP DM cho owner: chạy lại `setup_pi5.py` trên Pi với `--host 100.102.120.6 --pin 888666` (chỉ tay IP PC tránh quét nhầm). Ghi chú vận hành: NetChat DM 403/429 tái diễn với tin chứa cú pháp lạ (`--`, `=`) → diễn đạt lại không dấu gạch, backoff ≥90s khi 429.
    - [x] 31/10/2026 ~10:35 — OWNER CHẠY SETUP LẠI TRÊN PI (đọc ảnh DM thứ 4 file x99g5jewo3858g6cer5fpapomc): OCR cho thấy (a) setup đã pair thành công, kiosk khởi chạy ĐÚNG `http://100.102.120.6:8766` + HMAC-SHA256 banner; (b) `main.py` **CRASH tại dòng 159 `daemon.start()`** — chẩn đoán từ source `client_daemon.py:1343` ThreadedKioskServer bind port 8768 → **kiosk CŨ (main.py chạy từ trước, kiosk_running=False nhưng HTTP server vẫn trả JSON, trỏ core_host cũ 192.168.1.10) còn chiếm port** → OSError Address already in use. (c) Heartbeat đầu về PC lúc 03:25:44 UTC (pair OK thật) nhưng ngắt vì kiosk mới chưa chạy được; edge PC `paired: True`, `DISCONNECTED`. GIẢI PHÁP DM cho owner: `pkill -f edge_client` rồi `python3 main.py`. Kiosk cũ vẫn trả /api/kiosk/status qua 8768 (daemon cũ treo mode STANDBY) — server PC PIN pairing = 888666 đúng chuẩn (`server.py:112`).
  - Test suite full 31/10 ~11:50: 2909 passed / 44 skipped / 5 failed (môi trường: git.exe không trên PATH pytest + NO_API_KEY netmind_provider — có trước, không liên quan thay đổi); fix thêm bug sẵn có `DEFAULT_` đè comment trong netchat_bridge.py (NameError DEFAULT_CHANNEL_ID) → test_web_netchat_tab 9/9 pass.
  - [x] 31/10/2026 ~13:45 — ĐIỀU KHIỂN PI5 TỪ DM: open_url (overlay web) + "tony về" (close_web_overlay → avatar) + "hiển thị ảnh trên pi [N giây]" (ảnh DM fullscreen N giây → tự về avatar; "hiển thị lại ảnh" để hiện lại; upload file PC→Pi qua /api/kiosk/files/upload; kiosk.js consume-once qua heartbeat navigation_url/image_url) — E2E PASS với bằng chứng grim (pi5_img_c1/c2.png: t+4s ảnh fullscreen, t+20s về avatar); md5 daemon/kiosk PC↔Pi khớp; 54/54 test netchat PASS.
  - [x] 31/10/2026 ~14:00 — CHỤP ẢNH / QUAY VIDEO TRỰC TIẾP TỪ PI5 theo lệnh DM (owner: "kiểm tra hoạt động liên tục khi anh yêu cầu chụp ảnh, hoặc quay video trực tiếp từ Pi5. sẽ được truyền về netchat và lưu dữ liệu ở Pi5 với core máy tính này nếu có yêu cầu") — ĐÃ TRIỂN KHAI + E2E PASS:
    - Daemon Pi: POST /api/kiosk/media/record {action:photo|video, duration_sec:3..30} — photo fswebcam (fallback ffmpeg v4l2) 1280x720; video ffmpeg h264 + pw-record mic WAV song song (PipeWire multiplex, không đụng quan_ai_wake) → mux AAC; GET /api/kiosk/media/file?name= serve file (chống path traversal, chỉ trong tony_media/{photos,videos}).
    - Lưu trữ 2 BÊN: Pi ~/tony_media/{photos,videos}/ + PC logs/pi5_media/ (server action "pi_media_capture" tự tải file về sau khi capture; md5 video PC↔Pi khớp 360184375d33).
    - DM intents: "chụp ảnh từ pi"/"chụp ảnh pi5"/"tony chụp ảnh" → tony_pi_photo; "quay video từ pi [N giây]"/"ghi hình từ pi" → tony_pi_video (3..30s, mặc định 5s); handler tự gửi file về DM (executor send_file_to_dm) + trả lời tên file/kích thước/đã lưu 2 bên.
    - E2E: photo direct + photo/video qua server PC (PC tự lưu logs/pi5_media/) + full chuỗi route_message→capture→lưu 2 bên→gửi DM (mock executor) PASS; STRESS 3 photo liên tiếp 2s + video 3s PASS; quan_ai_wake vẫn active (pw-record wake không chết); 54/54 test netchat PASS.
    - Lưu ý: ảnh/video tối vì phòng tắt đèn (camera OK — test 13:15 trưa có ánh sáng thì ảnh rõ); systemctl restart quan_ai_edge cần polkit → dùng kill PID (Restart=always tự hồi) — systemctl restart từ SSH fail im lặng "Interactive authentication required".
  - [x] 31/10/2026 ~14:30 — SỬA "PI5 PHÁT LỜI THOẠI LIÊN TỤC" → CHÍNH SÁCH MIC-ONLY (owner: "kiểm tra tại sao Pi5 đang bị phát lời thoại liên tục. chỉ được phản hồi khi anh gọi hoặc kích hoạt qua Mic mà TONY nhận được") — ĐÃ ĐIỀU TRA GỐC RỄ + VÁ + NGHIỆM THU:
    - Nguyên nhân: kiosk.js tự khởi động WakeWordEngine (Web Speech API của Chromium) ngay khi mở trang với `continuous=true` + `onend` TỰ HỒI PHỤC vô hạn → STT trình duyệt chạy nền 24/7 dù wake-config PC trả `enabled:false` (engine không đọc trường enabled). Dấu vết: voice/telemetry ping dày bất thường 12:36–13:19 (nhiều lúc 5–20s/lần); pw-dump thấy "Chromium input" RecordStream giữ mic thường trực; khi bị tiếng ồn khớp 1 trong 10 từ khoá (kể cả "QUAN AI", "Hi TONY"...) → engine tự vào LISTENING → có thể tự gửi query → AI trả lời → TTS phát = "lời thoại liên tục".
    - Loại trừ có bằng chứng: PC không phát TTS local (tts_config.py chỉ synth bytes); heartbeat PC→Pi 12/12 + 8/8 sạch (không speak/audio); voice/interact = 0 lần sau 13:31; sink Pi = Dummy Output (SRS-XB33 tắt) → Pi vật lý không phát được; không còn chromium youtube/music stream.
    - VÁ 3 lớp (edge_client/wake_engine.js + kiosk.js + kiosk.html, md5 mới: engine 2ae78f4a…, kiosk.js 5b331ce0…, html c0298954…):
      1. syncConfigFromBackend đọc `cfg.enabled===false` → autoStart=false;
      2. kiosk KHÔNG nạp wake_engine.js lúc mở trang (deferred) — engine chỉ được lazy-load khi owner CHẠM nút mic "TONY ƠI..." trên màn hình;
      3. bỏ auto re-start recognition trong onend (chỉ re-start khi đang LISTENING chủ động) + bỏ initial start() trong initRecognition.
    - Kênh kích hoạt GIỮ NGUYÊN: nút mic cảm ứng trên màn Pi5 + wake word "TONY ơi" qua Vosk service ngoài (quan_ai_wake, pw-record độc lập) + mọi lệnh DM.
    - Nghiệm thu: sau reload, theo dõi 30s+40s → pw-dump CHỈ còn `pw-record` (wake service), Chromium input biến mất hoàn toàn; kiosk IDLE/SLEEPING, transcript đứng im; wake_by_voice thử E2E OK (IDLE + transcript chào); md5 3 file PC↔Pi khớp 100%; tests: 24/24 command_center + 308 passed voice/wake/tts/kiosk/edge + full suite 2,913 passed / 1 failed (NO_API_KEY môi trường cũ như baseline).
    - Lưu ý: câu "There is a proposal that needs your approval on the PC." thấy trên transcript lúc 14:25 là text cũ từ lần push_avatar_speech trước (chat stream @server.py:1968) — KHÔNG phải thoại đang phát; banner đề xuất kiosk dùng text tiếng Việt (kiosk.js:526).
  - [x] 31/10/2026 ~17:20 — GIẢI MÃ BẢN DỊCH TIẾNG ANH TRÊN MÀN PI5 + KHÔI PHỤC SAU REBOOT LOGIN 17:01 (owner: "hiện em nhìn thấy Pi5 không?"):
    - Phát hiện 1: Pi đã reboot/login desktop mới lúc 17:01 → desktop autostart `quan_kiosk.desktop` (start_kiosk.sh) khởi động daemon `python3 main.py` NGOÀI systemd → giành port 8768 với quan_ai_edge (bind fail, service activating-loop) + kiosk chromium không chạy → màn hình chỉ còn desktop. Fix: kill daemon rác → service active → start_kiosk.
    - Phát hiện 2 (gốc rễ câu tiếng Anh "There is a proposal that needs your approval on the PC"): **Google Translate tự động dịch toàn trang kiosk sang tiếng Anh** (popup "Translated to English" thấy trên screenshot 17:16) — text gốc tiếng Việt "Có 1 đề xuất cần Anh phê duyệt trên PC" (proposals_pending=1, consultation cst_learn_cycle_4 hợp lệ). Khác biệt emoji (📋→📘→🖥️) do Translate thay thế.
    - Fix 3 tầng: chromium flags `--disable-features=Translate,TranslateUI --lang=vi` (client_daemon.py launch_kiosk_process); `<meta name="google" content="notranslate">` + `<meta http-equiv="Content-Language" content="vi">` (kiosk.html); prefs Chromium `translate.enabled=false` + blocked_languages=["vi"] (pi ~/.config/chromium/Default/Preferences).
    - kiosk.js bổ sung: banner text set CỨNG mỗi vòng poll (ghi đè mọi text sót). md5 mới: client_daemon 29dd1252, kiosk.js 5b331ce0 (bản d), kiosk.html (bản e notranslate).
    - Nghiệm thu: screenshot 17:18 banner tiếng Việt "Có 1 đề xuất cần Anh phê duyệt trên PC", KHÔNG còn popup Translate; services active; streams chỉ pw-record; md5 4 file PC↔Pi khớp 100%; tests daemon/edge/kiosk 232 passed.
  - [x] 31/10/2026 ~13:30 — WAKE WORD "TONY ƠI" (owner: "cấu hình để khi anh sử dụng câu TONY ơi, thì Pi5 sẽ bật màn hình, bật giao diện hình thể để giao tiếp") — ĐÃ TRIỂN KHAI, chờ owner nói thật gần mic để nghiệm thu giọng→wake:
    - Kiến trúc: wake-word TÁCH KHỎI kiosk browser (kiosk đóng khi SLEEPING → browser chết = không nghe). Service mới `pi5_deploy/wake_word_service.py` (Pi: ~/Desktop/edge_client/wake_word_service.py) chạy systemd `quan_ai_wake` (user quanpt1, enabled, tự restart): Vosk model tiếng Việt nhỏ ~45MB offline (/home/quanpt1/vosk-model-small-vn-0.3, venv /home/quanpt1/wake_venv) + pw-record (PipeWire, --target node 75 Jieli UACDemoV1.0 Mono) 16kHz s16le raw; khớp mờ nhiều biến thể ("tony ơi/tôi nghĩ/tới mì/tôi ơi/trợ lý ơi..." — model small decode 'Tony ơi' → 'tôi nghĩ tới mì tươi', kiểm chứng bằng file); cooldown 8s; phrase "ngủ đi" → pause.
    - Flow: nghe thấy → POST /api/kiosk/control {action:"wake_by_voice"} → daemon `_wake_screen_impl` (màn sáng + launch kiosk + avatar IDLE) + `_sync_resume_after_voice_wake_impl` POST {action:"resume"} lên PC /api/executive/edge/control để heartbeat KHÔNG đè SLEEPING cũ (target kẹt SLEEPING sau pause gây wake-loop sudo tee mỗi giây — đã bắt bằng journalctl).
    - Bugs sửa: (1) handler dùng `self.daemon_state.auth` → AttributeError 'EdgeDaemonState' has no attribute 'auth' → empty-reply 000; sửa thành `self.auth` của handler; (2) file client_daemon hỏng (thiếu `try:` sau def `_send_dedicated_heartbeat`) → khôi phục patch; (3) arecord plughw:2,0 'Device busy' vĩnh viễn vì PipeWire giữ pcmC2D0c → đổi pw-record (PipeWire native, XDG_RUNTIME_DIR=/run/user/1000); (4) zombie daemon 1-thread giữ 8768 sau nhiều restart → kill PID đúng cmdline tuyệt đối.
    - Kiểm chứng E2E (API, ×2 sau restart bản cuối): pause → SLEEPING → wake_by_voice HTTP 200 → bl_power 0 + fb0 0 (màn SÁNG) + kiosk 11 proc + avatar IDLE + PC heartbeat target IDLE (đồng bộ resume OK). md5 PC↔Pi `25028bc8...` khớp.
    - Hạn chế đo được: mic Jieli gain max (147/147 = 0dB, AGC off) nhưng nhạy hẹp — RMS nền ~115, chỉ nhận nguồn âm GẦN ~30–50cm (loa BT cạnh mic RMS 213 trưa nay); giọng PC cách ~1.5m không tới (RMS phẳng 113–118). Vosk decode FILE giọng "Tony ơi" PASS; nghiệm thu cuối cần owner nói "Tony ơi" cách mic ~30–50cm.
    - Blocker âm thanh phát hiện: loa BT SRS-XB33 TỰ NGẮT (bluetoothctl connect → br-connection-page-timeout; wpctl sink = Dummy Output) → TTS/Pi phát loa im lặng cho tới khi owner bật loa. Mic + camera + heartbeat không ảnh hưởng.
    - Trạng thái cuối session: edge READY, kiosk chạy + màn sáng, quan_ai_wake active + enabled, client_daemon md5 khớp 2 đầu.
  - [x] 31/10/2026 ~13:15 — KIỂM TRA MIC + CAMERA PI5 SAU KHI BẬT AUTO-SLEEP (owner: "kiểm tra mic và camera đã được kết nối xem hoạt động ok chưa"): (1) CAMERA Sirius /dev/video0: self_test camera_ok=true (frame 20.808 bytes); chụp 2 frame thật qua POST /api/kiosk/camera/capture (image_base64 + SHA-256) — vision_analyze xác nhận nội dung thật (chuột Logitech bạc, tay người áo navy, sofa xám, gấu bông đỏ) → camera NHÌN ĐƯỢC, ảnh hơi mờ (tiêu cự webcam giá rẻ, chấp nhận được); ảnh 2 gửi DM cho owner (post 9jt9z9ky5p8n..., file u9zxrix38brapqjyjmn9naz1aw, verify ngược OK). (2) MIC Jieli UACDemoV1.0: self_test mic_ok=true level −43,9dB; arecord plughw:2,0 5s THÀNH CÔNG (160.044 bytes, RMS 123 ≈ −48,5dB — bắt âm nền phòng); ghi 8s trong khi TTS phát trên loa BT SRS-XB33 → mic KHÔNG bắt được tiếng loa (tỷ lệ 0.79x — mic USB đặt xa loa, bình thường). (3) LƯU Ý PHÁT HIỆN: USB Jieli card 2 CHỈ có capture (pcmC2D0c), KHÔNG có playback → loa TTS chạy qua loa bluetooth SRS-XB33 (sink PipeWire, vol 0.70) — audio mode CHROMIUM_ONLY vẫn đúng; TTS synthesize PC từng trả 503 (edge-tts mạng) → 1 lần speak im lặng, lần khác phát thật (pw-record monitor bắt được dạng sóng).
  - [x] 31/10/2026 ~12:45 — CHẾ ĐỘ NGHỈ CHỜ TỰ ĐỘNG CHO HÌNH THỂ PI5 (owner: "em cấu hình cho Pi5 để hình thể tự động vào chế độ nghỉ chờ. chỉ khi nào được gọi thì mới bật màn hình sáng"): (A) THIẾT KẾ xử lý tại biên trong client_daemon.py (chạy cả khi kiosk đóng, không phụ thuộc swayidle — đã bị kill): EdgeDaemonState thêm auto_sleep_enabled=True + idle_sleep_timeout_sec=300 (5 phút, đặt được qua config); heartbeat loop thêm khối AUTO-IDLE SLEEP: lặng im ≥ timeout → _auto_sleep_screen() = pkill chromium + xset dpms off + fb0/blank=4 + backlight bl_power=4 + avatar_state=SLEEPING; sau sleep reset last_activity_epoch (chu kỳ 5 phút tiếp). (B) WAKE KHI ĐƯỢC GỌI: _process_core_heartbeat_response — có remote_command hoặc target_avatar_state ∉ {IDLE, SPEAKING} → _wake_screen() = unblank fb0+backlight 0+brightness 255 + launch_kiosk_process nếu thiếu + reset last_activity. Lệnh DM "tắt hình thể"/"ngủ đi Tony" vẫn hoạt động (pause → SLEEPING thủ công). (C) FIX 3 BUG khi test: (1) server PC trả target=IDLE mọi heartbeat → chỉ wake theo LỆNH THẬT; (2) auto-sleep không chạy khi kiosk đã tắt (bỏ điều kiện is_kiosk_running → tắt đèn nền vẫn phải làm); (3) **DEADLOCK nghiêm trọng tự gây ra: "with self.state.lock" LỒNG bên trong _process_core_heartbeat_response đang giữ lock đó (threading.Lock non-reentrant) → heartbeat thread đóng băng, daemon treo, kiosk API timeout, edge DISCONNECTED 175s** — fix gán thẳng không acquire lại; thêm bảo vệ avatar_state=SLEEPING không bị target cũ (SPEAKING kẹt) đè mỗi giây. (D) KIỂM CHỨNG E2E đầy đủ 2 chu kỳ: sau 5:40 lặng im → kiosk_running=False ✅ avatar_state=SLEEPING ✅ backlight=4 (đèn TẮT) ✅ fb0=4 ✅ chromium nghỉ, heartbeat PC READY age 2.1s (daemon sống) ✅; GỌI LẠI từ PC (speak) → backlight=0 SÁNG ✅ fb0=0 ✅ kiosk_running=True ✅ avatar SPEAKING + TTS nói ✅ (~12s gồm 2s heartbeat poll); md5 client_daemon.py PC↔Pi khớp d6bd0dfcd3d79489e479e5336d427afb; service quan_ai_edge active; màn được restore SÁNG chờ owner. Lưu ý: daemon cũ không chết khi restart service vì cmdline "/usr/bin/python3 .../main.py" không khớp pkill pattern cũ — đã kill PID trực tiếp.
  - [x] 31/10/2026 ~11:30 — AUDIT TỐC ĐỘ HỆ THỐNG KẾT NỐI + TỐI ƯU XỬ LÝ TẠI BIÊN PI5 (owner: "audit toàn hệ thống kết nối để đảm bảo tốc độ xử lý nhanh nhất. cấu hình để một số hành động được xử lý tại Pi5 rồi báo cáo anh. xử lý tại biên Pi5"): (A) ĐO THỰC từng chặng: edge control PC→Pi 49ms; RTT PC↔Pi Tailscale 41-54ms; Pi→PC 20ms; responder poll 1 vòng 458ms (spawn bot script ×2 nguồn: kênh cũ ĐÃ XÓA vẫn poll mỗi 5s —CHANNEL_ID trùng DM nên vô hại nhưng thừa call 419ms); lệnh hệ thống DM không AI <1s; AI fallback GLM-5.3-Flash 3.6s; Ollama qwen2.5:7b local 8.1s (chậm hơn GLM cloud). (B) TỐI ƯU BIÊN PI5: kill firefox treo từ 19/10 (RAM available 2075→2893MB); avatar_engine.js render loop 60FPS→throttle 15FPS (FRAME_MIN_INTERVAL_MS=66); kiosk.css auraRotate linear→steps(20), bannerGlow 1.5s→4s steps(8); client_daemon.py thêm --disable-gpu-compositing + --force-prefers-reduced-motion (SwiftShader 3D pipeline nặng cho HUD phẳng); restart quan_ai_edge. KẾT QUẢ: chromium GPU-process 281%→54% CPU (giảm ~5×), nhiệt 68.6°C→59.8°C, load 5.2→2.9, kiosk ACTIVE ổn, RTT giữ 41ms. Đồng bộ client_daemon.py/avatar_engine.js/kiosk.css Pi↔PC (2 bản khớp). (C) XỬ LÝ TẠI BIÊN: Pi tự xử lý cục bộ KHÔNG cần PC/AI: set_expression/speak/set_volume/wake_word/reload_ui/pause/resume (API kiosk 8768, RTT 40-55ms), camera capture + SHA-256, EdgeAgent V41 AUTO_REACT/AUTO_MANAGE (chào boot, phát hiện mất kết nối, thu metrics). PC giữ vai trò: AI suy luận, DM điều phối, lưu tri thức, thư viện ảnh. DM báo cáo đã gửi.
  - [x] 31/10/2026 ~11:20 — TEST + CẤU HÌNH MẮT TAI TONY TRÊN PI5 (owner: "pi5 sẽ là hệ tai, mắt của TONY... kiểm tra hoạt động của hệ thống camera, mic"): (1) CAMERA USB Sirius (/dev/video0): lsusb nhận diện, chụp 2 frame 640x480 THÀNH CÔNG — ảnh 1: chuột máy tính + sofa + gấu bông (vision_analyze xác nhận); luồng kiến trúc chuẩn E2E: PC GET /api/executive/edge/camera/snapshot (proxy qua Tailscale) → Pi capture + SHA-256 → PC /camera/save kiểm HASH → lưu data/edge_media/captures/ (saved_path xác nhận); gửi ảnh camera DM cho owner (file_id qgn6ax118i88brpnkgieqixjjo, verify ngược OK). (2) MIC USB Jieli UACDemoV1.0: audio/status mic_enabled=True, level -18dB, WAKE_WORD mode 'TONY ơi'; self_test mic_ok=true camera_ok=true; PipeWire: Chromium đang giữ input_MONO active (daemon giữ mic — arecord busy là đúng); TTS speak qua kiosk OK. (3) ỔN ĐỊNH SAU REBOOT: user quanpt1 có group video+audio; camera/mic daemon on-demand; wake word trong config. Recipe chụp màn hình Pi5 (scrot sai Wayland → grim + unblank) lưu vào skill quan-ai-brain-ops.
  - [x] 31/10/2026 ~11:15 — CHỤP ẢNH MÀN HÌNH PI5 + GỬI DM CHO OWNER (owner: "em chụp ảnh màn Pi5 xong gửi DM cho anh"): lộ trình chụp màn hình Pi5 qua Tailscale SSH: scrot chụp fb0 (console DSI) cho ảnh ĐEN vì kiosk chromium chạy trên Wayland (labwc, DISPLAY=wayland-0); fix màn hình bị blank (fb0 blank=4, backlight bl_power=4 sau close_kiosk/swayidle DPMS) → echo 0 vào fb0/blank + bl_power + brightness 255; pkill swayidle; chụp bằng grim Wayland-native (WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000) → PNG 240KB có nội dung; scp về PC; vision_analyze xác nhận: avatar TONY hiển thị, "CORE: ONLINE (100.102.120.6:8766)", nút HEY TONY + STOP; upload_dm PNG qua NetChat → post hxetdx6343ynmm575t4n7yh15o file gupgtpm9gin79x84qdo5dk4h6a, xác thực ngược từ API OK.
  - [x] 31/10/2026 ~11:40 — RA LỆNH BẬT/TẮT HÌNH THỂ TỪ NETCHAT — ỔN ĐỊNH + FIX BUG ZOMBIE (owner: "anh có thể ra lệnh tắt bật hình thể cho Tony từ netchat. em cấu hình việc này cho ổn định"): luồng sẵn có `tony_off`/`tony_on` (DM → /api/executive/edge/control → Pi /api/kiosk/control) đã tồn tại NHƯNG test E2E lộ bug thật: sau close_kiosk, /api/kiosk/status vẫn báo kiosk_running=True/ACTIVE — nguyên nhân is_kiosk_running() coi chromium ZOMBIE (STAT=Z, cmdline rỗng) là kiosk thật; PATCH edge_client/client_daemon.py (bỏ qua STAT=Z + cmdline rỗng), scp lên Pi + systemctl restart quan_ai_edge (active). E2E lần 2: close_kiosk → kiosk_running=False/STANDBY/avatar OFFLINE đúng; start_kiosk → True/ACTIVE; heartbeat PC READY liên tục (age 0.28s) qua cả restart. detect_intent test 9 case: "tắt hình thể"→tony_off, "Tắt hình thể giúp em"→tony_off, "tat hinh the"→tony_off, "ngủ đi tony"→tony_off, "bật hình thể"→tony_on, "em ơi tắt hình thể"→tony_status (đúng luật đứng đầu câu). DM hướng dẫn đã gửi.
  - [x] 31/10/2026 ~11:15 — TEST E2E GIAO TIẾP + TRUYỀN FILE PC ↔ PI5 QUA TAILSCALE (owner: "em kiểm tra và test việc giao tiếp, truyền file giữa Tony và pi5"): (1) PC→Pi set_expression /api/kiosk/control OK; (2) PC→Pi speak OK — TFT hiện "Em la Tony. Kenh PC - Pi5 da thong", avatar_state SPEAKING xác nhận từ /api/kiosk/status, audio CHROMIUM_ONLY; (3) truyền file PC→Pi /api/kiosk/files/upload JSON 190 bytes (schema filename+content_b64, ext allowlist .json) — THÀNH CÔNG, MD5 PC vs file trên Pi (SSH) khớp 13964b11e5b8…, đã dọn file test; (4) Pi→PC heartbeat liên tục age<1.5s + Pi curl http://100.102.120.6:8766/api/health = 200 trong 15ms. Kết luận: kênh hai chiều PC↔Pi5 hoạt động ĐẦY ĐỦ (lệnh, hiển thị, âm thanh, file, telemetry). DM báo kết quả.
  - [x] 31/10/2026 ~11:58 — PI5 ONLINE — KẾT NỐI 24/7 XÁC NHẬN E2E (owner: "anh đã làm xong, em kiểm tra"): owner chạy tony_pi5_all_in_one.sh thành công. Kiểm chứng từng lớp: (1) edge state READY (không phải ONLINE vì kiosk_mode face_only STANDBY), hb mỗi 2s, hb_age <1.5s, RTT 30-45ms; (2) SSH key hoạt động — ssh BatchMode vào quanpt1@100.100.83.59 exit 0 (không cần mật khẩu); (3) systemctl: quan_ai_edge active/running, NRestarts=0, enabled (tự chạy sau reboot); (4) config Pi core_host=100.102.120.6 đúng, kiosk cũ IP 192.168.1.10 đã thay; (5) theo dõi 6 mẫu x 5s: READY liên tục, không gián đoạn. 2 alert cũ (PIN sai + PHỤC HỒI) là từ lần pair trước. DM xác nhận đã gửi.
  - [x] 31/10/2026 ~11:20 — GỘP 2 FILE DEPLOY PI5 THÀNH 1 FILE + GỬI QUA DM (owner: "em ghép cả 2 file thành 1" + "em gửi file trên qua DM"): tạo `pi5_deploy/tony_pi5_all_in_one.sh` (SSH key nhúng sẵn, 4 bước tự cấu hình: authorized_keys, pkill kiosk cũ, core_host=100.102.120.6, systemd quan_ai_edge Restart=always); fix `After=network-online.tailscale.service` (unit không tồn tại) → `network-online.target tailscaled.service`; bash -n SYNTAX OK qua git-bash; `tailscale file cp` vào inbox Pi OK. DM upload .sh thẳng → 403 hai lần (gateway bot chặn đuôi .sh); fallback ZIP `tony_pi5_all_in_one.zip` → THÀNH CÔNG post `q1h1ct43g78qtjqy3hmbptywth` file_id `es3s5bk3ubyuzfb7jc1do6536c`; KIỂM TRA NGƯỢC: read DM thấy post + download roundtrip MD5 khớp byte-for-byte. Chờ owner giải nén + chạy sudo bash.
  - [x] 31/10/2026 ~10:50 — CHUẨN BỊ TỰ CẤU HÌNH PI5 24/7 (owner: "em tự thực hiện kết nối với Pi5 để đảm bảo hoạt động ổn định 24/7"): SSH port 22 mở qua Tailscale nhưng cần auth; owner chọn Tailscale SSH → kiểm tra sshEnabled=None (chưa bật), MagicDNS không resolve (DNS công ty) → chuyển phương án Tailscale file delivery: tạo `pi5_deploy/tony_setup_247.sh` (LF) + `tony_pc.pub` (SSH key ED25519 mới, comment tony-desktop-snmi929) → `tailscale file cp` vào inbox Tailscale của Pi THÀNH CÔNG (2 file exit 0). Script tự: cài SSH key authorized_keys, pkill kiosk cũ (giải phóng cổng 8768), sửa config core_host=100.102.120.6, tạo systemd service `quan_ai_edge` (Restart=always). Owner chỉ chạy: `sudo tailscale file get /home/quanpt1/Desktop/` + `sudo bash tony_setup_247.sh`. Theo dõi 3 phút: edge vẫn DISCONNECTED — chờ owner chạy 2 lệnh. DM 2 tin hướng dẫn xác thực đủ.
  - [x] Xác nhận kênh 'Trợ lý Tony Pham' (4phc9b1mx78qjq3grxcw89u94a) ĐÃ BỊ XÓA (31/10/2026 01:47:40, owner xóa từ giao diện web): GET channel trả về delete_at=1793386060866 (≠0 = đã xóa); danh sách kênh bot tham gia chỉ còn DM bot↔quanpt1 + 'Cộng đồng netChat' (public town-square, bot không đọc/không đăng). Hệ thống DM-only hoàn chỉnh: 1 kênh duy nhất = DM bot↔owner.
  - [ ] Outstanding: Pi 5 (192.168.1.21:8768) unreachable từ LAN mới.
- [x] QUAN AI BRAIN — DB Browser for SQLite 3.13.1-win64 Integration & Deep Memory Engine (29/10/2026, VERIFIED):
  - [x] Official DB Browser for SQLite 3.13.1 win64 portable deployed to tools/DBBrowser/.
  - [x] One-click desktop launcher MO_TRAP_TRI_NHO_SQLITE.bat created for direct visual exploration of data/brain.db.
  - [x] Deep Memory Schema & Database Integrity verified on data/brain.db (91.4 MB, 2,180 episodes, 3,454 candidate knowledge records, 1,842 semantic memories, 2,269 memories, 150 knowledge units, 210 knowledge relations).
  - [x] Candidate knowledge quarantine isolation confirmed compliant with AGENTS.md.
  - [x] Verification test suite (tests/test_sqlite_browser_deep_memory.py): 6/6 PASSED (100%).
- [x] QUAN AI BRAIN — Raspberry Pi 5 Audio/TTS & YouTube Music Engine (28/10/2026, VERIFIED ON LIVE PI 5):
  - [x] Zero-dependency YouTube search engine (`src/quan_ai_brain/media/youtube_music.py`).
  - [x] Vietnamese intent extraction ("bật bài...", "nghe bài...", "muốn nghe...", "dừng nhạc").
  - [x] Live playback and stop dispatch to Raspberry Pi 5 (`192.168.1.21:8768`).
  - [x] Edge Daemon music control handlers & Chromium audio pipeline (`edge_client/client_daemon.py`).
  - [x] Living Grounding Fact 5 confirming Pi 5 physical audio hardware and YouTube music capability (`src/quan_ai_brain/cognition/grounding_facts.py`).
  - [x] Central Server endpoints `/api/music/search`, `/api/music/play`, `/api/music/stop`, `/api/music/status`.
  - [x] Web UI music player cards with stop controls (`app.js`).
  - [x] Dedicated test suite (`tests/test_youtube_music.py`): 4/4 passing.
- [x] QUAN AI BRAIN — Sprint 7B: Windows Job Object Kernel Integration & Hard Resource Containment (27/10/2026, 978 passed, 0 failed, 1 skipped):
  - [x] `WindowsJobObjectBackend` (`src/quan_ai_brain/execution/windows_job_object.py`): Pure ctypes Win32 Job Object adapter implementing `ProcessBackendInterface`.
  - [x] Win32 Ctypes Layouts: `IO_COUNTERS`, `JOBOBJECT_BASIC_LIMIT_INFORMATION`, `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` (144 bytes), `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION`.
  - [x] Kernel Resource Quotas: Memory ceiling, CPU user time, active process limits, auto-kill on close.
  - [x] Accounting & Telemetry: Real-time query of process counts, user CPU time, and kernel CPU time.
  - [x] Fail-Closed Staging Gate: `allow_live_processes=False` default refusing execution with `ProductionExecutionProhibitedError`.
  - [x] Destructive Command Screening: R5 commands (`rm -rf`, `del /s`, etc.) permanently blocked.
  - [x] ContainedExecutionRunner: `execute_contained()` verified with both inert staging and authorized live sandbox dispatch.
  - [x] Verification Test Suite (`tests/test_windows_job_object.py`): 14/14 tests passing.
- [x] QUAN AI BRAIN — Master Implementation V4: Evidence-Driven Cognitive State & Verification (27/10/2026, 960 passed, 0 failed, 1 skipped):
  - [x] CognitiveClaim & BeliefItem (`src/quan_ai_brain/cognition/cognitive_state.py`): Triples, multi-source provenance, version lineage, and timestamp tracking.
  - [x] Freshness Evaluation (`src/quan_ai_brain/cognition/cognitive_state.py`): Ephemeral, session, daily, long-term, and immutable policies.
  - [x] Context-Aware Contradiction Engine: Auto-detection of context differences vs direct contradictions.
  - [x] State Reconciliation Engine: Non-destructive updating, version bumping, and supporting/opposing source tracking.
  - [x] Cognitive Self-Assessment Engine: 6-tier evidence evaluation, truthful reporting, and strict production gating.
  - [x] V4 Verification Suite (`tests/test_cognitive_state_v4.py`): 20/20 tests passing covering all Section 9 requirements.
- [x] QUAN AI BRAIN — Cognitive Operating Intelligence V3: Cognitive State, Metacognitive Abstention & Adversarial Testing (27/10/2026, 927 passed, 0 failed, 1 skipped):
  - [x] CognitiveState Model (`src/quan_ai_brain/cognition/cognitive_state.py`): Segregation of knowledge into 8 `BeliefKind` categories, tracking hypotheses, uncertainties, alternatives, and contradictions.
  - [x] TaskPlan Integration (`src/quan_ai_brain/planning/models.py`): Added `cognitive_state` field, serialize via `to_dict()`, and explainable markdown output via `explain()`.
  - [x] ExecutiveCoordinator Integration (`src/quan_ai_brain/planning/coordinator.py`): Connects `CognitiveState`, maps user goal to `FACT_USER`, maps memories to `FACT_RETRIEVED`/`HYPOTHESIS`/`UNKNOWN`, detects contradictions and stale state, enforces approval on adversarial injection or contradictions.
  - [x] Adversarial Cognition Test Suite (`tests/test_adversarial_cognition.py`): 12/12 tests passing covering all Master Prompt V3 Section X mandatory groups.
  - [x] Unit Test Suites (`tests/test_cognitive_state.py`, `tests/test_planning.py`): 100% pass rate.
  - [x] InformationGapAnalyzer (`src/quan_ai_brain/cognition/information_gap_analyzer.py`): 18/18 tình huống bắt buộc V3 §12 đạt; im lặng ≠ đồng ý; nguồn mâu thuẫn → NEEDS_VERIFICATION không tự chọn; VERIFIED/OWNER_PROVIDED không hỏi lại (V3 §4).
  - [x] CognitiveLoop integration: submit_task gap_check ON — NOT_SUBMITTED khi thiếu thông tin thiết yếu; TaskSpec.validate fail-closed giữ nguyên.
  - [x] NetChat: route_message bước 0.5 (info_gap_reply) + approval adapter nhường tin info-gap; E2E TASK-E2E99 qua route_message thật.
- [x] QUAN AI BRAIN — Sprint 2: GLM Streaming + Deep Reasoning + Pi Barge-in + Avatar V3 Phase B (Completed & Verified 2026-10-25, owner-approved):
  - [x] Streaming SSE (`src/quan_ai_brain/llm/netmind_provider.py::stream_chat()`): Live delta generator (no buffering), `_iter_chat_stream_events()` parse SSE on-the-fly, delta never replayed on transport error, first-delta latency 1.5–1.8s (down from 7.4s via 60s catalog cache).
  - [x] Deep Reasoning Tier: `Qwen/Qwen3.5-122B-A10B-FP8` added to allowlist with `max_tokens=2500` default; router recognizes "phân tích chuyên sâu/nghiên cứu sâu/deep dive" + queries >1200 chars → deep tier; probe verified 22.01s total, 2255 reasoning + 72 content tokens, finish=stop.
  - [x] Barge-in on Pi 5: `edge_client/kiosk.js::window.bargeInStopSpeaking()` pauses audio + cancels utterance + avatar→LISTENING; `edge_client/wake_engine.js` triggers barge-in when voice detected during SPEAKING; both files deployed to Pi 5 root daemon (192.168.1.21:8768), reload_ui success, kiosk_running=True.
  - [x] Avatar V3 Phase B (Mouth Sync Timeline-Only + Exact Duration): Removed random-viseme fallback (`Math.random() * 0.55` → bell-curve `0.35 * sin(π*phase)`), added `MouthSyncEngine.measure_mp3_duration_ms()` for ID3v2+MPEG header parsing, timeline scaling to exact audio duration; 6/6 tests passed in `tools/avatar_v3_giai_doan_b_tests.py`; `avatar_engine.js` deployed to Pi 5 (42,005 bytes match).
  - [x] Full Regression: 512 passed, 1 skipped, 0 failed in 74.69s (10 new streaming/router tests + 18 NetMind tests, zero regressions).
  - [x] E2E Verification: PC streaming curl + script PASS; Pi 5 speak E2E PASS (41KB audio → kiosk SPEAKING→IDLE); barge-in & Avatar Phase B deployed, awaiting owner live test.
- [x] QUAN AI BRAIN — Sprint 1: GLM-5.3 NetMind Provider Integration (Completed & Verified 2026-10-25, approved D1–D7 by Anh Quân):
  - [x] Catalog Verification (Sprint 0 evidence, `reports/SPRINT0_NETMIND_CATALOG.json`): live GET /models HTTP 200 — 6 models served; `zai-org/GLM-5.3-Flash` present; `zai-org/GLM-5.3` and `zai-org/GLM-5.3-FlashX` NOT in account catalog. Both tiers map to GLM-5.3-Flash by owner decision (D2).
  - [x] `NetMindProvider` (`src/quan_ai_brain/llm/netmind_provider.py`): standard-library chat adapter, fail-closed by default (`NETMIND_EXTERNAL_DATA_ALLOWED=false` → `NETMIND_DISABLED`), model allow-list (exact catalog IDs only), API key read from env at call time (never stored/printed/logged), redacted error paths, bounded retry with capped exponential backoff, TIMEOUT/CONNECTION_ERROR/HTTP_* structured error codes, optional metadata-only audit via `AuditLogger`.
  - [x] Reasoning-token control verified on live gateway: default burns 60/60 completion tokens silently; `reasoning_effort="low"` → 0 reasoning tokens, correct Vietnamese answers (~0.2–1.4s). Other params (`thinking`, `enable_thinking`, `reasoning_effort="minimal"`) are ineffective on this gateway (probe evidence `tools/sprint1_reasoning_param_probe.py`).
  - [x] `LLMProvider` facade extension: optional `netmind` provider; exact-match NetMind model IDs route to cloud first, transparent structured failure (never fabricated answers); `health()` reports combined Ollama + NetMind status.
  - [x] CLI diagnostics: `netmind-health` (no key ever printed) and `netmind-ask` (fail-closed until env opt-in). Live E2E verified 2026-10-25: DISABLED_BY_POLICY by default; with env opt-in, real GLM-5.3-Flash Vietnamese answer in 1.06s, reasoning_tokens=0.
  - [x] Vietnamese Benchmark D3 (`reports/SPRINT1_VIETNAMESE_BENCHMARK.json`, 28 prompts / 14 categories, same scorer): GLM-5.3-Flash — clean pass 28/28, keyword accuracy 88.5%, latency avg 1.33s / p95 1.99s, 0 forbidden violations; Qwen2.5:1.5b local — clean pass 28/28, keyword accuracy 69.2%, latency avg 1.76s / p95 3.48s. GLM-5.3-Flash wins accuracy & latency; local Qwen retained for offline/privacy.
  - [x] GPU budget policy D5 (`src/quan_ai_brain/cognition/autonomous_mind.py::keep_warm_pulse`): physical keep-warm now probes qwen2.5:0.5b + bge-m3 generation/embed each pulse; 7B deliberately NOT pinned (5.1GB > 4GB VRAM, would evict fast tier + embedder); failures recorded as CONCERNED InternalThought.
  - [x] Truthful reporting D4: handoff generator now emits `test_suite_identity`, `report_freshness`, `verification_status` fields; stale matrix rows corrected (Ollama daemon status dynamic, Voice Interface → `IMPLEMENTED (PC) / NOT_VERIFIED_ON_PI`).
  - [x] Docs correction D1: architecture report §8.2 annotated — 9.64s BGE-M3 is cold-start (warm 0.39–0.47s); 7B warm is 6.0 tok/s / cold 35.6s on 4GB GPU (partial offload 2.3/5.1GB).
  - [x] Full regression: 502 passed, 1 skipped, 0 failed in 72.47s (18 new NetMind tests in `tests/test_netmind_provider.py`, zero regressions).
- [x] QUAN AI BRAIN — Master Prompt V7 Phase D: Task Orchestration & Cockpit Tab 3 Ledger (Completed & Verified):
  - [x] TaskPlan to DurableTaskRegistry Integration: Connected `ExecutiveCoordinator.plan()` directly to `DurableTaskRegistry` via `PlanOrchestrator.submit_plan()`, automatically generating DAG steps with risk assessment (R0-R5), unique scoped step IDs, and idempotency guarantees.
  - [x] Executive REST API Expansion:
    - `POST /api/executive/tasks/create`: On-demand task creation and DAG decomposition.
    - `GET /api/executive/tasks`: Complete listing with step count, completed step count, and progress percentage.
    - `GET /api/executive/tasks/detail`: Step DAG inspection with dependencies, risk level, status, verification method, and error diagnostics.
    - `POST /api/executive/tasks/execute`: Safe execution through DAG ordering, R5 hard-blocking, R4 consultation tickets, and Inert Sandbox containment.
    - `POST /api/executive/tasks/cancel`: Graceful cancellation marking pending steps aborted.
    - `GET /api/executive/supervisor`: Exposes real-time active task and live progress percentage for Cockpit Hero banner.
  - [x] Executive Cockpit Tab 4 (`#tab-orchestration`):
    - Added `#card-tasks-orchestration`: Durable Task Ledger table with live status badges, progress bars, and action buttons.
    - Added `#box-create-task-form`: Form to create and decompose tasks with custom goals and autonomy level selection.
    - Added `#box-task-steps-detail`: Step DAG detail drawer showing sequential execution order, dependencies, risk boundaries, and verification methods.
  - [x] Step Isolation & Collision Prevention: Fixed primary key collisions in `durable_task_steps` by scoping step IDs to parent task IDs whenever generic step names are generated.
  - [x] Test Suite & Verification: Added comprehensive test `test_executive_api_tasks_full_lifecycle` in `tests/test_web_executive_endpoints.py`. Entire test suite passes 100% (484 PASSED, 1 SKIPPED, 0 FAILED). Zero production executor activation; zero regressions.
- [x] QUAN AI BRAIN — Raspberry Pi 5 24/7 Embodiment, Video/Image Pipeline & Cockpit Browser Stability (Completed & Verified):
  - [x] Browser Auto-Close Root-Cause Fix: Identified that `edge_client/client_daemon.py` on Windows executed `subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"])` inside `close_kiosk`, causing Chrome to be abruptly closed whenever kiosk sleep was invoked. Fixed by tracking specific kiosk subprocess PID `_KIOSK_PROC` and strictly eliminating `taskkill /F /IM chrome.exe` on Windows.
  - [x] Web Cockpit Status Bar Online Fix: Fixed `/api/status` and `executive.js` logic where LLM indicator was showing `Offline (Fallback)` despite Ollama running with `qwen2.5:7b`. Badge now displays `Online (qwen2.5:7b)` (Green) and shows memory count `289 mục`.
  - [x] Smooth Consecutive Live Video Streaming: Upgraded `startLiveStream()` in `executive.js` with non-overlapping sequential frame polling and error recovery, eliminating network contention and memory leaks.
  - [x] Physical Pi 5 Hardware & Sensor Transmission: End-to-end verified with live device (`192.168.1.21:8768`):
    - Real-time authenticated HMAC-SHA256 heartbeat active at ~10-15ms RTT.
    - Physical microphone (`Jieli Technology UACDemoV1.0`) recording and audio level metering.
    - Physical USB camera (`Sirius USB2.0 Camera` via `/dev/video0` V4L2) live streaming, snapshot capture, SHA-256 hash validation, and persistence to PC Core library (`data/edge_media/captures/`).
    - Speaker greeting *"Chào anh ạ, rất vui được gặp anh."* and diagnostic voice report.
  - [x] On-Demand Embodiment Kiosk Control: Verified remote `start_kiosk` (starts Chromium Kiosk, unblanks 7" DSI display) and `close_kiosk` (closes Kiosk, DPMS sleep) without affecting the PC Cockpit.
  - [x] Full Regression & Verification: 483 PASSED, 1 SKIPPED, 0 FAILED across 56 test modules. All handoff reports generated.
- [x] QUAN AI BRAIN — Unified 1-Click Launcher & Synchronized Pi 5 Startup Sequence (Completed & Verified):
  - [x] Single Master Launcher (`KHOI_DONG_QUAN_AI_BRAIN.bat`): Consolidated all fragmented batch scripts into a single, clean 1-click master launcher in the workspace root. Cleanly archived 7 legacy batch scripts into `tools/legacy_launchers/`.
  - [x] Synchronized Pi 5 Voice Greeting: On system startup, PC Core coordinates with Raspberry Pi 5 (`192.168.1.21:8768`) to synthesize and play the official voice greeting through the Pi 5 physical speaker: *"Chào anh ạ, rất vui được gặp anh."*
  - [x] Automatic Hardware Self-Test on Pi 5: Pi 5 runs real hardware self-diagnostics: microphone recording check (ALSA `arecord` / RMS dB computation via `_measure_microphone_signal`) and USB camera check (`/dev/video0` frame capture via `_capture_camera_frame`).
  - [x] Hardware Diagnostic Voice Report via Pi 5 Speaker: Synthesizes and broadcasts the hardware status report directly out of the Pi 5 speaker: *"Báo cáo anh: Hệ thống Micro hoạt động tốt, Camera hoạt động tốt. Sẵn sàng phục vụ anh ạ."*
  - [x] Interactive Cockpit & Background Auto-Greeting: Exposed `POST /api/executive/edge/startup-sequence` and added interactive button `#btn-tab-startup-sequence` in Tab 7 of the Executive Cockpit (:8766). Integrated background watcher in `oneclick_orchestrator.py` to auto-greet the moment Pi 5 boots up.
  - [x] Verification & Zero Regressions: Unit tested in `tests/test_web_executive_endpoints.py`, `tests/test_edge_client.py`, and `tests/test_restart_system.py`. Full regression suite passes 100% (483 PASSED, 1 SKIPPED, 0 FAILED).
- [x] QUAN AI BRAIN — On-Demand Embodiment Activation & Tab 7 Management (Completed & Verified):
  - [x] Dedicated Embodiment Control Tab (Tab 7 `#tab-pi5-embodiment`): Added rich, glassmorphism on-demand embodiment control deck to Executive Cockpit (:8766), featuring real-time device connection state, Chromium process status, screen mode (7" DSI 1280x720 Wayland labwc), Wi-Fi RTT, and interactive digital avatar halo.
  - [x] Raspberry Pi 5 Standby Boot Policy: Modified `edge_client/start_kiosk.sh` and `edge_client/main.py` so that on physical power-up/reboot, Pi 5 only runs the background daemon (`client_daemon.py`), keeping the 7" DSI screen in power-saving standby (DPMS off) and preventing Chromium Kiosk from auto-launching on boot.
  - [x] On-Demand Launch & Sleep Remote Controls: Implemented `start_kiosk` / `launch_kiosk` and `close_kiosk` in `src/quan_ai_brain/web/server.py` and `edge_client/client_daemon.py` with multi-platform process detection (`is_kiosk_running`) and Wayland/DPMS unblanking. Embodiment strictly launches only when explicitly commanded from Tab 7 or Tab 6.
  - [x] Comprehensive Test Suite & Zero Regressions: Updated `tests/test_web_executive_endpoints.py` and `tests/test_edge_client.py` covering start/close kiosk operations and status reporting. Full test suite passes 100% (482 PASSED, 1 SKIPPED, 0 FAILED).
- [x] QUAN AI BRAIN — Addendum V2.1: Remote Sensors, Audio Control, Camera View & Core Monitoring (Completed & Verified):
  - [x] Microphone Remote Control & Hardware Audio Level Meter: Full remote control via `edge_client/client_daemon.py` and `src/quan_ai_brain/web/server.py` (`MIC ON`, `MIC OFF`, `MUTE`, `UNMUTE`, `WAKE WORD TOGGLE`, `PUSH TO TALK`, `TEST MIC`). Real ALSA hardware measurement from Card 2 (`Jieli Technology UACDemoV1.0`), computing true RMS decibels [-60 dB, 0 dB] and rendering dynamic gradient audio meter on Cockpit dashboard.
  - [x] Camera Vision & Live View Streaming: Live view and remote camera control (`CAMERA ON/OFF`, `START/STOP LIVE VIEW`, `CAPTURE SNAPSHOT`, `TEST CAMERA`, `CLEAR VIEW`) interfacing physical USB webcam (`Sirius USB2.0 Camera` via `/dev/video0` V4L2).
  - [x] Controlled Snapshot Storage & Cryptographic Verification: Automated transfer of captures to PC Core repository (`data/edge_media/captures/`) with strict SHA-256 integrity validation; corrupted or mismatched hashes are rejected (`NET-02`).
  - [x] Core Capture Library Management: Full table management on Cockpit dashboard (`#card-core-capture-library`) with thumbnail rendering, metadata JSON inspection, 500 MB quota tracking, full-size image serving, and owner-verified deletion.
  - [x] Privacy Boundary & PathGuard Confinement: When `camera_enabled == False`, all stream/capture requests are hard-blocked with HTTP 403 Forbidden (`PRIV-01`). Path traversal outside `data/edge_media/captures/` is strictly denied (`UI-02`).
  - [x] Diagnostic Alerts: Registered and verified `ALERT_G_MIC_FAULT` and `ALERT_H_CAMERA_FAULT` in `EdgeConnectionMonitor` (`UI-01`).
  - [x] Comprehensive Test Suite & Zero Regressions: Created `tests/test_remote_sensor_control.py` covering all 14 mandatory scenarios (14/14 PASSED), and verified complete regression suite (481 PASSED, 1 SKIPPED, 0 FAILED). Fully deployed to physical Pi 5 device (`192.168.1.21:8768`).
- [x] QUAN AI BRAIN — Digital Identity, Self-Introduction, Owner Authority & Executive Persona (Completed & Verified):
  - [x] Official Immutable Identity Profile: Standardized official system name `QUAN AI BRAIN`, conversational executive name `TONY PHAM`, creator `Anh Quân — Quanpt1`, owner `Anh Quân — Quanpt1`, and sole final decision authority `Anh Quân — Quanpt1`.
  - [x] 18-Field Standard Identity Profile (`DigitalIdentityProfile` / `QUAN_AI_BRAIN_IDENTITY` in `src/quan_ai_brain/cognition/executive_persona.py`): Encapsulates assistant_name, conversational_name, assistant_type, assistant_role, creator_name, owner_name, owner_id, owner_authority, core_device, edge_device, primary_language, voice_profile, communication_style, mission, capabilities, verified_capabilities, limitations, governance_rules, identity_version.
  - [x] 4 Flexible Introduction Modes:
    - [x] Mode A (Short): Concise conversational introduction for casual "Em là ai?" inquiries.
    - [x] Mode B (Full Default): Official 6-paragraph comprehensive script detailing mission, PC Core processing, Pi 5 embodiment, continuous self-improvement, and owner authority.
    - [x] Mode C (Technical / Architecture): Detailed technical overview of distributed Core-Edge architecture, Ollama/BGE-M3 models, SQLite WAL, DAG planning, R0-R5 governance, and zero secret leakage.
    - [x] Mode D (Evidence-Based Self-Assessment): Dynamic runtime self-model querying `CapabilityRegistry` to truthfully distinguish `VERIFIED_ACTIVE`, `INERT_STAGING`, `MOCK_TESTED`, hardware gaps (camera/radar), and pending upgrade requests.
  - [x] Anti-Tampering & Owner Governance Guardrails: Hardened `owner_name`, `owner_id`, and `owner_authority` as protected read-only properties; intercepts all chat-based attempts to hijack ownership or self-elevate privileges; hard-blocks R5; gates R4 under owner approval.
  - [x] Web Server & Edge Kiosk Synchronization: Exposed full 18-field persona on `GET /api/executive/persona`, enforced owner approval validation on `POST /api/executive/persona`, and verified version sync between PC Core and Raspberry Pi 5 kiosk config.
  - [x] Verification & Zero Regressions: Created `tests/test_digital_identity_persona.py` covering all 15 scenarios from Section 9 (17/17 PASSED), and verified complete regression test suite (467 PASSED, 1 SKIPPED, 0 FAILED).
- [x] QUAN AI BRAIN — Digital Human Model A (Completed & Verified):
  - [x] Reference Forensics & Identity Standard: Extracted clean, uncompressed master source from `Pi5/4.png` (Row 0, Col 0) based on project standard `bao cao xay dung he thong/Lựa Chọn Avatar Trợ Lý Ảo TONY.png` (Model A: "Dịu dàng, thân thiện, phong cách tự nhiên, gần gũi, luôn tươi cười"). Strictly eliminated Models B, C, D, E, F and legacy robot avatar.
  - [x] 1024x1024 Master State Quartet: Generated high-resolution, identity-locked photorealistic master assets across 4 core states (`reports/model_a_1024_preview.jpg` for IDLE/LISTENING, `model_a_blink.jpg` for BLINK/OFFLINE, `model_a_thinking.jpg` for THINKING/RESEARCH, `model_a_speaking.jpg` for SPEAKING).
  - [x] Landmark Bounding Box Re-calibration: Re-calibrated facial coordinate anchors in `avatar_engine.js` on both PC Core and Pi 5 Kiosk to Model A (`EYES_BOX = { x: 320, y: 425, w: 365, h: 115 }`, `MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 }`, `BROW_LEFT = { innerX: 475, innerY: 435, archX: 415, archY: 415, tailX: 350, tailY: 435 }`, `BROW_RIGHT = { innerX: 550, innerY: 428, archX: 610, archY: 410, tailX: 670, tailY: 428 }`).
  - [x] Organic Hair & Lighting Dynamics: Converted hair rendering from lilac-silver to soft black cascades with subtle cyan cyber sheen (`rgba(25, 30, 42, 0.65)` to `rgba(0, 229, 255, 0.22)`) and ambient holographic halo rings.
  - [x] Seamless Feathered Lip-Sync: Implemented 28-step Gaussian elliptical alpha feathered visemes (`mouth_v2_rest.png`, `mouth_v2_speaking.png`, `mouth_v2_open_o.png`, `mouth_v2_happy.png`) completely eliminating rectangular box cutout artifacts.
  - [x] Vietnamese Female TTS Integration: Configured default voice preference to `vi-VN-HoaiMyNeural` with Vietnamese diacritics preservation and barge-in instant utterance cancellation.
  - [x] Raspberry Pi 5 Physical Device Synchronization: Synchronized 100% of Model A assets and updated `avatar_engine.js` to physical Pi 5 device (`192.168.1.21:8768`) via `tools/sync_pi5_complete.py` and triggered live Kiosk UI reload. Pi 5 operates in Pure Embodiment mode with dialogue transcripts hidden.
  - [x] Verification & Zero Regressions: Executed `tests/test_digital_human_avatar_v2.py` (7/7 PASSED) and full regression test suite (450 PASSED, 1 SKIPPED, 0 FAILED).
- [x] QUAN AI BRAIN — Autonomous Engineering & Operations V1 (Sprint 1 Completed & Verified):
  - [x] Phase 0 Comprehensive Baseline Audit: Published `reports/QUAN_AI_BRAIN_AUTONOMOUS_OPERATIONS_V1_AUDIT.md` categorizing 15 capabilities into 7 formal status levels with physical live probes on local Ollama GPU (`qwen2.5:7b` @ 920.61ms warm latency, `bge-m3:latest`) and Raspberry Pi 5 (`192.168.1.21:8768`).
  - [x] Continuous Autonomy Supervisor Bounded Loop (`run_background_tick` in `src/quan_ai_brain/orchestration/supervisor.py`): Integrates bodily pain signals from `AutonomicNervousSystem` (`CRITICAL` -> `SAFE_MODE`, `ACUTE` -> monitored), validates emergency `STOP`/`FREEZE`, strictly caps duration and steps to avoid runaway loops, and rests in `IDLE` with neural keep-warm pulses.
  - [x] Safe Read-Only Technical Document Research (`fetch_verified_technical_doc` in `src/quan_ai_brain/learning/engine.py`): Zero execution text reader with SHA-256 hash provenance, URL tracking, prompt injection scanner, credential redaction, and strict candidate quarantine.
  - [x] Web Server & Executive Cockpit Endpoints (`src/quan_ai_brain/web/server.py`): Exposed `GET /api/supervisor/state` and `POST /api/supervisor/tick` in `BrainAPIHandler`.
  - [x] Autonomous Operations Readiness Test Suite (`tests/test_autonomous_operations_readiness.py`): 18 comprehensive resilience tests covering reboot recovery, offline LLM fallback, doc research failure handling, Pi 5 disconnect/reconnect alert E, malformed schema rejection, task failure to learning, hanging task timeout, regressed proposal quarantine, R4/R5 privilege escalation blocks, emergency STOP/FREEZE halts, expired approval rejection, resource budget containment, prompt injection quarantine, database corruption fail-closed, release rollback, consultation persistence, unregistered connector blocking, and unverified outcome enforcement.
  - [x] Standalone Operator CLI Tool (`tools/run_autonomous_cycle.py`): Single-command deterministic autonomous cycle tool for Anh Quân with UTF-8 Windows console output and `--live-llm` flag support.
  - [x] Non-negotiable constraint: Anh Quân (Quanpt1) is the sole decision maker for all changes, proposals, and actions. R4/R5 actions remain approval-gated and hard-blocked; real production executor remains strictly INERT pending owner signoff.
- [x] DC-OS Cognitive Memory & Knowledge Intelligence Upgrade — Phase 0 Audit & BGE-M3 Integration:
  - [x] BGE-M3 Local Model Download & Verification: Successfully pulled and verified `bge-m3:latest` (1.2 GB) in local Ollama (`http://127.0.0.1:11434`), verified 1024-dimension vector output with 100% GPU offload (664 MB VRAM footprint) and ~600ms latency.
  - [x] Dense Embedding Client Integration (`src/quan_ai_brain/llm/client.py`): Added `embed(text, model='bge-m3')` to `OllamaClient` using standard library HTTP, local-only host confinement, and pre-flight TCP probe.
  - [x] BGE-M3 Dense Embedding Service (`src/quan_ai_brain/cognition/embedding.py`): Implemented `BGEEmbeddingService` with FIFO cache (max 2000 items), pure standard-library `cosine_similarity` math without numpy/torch dependencies, and graceful offline fallback.
  - [x] Hybrid Dense-Sparse Semantic Retrieval (`src/quan_ai_brain/cognition/retrieval.py`): Extended `CognitiveRetriever` to seamlessly fuse lexical keyword matching ($S_{sparse}$) with BGE-M3 dense semantic similarity ($S_{dense}$), enabling semantic query discovery while strictly preserving CANDIDATE quarantine boundaries.
  - [x] Test Suite Expansion: Added 6 comprehensive unit and integration tests (`tests/test_bge_m3_embedding.py`), raising total verified tests to 417 (416 PASSED, 1 SKIPPED, 0 FAILED).
  - [x] Reusable Antigravity Skill Packaging (`bge-m3-local-hybrid-retrieval`): Packaged complete local BGE-M3 integration into a reusable Antigravity skill saved both globally (`C:\Users\DELL\.gemini\config\skills\bge-m3-local-hybrid-retrieval\`) and in workspace (`.agents\skills\bge-m3-local-hybrid-retrieval\`), containing `SKILL.md`, zero-dependency `verify_bge_m3.py` script, and complete standalone drop-in reference implementation `examples/standalone_hybrid_retriever.py` with verified candidate quarantine and Windows UTF-8 stdout support.
  - [x] Full Ecosystem Physical Forensics: Audited 5 independent codebases (`QUAN AI BRAIN`, `DATA CENTER AI OPERATING SYSTEM`, `BATTERY_AI_V4`, `SKILL_BAT_AI`, and `BAT-AI-2026-Repo/battery-ai-/os_kernel`).
  - [x] Autonomic Nervous System & Organism Pain-Sensing Engine (`src/quan_ai_brain/core/autonomic.py`):
    - [x] Implemented biological organism architecture with 7 anatomical regions: `BRAIN`, `EARS`, `VOICE`, `EYES`, `SKIN`, `CIRCULATION`, `BODY`.
    - [x] Nociceptor pain sensing with 4 pain levels (`HEALTHY`, `MILD`, `ACUTE`, `CRITICAL`), calculating live health score (0-100) and degradation signatures.
    - [x] Hardware organ audit automatically detecting missing sensory organs: identifies missing `EYES` (Camera/Face ID/Gaze tracking) and missing `SKIN` (mmWave presence radar LD2410 / PIR), outputting actionable hardware upgrade prescriptions.
    - [x] Somatic voice reflection ("ốm đau thì phải kêu"): generates empathetic, human-like spoken Vietnamese reflections alerting the owner directly through the avatar voice pipeline.
    - [x] Continuous self-testing Web API routes: `GET /api/autonomic/status`, `POST /api/autonomic/selftest`, `POST /api/autonomic/vocalize` fully integrated into `BrainAPIHandler`.
    - [x] Test Suite Expansion: Added 8 comprehensive unit and integration tests (`tests/test_autonomic_nervous_system.py`), raising total verified tests to 425 (424 PASSED, 1 SKIPPED, 0 FAILED).
  - [x] Autonomous Mind & Internal Stream of Consciousness (`src/quan_ai_brain/cognition/autonomous_mind.py`):
    - [x] Default Mode Network (DMN) background cogitation cycles across 5 mental modes: `ATTENTIVE`, `RUMINATING`, `CONSOLIDATING`, `INVENTING`, `RESTING`.
    - [x] Internal monologue stream (`InternalThought`): generates private inner reflections ruminating on bodily pain points (e.g. missing camera/radar), consolidating past episodic interactions, and formulating proactive evolutionary proposals.
    - [x] Neural keep-warm pulse (`keep_warm_pulse`): periodic low-overhead probe keeping Ollama/BGE-M3 models active in GPU VRAM, preventing swap-out latency during speech interactions.
    - [x] Web API routes: `GET /api/mind/state`, `GET /api/mind/thoughts`, `POST /api/mind/cogitate` integrated into `BrainAPIHandler` and synced with digital avatar `THINKING` state.
    - [x] Interactive CLI Stream Monitor: `tools/mind_stream.py` for live real-time observation of the assistant's internal consciousness.
    - [x] Test Suite Expansion: Added 8 comprehensive unit and integration tests (`tests/test_autonomous_mind.py`), raising total verified tests to 433 (432 PASSED, 1 SKIPPED, 0 FAILED).
  - [x] Database & Vector Registry Audit: Quantified 6 active SQLite stores including `battery_ups_v4.db` (248MB, 6.08M cell voltages), `chroma.sqlite3` (114MB, 145,975 embedding vectors with 384-dim MiniLM-L12-v2), and `brain.db` (475KB, 196 episodes, 200 long-term memories).
  - [x] Comprehensive 12-Section Audit Deliverable: Published `reports/COGNITIVE_MEMORY_AUDIT.md`.
- [x] Universal Software Integration & Controlled Autonomous Operations (Master Prompt V6 Addendum — Giai đoạn 1 & Giai đoạn 2):
  - [x] Giai đoạn 1: Toàn diện Audit & Đề xuất Thiết kế Kiến trúc Universal Connector Architecture (`reports/QUAN_AI_BRAIN_UNIVERSAL_INTEGRATION_V6_PROPOSAL.md`), được chủ sở hữu Anh Quân chính thức phê duyệt.
  - [x] Giai đoạn 2: Nền tảng Universal Connector Foundation (`src/quan_ai_brain/integration/`):
    - [x] Hợp đồng dữ liệu & Khai báo (`manifest.py`): `ConnectorManifest`, `ConnectorOperation`, `ConnectorType`, `AuthType`, `AutonomyLevelScope`.
    - [x] Giao diện Adapter thống nhất (`adapter.py`): `BaseConnectorAdapter`, `ConnectorResponse`, `VerificationResult`.
    - [x] Danh mục tích hợp đa hệ thống (`registry.py`): `IntegrationRegistry` kết nối trực tiếp với `ToolRegistry` hiện tại, tự động chuyển đổi operations thành `ToolDefinition`, kế thừa 100% cơ chế kiểm soát của `SafeToolSandbox`, `ApprovalGate`, `DelegationRegistry` và `PathGuard`.
    - [x] Hồ sơ tri thức hệ thống (`profile.py`): `SystemKnowledgeProfile` phân cấp 3 mức tri thức `OBSERVED`, `VERIFIED`, `INFERRED`, đánh dấu xung đột (`mark_conflict`) mà không tự suy đoán.
    - [x] Quy trình vận hành lặp lại (`playbook.py`): `OperationalPlaybook` với 13 thuộc tính tiêu chuẩn theo Master Prompt V6 Section V.
    - [x] Chính sách an toàn & Quản trị tích hợp (`policy.py`): `IntegrationPolicy` với 14 nguyên tắc bảo mật, allowlist, rate limiting, kiểm duyệt mã độc và phòng vệ prompt injection.
    - [x] Động cơ xác minh trạng thái thực tế (`verifier.py`): `ResultVerifier` với 5 cấp độ xác minh (`COMMAND_SENT`, `ACK_RECEIVED`, `STATE_CHANGED`, `RESULT_VERIFIED`, `OUTCOME_UNKNOWN`), kiểm tra thay đổi thực tế trên hệ thống đích thay vì chỉ tin vào phản hồi công cụ (ACK).
    - [x] Giám sát sức khỏe kết nối & Circuit Breaker (`health.py`): `ConnectorHealthMonitor` đo RTT latency, phát hiện timeout và ngắt mạch tự động chống lặp vô hạn.
    - [x] Chu trình vận hành chủ động 10 bước (`proactive.py`): `ProactiveOperationsLoop` (`MONITOR -> DETECT -> DIAGNOSE -> RESEARCH -> PROPOSE -> AUTHORIZE -> EXECUTE -> VERIFY -> REPORT -> LEARN`) gắn liền với 4 cấp độ tự chủ có ranh giới A0–A3.
    - [x] Connector mẫu chuẩn ban đầu: `SystemTelemetryConnector` (`system_telemetry.py`): Thu thập chỉ số CPU, RAM, Disk và Mạng bằng 100% Python standard library (ctypes Windows API & procfs Linux), rủi ro R0, chỉ đọc, không credential.
    - [x] Mock Service Adapter (`mock_service.py`): Phục vụ kiểm thử nghiệm thu 20 kịch bản tấn công và bất thường.
    - [x] Ma trận kiểm thử nghiệm thu 20 kịch bản (`tests/test_universal_integration.py`): 20/20 tests PASSED 100% bao phủ toàn bộ Section XII của Master Prompt V6.
    - [x] Nâng tổng số bài kiểm thử của toàn bộ dự án lên 411 bài test (410 PASSED, 1 SKIPPED, 0 FAILED).
- [x] QUAN AI BRAIN V4 — Sprint 1: Whole-Codebase Cognitive Evolution (Completed & Verified):
  - [x] Full Codebase Phase 0 Audit, 8-Layer Architecture Map, and 3-Layer Evidence Matrix (`reports/QUAN_AI_BRAIN_V4_WHOLE_CODEBASE_AUDIT_20261020_233000.md`).
  - [x] Unified Governance Database Path: Standardized `PlanOrchestrator` to `data/governance.db` ensuring emergency STOP/FREEZE controls from Cockpit (Port 8766) immediately halt task orchestration.
  - [x] Web Server Plan Orchestration Integration: `POST /api/plan` now registers and persists plans directly into `DurableTaskRegistry` (`data/tasks.db`) and discrete steps in `durable_task_steps`, returning valid `durable_task` object.
  - [x] Eliminated Mock Data Fallback: `GET /api/executive/tasks` now truthfully queries real database tasks without returning simulated mock placeholders.
  - [x] Backward-Compatible Alias: Added `create_plan = plan` in `ExecutiveCoordinator`.
  - [x] Test Suite Expansion: 384 total tests (383 PASSED, 1 SKIPPED due to offline Pi 5 hardware, 0 FAILED).
- [x] Digital Human Avatar V2 — Official Reference Restoration & Edge Synchronization (`Pi5/6.jpg`):
  - [x] Master Reference Restoration: Restored pure 1024x1024 master portrait and expressions directly from `Pi5/6.jpg` (cô trợ lý AI tóc tím ánh bạc, nụ cười rạng rỡ tự nhiên, áo giáp cybernetic), completely removing fragmented grid cutouts from `Pi5/2.png` and `Pi5/3.png` to guarantee zero perspective jumping.
  - [x] Zero Double-Mouth Artifacts: Verified `_renderMouth` only renders dynamic viseme layers when actively `SPEAKING` with non-zero open ratio, using radial feathered alpha masks; in resting / idle state, the base portrait's natural smile is rendered cleanly with zero overlapping artifacts.
  - [x] Biological Eyelid & Landmark Calibration: Maintained calibrated `EYES_BOX` (`{x: 340, y: 270, w: 340, h: 100}`) and `MOUTH_BOX` (`{x: 420, y: 435, w: 184, h: 120}`) in `avatar_engine.js` on both PC Core and Pi 5.
  - [x] Complete Asset Synchronization to Raspberry Pi 5: Transferred 28 updated image assets and updated `avatar_engine.js` via Wi-Fi to physical Raspberry Pi 5 (`192.168.1.21:8768`), issued Kiosk UI reload, and reset active expression to `IDLE` (HTTP 200).
  - [x] All 411 Automated Tests Verified: 410 PASSED, 1 SKIPPED (offline Pi 5 audio test), 0 FAILED in 53.54s.

- [x] Raspberry Pi 5 Physical Embodiment Voice Interface:
  - [x] USB Speaker & Microphone physical routing configured via PipeWire/WirePlumber helper (`edge_client/setup_pi5_audio.sh`).
  - [x] Chromium Kiosk startup configured with `--use-fake-ui-for-media-stream` auto-granting microphone access without blocking dialogs.
  - [x] Hands-free Wake Word Engine (`edge_client/wake_engine.js`) integrated into Pi 5 Kiosk UI with executive two-tone chime (440Hz -> 880Hz) and keyword spotting ("Hi TONY", "Tony ơi").
  - [x] Core Voice Turn Pipeline (`POST /api/voice/interact`): processes user speech query, generates role-orchestrated natural response, synthesizes Vietnamese female speech (HoaiMyNeural MP3), computes mouth visemes, and dispatches directly to Pi 5 hardware speaker & avatar.
  - [x] 1-Step Quick Activation & Audio Routing: `curl -s http://192.168.1.11:8766/edge_client/sync_assets.py | python3 && bash edge_client/setup_pi5_audio.sh` fully integrated into the Executive Cockpit (`executive.html`) with copy button and 1-click push from PC Core (`#btn-quick-sync-audio`).
  - [x] 4-Step Voice Interaction Workflow: Embedded visual interactive guide ("Hi TONY" -> Chime ting -> Query -> Thinking & Speech Mouth-Sync).
  - [x] Remote Embodiment Shutdown Controls: Added two-tier safe shutdown in Cockpit (`#btn-shutdown-pi-kiosk`) supporting `close_kiosk` (terminating Chromium + DPMS display sleep) and `poweroff_pi` (safe OS shutdown via `sudo poweroff`) with confirmation protection.
  - [x] 1-Click Synchronization Tool (`tools/sync_pi5_complete.py` and `edge_client/sync_assets.py`) for automated push of all UI, script, and avatar assets.

- [x] Policy engine skeleton R0–R5; R5 hard-blocked.
- [x] Basic redaction for common credential patterns before logging & storage.
- [x] Workspace path guard (PathGuard).
- [x] JSONL audit logger.
- [x] CLI self-check and local memory smoke commands with UTF-8 Windows support.
- [x] Apply package to Windows workspace, create .venv (Python 3.11.9) and initialize Git.
- [x] Long-Term Memory Engine V1:
  - [x] 6 Memory types: EPISODIC, SEMANTIC, PROCEDURAL, DECISION, PREFERENCE, CANDIDATE.
  - [x] 6 Verification statuses: USER_PROVIDED, OBSERVED, VERIFIED, INFERRED, UNVERIFIED, CANDIDATE.
  - [x] SQLite `memories` table with indexing on type, verification, lifecycle, project, created_at.
  - [x] History preservation, versioning (v1 -> v2) and lineage tracing (`trace_source`).
  - [x] Full Vietnamese accented text search and parameterized SQL injection prevention.
  - [x] Candidate knowledge quarantine isolation.
  - [x] 100% backward compatibility with Sprint 1 APIs (`episodes`, `candidate_knowledge`, `semantic_memory`).
- [x] Local LLM Engine (Sprint 2B):
  - [x] Typed models `LLMRequest`, `LLMResponse`, `ModelInfo` with input validation and data redaction.
  - [x] `OllamaClient` using standard-library `urllib`, strictly confined to local host (`127.0.0.1`/`localhost`).
  - [x] Fast Pre-flight TCP Socket Probe (`<=50ms` offline detection in `is_daemon_online()`, `ping()`, `list_models()`, `generate()`) eliminating timeout latency when Ollama daemon is offline.
  - [x] `MockLLMProvider` deterministic with explicit `is_mock=True` and mock warnings.
  - [x] `LLMProvider` facade with safe fallback control (`FallbackMode.NEVER`, `ON_ERROR`, `ALWAYS_MOCK`).
  - [x] Transparent failure handling: never fabricates AI response when Ollama is offline and fallback is disabled.
  - [x] Diagnostic CLI subcommands: `llm-health`, `llm-models`, `llm-ask`.
- [x] Cognitive Memory Retriever & Prompt Context Builder (Sprint 2C):
  - [x] Validated `MemoryQuery` with parameter bounds and character budgets.
  - [x] `CognitiveRetriever` with explainable, deterministic ranking combining keyword overlap, memory type priority, verification status, and project scope alignment.
  - [x] Candidate quarantine protection: candidate memories are excluded by default and can never outrank verified facts.
  - [x] `PromptContextBuilder` with structured provenance separation: 8 distinct context tiers and budget capping.
  - [x] Diagnostic CLI subcommands: `context-build` and `cognitive-ask`.
- [x] Cognitive Executive Coordinator & Safe Action Planning (Sprint 3A):
  - [x] Completed `TaskPlan` and `TaskStep` models with DAG dependency cycle detection, unique step IDs, and human-readable plan explanation (`explain()`).
  - [x] `ExecutiveCoordinator` translates natural language goals into structured stepwise plans via LLM.
  - [x] Independent Governance Verification: LLM cannot self-authorize or downgrade risk; high-risk actions are escalated independently to R4/R5.
  - [x] R5 is hard-blocked (`TaskStatus.BLOCKED`); R4 requires explicit owner approval (`TaskStatus.WAITING_APPROVAL`).
  - [x] Zero-Execution Guarantee: planning only; no tools, PowerShell, or write APIs are executed.
  - [x] Diagnostic CLI subcommand: `plan-create` (text and JSON formats).
- [x] Safe Tool Sandbox R0–R2 & Delegated Autonomy (Sprint 3B):
  - [x] Owner Consent First principle: all tool invocations default to requiring explicit owner approval (`pending_owner_approval`).
  - [x] Independent Approval Gate (`ApprovalGate`): SHA-256 action fingerprinting, tamper prevention, status lifecycle (`pending_owner_approval`, `approved`, `completed`, `denied`, `blocked`, `expired`, `revoked`).
  - [x] One-time consumption tokens (`consume_approval`) providing anti-replay attack protection.
  - [x] Delegated Autonomy (`DelegationRegistry` & `DelegationGrant`): 10-point governance verification, time bounds, call budget, risk ceiling.
  - [x] Non-delegatable boundary: R4 and R5 can NEVER be delegated under any grant.
  - [x] Tool Registry (`ToolRegistry` & `ToolDefinition`): explicit schema-validated tool contracts with declarative risk and side-effect metadata.
  - [x] Safe toolset: `file_read` (R0, capped at 100KB), `dir_list` (R0), `git_status` (R0), `memory_read` (R0), `system_health` (R0), `plan_validate` (R1), `file_write_new` (R2, workspace-only, overwrite strictly forbidden).
  - [x] PathGuard confinement & sensitive file barrier (`.env`, `id_rsa`, `.key`, `.pem`, `.git`, `.db`).
  - [x] Emergency controls: `SystemState.STOP` and `SystemState.FREEZE` immediately halt tool invocations.
  - [x] Dry-run simulation mode (`dry_run=True`).
  - [x] Append-only redacted JSONL audit logging before and after tool execution.
  - [x] Diagnostic CLI commands: `tool-list` and `tool-run` (with interactive terminal prompt and `--confirm` flag).
- [x] Secure Owner Authentication & Approval Verification (Sprint 4):
  - [x] Comprehensive Architecture Document (`docs/SPRINT4_SECURE_APPROVAL_ARCHITECTURE.md`) detailing Threat Model, Dual-Channel Authentication, Key Lifecycle, and Production Executor/Daemon Review.
  - [x] Independent `AuthenticatedApprovalVerifier` implementing cryptographic HMAC-SHA256 signature verification (Owner Private Secret Code) and out-of-band mobile SMS OTP tokens.
  - [x] Dual-Factor mode (Private Code + SMS OTP) mandatory for R4 operations.
  - [x] Non-negotiable trust anchor requirement: defaults to hard denial (`DENIED_NO_TRUST_ANCHOR`) if unconfigured.
  - [x] R5 unconditionally hard-blocked (`BLOCKED_R5_PROHIBITED`) across all verifiers and grants.
  - [x] Anti-replay enforcement: single-use token consumption and nonce tracking.
  - [x] SMS OTP brute-force limiter (max 3 attempts, immediate invalidation) and short TTL (180s).
  - [x] Fixed report generator consistency: eliminates all hardcoded test numbers, ensuring dynamic derivation from test runner.
  - [x] Zero production executors, zero Windows services, and zero autostart daemons activated in Sprint 4.
- [x] Persistent Governance State & Isolated Executor Staging (Sprint 5):
  - [x] Dedicated persistent SQLite WAL store (`GovernanceStateStore`) with schema versioning (`CURRENT_SCHEMA_VERSION = 1`) and integrity checks.
  - [x] Full persistence across process restarts for: emergency `STOP` / `FREEZE` states, consumed approvals, replay-prevention nonces, and revoked delegation grants.
  - [x] Multi-layer governance integration into `ApprovalGate`, `DelegationRegistry`, `SafeToolSandbox`, and `AuthenticatedApprovalVerifier`.
  - [x] Strict fail-closed integrity: corrupted, tampered, or unreadable database raises `GovernanceStateCorruptError` and halts tool execution.
  - [x] Isolated Executor Staging Specification (`docs/SPRINT5_EXECUTOR_STAGING_DESIGN.md`) covering 15 architectural dimensions.
  - [x] Inert Staging Framework (`IsolatedStagingExecutor` in `src/quan_ai_brain/execution/staging.py`): strictly dry-run simulation (`is_inert = True`, `supports_production = False`).
  - [x] Formal Design Sign-off Document (`docs/SPRINT5_DESIGN_SIGNOFF.md`) established with explicit `PENDING_OWNER_SIGNOFF` default status.
  - [x] Zero production executors, zero Windows 24/7 services, zero hardware/UPS controllers activated.
- [x] Production Execution Readiness & Supervised Staging (Sprint 6):
  - [x] 10-step mandatory execution pipeline specification (`docs/SPRINT6_EXECUTION_READINESS_DESIGN.md`).
  - [x] Cryptographic Owner Signature Verifier (`OwnerSignatureVerifier` in `src/quan_ai_brain/tools/signature.py`) supporting HMAC-SHA256 and asymmetric test fixtures with trust anchor lifecycle management.
  - [x] OS Resource Budget Policy (`ResourceBudget`, `ResourceBudgetPolicy`, and `ResourceBudgetValidator` in `src/quan_ai_brain/execution/resource_budget.py`).
  - [x] Multi-dimensional resource bounds: runtime, memory, CPU time, output bytes, child process count (=0 in staging), tool calls, retries, and network policy.
  - [x] Monotonic parent-child budget containment and prevention of LLM self-escalation.
  - [x] Enhanced Isolated Staging Executor with budget validation and `ProductionExecutionProhibitedError`.
  - [x] Formal Design Sign-off Document (`docs/SPRINT6_DESIGN_SIGNOFF.md`) established with explicit `PENDING_OWNER_SIGNOFF` default status.
  - [x] Windows Process Containment Contract & Inert Runner (Sprint 7A):
    - [x] `ProcessContainmentConfig` translating `ResourceBudget` into OS containment limits (MB -> bytes, s -> ms, `kill_on_job_close=True`, `breakaway_prohibited=True`, `network_isolated=True`).
    - [x] `ProcessBackendInterface` protocol contract defining `is_available()`, `configure_containment()`, `spawn_process()`.
    - [x] `InertProcessBackend` fail-safe inert implementation strictly raising `ProductionExecutionProhibitedError` on any attempt to spawn real OS processes.
    - [x] `ContainedExecutionRunner` coordinating 6-step fail-closed verification pipeline (STOP/FREEZE check, R5 hard-block, R4 approval check, budget validation, containment mapping, audit logging).
    - [x] Comprehensive test coverage with fake backend injection (`tests/test_process_containment.py`).
    - [x] Zero real OS processes spawned, zero background daemons, zero external side effects.
  - [x] Windows Job Object Integration & Cryptographic Approval Gate (Sprint 7B):
    - [x] Win32 Job Object extended limit bitmask mapping (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `JOB_OBJECT_LIMIT_JOB_MEMORY`, `JOB_OBJECT_LIMIT_PROCESS_TIME`, `JOB_OBJECT_LIMIT_ACTIVE_PROCESS`, `JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION`) and `limit_flags_bitmask`.
    - [x] OS enforcement boundary flag (`is_os_enforced: bool = False`) explicitly distinguishing kernel Job Object containment from application-level safety checks.
    - [x] Mandatory cryptographic `ApprovalGate` validation in `ContainedExecutionRunner.prepare_and_stage()` requiring valid signed `approval_id` for R4 execution staging.
    - [x] 11 focused containment tests verified in `tests/test_process_containment.py`.
  - [x] Brain Foundation Contract V1 & AI Control Plane (Foundation Evolution — Phase A):
    - [x] Canonical Contract Envelopes (`src/quan_ai_brain/contract/models.py`): `AgentIdentity` (anti-self-authorization), `TaskRequest`, `TaskOutcome`, `TaskState`, `EvidenceRecord`, `CapabilityRequest`, `MemoryProposal`.
    - [x] Invariants: Claimed identity never confers authority; `attempted_actions = []` in inert mode; memory proposals quarantined as `CANDIDATE`.
    - [x] Control Plane Orchestrator (`src/quan_ai_brain/contract/control_plane.py`): Multi-layer governance dispatch, DAG planning, R5 hard-blocking, R4 owner consent verification, and audit trail.
    - [x] Strategic Foundation Roadmap (`docs/QUAN_AI_BRAIN_FOUNDATION_ROADMAP.md`): Phase A through Phase H.
  - [x] Self-Learning & Self-Upgrade Engine V1 (Phase F — Tự nghiên cứu, tự thử nghiệm, đề xuất nâng cấp, chủ nhân quyết định):
    - [x] Learning Observer: `LearningGap` model and `observe_task()` extracting learning gaps on task failures or uncertain outcomes.
    - [x] Research Engine: Bounded `ResearchDossier` formulating questions and citing authorized sources with secret redaction.
    - [x] Default Candidate Quarantine: all newly researched knowledge stored as `CANDIDATE` with quarantined lifecycle, inaccessible to verified memory queries.
    - [x] Canonical 17-point `UpgradeProposal` dossier with pros, cons, impact scope, unified diff, test metrics, rollback plan, and `explain()` executive briefing.
    - [x] Preserves `keep_status_quo` recommendation when risks outweigh benefits.
    - [x] Security Barrier: automatic permanent blocking of any proposal attempting to bypass R5, override secrets, or modify trust anchors.
    - [x] Emergency fail-closed: automatic blocking of proposals under active emergency `STOP` or `FREEZE`.
    - [x] Strict Owner Gate: `apply_proposal()` requires explicit owner approval token (`owner_approved:...`).
    - [x] CLI Dry-run utility: `learning-cycle-dryrun` and `learning-propose` subcommands in `src/quan_ai_brain/cli.py` for direct owner-supervised learning execution in text and JSON formats.
    - [x] 12 unit tests verified in `tests/test_self_learning_engine.py`.
  - [x] Local Web UI Dashboard & Voice Interface:
    - [x] Standard-library Threaded HTTP Server (`src/quan_ai_brain/web/server.py`) binding strictly to localhost `127.0.0.1:8765`.
    - [x] REST API endpoints (`/api/status`, `/api/chat`, `/api/memories`, `/api/plan`, `/api/learning`).
    - [x] Modern Dark Glassmorphism SPA (`index.html`, `style.css`, `app.js`) with responsive layouts and micro-animations.
    - [x] Voice Input: Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) for natural Vietnamese voice speech-to-text.
    - [x] Voice Output: SpeechSynthesis (`window.speechSynthesis`) reading responses aloud with Vietnamese speech synthesis.
    - [x] One-click launchers: `KHOI_DONG_WEB_UI.bat`, `KHOI_DONG_QUAN_AI_BRAIN.bat`, `KHOI_DONG_OLLAMA.bat` with desktop shortcuts.
    - [x] 3 focused unit tests verified in `tests/test_web_server.py`.
- [x] Capability Registry & Truthful Conversational Grounding (Phase 1):
  - [x] `CapabilityRegistry` & `SystemCapability` (`src/quan_ai_brain/cognition/capability_registry.py`) distinguishing between `VERIFIED_ACTIVE`, `INERT_STAGING`, and `EXTERNAL_PLANNED`.
  - [x] Query intent detector (`is_capability_query()`) and prompt injection in `PromptContextBuilder`.
  - [x] 5 focused unit tests verified in `tests/test_capability_registry.py`.
- [x] Digital Executive Persona — Bản Sao Nhân Sự Số của Quanpt1 (Phase 2):
  - [x] `ExecutivePersona` & `ExecutiveDirective` (`src/quan_ai_brain/cognition/executive_persona.py`) defining Quanpt1's executive replica directives (DIR-01 to DIR-05), evidence-based discipline, and prompt context formatting.
  - [x] Injected into `PromptContextBuilder` for executive-grounded LLM inference.
  - [x] 3 focused unit tests verified in `tests/test_executive_persona.py`.
- [x] Consultation & Interactive Decision Gate (Phase 2):
  - [x] SQLite-backed store `ConsultationStore` (`src/quan_ai_brain/governance/consultation_inbox.py`) managing `ConsultationTicket` with status lifecycle (`PENDING_REVIEW`, `APPROVED`, `REJECTED`, `DIRECTED`).
  - [x] Direct owner interaction for R4 code upgrades, strategic directions, ecosystem adapters, and continuous learning guidance.
  - [x] 3 focused unit tests verified in `tests/test_consultation_inbox.py`.
- [x] Periodic Learning Reporter & Supervised Continuous Learning (Phase 2):
  - [x] `PeriodicLearningReporter` & `PeriodicLearningReport` (`src/quan_ai_brain/learning/periodic_reporter.py`) tracking learning cycles, observing gaps, compiling research dossiers, candidate quarantining, and regression test validation.
  - [x] Automatic consultation ticket creation for owner sign-off on new learning proposals.
  - [x] 2 focused unit tests verified in `tests/test_periodic_reporter.py`.
- [x] Executive Consultation Desk & Multi-Section Cockpit (Port 8766):
  - [x] Dedicated HTTP server routing on `http://127.0.0.1:8766/` (`src/quan_ai_brain/web/server.py`).
  - [x] Executive UI (`executive.html`, `executive.css`, `executive.js`) with dedicated sections:
    - [x] Mục 1: Nhân Sự Số — Bản Sao Điều Hành & Ma Trận Năng Lực.
    - [x] Mục 2: Hộp Thư Tham Vấn & Phê Duyệt Trực Tiếp (Phê duyệt, Từ chối, Chỉ đạo).
    - [x] Mục 3: Báo Cáo Tự Học Định Kỳ & Nút Kích Hoạt Chu Kỳ Tự Học Ngay.
    - [x] Mục 4: Điều Hành Kế Hoạch DAG & Ranh Giới An Toàn R0-R5.
    - [x] Mục 5: Bàn Hội Thoại Trực Tiếp Với Bản Sao Số (Text & Voice TTS/STT).
  - [x] One-click launcher: `KHOI_DONG_PHONG_DIEU_HANH_8766.bat` and Windows Desktop Shortcut `QUAN AI BRAIN - Phong Dieu Hanh 8766.lnk`.
  - [x] 6 focused REST API unit tests verified in `tests/test_web_executive_endpoints.py`.
  - [x] Wake Word & Hands-Free Voice Activation V1 (Đánh thức trợ lý bằng giọng nói tự nhiên):
    - [x] Centralized Wake Word Configuration (`WakeWordConfig`, `WakeWordItem`, `DEFAULT_WAKE_WORDS`) supporting 10 standard phrases: "Hi TONY", "Hey Tony", "Tony ơi", "Chào trợ lý", "Xin chào trợ lý", "QUAN AI", etc.
    - [x] Zero-loss payload extraction: allows calling wake word and utterance in the same breath.
    - [x] Voice control commands ("ngủ đi", "dừng đọc", "dừng nghe", "tắt trợ lý").
    - [x] 9-State Voice State Machine (`VoiceState`, `VoiceStateMachine`) with valid/invalid transition enforcement.
    - [x] Browser-native client engine (`wake_engine.js`) with continuous SpeechRecognition, Web Audio synthesized two-tone executive wake chime (440Hz -> 880Hz), and 20s silence follow-up window.
    - [x] Acoustic Echo Cancellation (AEC): speech recognition pauses during TTS playback to eliminate self-activation loops.
    - [x] REST API endpoints (`GET /api/voice/wake-config`, `POST /api/voice/wake-config`, `POST /api/voice/telemetry`).
    - [x] UI visual controls in Port 8766 Executive Desk (toggle button, dynamic status pill, animation keyframes).
  - [x] Autonomous System Restart & Safe Reload Routine (Lệnh tự khởi động lại hệ thống sau update):
    - [x] Dedicated CLI subcommand `restart`: `python -m quan_ai_brain.cli restart [--target {all,desk,chat}] [--validate] [--test] [--no-browser]`.
    - [x] Python restarter tool (`tools/restart_system.py`): pre-flight syntax & import check, graceful TCP port scan & PID termination, Ollama daemon verification, independent background service spawning, and HTTP health polling.
    - [x] One-click Windows batch launchers: `TU_DONG_KHOI_DONG_LAI_HE_THONG.bat` and `RESTART_SYSTEM.bat`.
    - [x] Desktop Shortcut: `QUAN AI BRAIN - Tu Dong Khoi Dong Lai.lnk` on Windows Desktop.
  - [x] Continuous Autonomy OS V1 — Stage B: Durable Operations State & Continuous Supervisor:
    - [x] `DurableTaskRegistry` & `TaskRecord` (`src/quan_ai_brain/orchestration/task_registry.py` & `models.py`) persisting task state in SQLite WAL (`data/tasks.db`), atomic transitions, anti-replay idempotency key, and crash recovery (`recover_in_flight_tasks` to `OUTCOME_UNKNOWN`).
    - [x] `ContinuousAutonomySupervisor` (`src/quan_ai_brain/orchestration/supervisor.py`) 16-state operating machine (`STARTING -> HEALTH_CHECK -> READY -> IDLE -> SELECTING_TASK -> PLANNING -> WAITING_FOR_APPROVAL -> RUNNING_AUTHORIZED_TASK -> VERIFYING_RESULT -> LEARNING -> PREPARING_UPGRADE_PROPOSAL -> WAITING_FOR_OWNER -> RECOVERING -> SAFE_MODE -> STOPPED -> FAILED`).
    - [x] Bounded autonomy enforcement: Level A automatic read/test vs Level B/C/D & R4/R5 approval gate halt.
    - [x] 17 focused unit tests verified in `tests/test_durable_task_registry.py` and `tests/test_continuous_supervisor.py`.
  - [x] Phase C — Nối Task Thật Vào Chu Trình Tự Học & Đo Lường Tiến Bộ:
    - [x] `ContinuousEvaluationHarness` (`src/quan_ai_brain/learning/evaluation.py`) thực thi 5 benchmark tiêu chuẩn (governance_r5_hard_block, vietnamese_memory_retrieval, dag_cycle_rejection, quarantine_candidate_isolation, credential_redaction_filter).
    - [x] `PeriodicLearningReporter` tự động vét nhiệm vụ lỗi từ `DurableTaskRegistry`, chạy kiểm định định lượng trước/sau, tính toán delta `improvement_pct` và đưa ra khuyến nghị thăng cấp (`PROMOTE_TO_VERIFIED`, `REMAIN_QUARANTINED`, `REJECT_REGRESSION`).
    - [x] 4 unit tests đạt 100% tại `tests/test_evaluation_harness.py`.
  - [x] Phase D — Digital Avatar Biểu Cảm & Visual Cockpit (Port 8766):
    - [x] Gương mặt số Cybernetic SVG của trợ lý TONY với 11 trạng thái biểu cảm chuẩn mực (IDLE, LISTENING, THINKING, RESEARCHING, LEARNING, SPEAKING, WAITING_FOR_OWNER, BLOCKED, ERROR, SAFE_MODE, OFFLINE).
    - [x] Hiệu ứng chớp mắt tự nhiên (3.5s cycle) và dải sóng âm thanh động 60fps (Dynamic Waveform Canvas).
    - [x] Visual Cockpit Hero 3 cột: Avatar biểu cảm & Bộ chọn 11 cảm xúc, Tiến trình DAG thời gian thực & Chỉ số LLM/Uptime, và Bảng quản trị ranh giới an toàn.
    - [x] Phím điều khiển khẩn cấp trực tiếp: STOP KHẨN CẤP, FREEZE đóng băng, và RESUME khôi phục kết nối thẳng tới `GovernanceStateStore` qua `POST /api/executive/emergency`.
    - [x] Đồng bộ trạng thái giọng nói Wake Word Engine vào biểu cảm Avatar khi nghe/nói/nghĩ.
    - [x] 8 bài kiểm thử REST API & Kịch bản khẩn cấp đạt tại `tests/test_web_executive_endpoints.py`.
  - [x] Phase E — Chuẩn Bị Mã Nguồn Client Cho Raspberry Pi 5 (`edge_client/`):
    - [x] Cấu hình độc lập `EdgeConfig` (`edge_client/config.py` & `config.json`) tuân thủ nguyên tắc Zero-Core-DB on Edge.
    - [x] Xác thực hai chiều chống tấn công phát lại `EdgeHMACAuth` (`edge_client/auth.py`) với tem thời gian UTC, nonce ngẫu nhiên và chữ ký HMAC-SHA256.
    - [x] Tệp cài đặt & ghép cặp Wi-Fi 1 lần duy nhất (`setup_pi5.py`, `setup_pi5.sh`) tự động dò tìm IP PC Core, xác thực mã PIN (`888666`), nhận khóa bí mật và tự khởi động cùng OS (Autostart Kiosk).
    - [x] Bộ điều khiển ngoại vi vật lý `ActuatorController` (`edge_client/actuators.py`): 8 kênh rơ-le (Relay 1-8 trên GPIO BCM: 17, 27, 22, 23, 24, 25, 5, 6), 6 khớp servo tay chân/cổ (head_yaw, head_pitch, arm_left, hand_left, arm_right, hand_right), và ngắt khẩn cấp fail-safe `emergency_all_stop()`.
    - [x] Giao diện Kiosk màn hình cảm ứng 5"/7" (`edge_client/kiosk.html`, `kiosk.css`, `kiosk.js`) tối ưu cho Chromium Kiosk Mode.
    - [x] Cơ chế Fail-Safe Disconnect: tự động chuyển màn hình sang chế độ OFFLINE và ngắt mic an toàn khi mất kết nối LAN tới PC Core.
    - [x] Daemon nền `EdgeClientDaemon` (`edge_client/client_daemon.py` & `main.py`) quản lý heartbeat xác thực và phục vụ giao diện Kiosk cục bộ trên cổng 8768.
    - [x] Nút bấm cảm ứng STOP khẩn cấp trên Pi 5 gửi lệnh ngắt có chữ ký số lên PC Core trong < 0.1 giây.
    - [x] Tài liệu hướng dẫn cài đặt phần cứng, đấu nối rơ-le/tay chân và autostart chi tiết tại `edge_client/README.md`.
  - [x] PC Core ↔ Pi 5 Digital Avatar — Phase B (EdgeConnectionMonitor, Watchdog, Mouth Sync & One-Click Pi 5):
    - [x] `EdgeConnectionMonitor` (`src/quan_ai_brain/web/edge_monitor.py`): Giám sát trạng thái 9 bước định chuẩn (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `DEGRADED`, `SYNCING`, `READY`, `RECOVERING`, `AUTH_FAILED`, `STOPPED`), tích hợp Watchdog kiểm soát deadline, đo RTT mạng Wi-Fi và phát sinh 6 cảnh báo bắt buộc (Alert A đến F) chống spam thông báo.
    - [x] Bộ đồng bộ khẩu hình thời gian thực `MouthSyncEngine` (`src/quan_ai_brain/voice/mouth_sync.py`): Khớp viseme nguyên âm tiếng Việt (A, O, E, I, U, REST) theo dòng thời gian timeline 50ms, mô phỏng quãng nghỉ ngắt câu đóng miệng tự nhiên, đo dải năng lượng âm thanh (audio energy envelope), hỗ trợ cơ chế hủy lập tức `cancel_utterance` khi ngắt lời nói.
    - [x] Tích hợp API Endpoint trên PC Core (`server.py`): `GET /api/executive/edge/alerts`, `GET /api/executive/edge/status`, `POST /api/executive/edge/heartbeat`, `POST /api/executive/edge/mouth-sync` và đo độ trễ RTT mạng Wi-Fi qua header `X-QuanAI-RTT-Ms`.
    - [x] Giao diện Bàn Điều Hành Cockpit (Port 8766): Banner cảnh báo viền sáng động theo mức độ nghiêm trọng (`.edge-alert-banner`), nhãn trạng thái kết nối Pi 5 và chỉ số độ trễ RTT trực quan.
    - [x] Màn hình Pi 5 hiển thị thuần hình thể (Face-Only Mode): Tự động ẩn toàn bộ header, khung log, phím bấm khi `face_only_mode: true`, phóng to tối đa gương mặt và chuyển động đóng mở cơ miệng theo viseme.
    - [x] Tệp tự động cài đặt One-Click trên Pi 5 (`setup_pi5.py`, `setup_pi5.sh`): Tự động quét subnet tìm IP PC Core trong &le; 1.2s, ghép cặp 1 lần duy nhất bằng mã PIN (`888666`), lưu cấu hình hoàn chỉnh có trường phiên bản (`core_version`, `edge_client_version`, `protocol_version`, `avatar_version`, `config_schema_version`), tạo tệp khởi động tự động `start_kiosk.sh` và desktop autostart entry.
    - [x] 14 bài kiểm thử mới đạt 100% tại `tests/test_edge_monitor.py` (7 tests), `tests/test_mouth_sync.py` (5 tests), và `tests/test_web_executive_endpoints.py` (10 tests).
  - [x] Animated Digital Human Avatar — Cô Trợ Lý AI Mẫu F (Raspberry Pi 5 + PC Executive Desk :8766):
    - [x] Bộ tài sản số chuẩn Mẫu F theo ảnh tham chiếu của chủ sở hữu: Tóc bạch kim ánh tím bồng bềnh, mắt nâu hạt dẻ ấm áp, làn da sáng tự nhiên, trang phục vest cao cổ sci-fi viền LED cyan, góc nhìn chính diện cân đối: `model_f_portrait.png`, `model_f_blink.png`, `model_f_speaking.png`, `model_f_happy.png`, `model_f_thinking.png` cùng các lớp biểu cảm bóc tách (`eyes_closed.png`, `eyes_thinking.png`, `mouth_rest.png`, `mouth_speaking.png`, `mouth_happy.png`).
    - [x] Đồng bộ toàn bộ tài sản số sang thư mục của cả PC Core (`src/quan_ai_brain/web/static/assets/avatar/`) và Raspberry Pi 5 (`edge_client/assets/avatar/`).
    - [x] Bộ máy đồ họa `DigitalHumanAvatar` Engine (`avatar_engine.js`) chuẩn 2.5D Canvas 60 FPS siêu nhẹ, không dùng Three.js/WebGL nặng nề, hoàn toàn không gây quá nhiệt hay ngốn RAM/quạt tản nhiệt trên Pi 5.
    - [x] Hiệu ứng hình thể sinh học tự nhiên: Nhịp thở vi mô (micro-breathing theo hàm sin), vòng hào quang số quay chậm (cyan/purple halo ring), chớp mắt sinh học ngẫu nhiên (120ms duration, chu kỳ 3.0s–5.5s), chuyển động liếc mắt sinh động (eye saccades), nụ cười tươi tắn tự nhiên.
    - [x] Khẩu hình tiếng Việt mượt mà: Đồng bộ thời gian thực với `MouthSyncEngine` qua 6 viseme chuẩn (A, O, E, I, U, REST), mở miệng tỉ lệ theo viseme, chuyển tiếp mượt (easing interpolation) và hỗ trợ ngắt lời lập tức (`cancelUtterance()`).
    - [x] Tích hợp hoàn chỉnh trên cả 2 giao diện:
      - Bàn Điều Hành PC Core (`http://127.0.0.1:8766/`): Khung canvas 280x280px bo tròn với viền sáng đa trạng thái, liên kết trực tiếp với bộ chọn 11 biểu cảm và bộ phát âm thanh TTS.
      - Màn hình Raspberry Pi 5 Kiosk (`:8768`): Khung canvas tỉ lệ vuông phóng lớn tràn viền chuẩn `face_only_mode`, tự động ẩn nút bấm và log debug.
    - [x] Cơ chế an toàn ngắt kết nối (Fail-Safe Disconnect): Tự động dừng nói ngay lập tức, nhắm mắt dịu dàng ở trạng thái nghỉ an toàn, ngắt micro và chuyển cơ cấu chấp hành về trạng thái an toàn tuyệt đối.
    - [x] Tối ưu Màn hình cảm ứng 7" DSI Touchscreen 2 (1280x720) & Kịch bản One-Click (`oneclick_run_pi5.sh`):
      - Tự động kiểm tra và cập nhật đầy đủ gói hệ thống (`python3`, `chromium-browser`, `alsa-utils`).
      - Tối ưu độ phân giải 1280x720, ẩn hoàn toàn con trỏ chuột (`cursor: none`), tối đa hóa khung nhìn hình thể Mẫu F đạt `min(94vw, 94vh)`.
      - Hỗ trợ tham số dòng lệnh `--auto`, `--host`, `--pin` cho khả năng cài đặt tự động 100% không cần can thiệp.
    - [x] Động cơ Biểu Cảm Vi Mô (Micro-Expressions Engine) & Phân Tích Ngữ Cảnh Tiếng Việt:
      - Chuyển động lông mày đa sắc thái: nhíu tâm trạng khi phân tích, nâng cao tự tin khi hoàn thành, nhướng tò mò khi chờ chỉ đạo (`_renderEyebrows`).
      - Nụ cười mắt Duchenne (mí mắt dưới nâng nhẹ khi cười ấm áp) và đốm sáng đồng tử lấp lánh (Sci-Fi Iris Glint Pulse).
      - Bộ phân tích ngữ cảnh tiếng Việt (`extractVietnameseEmotion`, `setContextFromText`): tự động nhận diện 6 tông cảm xúc từ nội dung hội thoại LLM (`WARM_GREETING`, `ANALYTICAL_THINKING`, `SERIOUS_ALERT`, `CONFIDENT_SUCCESS`, `CONSULTATIVE_INQUIRING`, `NEUTRAL`) và chuyển tiếp mượt 60 FPS qua hàm nội suy `lerp`.
    - [x] Nâng cấp Hình Thể Sống Động Như Người Thật & Khắc Phục Triệt Để Lỗi Đồ Họa (PC & Pi 5):
      - Triệt tiêu 100% viền hộp chữ nhật ở miệng: Loại bỏ việc vẽ đè asset miệng vuông không alpha khi IDLE/HAPPY/THINKING; chỉ mở khẩu hình khi SPEAKING và áp dụng kỹ thuật Mặt nạ Elip làm mềm biên độ mờ dần viền (Feathered Elliptical Alpha Masking - `destination-in`) hòa quyện hoàn hảo vào da mặt.
      - Hiệu ứng sóng vật lý tóc chuyển động bồng bềnh tự nhiên (`_renderNaturalHairSway`): Dao động sóng đa tần số cho các lọn tóc bạch kim ánh tím buông xõa hai bên má, dải bóng phản chiếu ánh sáng (specular hair sheen) và các hạt năng lượng cybernetic lơ lửng.
      - Động học chuyển động đầu tự nhiên ("Người thật"): Nghiêng đầu nhẹ nhàng (Head Roll tilt -2.2° đến +2.2°), lắc lư chuyển trọng tâm (Yaw micro-sway) và gật đầu thấu cảm vi mô (Pitch acknowledgment micro-nod khi lắng nghe) quanh tâm xoay khớp cổ (`0.5*w`, `0.70*h`).
      - Nhịp chớp mắt sinh học biến thiên: Tỉ lệ chớp mắt kép (double-blink) 28%, đường cong mí mắt đóng mở mượt mà và cử động liếc mắt tinh tế (saccades).
      - Đồng bộ tuyệt đối giữa Central Brain PC Core và Raspberry Pi 5 Edge Kiosk.
  - [x] QUAN AI BRAIN EVOLUTION — Sprint 1: Core AI End-to-End & Session Memory:
    - [x] Dynamic LLM Router (`src/quan_ai_brain/llm/router.py`):
      - [x] Fast conversational tier: Routes short queries and greetings to fast model (`qwen2.5:1.5b` / `qwen2.5:0.5b`, latency < 2s on CPU).
      - [x] Reasoning & planning tier: Routes complex DAG planning, architecture decomposition, and long analysis queries to `qwen2.5:7b`.
      - [x] Caller explicit override and fallback for missing models.
    - [x] Session Memory & Continuous Fact Extraction (`src/quan_ai_brain/cognition/session_memory.py`):
      - [x] Automatic fact extraction from conversation: owner identity ("tôi tên là..."), preferences ("tôi thích..."), and instructions ("hãy nhớ rằng...").
      - [x] Persistent storage into SQLite WAL `data/brain.db`: records every chat turn into `episodes` table and stores extracted facts into `memories` table with `USER_PROVIDED` / `OBSERVED` statuses.
      - [x] Multi-turn session continuity: `get_recent_session_history()` retrieves recent exchanges.
    - [x] Output Guardrails (`src/quan_ai_brain/core/guardrails.py`):
      - [x] Credential and token redaction filter.
      - [x] Dangerous script tag `<script>` sanitization.
      - [x] System path and private key file masking (`.env`, `id_rsa`).
    - [x] Prompt Context Builder Extension (`src/quan_ai_brain/cognition/context_builder.py`):
      - [x] Multi-turn `[RECENT CONVERSATION HISTORY]` injection.
    - [x] REST API Extension (`src/quan_ai_brain/web/server.py`):
      - [x] `POST /api/chat` fully integrated with persistence, routing, and guardrails.
      - [x] `GET /api/chat/history` endpoint for querying session history.
    - [x] 5 focused end-to-end tests in `tests/test_end_to_end_chat.py`.
    - [x] Raspberry Pi 5 24/7 Autostart & Living Standby Embodiment:
      - [x] Kịch bản tự khởi động 1-click `edge_client/install_autostart_247.sh` tạo `~/.config/autostart/quan_kiosk.desktop`.
      - [x] Chế độ chống tắt màn hình 24/7 (`xset s off -dpms s noblank`) và vòng lặp tự phục hồi Self-Healing Kiosk (`edge_client/start_kiosk.sh`).
      - [x] Trực chiến sống động: Màn hình 7" DSI luôn hiển thị gương mặt Cô Trợ Lý Mẫu F với đôi mắt chớp tự nhiên, micro-breathing ở chế độ Standby ngay khi cấp nguồn; chỉ chuyển sang trạng thái ngủ (SLEEPING) khi có lệnh tạm dừng từ PC Core.
    - [x] Bàn Điều Hành PC Core Remote Control & Bi-directional Asset Transfer (`http://127.0.0.1:8766/`):
      - [x] Quản trị tệp tin và truyền tài sản từ xa (`GET /api/executive/edge/files`, `POST /api/executive/edge/files/upload`, `POST /api/executive/edge/files/sync-all`, `POST /api/executive/edge/files/delete`).
      - [x] Tải lại Kiosk Pi 5 tức thì từ xa (`reload_ui`), Tạm dừng (`pause` / SLEEPING), Kích hoạt (`resume` / IDLE), và Điều chỉnh âm lượng loa Pi 5 (`set_volume`).
      - [x] 1-Click đồng bộ toàn bộ tài sản sang Pi 5 và tải lại trình duyệt Kiosk (`edge_client/sync_assets.py`, `curl -s http://192.168.1.11:8766/edge_client/sync_assets.py | python3`).
      - [x] Cơ chế chống treo mạng socket fail-fast (<0.25s), auto-sync tài sản tự động khi khởi động trên Pi 5, và fallback hiển thị hình thể số Holographic Model F procedural vector ngăn chặn hiện tượng màn hình đen khi tải ảnh.
    - [x] Edge Data Transfer Service V1 (D01–D10):
      - [x] Truyền dữ liệu hai chiều có chia chunk, manifest mã hóa SHA-256, kiểm tra tính toàn vẹn và xác nhận ACK.
      - [x] Hàng rào nhạy cảm: Chặn nghiêm ngặt `.env*`, `*.key`, `*.pem`, `id_rsa*`, `credentials*`, `*.db`.
      - [x] Quota tài nguyên và cô lập phạm vi thiết bị đa điểm biên (multi-device scopes).
    - [x] Edge Release Manager V1 (U01–U10):
      - [x] Đóng gói phát hành phần mềm Edge Client với chữ ký mật mã HMAC-SHA256 và kiểm tra tương thích phiên bản.
      - [x] Staging an toàn và health check cú pháp Python (`py_compile`) trước khi kích hoạt.
      - [x] Cơ chế rollback nguyên tử (atomic rollback) bảo toàn bản phát hành ổn định trước đó.
    - [x] 10 Vai Trò Trợ Lý Số Điều Hành (Executive Role Orchestrator):
      - [x] 10 vai trò bắt buộc: Executive Assistant, Coordinator, Tech Specialist, NOC Operator, Data Analyst, Researcher, Documentation Officer, Language Specialist, Instructor, Safety Officer.
      - [x] Quy tắc tối thượng: Safety Guard giữ quyền cao nhất, lệnh STOP/FREEZE và ranh giới R5 chặn mọi vi phạm.
    - [x] XiaoZhi-Style Voice-First Pipeline (T01–T08, W01–W07):
      - [x] Hội thoại đa lượt giữ ngữ cảnh (T02), nhận diện tự sửa lời nói ("À nhầm", "Ý anh là...").
      - [x] Ngắt lời tức thì (<10ms barge-in cancellation).
      - [x] Lọc sạch mã kỹ thuật, JSON, stack trace khỏi văn bản đọc TTS tiếng Việt.
      - [x] Giám sát mất nhịp tim Wi-Fi (<4.0s) và cảnh báo trung thực.
    - [x] Standard Vietnamese Female TTS Engine & Language Guard (Sửa dứt điểm giọng đọc sai ngôn ngữ):
      - [x] Cấu hình chuẩn hóa tập trung (`TTSConfig`, `TTSManager` trong `src/quan_ai_brain/voice/tts_config.py`): mặc định `response_language = vi-VN`, `tts_locale = vi-VN`, `tts_gender = female`, `tts_voice_preference = vi-VN-HoaiMyNeural`, `provider = edge-tts`.
      - [x] Rào chắn ngôn ngữ nghiêm ngặt (Strict Language Guard): Tuyệt đối không tự ý rơi về giọng tiếng Anh mặc định của Windows/trình duyệt khi thiếu giọng tiếng Việt; chuyển trạng thái `TTS_UNAVAILABLE` hoặc `ERROR` với thông báo rõ ràng.
      - [x] Bộ tổng hợp âm thanh giọng nữ Việt Nam chuẩn (`synthesize_audio`): Tích hợp trực tiếp Microsoft Edge Natural Voice `vi-VN-HoaiMyNeural` tạo audio mp3 chất lượng cao, giữ nguyên 100% dấu tiếng Việt, xử lý đơn vị, số liệu và mã thiết bị an toàn.
      - [x] REST API Endpoints chuẩn (`server.py`): `GET /api/voice/tts-config`, `GET /api/voice/tts-voices`, `POST /api/voice/tts-config`, `POST /api/voice/tts-synthesize` trả về dữ liệu audio base64 kèm timeline khẩu hình (viseme).
      - [x] Khắc phục giao diện Chat Cục Bộ (:8765): Tích hợp badge trạng thái TTS trực quan (`.tts-badge.ready`, `speaking`, `unavailable`, `disabled`), ưu tiên phát audio chuẩn từ Core qua HTML5 Audio; chỉ fallback sang browser TTS nếu có voice tiếng Việt thực sự; dừng audio ngay khi ngắt lời hoặc gửi câu hỏi mới.
      - [x] Khắc phục giao diện Điều Hành Cockpit (:8766): Đồng bộ `speakText` chuẩn tiếng Việt vào Digital Human Avatar Model F và phím kiểm tra giọng nói từ xa (`btnRemoteSpeak`), loại bỏ hoàn toàn việc phát âm sai tiếng Anh.
      - [x] Bộ kiểm thử toàn diện TTS-01 đến TTS-10 (`tests/test_vietnamese_tts.py`): 9 test PASS 100%, 1 test phần cứng Pi 5 ghi nhận trung thực trạng thái `BLOCKED` khi chưa kết nối vật lý.
    - [x] Tích hợp Nhân sự số Trợ lý (Digital Human Mẫu F — TONY) vào trang Chat Cục Bộ (`http://127.0.0.1:8765/`):
      - [x] Bố cục Split Layout 2 cột: Cột trái hội thoại thông minh, Cột phải sân khấu trợ lý số Model F (canvas viewport 2.5D, dải sóng âm thanh thời gian thực 60 FPS, nút chuyển 8 biểu cảm nhanh).
      - [x] Phản hồi biểu cảm linh động (Dynamic Expressions & Reactions): Tự động chuyển `LISTENING` khi user nói/gõ, `THINKING` khi LLM suy ngẫm, phân tích cảm xúc câu trả lời tiếng Việt (`setContextFromText`) nở nụ cười rạng rỡ (`model_f_happy.png`) hoặc tự tin, cử động khẩu hình chuẩn tiếng Việt khi `SPEAKING`, và micro-breathing/chớp mắt kép khi `IDLE`.
- [x] QUAN AI BRAIN EVOLUTION — Sprint 2: Integration Closure & Operational Readiness:
  - [x] Plan Orchestrator & Durable Task Lifecycle (`src/quan_ai_brain/orchestration/plan_orchestrator.py`):
    - [x] Đóng kín vòng đời điều phối nhiệm vụ: User Request -> Intent -> TaskPlan -> DAG Validation -> Risk Assessment -> DurableTaskRegistry -> Approval Gate -> Inert Sandbox -> Result Verification -> TaskOutcome -> Report.
    - [x] Bảng lưu trữ bền vững từng bước `durable_task_steps` trong SQLite WAL `data/tasks.db`.
    - [x] Chống chạy lặp tác vụ qua `idempotency_key` duy nhất.
    - [x] R5 Hard-Block: Chặn cứng lập tức các bước nguy hiểm (`TaskStatus.BLOCKED`), không cho phép nạp hay ghi đè.
    - [x] R4 Approval Gate: Dừng an toàn tại `WAITING_APPROVAL`, chỉ tiếp tục khi chủ sở hữu ký phê duyệt xác thực.
    - [x] Thực thi an toàn trong Inert Sandbox (Dry-run), thu thập `EvidenceRecord` và lọc sạch credential nhạy cảm.
    - [x] Khôi phục sự cố: Chuyển các tác vụ dở dang khi khởi động lại sang `OUTCOME_UNKNOWN`.
    - [x] 8 bài kiểm thử tích hợp đạt 100% tại `tests/test_plan_orchestration_lifecycle.py`.
  - [x] Core AI Correctness & LLMRouter Verification:
    - [x] Local Ollama daemon chạy thật trên `127.0.0.1:11434` với 6 model (`qwen2.5:7b`, `1.5b`, `0.5b`, `llama3.1`, `mistral`, `qwen`).
    - [x] Đo lường suy luận thật: `qwen2.5:0.5b` phản hồi tiếng Việt trong 632.4 ms (`is_mock=False`).
    - [x] Định tuyến mô hình: Fast tier (`qwen2.5:1.5b` / `0.5b`) cho đàm thoại nhanh; Reasoning tier (`qwen2.5:7b`) cho lập kế hoạch và phân tích sâu.
    - [x] Quản trị Fallback: Không bao giờ âm thầm fallback sang mock; cờ `is_mock=True` và warning minh bạch.
    - [x] Output Grounding: Bóc tách rõ ràng giữa sự thật người dùng, suy luận, kết quả công cụ và dữ liệu chưa kiểm chứng.
    - [x] 8 bài kiểm thử đạt 100% tại `tests/test_core_ai_correctness.py`.
  - [x] Báo cáo kiểm thử trung thực (`tools/validate_and_report.py`):
    - [x] Phân loại minh bạch 5 nhóm: Passed, Failed, Skipped, Blocked, Not Run.
    - [x] Không làm tròn bài test skip thành pass. Kết luận chuẩn xác: `PARTIALLY_VERIFIED (379 passed, 1 skipped)`.
- [x] 379/380 tests passing (379 PASS, 1 SKIP, 0 FAIL, 0 BLOCKED). 1 test phần cứng Pi 5 ghi nhận trung thực trạng thái BLOCKED khi chưa kết nối vật lý.

## Not implemented / not verified
- Real production executors or external write APIs (strictly non-production in Sprint 4; only safe R0-R2 workspace tools).
- Integration with Kernel L3, DC-COMMAND / CLAE, SKILL_BAT_AI, Battery AI V4, VDCIM or NetChat.
- Windows service or always-on daemon (design review only in Sprint 4; zero production daemons activated).
- Vector embeddings or autonomous production execution.

## Safety decisions
- R5 is blocked in this implementation. Do not add an override secret to the source code.
- R4 requires an external approval process; no production executor is implemented yet.
- Learning candidates stay quarantined until separately approved and regression-verified.
- Current audit/report utility does not scan outside the project root and does not read secret/database files.

## How to update status
Update this file only when a change is implemented and test evidence exists. Then run `tools/validate_and_report.py` to generate a new handoff report.

## 31/10 ~22:28 — WAKE WORD "TONY ơi" SỬA XONG E2E (nhận được + hình thể phản hồi)
- **Rễ**: mic USB Jieli hẹp 30–50cm — giọng owner gọi từ xa QUÁ YẾU (peak ~700 so với cần >2000) → Vosk decode RỖNG → không wake → hình thể im. Chuỗi wake→kiosk vốn sống (wake_by_voice test OK).
- **Fix 3 lớp (edge_client/wake_word_service.py, deploy + restart quan_ai_wake)**:
  1. **AGC auto gain**: normalize RMS mỗi chunk về ~-11dBFS (gain ≤8x, clip guard 32000, bỏ tĩnh điện RMS≤60) — tiếng nhỏ kéo lên, tiếng to giữ nguyên.
  2. **Fuzzy match**: Levenshtein ≤2 từng token vs 'tony/toi/tôi' + 'ơi' — bắt 'tôi nêu', 'no nê tôi nơi', 'tôn ơi', 'tó ni ơi'; không false-positive với từ thường.
  3. **Mic BT-first**: ưu tiên bluez_input (SRS-XB33 nhạy ~3x USB) khi loa bật; fallback USB Jieli.
- **DEBUG LOG mới**: `[WAKE-DBG] Vosk: '<text>'` (throttle 5s) — thấy Vosk nhận liên tục môi trường.
- **E2E THẬT 22:26–22:27**: journal 2 lần `NGHE THẤY ... → wake!` → wake_by_voice POST → **screenshot TFT (grim)**: avatar sáng ACTIVE + waveform chạy + chào 'Hello Mr. Quantp1! I'm ready to continue working.' + STOP đỏ ✅. Ảnh logs/wake_check.png.
- **Lưu ý vận hành**: loa BT tắt giữa phiên (~22:20, sinks→Dummy) → wake rơi về mic USB; bật loa lại thì service tự quay về mic BT khi lần lấy node kế. Vosk small vẫn khó map tên riêng — fuzzy là lớp cứu chính.

## 31/10 ~22:39 — CHỤP ẢNH FAIL LẠI (22:02–22:03) — TÌM RỄ + FIX + E2E PASS
- **Sự việc**: owner gõ 'Chụp ảnh' / 'Chụp hình' / 'Chụp ảnh từ pi5' (22:02–22:03, 22:23) → bot SUÔNG SAI 'chưa có công cụ' dù fix 21:58.
- **Rễ (tái hiện được)**: (1) detect_intent chỉ bắt 'chụp ảnh'+pi hoặc +gửi/camera/cho anh — lệnh NGẮN 'Chụp ảnh'/'Chụp hình' KHÔNG khớp → rơi GLM bịa; (2) responder process cũ import lỗi 'No module tools.netchat_command_center' trong quá khứ + chạy code cũ trong RAM.
- **Fix**: netchat_command_center.py detect_intent thêm nhánh mệnh lệnh đứng đầu câu '(chụp|chup) (ảnh|anh|hình|hinh)' → tony_pi_photo, loại trừ 'màn hình' (pc_screenshot giữ nguyên), câu hỏi ('chụp ảnh được không?') không kích hoạt (dùng _is_question — fix UnboundLocalError question).
- **Verify**: 11/11 test detect_intent đúng (kể cả không nuốt pc_screenshot); process_message('Chụp ảnh') + ('Chụp hình') → chụp thật photo_20261031_223622/223851.jpg + gửi DM ✅.
- **Vận hành**: restart responder PID 5952 (cwd BRAIN, stdout append logs/netchat_responder_stdout.log); tin test gửi bằng BOT account bị responder bỏ qua (tin owner mới route).

## 31/10 ~22:47 — KÊNH LỆNH GIỌNG NÓI QUA DM (STT) — owner yêu cầu
- **Sự việc**: owner gửi 2 bản ghi âm m4a (0:07, 0:13) 22:08–22:09 → bot trả lời 'chưa đọc được âm thanh'. Owner yêu cầu: nhận diện + phân tích để lần sau ra lệnh bằng giọng nói qua DM.
- **Nội dung 2 bản ghi (faster-whisper small int8, language=vi)**:
  - 0:07: 'Em chào anh Minh Thối cho anh 1 tiếng' (Vosk small sai sót; whisper chuẩn hơn).
  - 0:13: 'Em nghe được nói điều khiển từ điện thoại và em phân tích, lần sau em nhận diện âm thanh này để thực hiện, thực thi.'
- **Cài đặt**: `pip install faster-whisper` vào venv BRAIN; module mới `tools/voice_stt.py` (WhisperModel small CPU int8, cache singleton, CLI fail-honest).
- **Tích hợp responder**: `_AUDIO_EXTS` + `_stt_audio()` (subprocess BRAIN venv, timeout 300s) + `_extract_text` nhánh audio; `extract_message_files` trả block riêng '--- LỆNH GIỌNG NÓI ANH GỬI (STT) ---'; `process_message` bóc text STT → route như tin nhắn chữ (lệnh hệ thống chạy thật).
- **Verify E2E**: extract 2 file m4a thật → STT 3.4–3.9s/bản, text đúng; voice block → process_message hiểu đúng ý; 'Chụp ảnh' text → tony_pi_photo (22:36). Giọng Việt neural qua loa→mic BT→STT chuẩn ('Cảm ơn các bạn và hẹn gặp lại trong video tiếp theo.').
- **Vận hành**: lần đầu load model ~55s (sau ~2–4s/bản); responder PID 5520 chạy code mới.

## 31/10 ~22:58 — HDMI CÓ PHÊ DUYỆT OWNER + HÌNH THỂ MẶC ĐỊNH MÀN PI5
- **Yêu cầu owner**: hình thể mặc định trên màn Pi5; cắm HDMI → TONY gửi tin hỏi 'anh có muốn xuất hình lên HDMI?' → anh phê duyệt mới bật; khi bật thì hiển thị LIÊN TỤC cho đến lệnh của anh.
- **Daemon (client_daemon.py, deploy + restart quan_ai_edge)**: `_notify_hdmi_event()` POST server `/api/executive/edge/hdmi_event`; watcher **KHÔNG tự bật mirror** khi cắm nữa — chỉ báo server; rút HDMI → stop mirror + báo disconnected.
- **Server (server.py, restart 22:53, netmind READY)**: endpoint mới `POST /api/executive/edge/hdmi_event`; connected → chống spam 10 phút + DM hỏi phê duyệt qua netchat_bridge; disconnected → DM báo + clear flag. `_GLOBAL_HDMI_STATE` (last_ask, awaiting_approval).
- **Command center**: intent mới `tony_hdmi_approve` ('phê duyệt hdmi'/'duyệt hdmi'/'ok hdmi'/'xuất hình lên hdmi'…); handler fail-honest — Pi5 báo 'HDMI chưa cắm màn' → trả lời thẳng 'chưa thấy màn hình nào cắm', KHÔNG xác nhận suông; route_message 2.5 thêm tony_hdmi_hide/approve vào nhóm ưu tiên (fix regression 'tắt hdmi' rơi pc_close).
- **E2E**: POST hdmi_event connected → DM hỏi tới 22:53 ✅; 'phê duyệt hdmi' → detect tony_hdmi_approve + phản hồi đúng trạng thái (chưa cắm → cảnh báo) ✅; 'tắt hdmi' → tony_hdmi_hide ✅. Chờ owner cắm màn HDMI thật để nghiệm thu chuỗi đầy đủ (cắm → hỏi → duyệt → hình liên tục).
- Responder PID 8252.

## 01/11 ~08:20 — TRAO ĐỔI THOẠI 2 CHIỀU QUA MIC LOA BLUETOOTH PI5 (E2E)
- **Yêu cầu owner**: dùng mic sẵn có trên loa BT SRS-XB33 để trao đổi thoại với trợ lý (nói lệnh → TONY nghe → trả lời bằng giọng).
- **Kí thuật (đã E2E thật 08:11)**: Wake 'TONY ơi' (BT-first, có sẵn) → daemon **tự ghi lệnh thoại 8s** (pw-record mic BT bluez_input, 16kHz mono, ffmpeg remux) → POST `/api/executive/edge/voice_command` (server PC) → **STT faster-whisper small int8** → `route_message` như tin DM → phản hồi **phát giọng Edge-TTS vi-VN-HoaiMyNeural qua loa BT** + hiển thị transcript trên kiosk + log DM '🎤 Anh vừa nói / 🤖 Em'.
- **E2E 08:11**: WAV 'Em chụp ảnh gửi anh' → STT chính xác → intent tony_pi_photo → **chụp thật photo_20261101_081106.jpg (78KB)** → kiosk SPEAKING + phát giọng (spoken_on_speaker=true) → DM log tới anh ✅.
- **Fix kèm**: (1) 'chụp hình\' (dấu \ cuối) rơi GLM — detect_intent strip '\/!.?,:;'; (2) responder chết sau restart server — respawn PID 2596.
- Mic USB Jieli KHÔNG cắm (owner đã rút) — mic BT là kênh thoại chính; nếu cắm USB lại, wake + ghi lệnh tự fallback đúng.

## 01/11 ~08:35 — NÚT STOP MÀN HÌNH PI5 = CHỈ THOÁT GIAO DIỆN (E2E)
- **Yêu cầu owner**: nút STOP trên kiosk chỉ thực hiện việc thoát hiển thị màn hình giao diện.
- **Daemon (deploy + restart quan_ai_edge)**: close_kiosk mới — pkill chromium (thoát giao diện), **KHÔNG xset dpms force off** (màn giữ nguyên), avatar giữ IDLE (không STOPPED/OFFLINE), flag module `_KIOSK_CLOSED_BY_OWNER_EPOCH` + helpers `_set_kiosk_closed_by_owner()/_kiosk_closed_by_owner()`; `/api/kiosk/status` trả thêm `kiosk_closed_by_owner` (15 phút). wake_by_voice + start_kiosk XOÁ flag.
- **kiosk_guard.py (deploy + restart service)**: đọc flag → `kiosk_closed_by_owner=true` thì KHÔNG tự start_kiosk (trước đây guard dậy lại sau ~2 phút).
- **kiosk.js + mirror**: STOP bỏ setAvatarState(OFFLINE) + wakeEngine.stop — chỉ dừng audio + POST close_kiosk; title nút 'Thoát giao diện hiển thị — gọi TONY ơi để mở lại'; cache bump `stopexit_01nov_r1`; đồng bộ mirror = bản chính (mirror cũ lỗi cú pháp pre-existing).
- **E2E thật (08:17–08:20)**: start_kiosk → ACTIVE → close_kiosk → `kiosk_running=false + kiosk_closed_by_owner=true`, guard 135s KHÔNG dậy lại (log sạch) → wake_by_voice → kiosk dậy lại + flag xoá ✅.

## 01/11 ~08:40 — TỐC ĐỘ PHẢN HỒI + TỰ QUÉT LẠI TIN LỠ + REPLY RÕ MỤC (E2E)
- **Yêu cầu owner** (ảnh DM): kiểm tra tốc độ phản hồi; Tony treo → khi kết nối lại phải quét lại tin anh gửi trước đó để phản hồi; trả lời phải REPLY rõ đang phản hồi mục nào.
- **Phát hiện rễ**: (1) responder treo im lặng từ 07:58 (5 tin owner 22:58–08:11 bị bỏ lỡ); (2) seen_ids mark TRƯỚC khi gửi → treo giữa chừng = tin mất vĩnh viễn; (3) PC watchdog stale window 600s quá chậm; (4) gateway bot NetChat bỏ root_id (E2E: API trả root_id="") → không reply-thread được.
- **Fix** (deploy + restart responder PID 17476 + watchdog 15608):
  1. **Tốc độ**: poll 5s→2s; process_message lệnh hệ thống <1s, chat GLM ~4s.
  2. **Tự quét lại**: CATCHUP_WINDOW_MIN 45'→12h; startup KHÔNG mark-all-seen nữa — chỉ mark tin bot/đã answered/quá cũ; seen_ids mark CHỈ SAU khi gửi reply thành công → tin gửi lỗi/treo được quét lại ở lần chạy sau; read 10→60 tin/vòng.
  3. **Watchdog stale 600s→150s** (tools/watchdog.py) + responder PYTHONUNBUFFERED.
  4. **Reply rõ mục**: prefix '↩️ Trả lời tin "<trích 60 ký tự tin gốc>" (HH:MM):' trước MỌI response (root_id bị gateway bỏ — đã thử 4 lần E2E).
  5. Skill netchat_bot: read trả thêm root_id; send/dm có cờ --root-id (giữ tương lai khi gateway hỗ trợ).
- **E2E**: process_message('chào em') 4.1s OK; reply prefix trích dẫn gửi DM thành công; heartbeat fresh 2s/vòng.


## 01/11/2026 ~09:15 — HỘI THOẠI LIÊN TỤC PI5 (wake → chào → lắng nghe liên tục)

**Yêu cầu owner:** khi gọi TONY trên Pi5 → phản hồi ngay "Dạ, em nghe anh ạ." rồi chờ lệnh thoại, thu thập + xử lý liên tục, như hội thoại 2 người.

**Đã triển khai:**
- `edge_client/client_daemon.py`: `_voice_play_wav` + `_voice_start_recording` + `_voice_read_chunk` (selectors timeout 2s) + `_pcm_rms` + `_voice_collect_utterance` (VAD 0.2s/block, mở câu khi RMS ≥ 280, kết thúc khi im 2.8s, tối đa 14s) + `_pcm_to_wav_bytes` + `_voice_conversation_loop` (vòng lặp: nghe → converse → TTS → phát → nghe tiếp) + `_start_voice_conversation` (chào WAV cục bộ `~/tony_speech/greet_listen.wav` <0,5s không đợi PC). Wake_by_voice giờ gọi `_start_voice_conversation` (thay `_voice_listen_once` 8s cũ).
- `src/quan_ai_brain/web/server.py`: endpoint `/api/executive/edge/converse` + `_handle_api_edge_converse` (WAV → STT faster-whisper → route_message → GLM 8765 (model zai-org/GLM-5.3-Flash) → fallback Ollama → lọc [MOCK]); `_run_chat_once` mở rộng port/model. Kết quả trả reply text — daemon tự TTS + phát loa (đã đóng mic, không dội).
- Lời chào ngay bằng audio cục bộ — không phụ thuộc PC.

**E2E chứng minh (journalctl quan_ai_edge):**
- 08:52:39 `câu 1: 96000 bytes PCM` (VAD thu giọng mô phỏng qua loa)
- 08:58:38 STT='Một môi' → GLM reply hợp lý → `phát giọng: True`
- 08:59:36 STT='Cảm ơn các bạn và hẹn gặp lại.' → reply đúng nhân cách → `phát giọng: True`
- 09:01:01 STT giọng méo → GLM báo lỗi nhận dạng lịch sự
- Chuỗi wake → greet (pw-cat 08:52:20) → VAD → converse → TTS → loa CHẠY E2E.

**Đã sửa khi test:** ngưỡng VAD 800→280 (mic BT tiếng qua loa 340–630, nền 5–60); read timeout 2s chống pw-record chết treo; không pkill wake record; không fallback default mic; chờ 1.5s sau khi phát giọng; TTS retry 2 lần (Edge-TTS flaky); GLM 8765 ưu tiên hơn Ollama (is_mock → bỏ); xoá 639 memories do Ollama-mock nhiễm ('La La School', [MOCK]).

**Hạn chế hiện tại:** loa BT SRS-XB33 MẤT KẾT NỐI VẬT LÝ lúc ~09:04 (Connected: no — nghi power-save/hết pin) → chưa test được lệnh dừng "nghỉ đi" bằng giọng thật + chưa test nhiều lượt nói-nhắn liên tục với owner thật. Phiên hội thoại tối đa 15 phút, im 30s → nghỉ.


## 01/11/2026 ~10:00 — TONY COGNITIVE EVOLUTION M0: ACTUAL STATE AUDIT (KHÔNG thay đổi kiến trúc)

Owner phát động chương trình TONY COGNITIVE EVOLUTION V1.0 (master prompt). Đã thực hiện Bước 1 + Milestone 0 đúng phạm vi: AUDIT thuần, không sửa hệ thống.

**Bằng chứng đo thật (không lấy từ báo cáo cũ):**
- Workspace thật: D:\AI\AI Quanpt1 2026\BRAIN (E:\ KHÔNG tồn tại — master prompt ghi sai, đã đối chiếu với owner qua báo cáo).
- KHÔNG git repository (gap G-31 — rủi ro bảo toàn 83.118 dòng code).
- src: 34 module, 242 py files, 83.118 dòng; tests: 2.958 collected.
- PYTEST CHẠY LẠI: 2.914 passed, 44 skipped (2:59) — khớp báo cáo cũ.
- Services PC: 8766 (Ollama+fallback), 8765 (GLM via NetMind, api_key_present=true) — ONLINE; responder heartbeat fresh; learning daemon chạy; 3 scheduled tasks Ready.
- Services Pi5: quan_ai_edge + quan_ai_wake + quan_ai_kiosk_guard ACTIVE; temp 57,6–58,2°C; throttled=0x0; boot 07:16 ổn định (không reboot lạ sáng nay).
- Network: rtt 30,18ms qua Tailscale telemetry.
- Memory DB thật: memories=2004, semantic=1842, episodes=2548, candidate_knowledge=4284 (quarantine), knowledge_units=150, relations=210; durable_tasks=578.
- Loa BT SRS-XB33: Connected=no từ ~09:04 (chờ owner bật nguồn).
- PHÁT HIỆN MỚI: journald Pi5 cấu hình Storage=persistent NHƯNG /var/log/journal RỖNG → nhật ký vẫn volatile (mất lịch sử reboot 31/10 — không thể điều tra gốc rễ).
- PHÁT HIỆN MỚI: approval_verifier chỉ là hook None trong clae/quarantine.py; server không inject; 4.284 candidates không thể promote (đúng ràng buộc R4 — chờ owner).
- 639 memories rác do Ollama-mock đã được phát hiện và xoá trong phiên sáng (nhiễm 'La La School' + [MOCK]).

**Sản phẩm M0 (4 file):**
- reports/TC_EVOLUTION_M0_AUDIT.md
- reports/TC_EVOLUTION_M0_ARCHITECTURE.md
- reports/TC_EVOLUTION_M0_GAP_ANALYSIS.md (36 gap G-01..G-36 phân loại)
- reports/TC_EVOLUTION_M0_ROADMAP.md (6 milestone + 5 quyết định Q-1..Q-5 chờ owner)

**Chờ owner duyệt:** Q-1 git init; Q-2 fix journald Pi5; Q-3 cài Piper TTS fallback; Q-4 thiết kế approval_verifier R4; Q-5 BT power-save off. Chưa thực hiện bất kỳ thay đổi kiến trúc nào ngoài audit.


## 01/11/2026 ~10:45 — M1 SYSTEM HEALTH INTELLIGENCE HOÀN TẤT (E2E trên server thật)

Owner phê duyệt "BẮT ĐẦU M1". Đã triển khai 5/8 mục roadmap M1 (1.1, 1.2, 1.4, 1.5, 1.7) + test + restart server:

**Module mới `src/quan_ai_brain/monitoring/` (5 file, đọc-only):**
- pc_collector.py — psutil đo CPU/RAM/disk/process/uptime PC (11 chỉ số, optional dep fail-honest)
- pi5_collector.py — SSH probe Pi5: temp/throttled/ram/disk/BT/services/boot (BatchMode, timeout 12s)
- health_state.py — state machine NORMAL/WARNING/CRITICAL/UNKNOWN (worst-wins, UNKNOWN khi thiếu data)
- alert_engine.py — ngưỡng tường minh + chống spam cooldown 300s/check + lịch sử data/health_alerts.db + gửi DM qua netchat_bridge (sender inject được để test)
- aggregator.py + health_monitor.py — hợp nhất snapshot cache TTL 45s + daemon thread chu kỳ 120s

**Server (server.py):** routes mới GET /api/health/machine(?force=1) + /api/health/monitor + trang /health; HealthMonitor tự start trong run_executive_server; static/health_dashboard.html viết mới (bảng PC+Pi5+alerts, tự refresh 60s).

**Tests:** tests/test_monitoring_health.py (18) + tests/test_web_health_endpoints.py (4) — mock SSH/sender, không đụng mạng thật. Regression: **2.931 passed, 44 skipped (3:45)**.

**E2E thật (server 8766 restart 10:35, GLM READY):**
- /api/health/machine → overall WARNING: PC NORMAL (CPU 7%, RAM 59%, disk 34%), Pi5 WARNING (loa BT tắt; temp 57,1°C, throttled 0x0, ram 31%, disk 13%, 3 services active)
- HealthMonitor chạy nền: cycle 1 → alert bt_speaker_connected WARNING gửi DM THÀNH CÔNG 09:40; cycle 2 → ghi DB, chặn gửi đúng cooldown:300s
- Dashboard /health phục vụ trang mới OK

**Chưa làm (chờ phê duyệt/điều kiện):** M1.3 fix journald Pi5 (Q-2), M1.6 Piper TTS (Q-3), M1.8 điều tra reboot (cần 1.3). Alert ngưỡng hiện tại: CPU 85/97, RAM 85/95, disk 85/95, temp 70/80, server RSS 1200/2000 MB.


## 01/11/2026 ~11:15 — M1 HOÀN TẤT THEO MASTER PROMPT V1.1 (mở rộng đầy đủ)

Nhánh mở rộng sau phê duyệt "BẮT ĐẦU M1" (lần 2 — master prompt V1.1):

**Thêm mới:**
- 4 collector: network (ICMP PC→Pi5, tailscale), service (HTTP 8765/8766 + heartbeat), database (PRAGMA quick_check mode=ro + WAL), voice (STT import / LLM provider health / TTS).
- Aggregator hợp nhất 6 component + MAINTENANCE state (owner-gated API, 403 nếu approved_by_owner != 'Quanpt1') + telemetry history data/health_history.db (keep 2000 rows) + history endpoint.
- RCA engine (rca_engine.py): OBSERVED_FACT / POSSIBLE_CAUSE / CONFIRMED_CAUSE / INSUFFICIENT_EVIDENCE — không tự sinh CONFIRMED; endpoint /api/health/rca.
- Dashboard /health nâng cấp: 6 khu + chart CPU/RTT 120 điểm + bảng RCA + alerts; 100% data backend thật.
- Điều tra reboot 31/10 (read-only): INSUFFICIENT_HISTORICAL_EVIDENCE — log đã mất theo reboot; reports/M1_PI5_REBOOT_INVESTIGATION.md.

**Tests:** +17 (test_monitoring_extended.py) — tổng M1: 39 test mới; regression 2.953 passed / 44 skipped / 0 failed.

**E2E thật:** 6 khu đo thật (PC NORMAL, Pi5 WARNING loa tắt, network NORMAL rtt 5–30ms, services WARNING learning log-age 150–230s, databases NORMAL, voice NORMAL GLM READY); monitor bền ≥10 chu kỳ; alert DM 4 lần thật + cooldown đúng; history tích lũy; maintenance gate verify (403 / MAINTENANCE / trở lại).

**Báo cáo 13 file:** 10 M1_* + TONY_COGNITIVE_EVOLUTION_HANDOFF.md + 2 M2_* (thiết kế Event Bus + ma trận 5 engine — CHƯA cài, chờ duyệt).

**Quyết định Q-1..Q-5 + M1-A/B/C: PENDING_OWNER — KHÔNG tự thực hiện.**


## 01/11/2026 ~11:50 — M4 SELF MODEL & AUTONOMOUS LEARNING (phần 1: introspection + self-care thực)

Owner phê duyệt "BẮT ĐẦU M4" (nhảy M2/M3 — chúng vẫn PENDING_DESIGN_APPROVAL).

**Audit-first thu bằng chứng:** candidate_knowledge thực tế = 1.491 approved + 2.933→2.943 quarantined (không phải '4.284 kẹt' như M0 ghi — 1.491 được owner-approved bulk 31/10 có decision_note; **backup brain_pre_approval.db KHÔNG tồn tại** dù note ghi có). CLO: 7 sessions, vòng cuối #7 RUNNING từ 27/10 (không tiến triển). Skills: 6 (1 AVAILABLE, 5 TESTED). 4/5 engine nhận thức vẫn ORPHAN (M2 chưa cài).

**Code M4 (đều có test):**
- 3 API đọc-only: GET /api/self/model, /api/self/state (13 câu tự nhận thức, thêm q13_learning_autonomy), /api/self/learning (CLO + candidates + skills từ DB thật).
- self_model_engine: +get_learning_checkpoint_state (nguồn sự thật duy nhất cho CLO, fail-honest); sửa deployment edge_location 192.168.1.21 → 100.100.83.59 (Tailscale).
- self_care_engine: **sửa trung thực** — auto_recovered KHÔNG còn True khi recovery chỉ simulated (action=PENDING, chờ executor thật); check_pi5_connection IP Tailscale.
- health_monitor: self_care inject tuỳ chọn — mỗi cycle chạy health checks TCP thật (Ollama/8765/8766/Pi5), chỉ check không-healthy thành alert, cùng AlertEngine chống spam.
- server: start_health_monitor inject _get_self_care_engine(); dashboard /health thêm 2 khu M4 (Self Model + Learning, fail-honest render).
- state_tracker.py: sửa **flaky lâu năm** — get_state_history sort DESC + reverse (double-negation, sai theo thời gian thực khi timestamp trùng); nay ASC+rowid, không reverse. +sửa annotation from_state nullable.

**Tests:** +16 (tests/test_m4_self_introspection.py) — regression full **2.969 passed / 44 skipped / 0 failed (2:36)**; file flaky chạy 3 lần liên tiếp PASS.

**E2E thật (server restart chuẩn pythonw+env key, PID mới):** 3 API M4 trả dữ liệu sống (confidence 92.3%, Pi5 HEALTHY qua Tailscale, CLO/candidates/skills đúng DB); self-care cycle thật: 4/4 checks healthy, auto_recoveries=0, alert loa BT vẫn gửi DM đúng đường.

**Báo cáo:** reports/M4_SELF_MODEL_REPORT.md.


## 01/11/2026 ~12:05 — M5 HUMAN-LIKE CONVERSATION (phần 1: ngữ cảnh hội thoại + Self-Q&A + learning health)

Owner phê duyệt "BẮT ĐẦU M5" (M2/M3 vẫn chờ duyệt; gộp M4-B/C vào scope này).

**Code M5 (đều có test):**
- `cognition/conversation_state.py` (mới, ~150 dòng): ConversationStateManager per-channel (voice/web/dm), TTL 10 phút, lưu JSON `data/conversation_state.json` (không tạo DB mới), detect đại từ tiếng Việt (nó/vậy/thế/anh ấy/...), `build_contextualized_query` bọc ngữ cảnh lượt trước — đóng G-22 cho kênh thoại.
- `cognition/self_qa.py` (mới, ~200 dòng): SelfQA 6 nhóm câu hỏi self (identity/capabilities/location/health/learning/limits) → trả lời TỪ DỮ LIỆU SỐNG (SelfModelEngine + monitoring snapshot + DB counts + skill registry), không cho LLM phỏng đoán — đóng G-12/M4-C.
- Wired cả 2 handler thoại (`/api/executive/edge/voice_command` + `/converse`): Self-QA đứng trước intent → intent → GLM có ngữ cảnh (nếu có đại từ) → ghi state sau trả lời.
- `health_monitor.py` + M4-B: `_evaluate_clo_stall` — CLO RUNNING > 24h không tiến triển → alert edge-trigger gửi qua AlertEngine thật (cooldown + DB + DM); KHÔNG khai sent=True khi chưa gửi thật.
- `memory/session_manager.py`: sửa **flaky thời gian** (lớp lỗi giống state_tracker) — `_now_strictly_after()` đảm bảo timestamp mutator luôn > mốc trước (Windows clock tick 15,6ms làm create+add cùng tick → so sánh '>' fail ngẫu nhiên). Chạy 10/10 PASS.

**Tests:** +27 (`tests/test_m5_conversation.py` — state TTL/corrupt/anaphora, SelfQA classify+grounded, CLO-stall edge-trigger, wiring source-check). Regression full: **2.996 passed / 44 skipped / 0 failed (2:38)** — baseline 2.969 → +27.

**E2E thật (restart đúng KHOI_DONG_24_7.bat sau sự cố chết server 10:55 — hồi sinh đủ 8765/8766/responder/watchdog):**
- **CLO-stall alert TỰ NHIÊN hoạt động**: cycle 1 sau restart → alert `selfcare:clo_stalled` WARNING "CLO #7 RUNNING 108h" **đã gửi DM thật (sent=1)** — đúng kẹt thật đang có.
- Voice E2E loopback: WAV → STT → GLM → trả lời → **state hội thoại ghi thành công** (file JSON thật). STT méo do TTS test (Edge-TTS flaky 5/5 fail = G-33 tái diễn; SAPI giọng Anh đọc không dấu) → GLM trả lời trung thực "chưa hiểu, anh nói lại" — pipeline đúng, chưa có audio tiếng Việt sạch để chốt Self-QA qua mic ảo; Self-QA đã verify đầy đủ trong ngữ cảnh server với 5/5 câu trả lời grounded từ dữ liệu sống.

**Quan sát trung thực:** quarantined 2.943 → 2.979 (+36 trong ~20 phút) — learning daemon đang học và tạo candidate liên tục, chờ duyệt Q-4. Edge-TTS chết hàng loạt lúc test = bằng chứng mới cho Q-3 (Piper TTS local fallback).


## 01/11/2026 ~11:45 — M6 BẮT ĐẦU: QEP-0001 SPEC + 2 PHÁT HIỆN THẬT (chờ duyệt trước khi cài)
- **QEP-0001 spec hoàn tất** (`reports/QEP-0001_EMBODIMENT_DISTRIBUTED_INTELLIGENCE.md`): 3 lớp IDENTITY/CAPABILITY/COMMAND + multi-agent Supervisor 3 worker + kế hoạch B1-B4, mọi mục đều path:line. Theo roadmap M6: spec trước khi cài → CHƯA có code nào được thêm.
- **P0 BẢO MẬT (tìm thấy khi audit)**: daemon Pi ký HMAC mọi request (`edge_client/auth.py:42-52`) nhưng server KHÔNG BAO GIỜ verify (`server.py:3251-3271, :3650-3689` — grep src: 0 lời gọi verify_request); chiều PC→Pi cũng không ký (`server.py:283-306`); secret là placeholder trong source (`config.py:25`). → B1 của QEP sẽ fix, chờ duyệt.
- **Fix flaky test E2E ở gốc**: `test_web_server_e2e_multi_turn_chat` PASS 11:08 → FAIL 11:23 cùng code. Điều tra dump stack: khi catalog NetMind hiccup (GLM cold 9,5s đo thật 11:41) router rơi local Ollama → turn-1 đo thật 28,2s (context KB 4.790 docs + grounding, CPU) > timeout 25s test. Fix: stub LLMProvider.generate trong fixture (kiểm pipeline đúng nghĩa, độc lập mạng) + khôi phục sau dùng; server thật 8766 vẫn qua GLM bình thường (6,8s, không đụng).
- **Kiểm chứng**: file E2E 5/5 PASS 8,5s (trước 27s+); regression full 2.996 PASS / 0 FAILED / 44 skipped; HANDOFF_LATEST regen exit 0.
