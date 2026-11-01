# V3 & V4 Compatibility Rule

Hệ thống BAT Workforce KHÔNG ĐƯỢC PHÉP thay thế hoặc chỉnh sửa các component đang chạy của hệ thống V3 và V4:
1. **API & Database:** Tuyệt đối không can thiệp vào `battery_data.db` hay `battery_ups_v4.db` (trừ khi dùng quyền Read-Only).
2. **Backward Compatibility:** Nếu V3 API trả về định dạng cũ, Orchestrator phải tự mapping dữ liệu để hiểu, không được yêu cầu viết lại API của V3.
3. Chức năng của BAT Workforce là một lớp vỏ nhận thức (Cognitive layer) bọc bên ngoài logic hiện có của V3/V4.
