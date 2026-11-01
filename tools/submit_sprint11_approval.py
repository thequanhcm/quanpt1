"""Lập card TASK-V3-SPRINT11 — Experience Memory (consolidation & lessons learned).

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("em triển khai Sprint 11 (Experience Memory").
Theo roadmap §XIV master prompt Sprint 9: Sprint 11 = Experience Memory.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT11"
TITLE = "Sprint 11 — Experience Memory (consolidation & lessons learned)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT11

## 1. Mục tiêu
Biến kết quả nhiệm vụ (thành công LẪN thất bại) thành kinh nghiệm tái sử dụng:
capture khi task kết thúc → consolidate thành lessons (đề xuất) → duyệt một lần →
phục vụ đề xuất email (Sprint 10) qua experience_retrieval (Sprint 9 D).
KHÔNG tạo memory store mới — dùng MemoryStore hiện có (memories + episodes).

## 2. Phạm vi
- (a) experience_consolidation.py: khi task COMPLETED/FAILED → extract_candidate_lesson()
  sinh lesson CANDIDATE (UNVERIFIED, quarantine lifecycle) vào MemoryStore hiện có;
  idempotent theo task_id (1 task = 1 lesson tối đa, lặp lại không trùng).
- (b) API: POST /api/experience/consolidate (task_id, outcome) — localhost-only,
  fail-closed; GET /api/experience/lessons — list lessons (candidates + confirmed tách
  riêng); POST /api/experience/lessons/promote — CHỈ owner duyệt (localhost-only, consume
  như approvals: approval_verified=True phải có card duyệt; không tự duyệt).
- (c) UI Workbench: khu "Kinh nghiệm (Experience Memory)" — xem lessons ứng viên/đã
  duyệt, nút duyệt (gọi approvals flow hiện có: card → decide), nút "nâng cấp kinh
  nghiệm" promote candidate lesson → confirmed (VERIFIED) chỉ sau khi owner bấm.
- (d) Tích hợp đề xuất email (Sprint 10): proposal builder đã find_similar_experiences —
  lessons mới tự động xuất hiện ở đó (không sửa email_intelligence).

## 3. Tác động & rủi ro
- File mới: memory/experience_consolidation.py; PATCH server.py (3 endpoint);
  executive.html/js (khu lessons); PATCH plan_orchestrator.py? KHÔNG — hook qua API
  consolidate (gọi từ _handle_api_executive_task_execute sau execute_lifecycle, fail-closed
  try/except — không phá luồng execute hiện có).
- Rủi ro thấp: lesson = memory CANDIDATE + lifecycle QUARANTINED — KHÔNG được dùng làm
  căn cứ mạnh (S9 retrieval đã tách confirmed/candidates). Promote cần owner bấm.
- Không LLM; không gửi ra ngoài; không đụng Vmail/R5.

## 4. Tiêu chí nghiệm thu
- Task COMPLETED/FAILED → lesson CANDIDATE sinh đúng 1 lần; lặp consolidate → no-op.
- Lesson candidate KHÔNG xuất hiện trong experience_retrieval.confirmed (chỉ candidates).
- Promote chỉ khi owner gọi; sau promote → verification VERIFIED, lifecycle active,
  xuất hiện trong confirmed của retrieval.
- 3 API localhost-only; DB lỗi → fail-closed trả lỗi trung thực.
- Regression sạch; smoke thật qua watchdog respawn.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
