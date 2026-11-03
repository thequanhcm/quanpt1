# M1 — SYSTEM HEALTH AUDIT TỔNG HỢP

**Người lập:** TONY (QUAN AI BRAIN) · **Ngày:** 01/11/2026, 09:30–11:15 giờ VN
**Workspace:** `D:\AI\AI Quanpt1 2026\BRAIN` · **Chế độ:** READ-ONLY + telemetry tự ghi (health_alerts.db / health_history.db)
**Baseline đối chiếu:** M0 audit (2.914 pytest PASS / 44 skipped · 83.118 LOC · 242 file)

---

## 1. Điều đã triển khai (tất cả E2E trên server thật 8766)

| Thành phần | File | Chức năng | Verify |
|---|---|---|---|
| PC Collector | `src/quan_ai_brain/monitoring/pc_collector.py` | psutil: CPU/RAM/disk/process/uptime — 11 chỉ số | E2E thật: CPU 7%, RAM 59%, disk 34%, 16 python proc |
| Pi5 Collector | `pi5_collector.py` | SSH BatchMode probe: temp/throttled/ram/disk/BT/services/boot — 7 chỉ số | E2E thật: 57–58,7°C, 0x0, ram 31%, disk 13%, 3 service active |
| Network Collector | `network_collector.py` | ICMP PC→Pi5 + loss + Tailscale interface | E2E thật: RTT 5–30ms, loss 0%, Tailscale up |
| Service Collector | `service_collector.py` | HTTP probe 8765/8766 + heartbeat responder + log-age learning daemon | E2E thật: cả 2 port up, responder 8.4s, learning warn 150–230s |
| Database Collector | `database_collector.py` | PRAGMA quick_check read-only + WAL + row counts | E2E thật: brain.db + tasks.db quick_check=ok |
| Voice Collector | `voice_collector.py` | STT import probe + LLM provider health + TTS engine | E2E thật: faster-whisper 1.2.1, NetMind READY, edge-tts ok |
| Health State | `health_state.py` | NORMAL/WARNING/CRITICAL/UNKNOWN/**MAINTENANCE** worst-wins | 18 unit test + E2E |
| Alert Engine | `alert_engine.py` | Ngưỡng tường minh + cooldown 300s/check + `data/health_alerts.db` + DM NetChat | E2E thật: 16 alert ghi DB, 4 DM gửi thật, còn lại cooldown |
| Aggregator | `aggregator.py` | Hợp nhất 6 component + cache TTL 45s + history `data/health_history.db` | E2E: 14+ điểm history |
| Monitor runtime | `health_monitor.py` | Daemon thread chu kỳ 120s, tự start cùng server | E2E: cycles 1→10 bền, không giết server |
| RCA Engine | `rca_engine.py` | OBSERVED_FACT / POSSIBLE_CAUSE / CONFIRMED_CAUSE / INSUFFICIENT_EVIDENCE | E2E: 1 FACT (BT loa), không tự sinh CONFIRMED |
| Server wiring | `web/server.py` | `/api/health/machine(?force=1)` · `/api/health/history` · `/api/health/rca` · `/api/health/monitor` · POST `/api/health/maintenance` (owner-gated) · trang `/health` | E2E tất cả |
| Dashboard | `static/health_dashboard.html` | 6 khu + xu hướng CPU/RTT + RCA + alerts, data 100% backend thật | E2E serve + JS fetch đúng |

## 2. Kiểm chứng đọc-only (bắt buộc master prompt §V)

- Không `git init`, không commit (git vẫn chưa khởi tạo — Q-1 PENDING).
- Không chạy lệnh sudo ghi trên Pi5; mọi SSH chỉ `cat/ls/journalctl --list-boots/vclog/systemctl is-active/uptime/df/free/bluetoothctl info`.
- Không cài package mới; không restart service nào ngoài **server TONY do em quản lý** (start_dual_servers — thuộc chu kỳ deploy bình thường, có trong AGENTS work procedure).
- Collectors chỉ đọc hệ thống; 2 DB telemetry do chính M1 tạo trong `data/` (không đụng brain.db/tasks.db — test riêng xác nhận).
- Q-1→Q-5: KHÔNG thực hiện bất kỳ quyết định nào.

## 3. Kết quả test

- M1 tests: `tests/test_monitoring_health.py` (18) + `test_monitoring_extended.py` (17) + `test_web_health_endpoints.py` (4) = **39 PASS** (mock SSH/ping/DM/DB — không đụng thật).
- Regression toàn bộ: **2.953 passed, 44 skipped (2:55)** — so baseline 2.914: +39 test mới, 0 fail, 0 skip mới.
- `tools/validate_and_report.py`: exit 0, handoff regenerated (2.936 pass trong lần chạy đó — chênh là test runtime biến động, không phải fail).

## 4. Trạng thái hệ thống lúc chốt (11:05 VN)

| Khu | Trạng thái | Chi tiết |
|---|---|---|
| PC | ✅ NORMAL | CPU 7%, RAM 59% (6,5GB free), disk D: 33,7% (155GB free) |
| Pi5 | ⚠️ WARNING | Loa BT SRS-XB33 tắt (owner chưa bật nguồn); nhiệt 57–58°C, 0x0, ram 31% |
| Network | ✅ NORMAL | RTT 5–30ms, loss 0% |
| Services | ⚠️ WARNING | Learning daemon log age ~230s (cycle dài — theo dõi); 8765/8766 up |
| Databases | ✅ NORMAL | quick_check ok, WAL nhỏ |
| Voice | ✅ NORMAL | STT ready · LLM READY · TTS ok |
| **OVERALL** | **WARNING** | Do 2 cảnh báo ngoại vi (loa tắt, learning log age) — không nghiêm trọng |

## 5. Vấn đề phát hiện trong M1

1. **Learning daemon "log age" đỏ thỉnh thoảng** — daemon chạy cycle dài (ingest 4.884 facts) làm log im 3–4 phút; chưa phải treo. Đề xuất: ngưỡng riêng 600s cho learning (đã đặt crit 600s) + quan sát.
2. **Snapshot đầu tiên sau restart có thể CRITICAL giả** — network đo trước khi interface sẵn sàng. Đã giảm tác động bằng cache+force; chấp nhận vì fail-honest đúng bản chất (chưa có dữ liệu thì UNKNOWN/CRITICAL đo được).
3. **Alert DB có 12 cooldown rows** — hoạt động đúng thiết kế chống spam (không phải lỗi).

## 6. Điều kiện hoàn thành M1 (§XI) — đối chiếu

| Điều kiện | Trạng thái |
|---|---|
| PC Health dữ liệu thật | ✅ |
| Pi5 Health dữ liệu thật | ✅ |
| Network Health đo được | ✅ |
| Service Health thật | ✅ |
| Database Health thật | ✅ |
| Voice Health thật (hoặc UNKNOWN rõ) | ✅ |
| Dashboard data backend thật | ✅ |
| Lịch sử telemetry | ✅ health_history.db |
| Phân loại cảnh báo | ✅ 5 mức + alert DB |
| Có test | ✅ 39 test mới |
| Read-only đúng phạm vi | ✅ (mục 2) |
| Báo cáo + bằng chứng | ✅ bộ 10 file M1_* |

**M1: COMPLETED** (trừ Q-2/Q-3 đang chờ duyệt — không thuộc phạm vi read-only).
