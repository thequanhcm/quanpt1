"""Tạo + post Approval Card TASK-V3-SPRINT6-GOP (card lưu TRƯỚC khi post).

Sprint 6 GỘP 4 hướng nâng cấp owner yêu cầu "gộp thành 1 card như Sprint 4":
(1) Document RAG (từ card TASK-V3-SPRINT5 cũ — sẽ cancel)
(2) 24/7 hardening: backup 2AM + Ollama vào startup + checklist reboot
(3) Báo cáo sáng tự động 8h qua NetChat
(4) Tra cứu lịch họp/nhân sự TTNS read-only vào chat
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.governance.netchat_approval_adapter import (
    create_and_post_approval_card,
)

CARD = """📋 **HỒ SƠ PHÊ DUYỆT — TASK-V3-SPRINT6-GOP**

**V3 Sprint 6: GỘP 4 hướng nâng cấp** *(anh yêu cầu gộp 1 card như Sprint 4)*

**1. Hạng mục (1) — Document RAG tài liệu nội bộ** *(kế thừa card Sprint 5 cũ)*
• `document_rag.py`: chunking size+overlap + metadata (nguồn/version/ngày/loại) + BGE-M3 có sẵn + index SQLite riêng + `retrieve(query, top_k, threshold)`; dưới ngưỡng → "không tìm thấy bằng chứng" (không ép trả lời).
• Benchmark 10 câu tiếng Việt (3 direct + 2 multi-chunk + 2 paraphrase + 2 no-answer + 1 nhầm-version) + bảng context_recall/faithful/citation_ok + error analysis.
• Tool `search_documents(query, top_k)` read-only + grounded prompt "chỉ trả lời từ context + dẫn nguồn" vào /api/chat. Mức Assist.
• KHÔNG đụng CognitiveRetriever/CognitiveLoop/ApprovalOrchestrator; KHÔNG ingest .env/credentials; KHÔNG fine-tuning/CV. Ollama chết → fallback keyword.

**2. Hạng mục (2) — 24/7 Hardening**
• Đăng ký lại scheduled task backup 2AM (đang MẤT — backup cuối 26/10; `schtasks /create` user-level, không cần admin; script `run_backup.bat` có sẵn).
• Đưa Ollama vào `KHOI_DONG_24_7.bat` (hiện KHÔNG được quản → chết khi reboot; start tối thiểu, kiểm tra port 11434 trước khi start).
• Checklist + test reboot thật PC (anh thực hiện nhấn restart; em verify sau boot: servers, responder, watchdog, backup task, Ollama, Pi 5 reconnect).

**3. Hạng mục (3) — Báo cáo sáng tự động 8h qua NetChat**
• Job 08:00 hằng ngày: trạng thái 8765/8766 + Pi 5 edge + Ollama + backup gần nhất + số task chờ duyệt + task đang chờ info-gap → gửi 1 tin gọn kênh "Trợ lý Tony Pham".
• Dùng scheduler hiện có (learning_daemon pattern); fail-closed — lỗi probe → báo "chưa xác minh được X", không bịa số.

**4. Hạng mục (4) — Tra cứu lịch họp/nhân sự TTNS vào chat**
• Skill ttns-meeting-lookup đã có (read-only) → bọc thành tool `lookup_meetings(query)` cho chat pipeline: hỏi "ngày mai có lịch họp gì" → trả danh sách có nguồn.
• Read-only tuyệt đối; không cache dữ liệu nhạy cảm vào DB; không gửi dữ liệu nhân sự ra ngoài (redact trước khi LLM tổng hợp).

**5. Ràng buộc chung**
• +20 test mới (mock gateway/HTTP); regression 756+ pass; mỗi hạng mục test riêng, làm theo thứ tự (2)→(3)→(4)→(1); card duyệt 1 lần cho cả 4.
• Không đụng R4/R5; không đọc secret; mọi thay đổi startup có diff cho anh xem trước khi commit.

**6. Xin duyệt**
Anh gõ **DUYỆT TASK-V3-SPRINT6-GOP** — em làm cả 4 hạng mục theo thứ tự trên, báo cáo từng mục + tổng kết. TỪ CHỐI/SỬA → em điều chỉnh. (Card TASK-V3-SPRINT5 cũ sẽ bị thu hồi, nội dung RAG chuyển vào card này.)"""

result = create_and_post_approval_card(
    "TASK-V3-SPRINT6-GOP",
    "V3 Sprint 6: Gộp 4 hướng — RAG + 24/7 Hardening + Báo cáo sáng + TTNS lookup",
    CARD,
    risk_level=2,
    goal="Gộp 4 hướng nâng cấp owner chọn: Document RAG, 24/7 hardening, báo cáo sáng tự động, tra cứu TTNS vào chat.",
)
print("card_saved:", bool(result.get("card")), "| task:", result["card"].get("task_code"))
print("posted:", result.get("posted"), "| error:", result.get("error", ""))
