# TONY TOOL / SKILL / AGENT ASSESSMENT — Kiểm kê năng lực công cụ
**Cập nhật:** 01/11/2026 16:45 · PHẦN 6.3 mở rộng

## 1. Tools (126 scripts tools/)

| Nhóm | Ví dụ | Runtime? |
|---|---|---|
| Vận hành 24/7 | watchdog.py ⚠MISSING, ensure_single_instance.ps1, KHOI_DONG_24_7.bat | ✅ (watchdog ngoại lệ) |
| Trí nhớ/backup | backup_database.py, mirror_workspace_to_f.py (MỚI), sched_task_setup.py | ✅ mirror chạy 16:32 |
| Giao tiếp | netchat_auto_responder.py (fix P0), netchat_command_center.py, morning_report.py | ✅ LIVE |
| Di trú | migrate_paths_to_new_pc.py | ✅ đã dùng 30/10 |
| Kiểm thử | _test_import_repro.py, 155 tests | ✅ |
| Cron setup | run_backup.bat ⚠, run_morning_report.bat, run_mirror_f.bat | ✅/⚠ backup dừng |

## 2. Skills (netmind + workspace)

- bot-netchat (DM command center), browser-use, outlook-local, ttns-meeting-lookup, quan-ai-brain-ops, perplexity, viettel-ppt-master, minimax-docx/pdf/xlsx, skill-creator, coding-agent… ✅ đăng ký thống nhất qua netmind.

## 3. Agents

| Agent | Vai trò | Trạng thái |
|---|---|---|
| GLM Cloud (netmind) | suy luận chính | ✅ LIVE RTT ~6,8s |
| Ollama BGE-M3 | embedding địa phương | ✅ 8 models, port 11434 |
| Delegation subagents | việc dài | ✅ (deleg_e6f576a9 OK) |
| **Supervisor multi-agent** | điều phối agent con | ⚠️ thiết kế (M6-B2) — chưa runtime |

## 4. Phân biệt "đã xây" vs "đã làm việc thật" (ngày 01/11)

| Năng lực | Đã xây | Đã làm việc thật hôm nay |
|---|---|---|
| Fix P0 responder | ✅ | ✅ E2E 0 router-error sau 16:13 |
| HMAC M6-B1 | ✅ | ✅ 0 fault 120s Pi↔PC |
| Owner-ACK alert | ✅ | ✅ sent=0 từ 16:10 |
| Mirror F | ✅ | ✅ 47.051 file, verify 3 lớp |
| Morning report | ✅ | ✅ cron OK sáng nay |
| Voice TTS tiếng Việt | ✅ code | ⚠️ Edge-TTS 403 flaky → chờ Q-3 Piper |
| Outlook/Email flow | ⚠️ skill có | NOT_VERIFIED bài thật |

## 5. Điểm: Tool/Skill = **CẤP 2**; Agent orchestration = **CẤP 1** (supervisor chưa chạy). Không thăng cấp khi chưa có bằng chứng.
