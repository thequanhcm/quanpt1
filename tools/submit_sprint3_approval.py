"""Tạo + post Approval Card TASK-V3-SPRINT3 (card lưu TRƯỚC khi post).

V3 §14 bước 10: trình anh Quânpt1 báo cáo kết quả — KHÔNG commit khi chưa
có 'DUYỆT TASK-V3-SPRINT3'.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.governance.netchat_approval_adapter import (
    create_and_post_approval_card,
)

CARD = """📋 **HỒ SƠ PHÊ DUYỆT — TASK-V3-SPRINT3**

**Sprint 3 (Master Prompt V3): Information Gap Awareness Engine**
*Em tự nhận biết thông tin còn thiếu, chủ động hỏi anh đúng câu, chờ chỉ đạo — chỉ tiếp tục khi đủ căn cứ.*

**1. Em đã xây gì**
• `information_gap_analyzer.py` — Task Specification 15 trường, phân loại 9 nhóm thiếu (A–I), 3 trạng thái READY / NEEDS_OWNER_INPUT / NEEDS_VERIFICATION, câu hỏi có lý do + why_it_matters + options.
• Nối vào `CognitiveLoop.submit_task` (gap_check mặc định BẬT): thiếu thông tin thiết yếu → nhiệm vụ KHÔNG được đăng ký, KHÔNG hành động nào chạy, trả câu hỏi cho anh.
• NetChat (kênh hiện có): tin `[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]` đúng format V3 §7; anh trả lời → em ghi nguồn "phản hồi của anh", hỏi tiếp phần còn thiếu hoặc báo đủ. **Trả lời ≠ phê duyệt** — phê duyệt vẫn qua Approval Card riêng.
• Trạng thái chờ lưu SQLite, khôi phục đầy đủ sau restart; im lặng KHÔNG đồng ý; nhắc tối đa 5 lần/cách 12 giờ.

**2. Bằng chứng kiểm thử**
• 18/18 tình huống bắt buộc V3 §12 — ĐẠT (23 test pass).
• NetChat routing: 10 test pass — info request KHÔNG trộn approval request.
• Chỉ số §13: hành động khi thiếu điều kiện = 0; hành động khi đang chờ = 0; tự suy đoán = 0.
• Full regression: **717 passed, 2 skipped, 1 failed** (Ollama OFFLINE — fail môi trường cũ, không liên quan).

**3. Giới hạn trung thực**
• Gap detection hiện là luật khai báo + heuristic từ TaskSpec — CHƯA dùng LLM suy luận từ văn bản tự do (đề xuất sprint sau, vẫn fail-closed).
• Danh tính owner reply cấp-1 = tài khoản NetChat (chưa sinh-trắc-học).

**4. Đề nghị của em**
DUYỆT TASK-V3-SPRINT3 để em commit code lên master. Anh từ chối/sửa → em giữ nguyên trạng thái chờ, không tự commit."""

result = create_and_post_approval_card(
    "TASK-V3-SPRINT3",
    "Sprint 3: Information Gap Awareness Engine (Master Prompt V3)",
    CARD,
    risk_level=2,
    goal="Tích hợp nhận biết khoảng trống thông tin vào CognitiveLoop + NetChat, chờ chỉ đạo chủ nhân trước khi thực hiện.",
)
print("card_saved:", bool(result.get("card")), "| task:", result["card"].get("task_code"))
print("posted:", result.get("posted"), "| error:", result.get("error", ""))
