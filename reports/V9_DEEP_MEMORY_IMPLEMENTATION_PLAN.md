# V9 — DEEP MEMORY IMPLEMENTATION PLAN
**Ngày:** 28/10/2026 · Triển khai theo lát cắt kiểm chứng được (PHẦN XV), tái sử dụng tối đa

## Tái sử dụng (không tạo trùng)
- Kho vận hành: `MemoryStore` (sqlite_store.py) — giữ nguyên.
- Truy xuất dense: `experience_semantic.py` (BGE-M3) — dùng cho Compare/Retrieve.
- Câu hỏi chủ: bảng `owner_questions` mới NHƯNG gửi thông báo qua info-gap adapter + NetChat đã có.
- CLO checkpoint pattern (learning_session.py) — tham chiếu cho checkpoint chu kỳ review.
- Kill-switch pattern V8 (env) — áp cho V9.

## Slice 1 — Nền tảng: schema + extractor + truy vết (Ưu tiên 1+2) — MODULE NÀY
- `src/quan_ai_brain/memory/deep_memory.py` (~400 dòng):
  - `DeepMemoryStore`: mở brain.db, tạo 5 bảng mới (additive), MemoryStore bên dưới.
  - `extract_from_chat_turns(limit)`: đọc episodes chat_turn → tách FACT/OPINION/QUESTION/RULE bằng quy tắc deterministic (không LLM): câu khẳng định có chủ ngữ+đối tượng cụ thể → FACT (status EXTRACTED); câu "tôi nghĩ/có lẽ" → OPINION; câu hỏi → QUESTION; "luôn/phải/quy tắc/nhớ" → RULE. Cùng 1 cặp user_query+reply tạo tối đa 5 KU.
  - `link_units()`: tạo quan hệ có căn cứ — REFINES (cùng subject, một câu chứa câu kia), RELATED_TO (≥2 token nội dung chung, đánh dấu is_speculative=1), SUPERSEDES (cùng subject+predicate, khác thời điểm valid_from), CONTRADICTS (cùng subject+predicate, object phủ định nhau — từ điển phủ định tiếng Việt nhỏ), SUPPORTS (cùng subject cùng hướng object).
  - `compare_similar()`: phát hiện trùng lặp (Jaccard statement) → RELATED_TO + stats (không tự merge).
  - `trace(knowledge_id)`: vòng DERIVED_FROM + source episodes + relations.
  - `archive_semantic_junk()`: đánh dấu semantic_memory rác (script/shebang/version) → không DELETE, ghi nhận vào stats (Test I an toàn).
- API server.py: `GET /api/memory/deep/stats`, `GET /api/memory/deep/units?status=&limit=`, `GET /api/memory/deep/unit/<id>` (kèm relations + trace), localhost-only.
- Tests: extraction phân loại đúng (Test A), quan hệ có căn cứ (Test B), trace về được nguồn (Test K), additive migration không mất dữ liệu (Test I).

## Slice 2 — Suy luận có bằng chứng (Ưu tiên 3)
- `src/quan_ai_brain/cognition/logical_reasoning.py`:
  - `answer_question(question)`: quy trình 12 bước §V.1 rút gọn deterministic — truy xuất KU liên quan (LIKE + scope) → phân loại bằng chứng trực tiếp/gián tiếp → phát hiện mâu thuẫn qua relations → kết luận loại A (trực tiếp, có VERIFIED) / B (INFERRED, lưu derived_from + assumptions) / C (hypothesis, không đủ bằng chứng).
  - Chống vòng tròn: khi đi theo DERIVED_FROM, không cho phép 1 KU xác nhận tổ tiên trực tiếp của chính nó (DFS với tập đã thăm + ghi shared-origin khi nhiều kết luận cùng gốc).
  - Kết quả: dict có `conclusion_type`, `evidence_refs`, `assumptions`, `missing_info`, `confidence_breakdown`.
- Tests: Test D (suy luận lưu nguồn), chống vòng tròn (KU A suy từ B không dùng A xác nhận B), Test J (truy xuất nhiệm vụ mới).

