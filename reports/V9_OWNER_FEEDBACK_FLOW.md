# V9 — OWNER FEEDBACK FLOW
**Ngày:** 28/10/2026 · Trạng thái: IMPLEMENTED + TESTED (Test F/L/xác nhận đầy đủ); LIVEVerified chờ câu hỏi thật đầu tiên của chủ

## 1. Luồng tiếp nhận phản hồi (PHẦN IX — 12 bước)

```
Chủ trả lời câu hỏi (UI "Gửi" / POST /api/memory/deep/answer)
  → (1) lưu câu trả lời qua _deep_redact (Bearer/key=value/ghp_/sk-/AKIA/xox)
  → (2) liên kết question_id + run_id sẵn có trong owner_questions
  → (3) phân loại: FACT / CLARIFY / DECISION / SCOPE (keyword tiếng Việt)
  → (4) phạm vi: "tổng quát/mọi trường hợp" → general; else scope_hint của câu hỏi
  → (5) phân biệt dữ kiện mới vs diễn giải vs quyết định (feedback_kind)
  → (6) cập nhật KU liên quan (tìm k_id trong evidence): supersede_unit version+1
  → (7) kiểm tra mâu thuẫn nguồn VERIFIED (polarity + antonym flip)
  → (8) nếu mâu thuẫn: mark_units_conflicted — KHÔNG âm thầm đổi (test ✅)
  → (9) SUPERSEDES relation cũ→mới + derived_from + review_status OWNER_CLARIFIED/OWNER_CONFIRMED
  → (10) test case khi quy tắc thay đổi: audit qua exchange log (owner_feedback_applied)
  → (11) affected_conclusions(): liệt kê KU INFERRED/CONCLUSION derived từ KU bị sửa
  → (12) trả kết quả: version_updates + production_approved=False (Test L)
```

## 2. Phân biệt câu trả lời và phê duyệt (§VIII.4 — Test L ✅)
- `production_approved` **luôn False** trong kết quả feedback — câu trả lời làm rõ tri thức không tự động thành phê duyệt production.
- Module feedback không import/đụng `approval_cards` / `ApprovalGate` / R0–R5 (test chứng minh bảng approval_cards không tồn tại trong test DB và không được tạo).
- Phê duyệt production vẫn phải qua NetChat approval cards + ApprovalGate như hiện hành.

## 3. Không âm thầm thay đổi toàn hệ thống (§IX cuối ✅)
- Mỗi câu trả lời chỉ tác động KU được trỏ trong `evidence` của câu hỏi — không quét/sửa hàng loạt.
- Nếu phản hồi mâu thuẫn nguồn VERIFIED → giữ CONFLICTED + `kept_conflicted` trong version_updates (test_answer_conflicting_with_verified_keeps_conflicted ✅).
- Câu hỏi đã trả lời không trả lời lại được (`ValueError: not OPEN`) — chống sửa history (test_answer_not_allowed_twice ✅).

## 4. Bảo đảm lịch sử (Test F ✅)
- KU cũ → `SUPERSEDED` (giữ nguyên statement) — không DELETE.
- KU mới: `version = cũ + 1`, `derived_from = [k_cũ]`, `extraction_meta.superseded_from`, `owner_answer_preview` (đã redact).
- Quan hệ `SUPERSEDES` (k_cũ → k_mới) với basis "owner feedback v1→v2".
- Trace: `store.trace(k_mới)` đi về k_cũ → episode gốc.

## 5. Kênh trả lời cho chủ
- **Dashboard**: tab 🧠 Trí Nhớ Chuyên Sâu → Memory Review Center → ô trả lời + nút Gửi (`window.__deepAnswer`).
- **API**: POST /api/memory/deep/answer `{question_id, answer}` — trả 400 nếu câu hỏi không tồn tại/đã trả lời (live smoke ✅).
- NetChat route "trả lời q_xxx" — DEIGNED (Slice 4 có hằng; chưa nối router tin nhắn — làm ở phiên sau nếu chủ duyệt, tránh đụng responder đang chạy 24/7).
