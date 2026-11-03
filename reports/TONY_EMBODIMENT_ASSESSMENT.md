# TONY EMBODIMENT ASSESSMENT — Multi-embodiment & kiểm thử tích hợp thật
**Cập nhật:** 01/11/2026 16:45 · PHẦN IX

## 1. Kiến trúc embodiment

| Thành phần | Trạng thái | Bằng chứng live 16:32 |
|---|---|---|
| PC Main Brain | ✅ | 8765+8766 HTTP 200 |
| Raspberry Pi 5 | ✅ READY | state=READY, paired=true, RTT 220ms, heartbeat 1,4s |
| NetChat (embodiment văn bản) | ✅ | responder sạch, greeting 16:13 |
| Future devices | ✅ thiết kế | device_id + pair endpoint sẵn (EDGE-PI5-DESK-01 pattern) |
| QEP-0001 | ✅ spec 192 dòng | không đếm tài liệu là năng lực — đã có E2E thật (dưới) |
| Embodiment Registry | ✅ | edge status device_label + device_id |
| Device Identity | ✅ | HMAC per-device, secret 64 [REDACTED], SHA-8 khớp 2 phía |
| Capability Registry | ✅ | camera/audio/hdmi/telemetry actions |
| Sensor/Actuator Interface | ✅ | camera snapshot 117 KB; audio action pw-record sạch |
| Permission | ✅ | HMAC fail-closed 401; pairing exempt được kiểm soát |
| Heartbeat | ✅ | 4s timeout, 0 fault sau M6-B1 |
| Synchronization | ✅ | scp sync daemon + secret; clock drift -1s đã đo |

## 2. Trả lời 7 câu bắt buộc

1. **Pi5 hoạt động như hình thể độc lập?** ✅ CÓ — daemon riêng, offline queue, kiosk tự chạy; mất PC vẫn giữ trạng thái.
2. **Mất Pi5, PC có sống?** ✅ CÓ — server ALERT_E_PI5_RECOVERED chỉ là alert; 8765/8766 tiếp tục 200 (đã chứng minh khi Pi restart 15:40).
3. **Đăng ký hình thể mới?** ✅ CÓ — copy edge_client + pair + secret flow (đã làm 2 lần với Pi5).
4. **Quyền từng hình thể?** ✅ — HMAC key riêng, R0-R5 áp chung.
5. **Chia sẻ trí nhớ đúng cách?** ✅ — memory_exchange_log 40 bản ghi; edge chỉ gửi telemetry/events, không ghi trực tiếp DB lõi.
6. **Kiểm soát lệnh vật lý?** ✅ — action qua daemon, allowlist 21 app phía PC; camera/mic动作 yêu cầu HMAC.
7. **Ngắt kết nối & phục hồi an toàn?** ✅ — RECOVERED alert + restart đúng chuẩn setsid; không restart-loop (cap 5/giờ watchdog logic).

## 3. Kiểm thử tích hợp thực tế (không chỉ tài liệu)

| Bài | Kết quả |
|---|---|
| HMAC E2E Pi→PC giám sát 120s | ✅ 0 fault (trước: 20 fault/phút) |
| Camera thật → DM | ✅ 117 KB |
| Audio record + remux ffmpeg | ✅ (31/10, lệnh "nghe từ pi") |
| Heartbeat liên tục sau restart Pi | ✅ READY ngay |
| **Fail-over PC khi Pi mất** | ⚠️ chứng minh gián tiếp (alert) — chưa bài test có chủ đích (P2 test plan) |

## Điểm Multi-Embodiment: **CẤP 2 — Kiến trúc + identity + heartbeat + E2E thật; hạng mục còn lại chỉ là bài test fail-over có chủ đích.**
