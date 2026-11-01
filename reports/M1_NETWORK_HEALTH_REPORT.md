# M1 — NETWORK HEALTH REPORT

**Người lập:** TONY · **Thời điểm đo:** 01/11/2026 09:35–11:05 giờ VN
**Nguồn:** `network_collector.py` — 1 ICMP / lần đo (không tạo traffic lớn), psutil interface check

## Kết quả đo thật

| Chỉ số | Giá trị đo trong phiên | Ngưỡng WARN/CRIT | Trạng thái |
|---|---|---|---|
| RTT PC→Pi5 (Tailscale 100.100.83.59) | 5–30 ms (nền ~6ms direct) | 150 / 500 | ✅ NORMAL |
| Loss PC→Pi5 | 0% | >1 / ≥50 | ✅ NORMAL |
| Tailscale interface | up | down → warn | ✅ |

## Đặc điểm kiến trúc đo được

- RTT nền 5–6ms → PC↔Pi5 đang đi **direct** qua Tailscale LAN (không relay DERP).
- 1 lần đo đầu sau restart server rơi vào thời điểm interface chưa sẵn sàng → ghi CRITICAL đo được (loss 100%) rồi tự phục hồi ở chu kỳ sau — fail-honest đúng thiết kế: đo thấy gì ghi nấy, không bịa NORMAL.
- SSH PC→Pi5 (BatchMode key) hoạt động ổn trong toàn bộ phiên — mọi probe 7 chỉ số thành công.

## Voice round-trip (tham chiếu từ phiên hội thoại 09:15)

- Chuỗi thoại đầy đủ (greet → VAD thu → STT → GLM → TTS → phát) đo được 4–9s ở phiên trước; M1 chưa đo liên tục — đề xuất thêm latency tracking vào M5 (cần thiết kế chống ảnh hưởng vòng hội thoại).

## Nhận định

1. Mạng PC–Pi5 ổn định, direct connection, không mất gói.
2. Không đo packet loss liên tục ngoài ICMP đơn — đủ cho M1, tránh tạo traffic.
3. Đề xuất M2+: lưu rtt_ms vào history (đã làm — cột rtt_ms trong health_history.db) để phát hiện chuyển direct→relay.
