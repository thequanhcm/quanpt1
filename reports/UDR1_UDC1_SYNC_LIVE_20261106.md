# ĐỒNG BỘ UDR-1/UDC-1 PI5 — HOÀN TẤT 06/11/2026 (owner ra lệnh trực tiếp)

## Hành động
1. Backup 7 files cũ Pi5 → backup_pre_udr1_20261106/ (main, client_daemon, edge_agent, auth, config, actuators, config.json)
2. SCP 9 module lõi mới PC→Pi5: main, client_daemon, edge_agent, auth, config, actuators, device_readers, device_watcher, device_control
3. Verify sha256: 9/9 module khớp hash PC↔Pi5
4. Cài SSH key TONY (tony-desktop-20261103) vào authorized_keys — SSH bằng key TONY OK
5. systemctl restart quan_ai_edge → active
6. Fix 1 bug production server.py (nhánh action=device thiếu forward write_op + value=None gây 500)
7. Restart 8766 qua watchdog → nạp fix

## Kết quả E2E verify (bằng chứng runtime)
| Test | Kết quả |
|---|---|
| 9/9 module sync sha256 | KHỚP 100% |
| /api/kiosk/device op=status | success=true, **hardware_available=true, emulated_mode=false (GPIO THẬT)** |
| UDR-1 list_devices | **59 thiết bị** (usb 4, serial 2, i2c 4, gpio_spi 7, storage 3, hdmi 2, camera 25, bluetooth 2, lan 6, sensors 4) |
| UDC-1 WRITE không token | ❌ TỪ CHỐI đúng (fail-closed): "CHƯA CÓ XÁC NHẬN" |
| emergency_stop | ✅ chạy ngay: DE_ENERGIZED_ALL_RELAYS (8 relays) |
| stage_write (xin token) | ✅ token ba731725… TTL 600s gắn (relay_set, relay_1, CLOSED) |
| relay_set + token | ✅ **relay_1 GPIO17 THẬT: CLOSED → emulated=false** |
| Trả an toàn relay_1 OPEN | ✅ OPEN |
| Token one-shot (tái dùng token cũ) | ❌ TỪ CHỐI đúng |
| Heartbeat sau tất cả | READY, paired=True |

## Bug đã fix (production)
- `server.py` nhánh action=device: thiếu forward `write_op` (stage_write luôn fail "write_op không hỗ trợ") + value=None gây 500 `'str' object has no attribute get'`

## Trạng thái UDR-1/UDC-1: LIVE_VERIFIED trên phần cứng thật (GPIO relay thật)
