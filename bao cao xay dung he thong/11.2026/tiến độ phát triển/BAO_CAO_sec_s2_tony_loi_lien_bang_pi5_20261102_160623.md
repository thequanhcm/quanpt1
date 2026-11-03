# BÁO CÁO KỸ THUẬT — sec_s2_tony_loi_lien_bang_pi5

> Sinh tự động 02/11/2026 16:06:23 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Biến PC thành LÕI liên bang toàn quyền, Pi5/thiết bị là NÚT EDGE đăng ký+probe, AI cloud là ĐẦU NỐI có hạn ngạch fail-closed. Quét LAN thật: Pi5 tìm thấy ở 192.168.1.2 REACHABLE (đổi IP từ .21). E2E cảnh báo nút chết → DM thật tới owner → cooldown chống spam.

## 2. PHÂN TÍCH
- Trung thực kiến trúc: không AI nào 'xâm nhập lõi' AI khác — kiểm soát bằng đặt người cùng máy + giám sát điểm chạm + hạn ngạch.
- Pi5 REACHABLE nhưng SSH port 22 đóng + MAC 34-24-3e chưa khớp OUI Pi → chưa khẳng định 100% là Pi5.
- Script pi5_deploy trỏ Tailscale máy cũ 100.102.120.6 → sửa core_host=192.168.1.9 (CORE_HOST env linh hoạt).

## 3. ĐÁNH GIÁ
- 22/22 test mới; regression 3.370/0 (+22 đúng bằng test mới).
- E2E chu kỳ liên bang thật: nút test IP chết → phát hiện → DM cảnh báo thật tới kênh owner → cycle 2 cooldown = 0.
- Sạch DB test sau verify — không để rác trong data thật.

## 4. ĐỊNH HƯỚNG
- Chờ owner chạy script trên Pi5 (5 phút) để mở SSH — từ đó kiosk/loa/camera nối về lõi.

## 5. ĐỀ XUẤT
- Đăng ký DHCP reservation cho Pi5; xem xét Tailscale cho điều khiển ngoài LAN.

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- Quét LAN thật: 7 thiết bị sống /24; đăng ký edge_pi5 + pc_core_quanpt → probe REACHABLE.
- DM cảnh báo liên bang post thật (đọc lại kênh xác nhận).

## 7. RỦI RO & TRUNG THỰC
- MAC không khớp OUI → .2 có thể là thiết bị khác (TV/điện thoại); sẽ xác minh khi SSH mở.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyệt commit SEC-S2.
- Chạy trên Pi5: CORE_HOST=192.168.1.9 bash tony_pi5_all_in_one.sh

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `src/quan_ai_brain/federation/ (3 module)`
- `reports/BAO_CAO_SEC_S2_20261102.md`
