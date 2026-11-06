# TỐI ƯU KẾT NỐI PC↔Pi5 — LAN/WiFi-FIRST (06/11/2026)

## Yêu cầu owner
"kiểm tra kết nối và tối ưu vì thi thoảng Pi5 hay bị mất kết nối. em ưu tiên kết nối
qua wifi khi máy tính này và Pi5 cùng kết nối chung wifi."

## AUDIT — phát hiện 2 nguyên nhân mất kết nối

### 1. HMAC SECRET LỆCH (nguyên nhân chính — heartbeat 401)
- PC server (`web/server.py`) xác thực heartbeat bằng `data/edge_hmac_secret.txt`
  (hash head `3cca66f7…`).
- Pi5 daemon (`client_daemon.py`) ký bằng `config.json shared_secret`
  (hash head `e81366f2…`).
- → MỌI heartbeat supervisor GET trả 401 INVALID_SIGNATURE → dashboard báo
  "mất kết nối" dai dẳng dù mạng sống. Journal PC có bằng chứng
  `INVALID_SIGNATURE` 15:58:45.
- Fix: đồng bộ `data/edge_hmac_secret.txt` = `shared_secret` trong
  `edge_client/config.json` (nguồn đã pair với Pi5). Backup
  `edge_hmac_secret.txt.bak_20261106`.

### 2. SELECTOR ĐẶT MESH TRƯỚC LAN
- `tony_channel_selector.py` (Pi5, timer 30s) đặt ưu tiên MESH=1, LAN=2 →
  cứ 30s ghi đè `config.json core_host` về mesh IP, kể cả khi cùng WiFi.
- Fix theo owner: đảo ưu tiên **LAN=1, MESH=2, BT-PAN=3**; default state
  khi mất file state đổi từ MESH → LAN. Hysteresis 50% + probe RTT thật
  giữ nguyên (fail-honest). Backup `tony_channel_selector.py.bak_lanfirst_20261106`.

## TỐI ƯU BỔ SUNG
- `_resolve_core_base_url` trong `client_daemon.py`: probe TCP 1s theo thứ tự
  config host (LAN) → mesh fallback; cache 30s. LAN-first cả đường voice/HDMI.
- `edge_client/config.json`: `core_host` = `192.168.1.9` (LAN PC) — scp Pi5
  sha256 khớp `4fa8b733…`.
- LAN đã chết 2 chiều trước đó — nay ping 2ms, SSH 2 chiều OK (đã tự hồi phục
  hoặc do router; theo dõi thêm).

## BẰNG CHỨNG (LIVE, 06/11 23:05–23:08)
- Heartbeat 25s liên tục: state READY 10/10 mẫu, misses=0, RTT trung bình
  30.5–34.6ms (LAN trực tiếp, không DERP).
- Selector 2 chu kỳ 30s sau fix: GIỮ `core_host=192.168.1.9` (active=LAN,
  RTT 6.6–8.7ms probe), không nhảy về mesh.
- Journal Pi5: "Brain Core PC: http://192.168.1.9:8766" sau restart.
- Dashboard 8766 edge status: paired=True, READY.

## TRẠNG THÁI (Evidence First)
- LIVE_VERIFIED: heartbeat LAN-first ổn định 25s+; selector giữ LAN qua 2 chu kỳ.
- INFERRED: LAN chết 2 chiều hôm trước có thể do router/power-save — chưa root-cause
  sâu (đã hồi phục; đề xuất theo dõi).
- KHÔNG đụng: protected projects, .env, secret values (chỉ hash so khớp), R0–R5.

## Files đổi
- PC: `data/edge_hmac_secret.txt` (đồng bộ secret — KHÔNG commit file này),
  `edge_client/config.json` (core_host LAN — file config chạy thật, KHÔNG commit),
  `edge_client/client_daemon.py` (resolver LAN-first + mesh fallback + cache 30s).
- Pi5: `tony_channel_selector.py` (LAN-first + default state LAN),
  `config.json`, `client_daemon.py` (sha256 khớp PC).
- PC repo thêm: `edge_client/tony_channel_selector.py` (pull về để cùng version).

## Việc còn mở
- Theo dõi 24h: nếu LAN lại chết 2 chiều → kiểm router (DHCP lease, AP isolation)
  + wifi power save Pi5 (`iw wlan0 get power_save`).
- Commit chờ lệnh owner (tách changeset: (f) connection LAN-first).
