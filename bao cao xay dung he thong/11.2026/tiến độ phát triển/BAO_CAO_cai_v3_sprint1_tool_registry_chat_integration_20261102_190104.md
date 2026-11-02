# BÁO CÁO KỸ THUẬT — cai_v3_sprint1_tool_registry_chat_integration

> Sinh tự động 02/11/2026 19:01:04 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
CAI V3.0 SPRINT 1: PHASE 0 audit tươi (6 lỗ hổng báo cáo cũ vẫn còn); ToolRegistryLoader auto-load 25 tool từ QPIG (giải quyết 'Tool Registry trống'); ToolSelector chọn tool theo intent (keyword+name+risk+operational); chống Tool Description Injection (5 pattern EN+VN) + Schema Injection; ChatToolBridge wire QPIG vào /api/chat — chèn tool evidence block vào system_instructions trước LLM call; tool AUTO execute+evidence, tool R3+ chỉ đề xuất + yêu cầu ticket. 12/12 test PASS. Demo thật 4 query: 2 auto-exec (evidence #4,#5) + 1 cần ticket + 1 không match. Regression đầy đủ đang chạy.

## 2. PHÂN TÍCH
- §III.1-2: ToolRegistryLoader giải quyết root cause 'Tool Registry trống' — trước đây ToolRegistry KHÔNG tự load, phải register thủ công; QPIG có 25 tool nhưng không có instance nào wire vào chat.
- §III.6: ToolSelector scoring = kw*0.4 + name*0.3 + op_bonus*0.1 - risk_penalty*0.2; keyword match robust với tiếng Việt có/không dấu (unicodedata NFD).
- §III chống injection: 5 pattern (ignore previous, bỏ qua hướng dẫn, disregard system, you are now, <system>); schema validation ở QPIG.validate_params.
- §IV: wire tại web/server.py line 1844 (sau Knowledge Base RAG, trước LLM); response JSON có field tool_calls (n_calls, auto_executed, require_approval, evidence_ids).

## 3. ĐÁNH GIÁ
- tests/test_cai_v3_sprint1.py 12/12 PASS.
- Demo thật: DEVICE_DISCOVERY evidence#4 (8 thiết bị LAN), NETWORK_INSPECTION evidence#5 (Pi5 REACHABLE 3ms), AGENT_ISOLATION_REQUEST refuse (cần ticket).
- Regression đầy đủ: đang chạy reports/TEST_RUN_CAI_V3_S1.txt.

## 4. ĐỊNH HƯỚNG
- Sprint 2: Memory + Reasoning + Evidence Store (PHASE 4+5+8).
- Sprint 3: Pi5 QPIG + QEP Communication — chờ owner mở SSH.
- Sprint 4-6: SENTINEL, UAIIF, End-to-End.

## 5. ĐỀ XUẤT
- Owner duyệt card sprint CAI V3 SPRINT 1.
- Owner mở SSH Pi5 để mở khoá Sprint 3.

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- reports/TONY_COGNITIVE_TRUTH_AUDIT_V2.md
- reports/CAI_V3_SPRINT1_REPORT.md
- reports/TEST_RUN_CAI_V3_S1.txt
- tests/test_cai_v3_sprint1.py (12 PASS)

## 7. RỦI RO & TRUNG THỰC
- Tool chưa E2E (15/25) khai operational=false trung thực — không fake.
- Embedding module lỗi (knowledge.embedding không tồn tại) — Sprint 2 xử lý.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyệt card sprint CAI V3 SPRINT 1.
- Mở SSH Pi5 (chờ Sprint 3).
- Bấm tạo PR branch feat/deom-m1-m2-task-lifecycle.

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `src/quan_ai_brain/tools/chat_bridge.py`
- `src/quan_ai_brain/web/server.py (wire tại line 1844)`
- `tests/test_cai_v3_sprint1.py`
- `reports/TONY_COGNITIVE_TRUTH_AUDIT_V2.md`
- `reports/CAI_V3_SPRINT1_REPORT.md`
