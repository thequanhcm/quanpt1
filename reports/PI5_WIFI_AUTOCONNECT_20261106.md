# ĐỒNG BỘ + CÀI ĐẶT PI5 TỰ KẾT NỐI KHI CÙNG MẠNG WIFI (06/11/2026)

**Yêu cầu owner:** "tiếp theo em đồng bộ và cài đặt pi5 để kết nối khi máy tính này kết nối cùng mạng wifi"
**Kết quả:** **XONG — LIVE_VERIFIED.** Pi5 tự kết nối lại TONY trên PC khi 2 máy cùng mạng WiFi, không cần can thiệp; mất kết nối giờ báo OFFLINE trung thực (fail-honest fix mới).

## 1. Audit chuỗi auto-reconnect (trước khi cài đặt)

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| systemd `quan_ai_edge` | `Restart=always, RestartSec=5` + `After=network-online.target tailscaled.service` | service tự hồi sinh khi crash, đợi mạng sẵn sàng khi boot |
| `NetworkManager-wait-online` | enabled | boot không start service trước khi có IP |
| WiFi Pi5 | 4 mạng đã lưu, autoconnect=yes (`Ca Ngo 5G` hiện tại) | OS tự nối lại WiFi khi router bật lại |
| WiFi powersave | **off** (wlan0) + `802-11-wireless.powersave=2 (disable)` | không rớt kết nối do tiết kiệm năng lượng |
| kiosk_guard service | enabled + `Restart=always` | kiosk UI tự hồi sinh độc lập |
| PC Tailscale | Running, StartType=Automatic | mesh sống lại ngay khi boot |
| PC task `QUAN_AI_BRAIN_KHOI_DONG_LOGON` | Ready | core server 8766 tự bật khi đăng nhập |
| Heartbeat loop daemon | `while not stop_event`: probe mỗi 1s, timeout 4s | tự thử lại vô hạn lần |

## 2. Đồng bộ module (verify + sửa lệch)

- **9/9 module runtime** `edge_client` PC ↔ Pi5: sha256 khớp 100% (client_daemon, config, device_control, edge_agent, actuators, device_watcher, auth, main, device_readers).
- **`setup_pi5.py` lệch** (PC 28/10 cũ hơn Pi5 31/10) → **kéo ngược Pi5→PC** (scp), giờ khớp `230746e96c64`.
- Backup an toàn Pi5: `client_daemon.py.bak_pre_failhonest_20261106` + `config.json.bak_20261106`.

## 3. BUG MỚI PHÁT HIỆN + FIX: `core_connected` sticky-True (vi phạm fail-honest)

**Phát hiện bằng test chặn mạng thật:** khi PC "biến mất" (chặn iptables cả mesh + LAN), kiosk vẫn báo `core_connected=True` **vĩnh viễn** — code chỉ ever set True (`client_daemon.py:2515/2648`), không bao giờ reset False.

**Fix tối thiểu** (`edge_client/client_daemon.py` `to_kiosk_dict`): nếu `time.time() - last_heartbeat_epoch > heartbeat_timeout_sec × 3 (≥12s)` → hiển thị `core_connected=False, avatar=OFFLINE`. Chỉ sửa tầng hiển thị — heartbeat sống lại bật True ngay chu kỳ kế, không đụng logic điều khiển.

**Bằng chứng E2E sau khi sync fix lên Pi5 + restart service:**

| Pha | Thời điểm | core_connected | avatar |
|---|---|---|---|
| Bình thường | T0 | True | IDLE |
| Chặn heartbeat | T+12s | **False** | **OFFLINE** ← trước fix vẫn báo True giả |
| Vẫn chặn | T+30s | False | OFFLINE |
| Bỏ chặn (PC "quay lại mạng") | **T+3s** | **True** | IDLE — tự phục hồi |

**Tests:** `tests/test_edge_client_fail_honest.py` — 4/4 PASS (fresh→connected, stale→OFFLINE, never-seen→OFFLINE, recovery→connected); hồi quy edge suite **72/72 PASS**.

## 4. Kịch bản owner yêu cầu — tái lập bằng chứng

**"PC rời mạng → quay lại cùng mạng WiFi":** chặn CẢ mesh `100.92.219.98` VÀ LAN `192.168.1.9` từ Pi5 16s → `(False, OFFLINE)`; bỏ chặn → **T+3s tự nối lại `(True, IDLE)`** — không cần restart, không cần owner làm gì.

**Connectivity matrix 5/5 PASS:**
1. ✅ PC→Pi5 kiosk API (LAN `192.168.1.21:8768`)
2. ✅ PC→Pi5 SSH (key auth, BatchMode)
3. ✅ PC→Pi5 kiosk API (MESH `100.100.83.59:8768`)
4. ✅ Pi5→PC heartbeat (MESH `100.92.219.98:8766`)
5. ✅ Pi5→PC heartbeat (LAN `192.168.1.9:8766`)

## 5. Vì sao "cùng mạng WiFi" đã được phủ 2 lớp

- **Lớp 1 — Tailscale mesh (PRIMARY):** PC `quanpt`=100.92.219.98 ↔ Pi5 `quanpt1`=100.100.83.59, **direct 2–4ms** qua LAN; nếu 2 máy khác mạng WiFi vẫn nối qua Internet (DERP). IP mesh KHÔNG đổi khi đổi router — `core_host` không cần sửa lại bao giờ.
- **Lớp 2 — LAN fallback:** cùng router, heartbeat qua `192.168.1.9:8766` đã test PASS (mục 5 matrix).
- Auto-reconnect: heartbeat loop thử lại mỗi 1s vô hạn + `Restart=always` + autoconnect WiFi — mất mạng 5 phút hay 5 giờ, có mạng lại là nối lại trong ~3s.

## 6. Trạng thái an toàn cuối phiên

- iptables trên Pi5: **0 rule rác** (dọn sạch sau test).
- Services: `quan_ai_edge` active, `quan_ai_kiosk_guard` active; kiosk `(True, IDLE)`, core_host mesh đúng.
- 8 relay GPIO: OPEN (kế thừa estop G1) — không thiết bị nào đóng.
- Files modified PC: `edge_client/client_daemon.py` (fix fail-honest), `tests/test_edge_client_fail_honest.py` (4 test mới), `edge_client/setup_pi5.py` (sync từ Pi5) — **chưa commit, chờ owner ra lệnh**.

## Ghi chú minh bạch

- SSH từ PC sang Pi5 thỉnh thoảng timeout ngẫu nhiên (~2/30 lần) — retry 3 lần giải quyết; có thể do WiFi powersave router, không ảnh hưởng heartbeat kiosk (không qua SSH).
- Lịch sử backup Pi5: `client_daemon.py.bak_pre_failhonest_20261106` (bản sticky-True), `config.json.bak_20261106` (LAN fallback).
