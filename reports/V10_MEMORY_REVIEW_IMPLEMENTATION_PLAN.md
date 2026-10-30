# V10 — MEMORY REVIEW IMPLEMENTATION PLAN
**Ngày:** 28/10/2026 · Tái sử dụng V9 tối đa; additive-only; owner-gated ở từng bước

## 1. Schema 5 bảng mới (CREATE IF NOT EXISTS, không đụng bảng cũ)

```sql
memory_review_sessions (session_id PK, created_at_utc, status,          -- 8 trạng thái
    scope_json, selection_reasons_json, stats_json, closed_at_utc)
review_findings    (finding_id PK, session_id, finding_type,            -- DUPLICATE|SIMILAR|CONTRADICTION|
    ku_a, ku_b, evidence, reason, confidence, scope_impact,             --  STALE|MISSING_RELATION|INSUFFICIENT_INFO
    proposed_action, status, created_at_utc)
review_inferences  (inference_id PK, session_id, question, input_kus_json,
    evidence_refs_json, assumptions_json, proposed_conclusion,
    contradicting_evidence_json, missing_info_json, scope, certainty,   -- HYPOTHESIS|UNVERIFIED_INFERENCE|VERIFIED
    status, created_at_utc, INSUFFICIENT_EVIDENCE qua certainty)
review_questions   (question_id PK, session_id, problem, evidence,
    current_view, interpretations_json, question, impact, scope_hint,
    status, answer_text, answered_at_utc, finding_ref, created_at_utc)  -- tái dùng cấu trúc A–G V9
review_changes     (change_id PK, session_id, target_ku, change_kind,   -- CLARIFY|SUPERSEDE|REJECT_INFERENCE|...
    before_json, after_json, reason, owner_response_json,               -- lịch sử trước–sau (PHẦN VII)
    confirm_state, applied_at_utc, undo_json, result)                   -- PENDING→PREVIEWED→CONFIRMED→APPLIED (|CANCELLED)
```

## 2. Module `cognition/memory_review_session.py` (~600 dòng)

- `MemoryReviewSession` class — state machine: `IDLE → ANALYZING → REVIEW_READY → WAITING_OWNER → APPLYING_CONFIRMED_CHANGES → COMPLETED` (+`PAUSED`, `FAILED`).
- `start(scope_limit=20)`: guard 1 session mở (`if any session status not in (COMPLETED,FAILED,CANCELLED): return existing` — Test 9) → chọn mẫu minh bạch:
  1. Tất cả RULE + CONCLUSION (quan trọng — PHẦN III 3.2),
  2. Cặp có quan hệ CONTRADICTS/REFINES (liên quan),
  3. Cặp token-overlap cao nhất (trùng tiềm năng, `_tokens` + `_jaccard` V9),
  4. Đổ thêm EXTRACTED mới nhất đến đủ cap.
  Ghi `selection_reasons` cho TỪNG bản ghi; phần chưa chọn KHÔNG được coi đã kiểm tra (trả `sampled=false`).
- `analyze()` CHỈ ĐỌC: Nhóm 1 = KU detail + related + derived (get_unit V9); Nhóm 2 = findings (duplicate jaccard≥0.6, contradiction polarity/antonym, stale valid_until, missing relation cùng subject); Nhóm 3 = `LogicalReasoningEngine.answer_question` cho mỗi chủ đề chính → inference records (`INSUFFICIENT_EVIDENCE` khi thiếu); Nhóm 4 = questions từ findings + rules mơ hồ. Không INSERT vào bảng tri thức.
- `respond(target_type, target_id, response_kind, text)`: 9 loại (CLARIFY/ADD_FACT/CORRECT/CONFIRM_RELATION/CONFIRM_INFERENCE/REJECT_INFERENCE/LIMIT_SCOPE/MORE_REVIEW/NO_DECISION) — liên kết đúng question/finding theo ID (Test 5), không đoán văn bản tự do. `NO_DECISION` → giữ chờ (Test 8).
- `build_change(target_id, ...)`: tạo `review_changes` PENDING với before_json snapshot — chưa ghi vào tri thức.
- `preview_change(change_id)`: trả before/after + scope + impact (PHẦN V.4 — bắt buộc với thay đổi quan trọng).
- `confirm_and_apply(change_id)`: chỉ nhận khi `confirm_state=PREVIEWED` → áp:
  `CORRECT/CLARIFY` → `supersede_unit` V9 (version+1, SUPERSEDES giữ lịch sử); `CONFIRM_*` → nâng status CANDIDATE→(không vượt VERIFIED khi chưa có bằng chứng xác minh thật — ghi verification_method rõ); `REJECT_INFERENCE` → đánh dấu inference REJECTED. Sau khi ghi: after_json + result + đổi session WAITING_OWNER↔… (Test 6, 7).
- `undo(change_id)`: từ undo_json (supersede ngược: tạo KU v+2 derived_from v+1 khôi phục nội dung cũ — không DELETE).
- `close()`: COMPLETED + stats.
- Idempotency + chống vòng lặp: mỗi (session, target, kind) 1 response; session mở duy nhất.

## 3. API server.py (+5, localhost-only)
- POST `/api/memory/review/start` `{limit?}` → session + stats (gọi analyze ngay).
- GET `/api/memory/review/session?id=` → 4 nhóm + findings/inferences/questions/changes + sources (Test 2, 13).
- POST `/api/memory/review/respond` `{session_id, target_type, target_id, response_kind, text}`.
- POST `/api/memory/review/confirm` `{session_id, change_id, action: preview|confirm|cancel|undo}`.
- POST `/api/memory/review/close` `{session_id}`.
- Route `SÀNG LỌC` trong `_handle_api_chat` (exact match, strip) → gọi start + trả payload JSON review thay vì LLM.

## 4. UI trong tab 🧠 (không tạo trang demo riêng)
- Nút `+ SÀNG LỌC TRÍ NHỚ` + badge trạng thái 8 giá trị (màu: ANALYZING vàng, REVIEW_READY/WAITING_OWNER cam nhấp nháy, COMPLETED xanh, FAILED đỏ).
- Panel: mã đợt + 10 số liệu (§5.2) + 4 khu (tri thức / quan hệ & mâu thuẫn / suy luận & bằng chứng / câu hỏi) với nút mở chi tiết + xem nguồn (episode ref) + phản hồi 9 loại (dropdown) từng mục.
- Thay đổi quan trọng: dialog before→after + phạm vi + tác động, nút "Xác nhận áp" / "Huỷ".
- Badge câu hỏi chờ cập nhật theo session.

## 5. Tests `tests/test_v10_memory_review.py` — 13 test §IX
Cấu hình tmp_path DB + seed dữ liệu có kiểm soát; mock thời gian khi cần. Danh sách: session khởi tạo · 4 nhóm đủ · truy nguồn · chỉ-đọc (so sánh snapshot knowledge_units trước/sau) · response đúng ID · đúng phạm vi · before/after · NO_DECISION giữ chờ · chống lặp session · phục hồi (bỏ qua session FAILED, start lại được) · cap mẫu · integrity trước=sau · số liệu API khớp.

## 6. Báo cáo (PHẦN XI): 7 file V10_* cập nhật theo từng slice; trạng thái DESIGNED/IMPLEMENTED/TESTED/LIVE_VERIFIED/BLOCKED phân biệt rõ.

## 7. Không làm (PHẦN VIII)
Không auto full-DB review; không auto-merge; không auto-delete; không nâng hàng loạt VERIFIED; không suy luận→quy tắc tự động; không đa session; không mở rộng khi chưa chủ xác nhận quy trình mẫu (điều kiện 9 mục §8.1).
