# Safety Bounds & Authority Limits

Quy tắc này áp dụng cho TẤT CẢ các Agent trong hệ thống BAT AI. BẮT BUỘC PHẢI TUÂN THỦ.

1. **KHÔNG AUTO-EXECUTE nếu mức độ tin cậy < 80%:** Uncertainty Engine yêu cầu nếu bất kỳ chẩn đoán nào có độ tin cậy thấp, Agent chỉ được phép ĐỀ XUẤT (Recommend), không được ra LỆNH (Command).
2. **Nhiệt độ an toàn:** Mọi bài test xả ắc quy (Discharge test) phải bị HỦY NGAY LẬP TỨC nếu nhiệt độ môi trường > 28°C.
3. **Phân quyền (RBAC):** Chỉ `vibe-bat-dc-orchestrator` mới có quyền yêu cầu chữ ký phê duyệt (Command Signing) cho các thao tác thay đổi trạng thái phần cứng (Shutdown, Switch). Các Commander và Agent chỉ phân tích và đề xuất.
4. **Luôn ưu tiên Data Center Uptime:** Không được ưu tiên bảo vệ ắc quy nếu điều đó làm sập nguồn Server, trừ trường hợp có nguy cơ cháy nổ (Fire/Thermal Runaway).
