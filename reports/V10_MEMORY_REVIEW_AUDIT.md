# V10 — MEMORY REVIEW AUDIT
**Ngày:** 28/10/2026 · Audit thực tế trước khi viết code (PHẦN II MASTER PROMPT V10)

## 1. Git & working tree
- HEAD `b6077d7` trên `feature/cognitive-state-integration` = origin tip.
- **23 thay đổi chưa commit của V9** (4 module mới + tests + 8 báo cáo + server/UI patch) — được bảo vệ nguyên vẹn, không đụng.
- Chưa commit V9 là trạng thái chờ chủ duyệt — V10 xây TRÊN các file V9 (deep_memory.py v.v.) mà không revert/ghi đè gì.

## 2. Database trí nhớ (brain.db 89.4MB, journal=delete, **integrity ok**)

| Bảng | Rows | Ghi chú |
|---|---|---|
| episodes | 1.650 | chat_turn ~1.540 (nguồn đầu vào) |
| knowledge_units | 148 | từ live smoke V9 (83 FACT, 60 QUESTION, 4 RULE, 1 OPINION) |
| knowledge_relations | 208 | 173 RELATED_TO + 35 REFINES, mọi quan hệ có basis |
| memory_exchange_log | 40 | idempotency extract |
| memory_review_runs | 1 | run_e284a6c4afcd (V9 cycle) |
| owner_questions | 0 | chưa có câu hỏi chờ |
| memories / semantic_memory / candidate_knowledge | legacy | giữ nguyên, chỉ đọc |

WAL: tasks.db journal=wal; brain.db journal=delete — ghi MemoryStore/DeepMemoryStore đều qua transaction + lock. Backup sẵn: `backups/brain_pre_v9_live_20261028.db` (89.4MB, 28/10) + backup 2AM hằng ngày.

## 3. API đọc/ghi trí nhớ hiện có
- GET `/api/memories` (episodes), `/api/memory/deep/{stats,units,questions,timeline}` (V9)
- POST `/api/memory/deep/{extract,review,answer}` (V9), `/api/chat` (router chính — có `query`, `session_id`), `/api/approvals/decide`, `/api/executive/netchat/command`
- `/api/chat` là chỗ nối lệnh `SÀNG LỌC`: exact match ở đầu handler, không đụng luồng LLM thường.

## 4. Module liên quan (đã kiểm tra mã nguồn thật, không tin tên gọi)
- `cognition/cognitive_state.py`: CognitiveClaim/Contradiction/Hypothesis — runtime, không persist.
- `memory/deep_memory.py` (V9): DeepMemoryStore — nền tái sử dụng trực tiếp: `_tokens`, `_jaccard`, `_ANTONYM_PAIRS`, `get_unit`, `supersede_unit`, `list_owner_questions`, `mark_units_conflicted`, `trace`.
- `cognition/logical_reasoning.py` (V9): `answer_question()` trả conclusion A/B/C + evidence + assumptions + missing — dùng làm Nhóm 3.
- `memory/owner_feedback.py` (V9): phân loại phản hồi 4 loại — V10 cần 9 loại mịn hơn → xử lý trong review_session, không sửa V9.
- `governance/approval_cards.py` + ApprovalGate: phê duyệt R4 production — giữ nguyên, không nối vào luồng tri thức.
- UI: tab `tab-deep-memory` (V9) — nơi cài panel Sàng Lọc; JS pattern fetch/render đã có.

## 5. Phản hồi chủ nhân hiện được lưu thế nào?
- V9 `owner_questions`: 1 câu trả lời text + answered_at + feedback log qua exchange log. **Chưa có**: liên kết response↔finding/inference cụ thể, 9 loại phân loại, before/after snapshot, undo. → Khoảng trống chính V10 lấp bằng `review_changes` + `review_findings`/`review_questions` có session_id.

## 6. Khả năng tạo phiên sàng lọc độc lập
Chưa có bảng session riêng (memory_review_runs là checkpoint cycle V9, không phải phiên owner-gated có phạm vi + trạng thái 8 giá trị). → Tạo bảng mới `memory_review_sessions` additive (không tạo DB thứ 2 — đúng ràng buộc PHẦN II).

## 7. Lỗi/dữ liệu không nhất quán phát hiện (ghi rõ trước khi triển khai)
1. Bảng `approval_cards` RỖNG (0 rows) sót trong brain.db từ lần chạy nhầm V9 — vô hại, đề xuất DROP đã bị chặn phê duyệt, chờ chủ dọn tay. Không ảnh hưởng V10.
2. 148 KU đều status=EXTRACTED (chưa có VERIFIED) — suy luận sẽ kết luận loại B/C là TRUNG THỰC đúng thiết kế; không phải lỗi.
3. 50+ rác ingest trong semantic_memory — BLOCKED chờ chính sách của chủ (V9 đã báo cáo); V10 không đụng.
4. `semantic_memory` statement có nội dung code fragment — chỉ đọc, không dùng làm nguồn suy luận trong đợt mẫu.

## 8. Kết luận kiến trúc V10
- 1 module mới `cognition/memory_review_session.py` (state machine 8 trạng thái, selection minh bạch, phân tích chỉ-đọc, 4 nhóm kết quả, response handler 9 loại, apply hai bước với before/after).
- 5 bảng additive mới; tái sử dụng V9 tối đa; +5 API; panel trong tab 🧠 V9.
- Cap mẫu mặc định 20 KU — cấu hình được, không mở rộng khi chưa chủ duyệt (PHẦN VIII).
