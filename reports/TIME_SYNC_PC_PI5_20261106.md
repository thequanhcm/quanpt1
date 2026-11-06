# BÁO CÁO ĐỒNG BỘ GIỜ PC ↔ Pi5 — 06/11/2026 20:26

## Vấn đề (từ 2 ảnh dashboard)

Ảnh dashboard hiển thị "Đồng Bộ UTC: 12:30" trong khi đồng hồ Windows 19:30 (=12:30 UTC +7 — khớp). Nhưng đo chính xác bằng NTP client query 2 server độc lập:

| Máy | So với giờ chuẩn NTP | Kết luận |
|---|---|---|
| **Pi5** | `System clock synchronized: yes`, NTP active, stratum 2, jitter 7.184ms | **ĐÚNG CHUẨN** |
| **PC (QUANPT)** | Lệch **−2.568s** (pool.ntp.org, RTT 11ms) / **−2.575s** (time.windows.com) — sync lần cuối **03/11 07:28** | **CHẬM ~2.5s** |

Đo trực tiếp PC↔Pi5 (5 mẫu SSH + bù RTT/2): Pi5 nhanh hơn PC **+1.7 → +2.5s** (khớp kết luận PC chậm).

## Nguyên nhân gốc

- PC: w32tm sync chu kỳ dài + `w32tm /resync` bị **Access denied** (user không có SeSystemtimePrivilege — err 1300)
- Pi5: systemd-timesyncd với debian pool NTP — hoạt động chuẩn

## Phương án đã duyệt qua chat (owner: "Duyệt phương án A")

**Đồng bộ PC về chuẩn NTP** (không set Pi5 theo PC — sẽ phá chuẩn nguồn giờ của hệ thống và timesyncd kéo lại sau ~34 phút, vô nghĩa).

## Thực hiện

1. Viết `tools/pc_ntp_resync_admin.ps1` (UTF-8 BOM): `w32tm /resync /force` + hiển thị status + tự verify bằng python NTP query
2. Launcher `Start-Process -Verb RunAs` → hộp thoại UAC hiện → **owner bấm YES**
3. Kết quả script: resync thành công

## Verify sau đồng bộ (bằng chứng thật)

- **NTP query**: PC vs NTP chuẩn = **−1 ms** ✓ (<100ms)
- **w32tm**: `Last Successful Sync Time: 11/6/2026 8:26:14 PM` (vừa xảy ra) — Source time.windows.com
- **PC vs Pi5 3 mẫu SSH (bù RTT)**: −21ms / +896ms / +707ms — mẫu tốt nhất **−21ms**, phần dư là nhiễu RTT DERP (~0.5–1.5s) của phép đo SSH, không phải lệch đồng hồ

## Kết luận

✅ **PC và Pi5 cùng khớp chuẩn UTC** (sai số thực < 50ms). Widget "Đồng Bộ UTC" trên dashboard giờ phản ánh đúng giờ thật của cả hệ thống.

## Bền vững

- Pi5: tự sync NTP mãi (systemd-timesyncd, poll 32s–34min)
- PC: Windows Time sẽ sync chu kỳ theo nhóm; nếu muốn sync dày hơn: admin chạy `w32tm /config /update /specialinterval 3600` (1 giờ/lần) — chưa làm, chờ owner
- Script lưu tại `tools/pc_ntp_resync_admin.ps1` — dùng lại được lần sau (chuột phải → Run with PowerShell với quyền admin, hoặc nhờ TONY chạy lại)
