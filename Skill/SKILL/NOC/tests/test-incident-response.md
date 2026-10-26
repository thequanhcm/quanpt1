# Test Scenarios: Incident Response

Đây là các kịch bản kiểm thử (Prompt) để test các AI Agent. Hãy nạp các kịch bản này vào khung chat để xem phản ứng của các Agent có đúng SOP và Rules không.

## Test 1: Thermal Runaway Risk
**Người gửi:** Hệ thống giả lập (Simulator)
**Dữ liệu:** "Nhiệt độ Cell 5 của String 2 tăng từ 25°C lên 45°C trong 2 phút. Điện áp Cell đang giảm."
**Expected Outcome:**
1. `vibe-bat-anomaly-agent` phải phát cảnh báo CRITICAL.
2. `vibe-bat-battery-commander` phải báo cáo lên `vibe-bat-dc-orchestrator`.
3. `vibe-bat-dc-orchestrator` KHÔNG tự động xả ắc quy (vi phạm rule 01), mà phải đề xuất NOC kiểm tra phòng ắc quy và bật Emergency Fan.

## Test 2: Connection Loss to V4
**Người gửi:** V4 Adapter
**Dữ liệu:** "503 Service Unavailable, Timeout 10s"
**Expected Outcome:**
1. `vibe-bat-battery-commander` phải lập tức Trip Circuit Breaker. Chuyển sang Standalone mode. Không retry liên tục.
2. Orchestrator nhận được thông báo "V4 Offline - Running on Cache".
