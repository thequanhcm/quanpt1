"""Lập card TASK-V3-OPS-BULK-APPROVE — Duyệt 57 bài học + chốt dọn 249 task.

Chỉ đạo gốc của quanpt1 qua desktop chat 27/10: "duyệt 57 bài học + chốt dọn 249 task".
Số liệu thực tế lúc thực thi (18:50): 64 lesson candidates (smoke S14/S15 sinh thêm),
259 in-flight = 250+1 task trùng lặp 'năng lượng' + 5 'kiểm toán' trùng + 2 smoke + 1
task liên kết email proposal (GIỮ). Tiêu chí dọn: huỷ MỌI in-flight TRỪ task liên kết
email proposal; backup 2 DB trước khi ghi; promote idempotent qua promote_lesson().
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-OPS-BULK-APPROVE"
TITLE = "Vận hành — Duyệt hàng loạt bài học + dọn in-flight tasks (chỉ đạo quanpt1 27/10)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-OPS-BULK-APPROVE

## 1. Chỉ đạo chủ sở hữu (verbatim)
"duyệt 57 bài học + chốt dọn 249 task" — quanpt1, desktop chat 27/10/2026.
(R5 KHÔNG liên quan: promote lesson = thay đổi trạng thái tri thức nội bộ có audit trail
qua supersede; huỷ task = huỷ mục đã đăng ký trong registry, không xóa dữ liệu.)

## 2. Phạm vi thực thi (số liệu THẬT lúc chạy, không phải 57/249 trong lời dặn)
- (a) Duyệt TẤT CẢ lesson candidates (đếm lúc chạy: 64 — smoke S14/S15 sinh thêm 7):
  promote_lesson(approval_verified=True, approved_by=quanpt1) → VERIFIED + active,
  idempotent (bản đã VERIFIED trả promoted=False), superseded bị skip có ghi nhận.
- (b) Dọn in-flight: CANCEL mọi task PENDING/IN_PROGRESS/WAITING_APPROVAL/APPROVED
  TRỪ task_95c288281a43 (liên kết email proposal TASK_CREATED — luồng nghiệp vụ sống).
  Gồm 250+1 task trùng lặp 'năng lượng' (bug loop từ 20/10), 5 'kiểm toán' trùng,
  2 task smoke S15. Không DELETE — chỉ UPDATE status CANCELLED kèm lý do + giữ nguyên
  checkpoint/cognitive state làm bằng chứng.
- (c) Backup brain.db + tasks.db TRƯỚC khi ghi (bài học dedup Sprint 4).
- (d) Verify sau: lessons_pending=0, in_flight=1 qua improvement report live.

## 3. Tác động & rollback
- Không xóa dữ liệu; mọi thay đổi có audit trail (supersede version++, evidence_refs).
- Rollback: khôi phục DB từ backup nếu anh yêu cầu.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
