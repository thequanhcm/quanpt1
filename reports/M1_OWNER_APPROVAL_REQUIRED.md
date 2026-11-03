# M1 — OWNER APPROVAL REQUIRED (QUYẾT ĐỊNH CHỜ ANH)

**Người lập:** TONY · **Ngày:** 01/11/2026

Không có quyết định nào trong bảng dưới được em tự thực hiện. Mọi thông tin cần để anh quyết đều có trong các báo cáo kèm theo.

## 5 quyết định PENDING (giữ nguyên từ M0 — chưa có gì được thực hiện)

| ID | Quyết định | Tác động nếu duyệt | Rủi ro nếu KHÔNG duyệt | Báo cáo liên quan |
|---|---|---|---|---|
| Q-1 | `git init` + commit đầu tiên trong workspace | Bảo toàn 83.118+ dòng code; rollback mọi thay đổi; điều kiện cho M4 (version history) | Mất code không phục hồi được nếu dĩa hỏng | M0 audit |
| Q-2 | Fix persistent journal Pi5 (2 lệnh sudo tạo `/var/log/journal/<machine-id>` + restart journald) | Log survives reboot → điều tra được reboot lạ tương lai; hoàn tác = xoá thư mục | Mọi sự cố tiếp tục mất dấu vết (reboot 31/10 đã không tra cứu được) | M1_PI5_REBOOT_INVESTIGATION.md |
| Q-3 | Cài Piper TTS vào venv làm fallback | TTS hoạt động khi Edge-TTS 403; thoại Pi5 không phụ thuộc cloud | Cảnh thoại im khi gateway chặn | M1_VOICE_HEALTH_REPORT.md |
| Q-4 | Thiết kế + kích hoạt approval_verifier R4 | Mở khoá 4.378 tri thức quarantine + promotion tự học có kiểm soát | Tri thức học được không bao giờ vào sử dụng | M1_DATABASE_HEALTH_REPORT.md §3 |
| Q-5 | Tắt BT power-save loa SRS-XB33 trên Pi5 | Giảm mất kết nối loa (sự cố 09:04 hôm nay) | Mic/tai Pi5 rơi khi power-save cắt HFP | M1_PI5_HEALTH_REPORT.md |

## Quyết định MỚI phát sinh từ M1 (anh xem thêm nếu muốn)

| ID | Quyết định | Ghi chú |
|---|---|---|
| M1-A | Ngưỡng cảnh báo hiện hành (CPU 85/97, RAM 85/95, disk 85/95, temp 70/80, RSS 1200/2000MB, RTT 150/500ms, heartbeat 150/600s) — anh muốn đổi giá trị nào? | Em chỉnh trong 1 file (aggregator.py) khi anh nói |
| M1-B | Camera probe (v4l2) + HDMI vật lý vào Pi5 collector | Đọc-only, an toàn — chỉ hỏi để đồng ý phạm vi |
| M1-C | Cho phép alert gửi DM 24/7 (hiện gửi ngay khi phát hiện, cooldown 5 phút/loại) | Nếu anh muốn im ban đêm, em thêm khung giờ yên tĩnh |

## Trạng thái hiện tại không cần duyệt (đã trong phạm vi M1 read-only)

- Health Monitor tự chạy mỗi 120s, alert tự DM khi bất thường — đang hoạt động.
- Dashboard `/health` đã mở cho anh xem bất cứ lúc nào.

**Đề xuất:** anh duyệt Q-2 + Q-3 trước (rủi ro thấp, giá trị cao) — em thực hiện ngay và báo kết quả kèm bằng chứng.
