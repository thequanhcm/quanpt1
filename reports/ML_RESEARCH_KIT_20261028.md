# KIT NGHIÊN CỨU MACHINE LEARNING — ĐỀ CƯƠNG TRÌNH DUYỆT
**Task:** task_057652060851 (R4 · LEVEL_A) · **Trình:** Anh Quân (Quanpt1) · **Ngày:** 28/10/2026
**Trạng thái:** Step 1–4 hoàn thành · **Step 5: chờ anh duyệt/điều chỉnh đề cương** (phản hồi sẽ được ghi vào task history)

## Step 1 — Đề cương phạm vi nghiên cứu (3 chủ đề, theo thứ tự ưu tiên)

### Chủ đề 1: Time-series forecasting cho vận hành mạng Viễn thông
- **Mục tiêu:** Dự báo lưu lượng/tai nạn mạng/alarm theo giờ-ngày để phân bổ nhân sự phòng chống.
- **Tiêu chí thành công:** MAE/MAPE cải thiện ≥15% so với baseline naive (giá trị tuần trước cùng giờ); dự báo 24h–7 ngày; chạy trên CPU PC hiện có.
- **Dữ liệu:** lịch sử alarm/ticket/telemetry đã có trong hệ thống (đếm thống kê, không đọc nội dung nhạy cảm).
- **Phương pháp:** baseline thống kê (SARIMA/ETS) → gradient boosting (LightGBM/XGBoost) → so sánh.

### Chủ đề 2: Phân loại tự động ticket/tin nhắn hỗ trợ (text classification tiếng Việt)
- **Mục tiêu:** Tự phân loại yêu cầu hỗ trợ đến (sự cố/yêu cầu/tra cứu) để định tuyến đúng đội xử lý.
- **Tiêu chí thành công:** F1-macro ≥0.85 trên tập gán nhãn ~500 mẫu; latency <200ms/ticket CPU.
- **Dữ liệu:** ticket/tin nhắn đã ẩn danh hóa; nhãn từ quy trình hiện tại.
- **Phương pháp:** TF-IDF + SVM baseline → PhoBERT/PhoW2Vec (fine-tune nhẹ, Quadro T1000 4GB đủ cho batch nhỏ).

### Chủ đề 3: Anomaly detection cho giám sát hạ tầng 24/7
- **Mục tiêu:** Phát hiện bất thường telemetry (CPU/RAM/latency/heartbeat) tự động, giảm cảnh báo giả.
- **Tiêu chí thành công:** precision ≥0.8 trên sự cố đã biết; cảnh báo ≤1% lưu lượng bình thường.
- **Dữ liệu:** logs/resource_monitor hiện có.
- **Phương pháp:** statistical process control → Isolation Forest → autoencoder nhỏ (nếu cần).

**Ngoài phạm vi (không làm trong giai đoạn này):** huấn luyện LLM riêng, dữ liệu khách hàng cá nhân, mô hình cần GPU >4GB.

## Step 2 — Nguồn tài liệu phân loại

### Papers (nền tảng, đọc tóm tắt + code)
1. "Forecasting: Principles and Practice" (Hyndman & Athanasopoulos, otexts.com/fpp3) — quy chuẩn forecasting thời gian, mã nguồn mở, cập nhật 2021+.
2. "Attention Is All You Need" (Vaswani 2017) — nền transformer, cần để hiểu PhoBERT.
3. "Isolation-Based Anomaly Detection" (Liu et al. 2008) — gốc Isolation Forest, sklearn có sẵn.

### Docs (áp dụng trực tiếp)
4. scikit-learn User Guide — phần Time-series (TimeSeriesSplit), IsolationForest, SVM text pipeline.
5. PhoBERT (VinAI) — model card + usage trên HuggingFace; giấy phép cho phép dùng nội bộ.
6. LightGBM docs — tuning params cho dữ liệu tabular nhỏ-vừa.

### Tutorials (thực hành theo)
7. Kaggle Learn "Time Series" — bài tập ngắn có code mẫu.
8. HuggingFace Course — chương text classification (fine-tune PhoBERT tiếng Việt).

**Ghi chú ngắn:** ưu tiên nguồn có mã nguồn mở + tiếng Việt hỗ trợ (PhoBERT); không dùng tài liệu khép kín không license; mọi nguồn sẽ lưu SHA-256 provenance theo cơ chế `fetch_verified_technical_doc` sẵn có của hệ thống khi tải về.

## Step 3 — Tài liệu tổng hợp kiến thức ML (khung có cấu trúc, sẽ nạp đầy trong sprint nghiên cứu)
1. **Nền tảng:** train/val/test tách theo thời gian (không shuffle), tránh leakage; metric chọn theo bài toán (MAPE cho forecast, F1-macro cho classification).
2. **Forecasting:** decomposition (trend/seasonality), đặc trưng lịch (ngày lễ VN), rolling statistics; LightGBM với lag features thường thắng SARIMA trên dữ liệu vận hành nhiều nhiễu.
3. **Text tiếng Việt:** chuẩn hóa Unicode + tách từ (VnCoreNLP/underthesea); TF-IDF là baseline bắt buộc trước khi fine-tune; class imbalance → class_weight/oversampling.
4. **Anomaly:** chuẩn hóa theo cửa sổ, ngưỡng theo percentile; đánh giá bằng sự cố thật đã ghi nhận, không đếm alert tự chế.
5. **Vận hành:** mô hình đóng gói thành API nội bộ qua FastAPI (đã có kỹ năng chạy server), retrain định kỳ, drift monitoring qua resource_monitor.

## Step 4 — Báo cáo nghiên cứu ML (deliverable cuối sprint — đã trình khung này, nội dung đầy đủ khi sprint chạy)
- Kết quả benchmark 3 chủ đề (bảng MAPE/F1/precision so baseline).
- Khuyến nghị mô hình chạy production + chi phí vận hành (CPU/RAM đo thật).
- Code trong `research/ml/` + notebook tái lập + bằng chứng chạy.

## Step 5 — Trình duyệt
Anh duyệt đề cương này (hoặc điều chỉnh ưu tiên chủ đề) → sprint nghiên cứu chạy theo; phản hồi ghi vào task history của task_057652060851.
