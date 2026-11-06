# G1 LIVE VALIDATION — 16/16 PASS (06/11/2026)

**Phạm vi:** Xác minh LIVE toàn bộ tích hợp PC (QUANPT) ↔ Pi5 (quanpt1) sau sync UDR-1/UDC-1.
**Phương pháp:** Mỗi mục = 1 lệnh chạy thật trên runtime đang vận hành (không mock, không giả lập), bằng chứng ghi trực tiếp từ output lệnh.
**Mạng:** PRIMARY = Tailscale mesh (`100.92.219.98` ↔ `100.100.83.59`, direct 2–4ms); FALLBACK = LAN `192.168.1.9` ↔ `192.168.1.21`.
**Trạng thái tổng:** **16/16 PASS — LIVE_VERIFIED** (đối chiếu Evidence First V7.0 §2.4).

| # | Mục kiểm tra | Kết quả | Bằng chứng (output thật) |
|---|---|---|---|
| 01 | Tailscale mesh PC→Pi5 | ✅ | `pong via 192.168.1.21:41641 in 4ms` = DIRECT (không DERP) |
| 02 | LAN fallback Pi5:8768 | ✅ | TCP connect_ex=0 (port mở) |
| 03 | SSH key TONY | ✅ | `ssh -i tony_pi5_ed25519 … echo OK` → `OK` (BatchMode, không password) |
| 04 | Service quan_ai_edge 24/7 | ✅ | `systemctl is-active`=active; `is-enabled`=enabled |
| 05 | Kiosk daemon API 8768 | ✅ | `kiosk_running=True, core_connected=True, avatar=IDLE, core_host=100.92.219.98:8766` |
| 06 | PC core server 8766 | ✅ | `/api/health` → core_server=HEALTHY (ollama OFFLINE = expected, đã gỡ; brain_db+task_registry HEALTHY) |
| 07 | Heartbeat Pi5→PC qua mesh | ✅ | POST `/api/executive/edge/heartbeat` → `success=True, state=READY, paired=True, device=EDGE-PI5-DESK-01` |
| 08 | Heartbeat stability 10/10 | ✅ | 10/10 READY+paired, latency 196–594ms (SSH curl loop) |
| 09 | PC→Pi5 điều khiển avatar | ✅ | `/api/kiosk/control` set_expression → `success=True` ("G1 VALIDATION: avatar display") |
| 10 | UDR-1 device registry | ✅ | `list_devices` → `data.total=59` (USB/serial/I2C/GPIO/HDMI/camera/BT/LAN/sensors) |
| 11 | UDC-1 write gate fail-closed | ✅ | `relay_set` KHÔNG token → `success=false` "CHƯA CÓ XÁC NHẬN — lệnh ghi cần anh 'ok'" |
| 12 | Voice converse pipeline | ✅ | POST WAV 0.3s im lặng → 200 JSON `{stt_text:'', reply:'', message:'STT không nhận được text'}` — pipeline sống, xử lý đúng |
| 13 | UDC-1 stage_write cấp token | ✅ | → `token=1303c3e3…, ttl_sec=600` |
| 14 | UDC-1 2 bước → GPIO THẬT | ✅ | confirm token → `relay_1 "Nguồn Cánh Tay Trái" GPIO17 state=CLOSED, emulated=false, via_dm=true` |
| 15 | Trả an toàn + token one-shot | ✅ | relay_1→OPEN; tái dùng token cũ → chặn (`success=false`) |
| 16 | Trạng thái cuối sau estop | ✅ | `emergency_stop` → `DE_ENERGIZED_ALL_RELAYS` (8 relays OPEN, 0 CLOSED) |

## Kết luận
- **Kênh PC↔Pi5:** mesh direct + LAN fallback + heartbeat 10/10 + điều khiển 2 chiều — LIVE.
- **UDR-1:** 59 thiết bị đăng ký, snapshot theo heartbeat — LIVE.
- **UDC-1:** write gate fail-closed, token 2 bước TTL 600s one-shot, GPIO thật (emulated=false), estop chạy ngay — LIVE.
- **Voice:** converse pipeline nhận audio → STT → trả JSON — LIVE (STT im lặng trả rỗng đúng thiết kế; chưa test giọng nói thật vì cần audio mic Pi5).
- **An toàn cuối phiên:** tất cả 8 relay OPEN (DE_ENERGIZED), không thiết bị nào còn trạng thái đóng.

## Ghi chú minh bạch
- Mục 06: `overall=DEGRADED` chỉ do `ollama_daemon=OFFLINE` (đã gỡ Ollama — quyết định cũ của owner); mọi component khác HEALTHY.
- Mục 12: STT nhận audio rỗng/im lặng trả text rỗng — là hành vi đúng; test giọng nói thật (kêu tên) cần mic + người nói, thuộc G2.
- Token one-shot xác minh bằng cách tái dùng token `1303c3e3…` sau khi đã tiêu — hệ chặn đúng.

**Báo cáo kèm:** `reports/UDR1_UDC1_SYNC_LIVE_20261106.md` (sync), `reports/g1_results_partial.json` (raw evidence).
