# M1 — ĐIỀU TRA REBOOT Pi5 NGÀY 31/10/2026 (READ-ONLY INVESTIGATION)

**Người lập:** TONY (QUAN AI BRAIN) · **Thời điểm:** 01/11/2026 ~10:05 giờ Việt Nam
**Phạm vi:** chỉ đọc — không chạy lệnh ghi, không restart, không đổi cấu hình Pi5.
**Sự kiện cần điều tra:** Pi5 tự reboot lúc 20:32:13 ngày 31/10/2026 (ghi nhận trong phiên làm việc trước; nguồn: lịch journal phiên đó, hiện không còn truy xuất được).

---

## KẾT LUẬN CHÍNH

> **INSUFFICIENT_HISTORICAL_EVIDENCE** — không đủ bằng chứng lịch sử để xác định
> nguyên nhân reboot 31/10. KHÔNG suy đoán nguyên nhân gốc.

## Bằng chứng thu được (đọc trực tiếp 01/11 ~10:04–10:05)

| # | Hạng mục | Kết quả đo | Ý nghĩa |
|---|---|---|---|
| 1 | Boot ID hiện tại | `cb14e181-bdb8-4c1b-a6bd-82babf739583` | Boot duy nhất journal đang giữ |
| 2 | Boot lúc | 2026-11-01 07:16:40 (+07) | Uptime ổn định ≥ 2h48 tại lúc đo |
| 3 | `journalctl --list-boots` | **CHỈ 1 boot** (idx 0 = boot hiện tại) | Nhật ký kernel/systemd của boot 31/10 đã MẤT |
| 4 | `/var/log/journal/` | Rỗng (persistent được bật nhưng thư mục trống) | journald đang ghi volatile — mất log khi tắt máy |
| 5 | `/var/log` tổng | 1.7MB | Không có syslog/kern.log archive (rsyslog không ghi) |
| 6 | `/var/log/syslog`, `kern.log` | **KHÔNG TỒN TẠI** | Không có nguồn log cũ nào khác |
| 7 | `watchdog` service | inactive | Loại trừ: không phải watchdog OS tự reset (bằng chứng yếu — không log) |
| 8 | Firmware log (`vclog --msg`) | 30 dòng, chỉ chứa boot hiện tại | Không thấy undervoltage/throttle trong dữ liệu còn lại |
| 9 | AVS voltage hiện tại | `avs_2712: AVS pred 8595 859500` (0.86V core, bình thường) | Nguồn hiện tại ổn — KHÔNG chứng minh gì về 31/10 |
| 10 | Throttled flags hiện tại | `0x0` (đo nhiều lần trong ngày) | Hiện tại không throttle |

## Phân loại kết luận (theo quy tắc RCA)

- **ĐÃ XÁC ĐỊNH NGUYÊN NHÂN:** không có.
- **DẤU HIỆU LIÊN QUAN:** không có dữ liệu đủ để gán.
- **GIẢ THUYẾT (chưa xác nhận, chỉ để lập kế hoạch thu dữ liệu):** mất điện/nguồn 5V yếu momentary; nhiệt; kernel panic — *tất cả đều không có bằng chứng, vì toàn bộ log của boot 31/10 đã mất cùng lần tắt máy.*
- **KHÔNG ĐỦ BẰNG CHỨNG:** ✅ kết luận chính thức.

## Vì sao không điều tra được sâu hơn

journal volatile (Phát hiện 3 của M0 audit): `Storage=persistent` đã set trong
`/etc/systemd/journald.conf` NHƯNG `/var/log/journal/` rỗng → journald không có
nơi ghi persistent, mọi log mất khi reboot. Đó cũng là lý do reset 31/10 không
còn dấu vết. Đây là khoảng trống hạ tầng, không phải lỗi điều tra.

## Đề xuất (KHÔNG tự áp dụng — chờ Quanpt1 duyệt Q-2)

Phương án khắc phục (2 lệnh sudo, hoàn tác được bằng cách xoá thư mục):

```bash
sudo mkdir -p /var/log/journal/$(cat /etc/machine-id)
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

Sau khi duyệt Q-2 và hệ chạy ≥ 1 tuần với log persistent, thực hiện lại điều
tra này nếu reboot tái diễn — khi đó mới có dữ liệu thật để kết luận.

**Quyết định:** Q-2 `PENDING_OWNER`.

---
*Người lập: TONY (M1 investigation, read-only) — 01/11/2026. Mọi lệnh đã chạy chỉ đọc (`cat`, `ls`, `journalctl --list-boots`, `vclog --msg`, `systemctl is-active`).*
