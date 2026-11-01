"""Lập card TASK-V3-SPRINT14 — Information Gaps schema thật + Semantic search kinh nghiệm.

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("duyệt Sprint 14").
Nguồn phạm vi: §5 BÁO_CAO_V3_SPRINT13 (đã nghiệm thu) — 2 đầu việc chủ động được:
  (1) information_gaps còn CHƯA XÁC MINH vì Sprint 13 query sai schema (bảng thật là
      info_gap_tasks/info_gap_events) → sửa cho khớp schema thật, đóng khoảng trung thực.
  (2) Semantic search kinh nghiệm (BGE-M3 dense embedding — module có sẵn từ Module 3)
      bổ sung cho keyword search của experience_retrieval (Sprint 9).
Connector M-Suite KHÔNG nằm trong card này (cần thiết kế riêng, hỏi chủ quyền).
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT14"
TITLE = "Sprint 14 — Information Gaps schema thật + Semantic search kinh nghiệm (BGE-M3)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT14

## 1. Mục tiêu
Đóng 2 khoảng trống ghi trong báo cáo Sprint 13 (mục §5, đã nghiệm thu):
- (1) Ma trận năng lực mục information_gaps đang CHƯA XÁC MINH vì query sai schema —
  DB thật dùng bảng info_gap_tasks/info_gap_events (không có bảng information_gaps).
  Sửa build_improvement_report đọc ĐÚNG schema thật → số liệu thật, hết mục giả.
- (2) Tìm kinh nghiệm hiện chỉ là keyword LIKE (Sprint 9) — thêm SEMANTIC search
  dense bằng BGE-M3 (cognition/embedding.py có sẵn, Module 3 nghiệm thu 10/10),
  fail-open về keyword khi Ollama offline. Kinh nghiệm vẫn chỉ là THAM CHIẾU (§VII.3).

## 2. Phạm vi
- (a) PATCH cognition/improvement_report.py: mục information_gaps đọc info_gap_tasks
  (đếm waiting_state NOT IN ('RESOLVED','CANCELLED')) + info_gap_events; DB lỗi/hỏng
  → vẫn CHƯA XÁC MINH (giữ nguyên tắc fail-honest, không 0 giả).
- (b) cognition/experience_semantic.py (MỚI): find_similar_experiences_semantic() —
  dùng MemoryStore.search_memories(query='') lấy EPISODIC/PROCEDURAL active, embed
  BGE-M3, cosine similarity, trả về cùng shape {confirmed, candidates, keywords}
  cộng similarity; offline/biến空 → trả semantic_available=False + rỗng (fail-open,
  không lỗi luồng gọi).
- (c) API: GET /api/experience/search (localhost-only) — GET, read-only, tham số q.
- (d) UI Workbench: ô tìm kiếm kinh nghiệm trong khu bài học (Sprint 11) — hiển thị
  nguồn + trạng thái xác minh + % similarity; badge "semantic" / "không có semantic
  (Ollama offline)" trung thực.

## 3. Tác động & rủi ro
- PATCH improvement_report.py + tests Sprint 13 liên quan (sửa test khớp schema thật);
  FILE MỚI experience_semantic.py; PATCH server.py (1 route GET); PATCH executive.js/html.
- Chỉ ĐỌC DB + gọi Ollama local (đã có từ Module 3); không mạng ngoài, không ghi mới DB.
- Không trùng: experience_retrieval (keyword) — semantic là bổ sung, keyword vẫn fallback.

## 4. Tiêu chí nghiệm thu
- Ma trận information_gaps trả số liệu thật từ schema thật; DB hỏng → CHƯA XÁC MINH.
- Semantic search trả kết quả có similarity + nguồn gốc; Ollama offline → rỗng +
  cờ trung thực, KHÔNG chết luồng, keyword fallback vẫn chạy.
- Regression sạch; smoke thật qua server live (route, UI, embedding thật nếu Ollama on).
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
