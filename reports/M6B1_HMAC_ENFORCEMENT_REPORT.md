# M6-B1 — HMAC ENFORCEMENT — BÁO CÁO HOÀN TẤT
**Thời điểm:** 01/11/2026 15:50 · **Phê duyệt:** Quanpt1 ("DUYỆT M6-B1") · **Thực hiện:** TONY
**Kết quả:** ✅ HOÀN TẤT — regression 3.002 PASS / 0 FAIL · E2E Pi5 thật sạch 120s

---

## 1. VẤN ĐỀ (đã audit từ M6)

- Pi5 ký HMAC mọi request (`edge_client/auth.py`), nhưng server PC **không bao giờ verify** — chỉ đọc device header rồi tin ngay (`server.py` `_handle_api_executive_supervisor`).
- Hệ quả: bất kỳ host nào trong tailnet giả header `X-QuanAI-Device` đều nhận được **pending_commands** (lệnh điều khiển hình thể: nhạc, reload, navigation, camera...).

## 2. THAY ĐỔI (4 file)

### 2.1. `src/quan_ai_brain/web/server.py` — VERIFY TẬP TRUNG (401 fail-closed)
- Thêm `_edge_hmac_verify()` + gate ở **cả `do_GET` và `do_POST`** (trước khi dispatch).
- Device header có nhưng thiếu sig/nonce/ts → 401 `MISSING_HMAC_HEADERS`.
- Sig sai → 401 `INVALID_SIGNATURE`; nonce lặp → 401 `REPLAY_DETECTED` (anti-replay toàn process, cửa sổ 600s).
- Secret nguồn: `EDGE_HMAC_SECRET` env → `data/edge_hmac_secret.txt` (copy từ config.json Pi5, 64 ký tự — đã đối chiếu SHA-8 khớp: `3cca66f7`). **Không còn placeholder.**
- Drift 300s (đo PC↔Pi lệch ~1s).
- `do_POST` tái sử dụng body đã stash từ verify (tránh đọc 2 lần stream).
- Auth failure ghi vào `EdgeConnectionMonitor.record_auth_failure` → alert CRITICAL + DB.

### 2.2. `edge_client/client_daemon.py` — 2 BUG THẬT ĐƯỢC EXPOSE & FIX
1. `_poll_tasks_and_consultations` tái dùng 1 nonce cho 2 request → request 2 bị chặn REPLAY. **Fix:** mỗi request tạo bộ header riêng + thêm device headers (trước đây GET polls thiếu device header).
2. Gán `edge_agent.signed_headers_factory = self.auth.create_signed_headers` trong `EdgeClientDaemon.__init__`.

### 2.3. `edge_client/edge_agent.py` — POST events ký SAI payload
- `send_events_to_brain` nhận header ký trên payload rỗng rồi POST kèm body → `INVALID_SIGNATURE` ngay khi server verify.
- **Fix:** dùng `signed_headers_factory(payload)` để ký trên payload thật; backward-compat: nếu không có factory, bỏ hẳn 3 header HMAC cũ (không gửi sig rác).

### 2.4. `data/edge_hmac_secret.txt` — secret thật (không in giá trị)

## 3. ĐỒNG BỘ PI5
- `scp client_daemon.py edge_agent.py` → Pi5 `~/Desktop/edge_client/`, `py_compile` OK.
- Restart daemon (`setsid nohup python3 main.py`), PID mới, kiosk 8768 listen OK.

## 4. KIỂM CHỨNG

### 4.1. Unit tests (6 test mới — `tests/test_m6b1_hmac_enforcement.py`)
| Test | Kết quả |
|---|---|
| Device header không HMAC → 401 | ✅ |
| Ký sai secret (attacker) → 401 | ✅ |
| Ký đúng → 200 + READY | ✅ |
| Replay nonce → 401 | ✅ |
| UI không device header → không ảnh hưởng | ✅ |
| Secret env > file fallback | ✅ |

### 4.2. E2E với Pi5 THẬT
- **Signed request từ PC** (dùng secret file): 200 READY ✅
- **Signed request từ Pi5** (Python nội bộ Pi, secret config.json): 200 ✅
- **Daemon thật sau restart:** state **READY** liên tục, heartbeat RTT ~230ms
- **Giám sát 120 giây (6 cycle × 20s): 0 HMAC fault mới** — trước khi fix daemon: 10× INVALID_SIGNATURE + 10× REPLAY mỗi phút
- Active auth-fault alerts cũ: 2 (lịch sử từ lúc pre-fix daemon) — không phát sinh thêm

### 4.3. Regression
- **3.002 PASS / 44 skipped / 0 FAIL** (tăng +6 test so 2.996)
- `validate_and_report.py` exit 0 → `reports/HANDOFF_LATEST.md` regenerated

## 5. SỰ CỐ TRONG QUÁ TRÌNH (trung thực)
- Bản vá đầu tiên của em (sprint trước) nằm SAI chỗ (GET supervisor handler, dev-mode log-only, dùng placeholder secret) → đã xóa, thay bằng gate tập trung.
- Em từng ghi đè `tools/morning_report.py` của Sprint 6 (mất `_ollama_status`...) → 5 test fail → **đã khôi phục từ backup** `backups/path_migration_20261030/tools/morning_report.py`, 7/7 pass; bản mới của em lưu tại `reports/TONY_MORNING_REPORT_SCRIPT_V2_20261101.py.bak`.
- Cron `morning_report` script riêng (`~/.hermes/scripts/morning_report.py`) vẫn là bản V2 đơn giản hoá — hoạt động độc lập với tool Sprint 6.

## 6. TRẠNG THÁI SAU M6-B1
- Server PC: 8765+8766 UP (PID mới sau restart), responder UP, learning daemon đang khởi động lại.
- Pi5 daemon: READY, ký đúng, không còn bị từ chối.
- **Q-4 chưa làm** — candidates vẫn quarantine (đúng phạm vi duyệt).
- An toàn hoàn tác: `git` chưa init (Q-1) — bản vá có thể hoàn tác bằng cách remove gate do_GET/do_POST + khôi phục 2 file edge_client từ backup path_migration (nhưng sẽ mất 2 bugfix daemon).

## 7. VIỆC TIẾP THEO (chờ duyệt)
- **Q-3** Piper TTS (đã được duyệt trong "DUYỆT Q-3, M6-B1, Q-4" — sẽ làm tiếp)
- **Q-4** approval_verifier (đã được duyệt — làm sau Q-3)

---
*Báo cáo bởi TONY 01/11/2026 15:50. Mọi số liệu đều từ tool output thật trong phiên này.*
