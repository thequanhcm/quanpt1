"""Lập card TASK-V3-SPRINT15 — Evidence Traceability + Cognitive State Reconciliation.

Nguồn phê duyệt phạm vi: MASTER EXECUTION PROMPT Sprint 15 của quanpt1 (27/10, desktop chat) —
§IV ưu tiên số một: EVIDENCE TRACEABILITY + COGNITIVE STATE RECONCILIATION.
Phạm vi chặt: (1) persist cognitive_state của plan vào checkpoint_data_json hiện hữu;
(2) GET /api/tasks/{task_id}/cognitive-state read-only; (3) passthrough plan warnings.
KHÔNG: Vmail thật, M-Suite, batch 249 task, bulk promote 57 lesson, đổi R4/R5, executor thật.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT15"
TITLE = "Sprint 15 — Evidence Traceability + Cognitive State Reconciliation"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT15

## 1. Mục tiêu
Master Prompt Sprint 15 (quanpt1) §IV — ưu tiên số một. Audit (reports/SPRINT15_AUDIT.md)
chứng minh 3 thiếu sót thực sự:
- CognitiveState (beliefs/contradictions/uncertainties/metacognition) được dựng trong
  ExecutiveCoordinator.plan() nhưng KHÔNG được persist — mất ngay sau response.
- Plan warnings (CẢNH BÁO DỮ LIỆU CŨ, adversarial) bị nuốt — không tới owner.
- Không có API truy xuất lại bằng chứng của một kế hoạch đã đăng ký.

## 2. Phạm vi (tối thiểu)
- (a) plan_orchestrator.submit_plan(): ghi plan.cognitive_state.to_dict() + plan.warnings
  vào cột HIỆN HỮU durable_tasks.checkpoint_data_json (JSON, không migration) — chỉ task mới
  (idempotency hiện có bảo vệ replay không ghi đè).
- (b) API GET /api/tasks/{task_id}/cognitive-state (localhost-only, READ-ONLY):
  trả state + warnings; 404 trung thực; has_cognitive_state=false nếu task cũ (không 0 giả);
  needs_review=true khi còn UNRESOLVED contradiction (KHÔNG tự phân giải).
- (c) Passthrough plan warnings vào all_warnings hiện hữu của response chat.
- Tái sử dụng 100% schema hiện có; không tạo engine/store mới; không đổi R4/R5.

## 3. Tác động & rủi ro
- PATCH plan_orchestrator.py + server.py (CLEAN trong working tree — không đụng file nhánh
  song song cognitive_state/coordinator của họ); tests file mới.
- Ghi thêm thông tin vào task mới tạo; không sửa/xoá dữ liệu production hiện hữu.
- Rollback: hoàn tác 2 patch + không dùng file mới; revert 1 commit nếu đã commit sau duyệt.

## 4. Tiêu chí nghiệm thu
- Task đăng ký qua /api/executive/task/create có cognitive_state đọc lại được qua API mới.
- Task cũ (trước S15) → has_cognitive_state=false trung thực.
- UNRESOLVED contradiction → needs_review=true, không tự RESOLVED.
- Test mục tiêu + full suite xanh; smoke live read-only; không gián đoạn 24/7.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
