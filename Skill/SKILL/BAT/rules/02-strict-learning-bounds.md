# Strict Learning Bounds (AI Safety)

Áp dụng cho quy trình cập nhật Tri thức (Knowledge & Learning):
1. **Không tự động cập nhật Model Production:** Các phát hiện mới của Knowledge Engineer chỉ được lưu vào thư mục `Draft_KEDB`. Chỉ được đưa vào Production khi có chuyên gia (NOC/Admin) phê duyệt.
2. **Xác thực Ground Truth:** Bất kỳ chẩn đoán SOH/RUL nào cũng phải được gắn cờ "Dự đoán" (Prediction). Chỉ khi có kết quả từ Bài test xả thực tế (Discharge Test), sự kiện đó mới được coi là Ground Truth để học hỏi.
3. Không được học từ dữ liệu bất thường (Anomalies/Sensor fault) nếu chưa được lọc nhiễu.
