# Non-Breaking Architecture (BATTERY AI V4 Adapter)

Hệ thống BATTERY AI V4 đã hoạt động ổn định. Để không làm gãy hệ thống cũ (Non-breaking):

1. **Giao tiếp một chiều:** Battery Commander KHÔNG được ghi trực tiếp vào SQLite DB của V4. Chỉ được phép Read (Đọc) qua API hoặc Adapter.
2. **Circuit Breaker:** Khi V4 Adapter báo lỗi timeout (ví dụ V4 service bị sập), Battery Commander phải tự động chuyển sang chế độ Standalone (sử dụng cache gần nhất) và không được cố gắng retry liên tục làm treo DC-COMMAND.
3. Mọi thay đổi về thuật toán SOH phải nằm trong `vibe-bat-soh-agent`, không được sửa code của V4.
