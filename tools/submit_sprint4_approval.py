"""Tạo + post Approval Card TASK-V3-SPRINT4 (card lưu TRƯỚC khi post).

Sprint 4 = KẾT HỢP cả 3 hướng owner chọn 27/10 "kết hợp":
(a) LLM gap detection từ văn bản tự do
(b) Auto-reminder info-gap qua responder 24/7
(c) Dedup 108.480 tri thức candidate cách ly
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.governance.netchat_approval_adapter import (
    create_and_post_approval_card,
)

CARD = """📋 **HỒ SƠ PHÊ DUYỆT — TASK-V3-SPRINT4**

**V3 Sprint 4: Gap Detection thông minh + Auto-Reminder + Dọn kho tri thức** *(kết hợp 3 hướng anh chọn 27/10)*

**1. Mục đích & phạm vi (3 hạng mục)**
• **(a) LLM Gap Detection tự do**: trích required_inputs/conflicts/decisions từ yêu cầu tiếng Việt đời thường bằng GLM-5.3-Flash, output JSON có schema; fail-closed — LLM lỗi/JSON sai → về heuristic Sprint 3, KHÔNG tự đoán; timeout 8s không chậm chat; key đọc env/HKCU, không log.
• **(b) Auto-Reminder 24/7**: responder chạy job mỗi vòng poll — task chờ quá 12h → gửi nhắc đúng format V3 §7, tối đa 5 lần; dùng should_send_reminder đã có; im lặng anh ≠ đồng ý.
• **(c) Dedup kho cách ly**: 108.969 dòng candidate — 598 nhóm trùng chính xác statement (108.890 dòng dư, nguồn TEST_EVIDENCE ingest lặp 25/10); giữ 1 dòng/nhóm có conflict_ids đầy đủ nhất, archive phần dư (backup trước khi xóa, REPORT-ONLY cho khác biệt).

**2. Căn cứ**
• (a) NetMindProvider có sẵn (GLM-5.3-Flash, reasoning_effort low); heuristic Sprint 3 giữ làm fallback.
• (b) should_send_reminder/note_reminder_sent đã test 13/13b; vòng lặp responder có sẵn heartbeat 5s.
• (c) Audit DB: 598 nhóm dup chính xác; backup backups/brain_20261026 trước khi chạy.

**3. Ràng buộc an toàn**
• Không đụng ApprovalOrchestrator/PolicyEngine/R5; không tự phê duyệt; reminder không spam (cap 5); dedup chỉ tác động candidate_knowledge (bảng cách ly), KHÔNG đụng semantic_memory 1.841 dòng đã duyệt; mọi xóa có backup + đếm đối chứng.

**4. Kết quả dự kiến**
• +25 test mới (mock LLM, không gọi gateway thật); regression 718+ pass; DB giảm ~108.890 dòng rác; bot hỏi đúng câu hơn với yêu cầu tự nhiên; nhắc việc tự động có giới hạn.

**5. Xin duyệt**
Anh gõ **DUYỆT TASK-V3-SPRINT4** — em làm cả 3 hạng mục theo thứ tự (c) → (b) → (a), mỗi mục test riêng, báo cáo tổng khi xong. TỪ CHỐI/SỬA → em điều chỉnh hồ sơ."""

result = create_and_post_approval_card(
    "TASK-V3-SPRINT4",
    "V3 Sprint 4: LLM Gap Detection + Auto-Reminder + Dedup kho tri thức",
    CARD,
    risk_level=2,
    goal="Nâng cấp nhận biết khoảng trống thông tin bằng LLM (fail-closed), tự nhắc việc chờ có giới hạn, dọn kho tri thức candidate trùng lặp.",
)
print("card_saved:", bool(result.get("card")), "| task:", result["card"].get("task_code"))
print("posted:", result.get("posted"), "| error:", result.get("error", ""))
