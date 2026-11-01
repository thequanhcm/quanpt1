# Continuous Learning Loop Workflow

Quy trình chuẩn cho vòng lặp học hỏi kinh nghiệm (Tiến hóa từ V3 lên V4).

**Bước 1: Observation (Quan sát)**
- Orchestrator thu thập dữ liệu time-series hàng ngày từ V3 API.
- Memory Agent nén dữ liệu này thành các Episodic Memory.

**Bước 2: Prediction (Dự báo)**
- Prognostics Agent đưa ra dự đoán RUL và SOH hiện tại.

**Bước 3: Verification (Xác minh - Ground Truth)**
- Chờ đến lịch bảo trì/xả tải thực tế.
- Orchestrator ghi nhận kết quả SOH thực tế từ báo cáo bảo trì.

**Bước 4: Retrospection (Rút kinh nghiệm)**
- Causal RCA Agent so sánh SOH dự đoán (Bước 2) và SOH thực tế (Bước 3).
- Nếu sai số > 5%, phân tích tại sao mô hình sai.

**Bước 5: Knowledge Update (Cập nhật Tri thức)**
- Knowledge Engineer tổng hợp lỗi sai, xuất thành quy luật mới vào KEDB.
- Model được cập nhật (Có giám sát) để dự đoán chính xác hơn cho lần sau.
