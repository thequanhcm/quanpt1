# BÁO CÁO KIỂM TOÁN HIỆU NĂNG + BẢO MẬT DỮ LIỆU ĐIỀU HÀNH
Thời điểm: 2026-10-27T17:19:07.820276+00:00 · Thu thập thật trên hệ thống đang chạy (không mô phỏng)

## Step 1 — Trạng thái hệ thống
- /api/health OK, độ trễ 29.7 ms
- Tiến trình nền: watchdog.py (PID 4088)
- Tiến trình nền: watchdog.py (PID 92)
- Tiến trình nền: learning_daemon.py" (PID 7724)
- Tiến trình nền: learning_daemon.py" (PID 15200)
- Tiến trình nền: python.exe" start_dual_servers.py (PID 20192)
- Tiến trình nền: python.exe" start_dual_servers.py (PID 12416)
- Tiến trình nền: python.exe" -u start_dual_servers.py (PID 21236)
- Tiến trình nền: python.exe" -u start_dual_servers.py (PID 8216)
- Tiến trình nền: python.exe" -u tools/netchat_auto_responder.py (PID 18036)
- Tiến trình nền: python.exe" -u tools/netchat_auto_responder.py (PID 17184)

## Step 2 — Bảng chỉ số hiệu năng
| Chỉ số | Giá trị |
|---|---|
| Health latency | 29.7 ms |
| Server workingset | 81.1 MB |
| DB brain.db | 87.9 MB · journal=delete |
| DB consultations.db | 0.0 MB · journal=wal |
| DB document_index.db | 0.0 MB · journal=delete |
| DB email_intake.db | 0.0 MB · journal=delete |
| DB experience.db | 0.0 MB · journal=delete |
| DB gov_sandbox.db | 0.1 MB · journal=wal |
| DB governance.db | 0.5 MB · journal=wal |
| DB information_gaps.db | 0.0 MB · journal=delete |
| DB learning_checkpoints.db | 0.0 MB · journal=delete |
| DB learning_reports.db | 0.0 MB · journal=delete |
| DB learning_sandbox.db | 0.1 MB · journal=delete |
| DB memory.db | 0.1 MB · journal=delete |
| DB tasks.db | 11.9 MB · journal=wal |
| DB todos.db | 0.0 MB · journal=delete |
| File git đang track | 1497 |
| File nhạy cảm trong git | 0 |
| Audit log | 0.55 MB |

## Bảo mật dữ liệu điều hành
✅ Không có file secret/credential nào trong git index.

Bằng chứng thô (JSON): reports/audit_metrics_20261027.json