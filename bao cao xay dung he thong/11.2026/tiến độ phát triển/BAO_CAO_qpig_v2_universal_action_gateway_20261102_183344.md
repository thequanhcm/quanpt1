# BÁO CÁO KỸ THUẬT — qpig_v2_universal_action_gateway

> Sinh tự động 02/11/2026 18:33:44 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Nâng cấp QPIG từ skeleton 6 tool lên 19 tool chuẩn §2 directive QPIG V2.0 (25 đăng ký gồm 6 alias v1 backward-compat). Adapter framework §3: 7 adapter (HTTP/WebSocket/MCP/A2A/SSH/MQTT/Serial) + 6 giao thức PENDING (USB/UART/RS485/Bluetooth/BACnet/Modbus) khai báo trung thực không giả lập. Action engine §4 11 bước bắt buộc approval trước EXECUTE. Token phê duyệt một-lần gắn action_fingerprint §6. Evidence + đối chiếu độc lập §7. PHASE 1 demo live LAN thật: 8 thiết bị, Pi5 REACHABLE 2ms, SSH còn đóng. 15/19 tool chuẩn khai báo operational=false trung thực. Card appr_de50ca6a6a00 chờ duyệt.

## 2. PHÂN TÍCH
- §2: 19 tool có đủ 10 thuộc tính (Tool ID, Input/Output Schema, Protocol, Required Permission=RiskLevel, Risk, Timeout, Approval Requirement, Execution Log=steps, Verification Method) — test chốt từng tool.
- §4: engine dừng ở CHECK_APPROVAL khi thiếu token — KHÔNG execute, KHÔNG evidence.
- §6: token consume một-lần; tái sử dụng → refuse; gắn fingerprint tool đích.
- §8: AGENT_ISOLATION_REQUEST chỉ tạo approval card R4 — không tự cô lập.
- Bug tích hợp phát hiện + sửa: card service chỉ nhận R4 → isolation đổi R3→R4.

## 3. ĐÁNH GIÁ
- tests/test_qpig_v2.py: 9/9 PASS (mock tmp_path, không đụng LAN).
- tests/test_uaiif_s4.py: 33/33 PASS (backward-compat 6 tool v1 giữ nguyên).
- Demo live Phase 1: 5/5 bước thành công trên LAN thật (reports/QPIG_V2_LIVE_DEMO.md).

## 4. ĐỊNH HƯỚNG
- Phase 2 (Agent Communication): cần kênh agent thật đã xác minh — chờ SSH Pi5.
- Phase 3-5: từng tool phải chạy E2E thật mới được gắn operational=true.
- Phase 8: đấu QPIG vào chat pipeline qua ToolRegistry hiện có.

## 5. ĐỀ XUẤT
- Owner duyệt card appr_de50ca6a6a00 (R4) cho sprint QPIG V2.
- Owner chạy script tony_pi5_all_in_one.sh trên Pi5 để mở SSH/API — khoá Phase 2+.

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- reports/QPIG_V2_LIVE_DEMO.md — bảng 5 bước live thật.
- reports/TEST_RUN_QPIG_V2.txt — regression đầy đủ (đang chạy).
- Card appr_de50ca6a6a00 — PENDING, hết hạn 2026-11-03T11:30:17Z.

## 7. RỦI RO & TRUNG THỰC
- Pi5 SSH đóng: mọi tool tác động thiết bị thật refuse fail-honest — không fake.
- 15 tool chưa E2E: chỉ có mã + test mock — KHÔNG khai operational (§2).

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyệt card appr_de50ca6a6a00.
- Mở SSH Pi5 (script all_in_one) — điều kiện tiên quyết Phase 2-8.

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `src/quan_ai_brain/uaiif/qpig.py`
- `src/quan_ai_brain/tools/registry.py`
- `tests/test_qpig_v2.py`
- `tests/test_uaiif_s4.py`
- `reports/QPIG_V2_LIVE_DEMO.md`
