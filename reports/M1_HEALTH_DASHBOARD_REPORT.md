# M1 — HEALTH DASHBOARD REPORT

**Người lập:** TONY · **Ngày:** 01/11/2026
**URL:** `http://127.0.0.1:8766/health` (PC) — mở được cả từ Pi5 qua LAN/Tailscale `http://100.102.120.6:8766/health`

## Nguyên tắc

- **100% dữ liệu backend thật** (`/api/health/machine`, `/api/health/history`, `/api/health/rca`, `/api/health/monitor`) — không có số liệu giả trong production (§4.9 master prompt).
- Tích hợp vào dashboard hệ hiện có (static của web server) — không tạo UI demo rời.
- Auto-refresh 60s + nút làm mới + `?force=1` bỏ cache.

## 10 khu theo yêu cầu (§4.9) — thực trạng

| # | Khu | Trạng thái | Ghi chú |
|---|---|---|---|
| 1 | Overall System Health | ✅ | badge 5 màu TỐT/CẢNH BÁO/NGHIÊM TRỌNG/KHÔNG RÕ/BẢO TRÌ |
| 2 | PC Health | ✅ | 11 chỉ số, bảng đơn vị + trạng thái từng cái |
| 3 | Raspberry Pi 5 Health | ✅ | 7 chỉ số (nhiệt, throttle, ram, disk, BT, services, boot) |
| 4 | Network Health | ✅ | RTT/loss/Tailscale + biểu đồ xu hướng RTT |
| 5 | Service Health | ✅ | 8765/8766 + heartbeat responder + learning log-age |
| 6 | Database Health | ✅ | quick_check + size + WAL |
| 7 | Voice Health | ✅ | STT/LLM×2/TTS |
| 8 | Historical Trends | ✅ | canvas chart CPU% + RTT ms, 120 điểm từ health_history.db |
| 9 | Alerts | ✅ | bảng cảnh báo (đã gửi DM/cooldown) + trạng thái vòng monitor |
| 10 | Diagnostics | ✅ | bảng RCA: DỮ KIỆN ĐO THẤY / GIẢ THUYẾT (CHƯA XÁC NHẬN) / THIẾU BẰNG CHỨNG + bằng chứng từng nhận định |

## Điểm thiết kế đáng chú ý

1. **Mỗi khu hiển thị: current status + last update + metrics + warning + explanation** (label tiếng Việt + evidence) — theo §4.9. *Suggested action* nằm ở bảng RCA (cột đề xuất) và trong báo cáo.
2. Fail-honest trên UI: thiếu dữ liệu → badge KHÔNG RÕ, không bao giờ hiển thị TỐT khi không đo được.
3. Đã kiểm chứng E2E: trang serve OK, JS fetch 4 endpoint, chart vẽ ≥2 điểm, RCA 1 nhận định FACT (loa BT) hiện đúng.

## Hạn chế + đề xuất

- Biểu đồ canvas thuần (không thư viện) — đủ dùng; nâng cấp sparkline đa chỉ số ở M2 nếu anh muốn.
- Chưa có nút ACK alert từ UI (cần thiết kế phê duyệt) — hiện alert tự khỏi khi giá trị về bình thường.
