# EDGE PI5 "TAI MẮT" — AUDIT + TỰ CHỦ LIÊN HỆ (11/11/2026, 23:05)

**Yêu cầu owner:** kiểm tra và kết nối tai-mắt Cherry (Pi5), để Cherry tự chủ động liên hệ qua lại điều chỉnh tốt nhất giữa core ↔ Pi5.

---

## 1. Audit thực tế — Pi5 KHÔNG chết hẳn, đang FLAP

Decode log heartbeat (dual_servers_watchdog.log) + telemetry tối nay:

| Cửa sổ sống | Thời lượng | Ghi chú |
|---|---|---|
| 16:05–16:45 | ~40 phút | |
| 17:49–18:36 | ~47 phút | |
| 22:38–22:51 | 13 phút | đúng lúc owner gửi yêu cầu; sập lại 22:51:16 |

- Heartbeat từ 192.168.1.21 đều ~1.4s/lần, toàn 200 OK khi sống — **mạng + HMAC + auto-discovery HOẠT ĐỘNG ĐÚNG** (core_host config .9 sai nhưng client tự quét /24 tìm lại core .24 — cơ chế tự liên hệ tầng mạng đã có sẵn).
- **Snapshot metrics lần sống cuối (22:51):** temp 49.6°C, throttled_bits=0 (KHÔNG undervolt tại thời điểm đo), camera_dev0=true (25 thiết bị camera bus OK), RAM đủ (2895MB avail), mic Jieli USB có mặt, loa SRS-XB33 BT paired.
- **Nghi vấn chính:** `edge_daemon_alive: false` trong metrics cuối + uptime chỉ 795s + 3 lần chết đột ngột, KHÔNG có dấu nhiệt/điện tại thời điểm đo → nghi **nguồn (PSU)/nắp nối vật lý** hoặc service chết trước rồi máy sập. Cần owner kiểm tra: củ nguồn chính hãng 5V/5A, dây, khe thẻ SD.

## 2. Đã xây — Cherry TỰ LIÊN HỆ khi Pi5 sống lại

`tools/edge_pi5_reconcile.py` (được gọi từ watchdog mỗi 60s):

```
Pi5 sống lại (DISCONNECTED → READY/CONNECTED + hb < 60s)
   → SSH quanpt1@Pi5 (key-based, đã có)
   → (a) scp edge_client/wake_word_service.py  [bản CHERRY-only 0019c6c — CHƯA deploy từ hôm qua]
   → (b) systemctl ensure quan_ai_wake.service  (enable + restart nếu chết)
   → (c) systemctl ensure quan_ai_edge.service  (metrics cuối báo edge_daemon_alive=false)
   → (d) phát hiện IP DHCP mới → cập nhật data/edge_runtime.json
   → (e) ghi audit data/edge_reconcile_log.jsonl (mỗi bước ok/fail trung thực)
```

- Rate-limit 1 lần/giờ; Pi5 sống khỏe từ trước → KHÔNG đạp SSH.
- Fail-honest: SSH hỏng → verdict `PI5_UNREACHABLE_VIA_SSH` ghi log, không crash watchdog.
- Regression bắt được & sửa: NameError nuốt trong except khiến state file không bao giờ được ghi lần đầu (test `test_first_run_creates_state_file_no_crash`).

**Verify:** 5/5 test PASS (mock SSH); watchdog production restart 23:02 — hook chạy thật mỗi chu kỳ (state file mtime 23:03:04); servers 8765/8766 + learning daemon + responder đều còn 1 instance mỗi loại.

## 3. Phân quyền trung thực

| Việc | Ai làm |
|---|---|
| Deploy wake CHERRY + restart service Pi5 | **Cherry tự động** (reconcile) khi Pi5 online |
| Kiểm tra củ nguồn / dây / thẻ SD Pi5 | **Chỉ owner** (vật lý) |
| Sửa code kiosk/daemon Pi5 sâu hơn | sprint sau, sau khi reconcile chạy ít nhất 1 lần thành công |
| DHCP reservation cho .21/.24 | Owner đặt trên router (đã nhắc từ sprint trước) |

## 4. Việc tiếp theo

1. Đêm nay nếu Pi5 bật lại → reconcile tự chạy, sáng owner kiểm `data/edge_reconcile_log.jsonl`.
2. Owner kiểm nguồn vật lý → nếu Pi5 còn flap, mọi fix mềm đều vô nghĩa.
3. Sau khi Pi5 ổn định ≥1h + reconcile RECONCILED → verify E2E wake "Cherry ơi" + camera + mic.
