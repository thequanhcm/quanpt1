# BÁO CÁO: Tự kích hoạt 24/7 khi khởi động máy — Reboot-Proof Stack

**Mã báo cáo:** RPT-QAB-247-REBOOT-20261027
**Thời điểm:** 27/10/2026 ~00:30 ICT
**Yêu cầu chủ sở hữu:** "Thiết lập để mỗi khi máy tính khởi động lại thì hệ thống trợ lý tự kích hoạt và hoạt động 24/7, chạy ngầm ổn định, trơn chu."

## 1. Audit trước khi sửa — 4 lỗ hổng thật (tìm thấy, không đoán)

| # | Lỗ hổng | Hậu quả nếu không sửa |
|---|---|---|
| 1 | **API key GLM Cloud KHÔNG ở user-level env** — chỉ tồn tại trong session (kế thừa từ netMind Desktop). Đã verify registry `HKCU\Environment`: MISSING | Sau reboot server rơi vào MOCK mode — bot trả lời rác mà UI vẫn "nghe có vẻ ổn" |
| 2 | **Watchdog trỏ `C:\Users\DELL\.venv` — venv KHÔNG TỒN TẠI** | Auto-restart fail âm thầm vĩnh viễn (lỗi NotFound mỗi lần thử) |
| 3 | **Watchdog `stdout=PIPE` không bao giờ đọc** — dashboard refresh 10s sinh log liên tục → buffer ~64KB đầy → **server con TREO ĐỨNG** (block trên write) | Treo "ngụy trang" như hang thật; watchdog restart liên tục chạm circuit breaker |
| 4 | **Startup folder giữ BẢN COPY cũ** của `KHOI_DONG_24_7.bat` (1941 bytes, chỉ 8765 qua `start_server_fixed.py`) | Khởi động máy thiếu 8766 Executive; update launcher không bao giờ có hiệu lực |

Phát hiện phụ: cặp process .venv/Python311 chạy CÙNG script không phải zombie — Python311 là interpreter thật đằng sau venv launcher (`pyvenv.cfg` home = Python311). Đã xác minh bằng `sys.executable` trong cả hai.

## 2. Giải pháp triển khai

1. **Persist env user-level** (`tools/persist_netmind_env.ps1`): `NETMIND_API_KEY` + `HERMES_CUSTOM_NETMIND_API_KEY` + `NETMIND_DESKTOP_LLM_BASE_URL` + `NETMIND_EXTERNAL_DATA_ALLOWED=true` → registry `HKCU\Environment`. Giá trị KHÔNG in/log/truyền qua command line; verify chỉ kiểm tra existence + độ dài.
2. **Watchdog sửa tận gốc** (`tools/watchdog.py`): trỏ `.venv` của project; giám sát **CẢ HAI cổng** (`both_servers_healthy()`); restart qua `start_dual_servers.py`; stdout redirect ra `logs/dual_servers_watchdog.log` (hết bug treo PIPE); heartbeat responder log cập nhật path.
3. **Responder heartbeat** (`tools/netchat_auto_responder.py`): touch `logs/netchat_responder_heartbeat.log` mỗi vòng poll → watchdog phát hiện responder chết/stuck qua freshness (cơ chế có sẵn, trước giờ không có file để đọc).
4. **`KHOI_DONG_24_7.bat` viết lại (5 thành phần)**: Dual Servers 8765+8766 → NetChat Responder → Learning Daemon → Watchdog → đặt lịch backup 2AM (schtasks idempotent); `:LoadUserEnv` đọc key từ registry vào process env nếu chưa có.
5. **Startup folder → stub**: file trong Startup chỉ `call` bản chính trong workspace — từ nay sửa launcher chỉ cần 1 file, không lo bản copy lỗi thời.
6. **Backup 2AM**: task `QUAN_AIBRAIN_Backup_2AM` (user-level, không cần Admin) → `tools/run_backup.bat` → `backup_database.py` (giữ 30 bản).

## 3. Kiểm chứng E2E THẬT

- **Tự hồi phục:** kill dual servers 00:24:03 → watchdog phát hiện + restart 00:24:29 bằng project venv → **cả 2 cổng HTTP 200** sau ~75s. Log: "Starting servers via start_dual_servers.py on ports 8765+8766... Servers started (PID 21148)".
- **Heartbeat sống:** file mtime cập nhật mỗi 5s đúng chu kỳ poll.
- **Env sau "reboot giả lập":** registry đã SET (key len=25, base_url len=44) — khởi động mới sẽ kế thừa.
- **Backup:** chạy thử tạo `backups/brain_20261026_172523.db` (42MB); task Ready, Next Run 02:00 đêm nay.
- **Chat smoke sau restart:** GLM-5.3-Flash trả lời có grounding facts đúng.
- **Watchdog tự giám sát:** Ollama OFFLINE được báo trung thực từng vòng (DEGRADED→OFFLINE), không tự restart thứ nó không sở hữu (đúng GAP-R3 policy).

## 4. Trạng thái vận hành sau thiết lập

- Stack đang chạy: dual servers (watchdog-supervised), responder (heartbeat), learning daemon, watchdog, backup 2AM.
- Startup flow khi reboot máy: **logon → Startup\KHOI_DONG_24_7.bat (stub) → call bản chính trong workspace → 5 thành phần lên** — không cần thao tác tay.
- Đúng nguyên tắc: watchdog chỉ restart CỤM SERVER (mà nó sở hữu); responder/daemon/Ollama chỉ giám sát + cảnh báo qua kênh (policy GAP-R3 giữ nguyên).

## 5. Giới hạn trung thực

- Chưa test reboot MÁY THẬT (chỉ test kill-process + watchdog hồi phục + registry persist) — lần reboot thực đầu tiên anh nên mở dashboard kiểm tra 5 phút đầu; nếu thiếu thành phần, xem `logs/watchdog.log`.
- Responder chết thì watchdog CHỈ CẢNH BÁO (không tự restart) — đúng policy hiện hành; nếu muốn auto-restart responder, cần sprint riêng có duyệt.
- Task Scheduler full-set (4 task QUAN_AIBRAIN_*) vẫn cần Admin; giải pháp Startup + schtasks user-level là lựa chọn hiện tại.

## 6. Bước kế tiếp đề xuất
1. Reboot thật khi anh tiện → kiểm tra http://127.0.0.1:8765 + 8766 + kênh NetChat có tin chào.
2. Sprint tiếp theo (chờ duyệt): auto-restart responder trong watchdog; merge approval gates vào consultation tickets.
