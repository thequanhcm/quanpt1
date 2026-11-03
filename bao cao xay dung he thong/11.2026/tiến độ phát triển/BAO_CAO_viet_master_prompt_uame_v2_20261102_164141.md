# BÁO CÁO KỸ THUẬT — viet_master_prompt_uame_v2

> Sinh tự động 02/11/2026 16:41:41 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Soạn master prompt UAME V2.0 — kế thừa UAIIF v1.0 + SENTINEL v1.0, biến đích đến 'TONY hiểu và làm việc được với thế giới Agent' thành chương trình triển khai 4 giai đoạn (A: QEP core + mock body; B: QPIG trên Pi5 thật; C: MCP/A2A/Behavior SENTINEL GĐ2; D: Learning Engine + 200 kịch bản), kèm định nghĩa chuẩn QEP (envelope, capability advert, task contract, telemetry, security handshake), 5 giả thuyết kiểm chứng được H1–H5, KPI đo được, quy tắc chất lượng bắt buộc.

## 2. PHÂN TÍCH
- Grep xác nhận QEP chưa tồn tại trong codebase (0 kết quả) → QEP là mảnh ghép mới duy nhất cần chuẩn hóa; các mảnh còn lại (ToolRegistry, federation, SENTINEL GĐ1, UAIIF GĐ1) đã có và đã test — prompt yêu cầu import chứ không copy.
- Điểm xuất phát ghi trong prompt là hiện trạng thật 02/11: regression 3.442/0/45, scorecard 60/100, Pi5 SSH đóng — tránh đề xuất xây lại cái đã có.
- QEP thiết kế tách bạch: là hợp đồng embodiment chạy trên nhiều transport, tương thích MCP ở tầng message — không cạnh tranh MCP/A2A.
- Chống tự thương lượng: KPI 'PLUG-IN test' (tích hợp cơ thể/agent mới ≤1h/≤30ph không sửa core) là bài test khách quan do owner chọn đối tượng.

## 3. ĐÁNH GIÁ
- Prompt đầy đủ 5 đích đến owner yêu cầu: QUAN AI BRAIN trí tuệ thống nhất / TONY nhân sự số / Pi5 cổng tác nghiệp / SENTINEL an ninh / QEP+ToolRegistry giao tiếp thống nhất.
- Mọi giai đoạn đều có tiêu chí nghiệm thu kiểm chứng được và rollback plan — đúng quy chế: không tuyên bố khi chưa có bằng chứng.
- Hạn chế trung thực: Giai đoạn B phụ thuộc vật lý (owner chạy script trên Pi5); A/C/D có thể chạy ngay không phụ thuộc phần cứng.

## 4. ĐỊNH HƯỚNG
- Bước tiếp theo ngay: owner duyệt card TASK-UAME-S5 → triển khai Giai đoạn A (QEP core + fake body) không cần phần cứng.
- Song song: khi SSH Pi5 mở, Giai đoạn B kế tiếp liền mạch vì QPIG skeleton phía lõi đã sẵn.

## 5. ĐỀ XUẤT
- Prompt lưu tại docs/MASTER_PROMPT_UAME_V2.md để dùng làm chuẩn — owner có thể sửa trực tiếp trước khi duyệt GĐ A.
- Nên review phần risk_level trong capability advert với SENTINEL khi vào GĐ C (chống downgrade gian lận đã viết trong III.2).

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- File: docs/MASTER_PROMPT_UAME_V2.md (~20KB, 7 mục chính + 4 giai đoạn).
- Xác minh grep: 'QEP' = 0 match toàn codebase trước khi viết prompt.

## 7. RỦI RO & TRUNG THỰC
- Prompt dài — nếu trình thực thi chỉ đọc lướt có thể bỏ sót quy tắc fail-closed; đã đánh số mục rõ ràng.
- KPI '≤ 1 giờ tích hợp cơ thể mới' phụ thuộc chất lượng edge API hiện có — cần đo thật ở GĐ A/B.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Review + chỉnh sửa (nếu muốn) docs/MASTER_PROMPT_UAME_V2.md.
- Duyệt card TASK-UAME-S5 để bắt đầu Giai đoạn A.
- Chạy script trên Pi5 (SSH đang đóng) để mở khóa Giai đoạn B.

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `docs/MASTER_PROMPT_UAME_V2.md`
