# Incident Response Workflow (SOP)

Quy trình chuẩn khi xử lý sự cố trong Data Center.

**Phase 1: Detection**
1. Cảm biến phát hiện bất thường -> Gửi dữ liệu về tương ứng cho các Agent (Ví dụ: `vibe-bat-anomaly-agent`).
2. Agent đánh giá và phát [ALERT] cho Commander tương ứng.

**Phase 2: Triaging & Escalation**
1. Commander nhận [ALERT], thực hiện lọc nhiễu (Noise filtering).
2. Nếu Alert nghiêm trọng (Vd: Thermal Runaway), báo ngay lên `vibe-bat-dc-orchestrator`.
3. Orchestrator kích hoạt Mission Engine.

**Phase 3: RCA (Root Cause Analysis)**
1. Orchestrator gọi Cross-Domain Reasoning.
2. Ví dụ: Nhiệt độ cao -> Orchestrator hỏi Cooling Commander (Kiểm tra PAC/CRAC) và Battery Commander (Kiểm tra Cell).
3. Các Diagnostic Agent phân tích và trả về báo cáo.

**Phase 4: Resolution & Verification**
1. Orchestrator xuất Decision + Gửi NOC yêu cầu xác nhận.
2. Chờ phê duyệt -> Thực thi -> Xác minh sự cố đã hết.
