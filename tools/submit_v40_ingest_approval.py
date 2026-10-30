#!/usr/bin/env python3
"""Tạo + duyệt approval card cho TASK-V40-KHO-TAI-LIEU-INGEST (owner directive 29/10)."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

store = ApprovalCardStore(project_root / "data" / "governance.db", workspace=str(project_root))
task_code = "TASK-V40-KHO-TAI-LIEU-INGEST"

card_md = """## Sprint V40: Nạp kiến thức kho_tai_lieu vào não TONY

**Directive owner (29/10):** "hãy để trợ lý lấy kiến thức ở kho_tai_lieu để đọc và xử lý"

**Phạm vi:**
- (a) Sửa 2 bug V38: get_embedding() -> embed_text(); thêm ingest_documents() vào KnowledgeQueryEngine
- (b) Cài parser deps: pypdf, python-docx, pandas, openpyxl, nbformat
- (c) Chạy ingestion kho_tai_lieu -> data/knowledge_db (ChromaDB collection knowledge_base)
- (d) Test end-to-end: search + answer_question + smoke /api/knowledge trên server 8765

**Tiêu chí nghiệm thu:**
- ChromaDB knowledge_base có > 300 chunks (kho 1.7GB, 91 PDF + 20 DOCX + 30 XLSX + 22 ipynb + 11 md/txt)
- search("quy trình bảo trì") trả về kết quả đúng nguồn
- TONY (server 8765 /api/chat) trả lời câu hỏi về kiến thức với nguồn tài liệu

**Rollback:** xóa thư mục data/knowledge_db (không đụng brain.db, không đụng kho_tai_lieu gốc)
"""

try:
    card = store.create_card(task_code, "V40: Ingest kho_tai_lieu", card_md, risk_level=2)
    print("CARD CREATED:", card.status)
except ValueError as e:
    print("CARD EXISTS:", e)

# Directive trong desktop chat của owner = phê duyệt hợp lệ theo quy trình
card = store.approve_card(
    task_code,
    "quanpt1",
    auth_method="owner_desktop_chat_directive",
    notes="Owner directive 29/10: 'de tro ly lay kien thuc o kho_tai_lieu de doc va xu ly'",
)
print("APPROVED:", card.status)
ok = store.consume_if_execution_started(task_code)
print("CONSUMED:", ok)
