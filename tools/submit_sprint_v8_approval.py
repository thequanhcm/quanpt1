"""Submit approval card for V8 — Vietnamese Conversational Intelligence Engine.

Owner directive: MASTER PROMPT V8 (27/10/2026, desktop chat) — audit toàn bộ
đường đi hội thoại tiếng Việt (text + voice) và nâng cấp theo thứ tự ưu tiên
1-10 (hiểu đúng ý → ngữ cảnh → diễn đạt tự nhiên → đúng trọng tâm → hỏi lại →
không bịa → voice → học từ lỗi → kiểm thử → lưu quy tắc đã xác minh).
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V8-CONV-ENGINE"
TITLE = "V8 — Vietnamese Conversational Intelligence Engine"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V8-CONV-ENGINE

## 1. Mục tiêu
Audit đường đi hội thoại thực tế (text /api/chat + /api/chat/stream, voice
STT→TTS) và nâng cấp lớp tiếng Việt: hiểu ý, giữ ngữ cảnh, diễn đạt tự nhiên,
đúng trọng tâm, hỏi lại khi mơ hồ, không bịa. Không chỉ viết prompt mới —
phải có benchmark trước/sau để chứng minh.

## 2. Phạm vi
- (a) 3 báo cáo audit: V8_VIETNAMESE_CONVERSATION_AUDIT,
  V8_DIALOGUE_PIPELINE_MAP, V8_CONVERSATION_IMPROVEMENT_PLAN (reports/).
- (b) Lớp tiếng Việt mới `vietnamese_conversation.py` (cognition): phân loại
  yêu cầu (7 loại §3.2), phát hiện câu phụ thuộc ngữ cảnh (§4.2), quy tắc
  diễn đạt tự nhiên (§3.1) — TẤT CẢ làm CONTEXT INJECTION cho LLM, không
  hậu chỉnh sửa nội dung trả lời.
- (c) Wire vào PromptContextBuilder (thêm block [CONVERSATION GUIDANCE] khi
  query là tiếng Việt) + cả 2 luồng chat nhận điểm tăng cường.
- (d) Benchmark `tests/test_v8_vietnamese_benchmark.py` (5 nhóm A-E theo §VIII,
  ≥40 case, chấm bằng tiêu chí khách quan: keyword/không-lặp/độ dài/đại từ).
- (e) Voice: audit + tối ưu sanitize_for_spoken_vietnamese (từ điển đọc mã,
  số, đơn vị) — chỉ phần đã tồn tại, không báo cải thiện phần chưa tích hợp.

## 3. Tác động & rủi ro
- File mới: cognition/vietnamese_conversation.py, tests/test_v8_vietnamese_benchmark.py,
  6 báo cáo V8. PATCH: context_builder.py (thêm block, backward-compat),
  voice_pipeline.py (sanitize nâng cấp).
- Rủi ro: R1 (read-only audit + context injection; không đổi governance,
  không đổi quyền hạn, không đụng approval engine). Giữ nguyên thay đổi V7.1
  chưa commit (netchat_bridge.py, executive.js/html).
- Rollback: git revert; context block tách biệt, tắt bằng 1 flag.

## 4. Tiêu chí nghiệm thu
- Benchmark ≥40 case chạy PASS với tiêu chí khách quan; kết quả baseline vs
  after đều được ghi lại (không tuyên bố tăng nếu không có số liệu).
- Regression full suite không suy giảm so với baseline 1071/0/1.
- Context injection được xác minh CÓ XUẤT HIỆN thật trong rendered_context
  (không chỉ viết prompt rồi bỏ).
- Live smoke /api/chat với query tiếng Việt thật → reply có cải thiện đo được.
- Mọi phần chưa làm được báo trung thực (voice E2E cần mic thật, ASR
  reliability chưa có score...).
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
    # --- After the owner's explicit approval directive in chat ---
    # card = store.approve_card(
    #     TASK_CODE,
    #     "quanpt1",
    #     auth_method="owner_desktop_chat_directive",
    #     notes="Owner phe duyet V8 qua desktop chat 27/10/2026",
    # )
    # print("status:", card.status)
    # print("consumed:", store.consume_if_execution_started(TASK_CODE))  # consume-once
