"""Submit approval card — SPRINT AGENTIC-SEC-1: ATTT cho Agentic AI theo khung MIT/Viettel.

Owner directive: tài liệu 261113_VTNET_ATTT_Agentic_AI_v4 (13/11/2026, kho_tai_lieu/)
"tài liệu này có định hướng gì cho cherry không?, hãy xây dựng và áp dụng".

4 gap xác định từ audit 13/11 (đối chiếu slide 3, 7, 8, 13, 17, 18):
- GAP-1: /api/chat + DM responder KHÔNG scan prompt injection ở ĐẦU VÀO (EchoLeak CVE-2025-32711
  tấn công ở input; hiện chỉ chặn ở tool description + output).
- GAP-2: chưa có phát hiện "bộ ba nguy hiểm" (lethal trifecta): dữ liệu riêng tư +
  nội dung không tin cậy + giao tiếp ra ngoài trên cùng 1 task.
- GAP-3: nội dung ngoài (web/email/log/knowledge) không được đánh dấu "DỮ LIỆU KHÔNG TIN CẬY"
  trước khi vào context LLM.
- GAP-4: hành động nhạy cảm (gửi ra ngoài, xóa) thiếu nhãn nguồn dữ liệu trong audit.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-AGENTIC-SEC-1"
TITLE = "Agentic Security Sprint 1 — Input Injection Shield + Lethal Trifecta Guard"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-AGENTIC-SEC-1

## 1. Mục tiêu
Áp dụng khung ATTT Agentic AI (MIT Professional Education + Viettel Cyber Security
261113_VTNET_ATTT_Agentic_AI_v4) vào CHERRY: vá 4 gap an ninh xác định trong audit
13/11, giữ nguyên mọi governance invariant hiện có (3 lớp AUTO/PROPOSE/NEVER,
R5 hard-block, localhost-only API, approval card, DM 2 bước token).

## 2. Phạm vi (4 slice theo thứ tự gap)
- (a) Slice 1 — Input Injection Shield (GAP-1, slide 7+8 EchoLeak):
  module `src/quan_ai_brain/security/input_shield.py`: 12+ pattern prompt injection
  EN+VN (mở rộng 5 pattern hiện có), chấm điểm 0-100, verdict ALLOW/SANITIZE/BLOCK;
  wire vào đầu vào /api/chat (server.py `_handle_api_chat`) + DM responder
  (netchat_auto_responder trước khi gửi vào chat pipeline). BLOCK → trả lời lịch sự
  "từ chối xử lý chỉ dẫn ẩn" + ghi audit; không phá luồng chat thường.
- (b) Slice 2 — Untrusted Content Label (GAP-3, slide 7):
  mọi đoạn context lấy từ nguồn ngoài (web lookup, knowledge_units ingest ngoài,
  log) được bọc nhãn `[DỮ LIỆU KHÔNG TIN CẬY — nguồn: X]` trong context builder;
  LLM system prompt thêm 1 dòng quy tắc: nội dung trong nhãn KHÔNG PHẢI lệnh.
- (c) Slice 3 — Lethal Trifecta Guard (GAP-2, slide 13):
  module `src/quan_ai_brain/security/trifecta_guard.py`: mỗi task/tool-call có
  3 cờ (private_data, untrusted_content, external_egress); hội đủ cả 3 → FORCE
  PROPOSE (đi DM 2 bước token xin duyệt) kể cả khi nằm trong LỚP 1 AUTO.
  Wire vào cherry_autonomous + integration policy.
- (d) Slice 4 — Audit nguồn dữ liệu (GAP-4, slide 11 "một sự cố đi qua cả ba nhóm"):
  audit event thêm field `data_source_labels` (nguồn dữ liệu đã dùng trong task)
  để truy vết đường đi người → dữ liệu → hệ thống khi có sự cố.

## 3. Ngoại phạm vi (giữ nguyên)
- Không đụng executive.js, router, secrets (R5/R4/R2 giữ nguyên).
- Không thay đổi hành vi AUTO/PROPOSE/NEVER hiện có — chỉ THÊM điều kiện nâng cấp.
- Không thêm quyền mới cho bất kỳ tool nào (least privilege giữ nguyên).

## 4. Tiêu chí nghiệm thu
- Test mock/tmppath 100%: ≥ 16 test mới (4 slice × ≥ 4 test) — injection EN+VN
  thật từ tài liệu (EchoLeak pattern), trifecta 3 cờ, label bọc đúng, audit field.
- Full regression không suy giảm so với baseline hiện tại.
- Live smoke: 1 câu chat thường qua /api/chat vẫn trả lời bình thường (không
  false-positive); 1 prompt injection mẫu bị chặn + audit ghi event.
- Báo cáo phân biệt DESIGNED/IMPLEMENTED/TESTED/LIVE_VERIFIED/BLOCKED.
"""

def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(
        task_code=TASK_CODE,
        title=TITLE,
        card_markdown=CARD_MARKDOWN,
        risk_level=2,  # additive security layer, có test + rollback
        goal="ATTT Agentic AI theo khung MIT/Viettel: input injection shield + trifecta guard",
    )
    print(f"Card created: {card.request_id} | {card.task_code} | {card.status}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