## Slice 3 — Chu kỳ sàng lọc + hỏi chủ (Ưu tiên 4)
- `src/quan_ai_brain/cognition/memory_review_cycle.py`:
  - 10 bước §VII.1 COLLECT→...→REPORT với checkpoint vào `memory_review_runs` (tiếp tục sau gián đoạn — Test H), batch_limit mặc định 50 (§XII.7).
  - Sinh câu hỏi A–G vào `owner_questions` chỉ khi: mâu thuẫn không tự giải, RULE lặp lại chưa rõ chính thức, giả thuyết cần giả định chưa xác nhận (§VIII.1). KHÔNG hỏi lại câu OPEN (idempotent theo chứng cứ).
  - Xử lý mâu thuẫn theo §V.4: không xóa, so scope/valid_from, phân loại DIRECT vs CONTEXT_DIFFERENCE (tái dùng ContradictionType), không giải quyết được → CONFLICTED/NEEDS_OWNER_REVIEW (Test C).
- Gửi thông báo: có câu hỏi mới → post 1 tin gọn kênh NetChat qua netchat_bot (2 bước --confirmed) — tái dùng chuẩn hiện có, không spam (≤1 tin/đợt).
- Tests: Test E (câu hỏi đúng cấu trúc A–G), Test C, Test H (gián đoạn giữa stage → resume đúng cursor).

## Slice 4 — Phản hồi chủ + phiên bản (Ưu tiên 5)
- `answer_owner_question(question_id, answer_text, answered_by)`:
  - Lưu câu trả lời + thời điểm; phân loại: làm rõ ngữ nghĩa / phạm vi / dữ kiện mới / quyết định (§IX.5).
  - Cập nhật KU: version+1, updated_at, review_status=OWNER_CLARIFIED/OWNER_CONFIRMED; không tự nâng VERIFIED nếu thiếu bằng chứng (Test L — trả lời ≠ phê duyệt production: không đụng approval cards, không đổi R0-R5).
  - Nếu câu trả lời mâu thuẫn nguồn VERIFIED → tạo contradiction mới + hỏi lại (§IX.8).
  - SUPERSEDES cũ → mới trong cùng scope (giữ lịch sử — Test F).
- API: `POST /api/memory/deep/answer` (localhost-only) + route NetChat "trả lời q_<id>".
- Tests: Test F (đúng phạm vi + giữ lịch sử), Test L.

## Slice 5 — Giao diện Deep Memory (Ưu tiên 6)
- executive.html: card "🧠 Deep Memory" trong tab hiện hữu (không tái cấu trúc trang): overview 10 số liệu thật (§XI.1), Knowledge Explorer (search + filter status), Memory Review Center (danh sách owner_questions OPEN + contradictions), Memory Timeline (20 sự kiện mới nhất từ review_runs + KU created/updated).
- executive.js: fetch 3 API mới, render, nút "Trả lời" mở prompt → POST answer.
- Cache bump v4.1→v4.2.

## Thứ tự + tiêu chí nghiệm thu từng slice
Mỗi slice: unit tests (mock/tmppath 100%) → regression FULL → live smoke trên server 8765 thật → báo cáo cập nhật. Slice sau không bắt đầu trước khi slice trước TESTED. Báo cáo tổng: V9_TEST_RESULTS + V9_FINAL_HANDOFF + V9_LOGICAL_REASONING_REPORT + V9_MEMORY_REVIEW_RESULTS + V9_OWNER_FEEDBACK_FLOW (cập nhật dần theo slice hoàn thành).

## Phạm vi KHÔNG làm (t trung thực)
- Không thay SQLite bằng graph/vector DB (§XII.14 — đánh giá: quy mô 2.767 KU tiềm năng, SQLite + index + BGE-M3 retrieval là đủ; chi phí vận hành hệ mới > lợi ích).
- Không chạy review cycle liên tục — chỉ kích hoạt API/on-demand + lịch nhẹ sau này (§VII).
- Không dùng LLM để trích xuất ở Slice 1 (deterministic, kiểm chứng được; LLM chỉ là đề xuất sau này nếu cần).
