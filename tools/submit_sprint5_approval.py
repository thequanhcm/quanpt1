"""Tạo + post Approval Card TASK-V3-SPRINT5 (card lưu TRƯỚC khi post).

Sprint 5 = "Module 3 Applied" — áp dụng kiến thức Module 3 (RAG Pipeline,
Mini RAG Lab, AI Agent Lab) mở rộng trợ lý:
(a) Document RAG pipeline (chunking + BGE-M3 + index + threshold)
(b) Benchmark 10 câu + evaluation (context recall / faithful / citation)
(c) Grounded answer có citation qua tool search_documents() read-only
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.governance.netchat_approval_adapter import (
    create_and_post_approval_card,
)

CARD = """📋 **HỒ SƠ PHÊ DUYỆT — TASK-V3-SPRINT5**

**V3 Sprint 5: Module 3 Applied — Document RAG + Benchmark + Grounded Answer** *(áp dụng giáo trình Module 3 anh cung cấp)*

**1. Mục đích & phạm vi (3 hạng mục)**
• **(a) Document RAG pipeline** (Bài 4/5): `document_rag.py` — chunking size+overlap giữ metadata (nguồn, version, ngày, loại), embedding BGE-M3 có sẵn, index SQLite riêng `data/document_index.db`, `retrieve(query, top_k, threshold)` → dưới ngưỡng trả "không tìm thấy bằng chứng đủ tốt" (không ép trả lời). Chỉ ingest tài liệu trong `kho_tai_lieu/` anh chỉ định — KHÔNG đụng .env/credentials/DB.
• **(b) Benchmark 10 câu + Evaluation** (Lab Mini RAG): 3 câu direct + 2 multi-chunk + 2 paraphrase + 2 no-answer + 1 nhầm-version; bảng context_recall/answer_relevant/faithful/citation_ok + error analysis (tách lỗi retrieval khỏi lỗi generation); đo trên tài liệu mẫu.
• **(c) Grounded Answer có Citation** (Bài 7 + Lab Agent): tool `search_documents(query, top_k)` read-only schema rõ (input/output/not_found, log tool call); prompt "chỉ trả lời từ context + dẫn nguồn [tài liệu §mục]"; không đủ bằng chứng → nói thẳng "chưa tìm thấy căn cứ trong kho tài liệu". Mức **Assist** — không tự hành động.

**2. Căn cứ**
• BGE-M3 embedding service + cosine similarity có sẵn (`cognition/embedding.py`); hybrid scoring tham chiếu CognitiveRetriever (0.25 keyword / 0.30 dense).
• Lab Mini RAG: tiêu chí đánh giá faithfulness/relevancy/context recall + cấu trúc benchmark 10 câu.
• Bài 7: guardrail "không đủ dữ liệu thì không hành động" — khớp Sprint 3 đã có.

**3. Ràng buộc an toàn**
• KHÔNG đụng CognitiveRetriever/CognitiveLoop/ApprovalOrchestrator/PolicyEngine (chỉ thêm module mới + 1 tool read-only vào chat).
• KHÔNG fine-tuning (tri thức thay đổi liên tục — RAG mới đúng, theo Bài 6/7); KHÔNG Computer Vision (ngoài phạm vi).
• Ollama BGE-M3 offline → fallback về keyword scoring, không chết chức năng.
• Test mock embedding 100%, không gọi gateway thật; key không log.

**4. Kết quả dự kiến**
• +12 test mới; regression 748+ pass; trợ lý trả lời được câu hỏi TỪ TÀI LIỆU NỘI BỘ có dẫn nguồn, dám nói "không đủ căn cứ" khi tài liệu không có.

**5. Xin duyệt**
Anh gõ **DUYỆT TASK-V3-SPRINT5** — em làm theo thứ tự (a) → (b) → (c), mỗi mục test riêng, báo cáo tổng khi xong. TỪ CHỐI/SỬA → em điều chỉnh hồ sơ. Anh cũng có thể chỉ định thư mục tài liệu thật để ingest (mặc định em tạo `kho_tai_lieu/` với tài liệu mẫu vận hành mô phỏng)."""

result = create_and_post_approval_card(
    "TASK-V3-SPRINT5",
    "V3 Sprint 5: Module 3 Applied — Document RAG + Benchmark + Grounded Answer",
    CARD,
    risk_level=2,
    goal="Áp dụng kiến thức Module 3: RAG pipeline cho tài liệu nội bộ, benchmark đo lường, trả lời có dẫn nguồn fail-closed.",
)
print("card_saved:", bool(result.get("card")), "| task:", result["card"].get("task_code"))
print("posted:", result.get("posted"), "| error:", result.get("error", ""))
