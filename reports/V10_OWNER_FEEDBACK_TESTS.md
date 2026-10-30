# V10 — OWNER FEEDBACK TESTS
**Ngày:** 28/10/2026 · Map 13 test §IX MASTER PROMPT V10 → kết quả thật

## A. Unit/Integration — `tests/test_v10_memory_review.py` (16/16 PASS)
| # | Test §IX | Test name | Kết quả |
|---|---|---|---|
| 1 | Khởi tạo đợt sàng lọc | `test_start_creates_unique_session_with_scope` | PASS — session_id `rev_*`, scope ≤ cap, lý do chọn từng bản ghi |
| 2 | Hiển thị bốn nhóm | `test_four_groups_present_from_real_data` | PASS — units/findings/inferences/questions đủ |
| 3 | Truy xuất nguồn | `test_sources_traceable` | PASS — source_refs + evidence_refs không rỗng |
| 4 | Không sửa trước khi xác nhận | `test_no_mutation_before_confirm` | PASS — KU/relations nguyên vẹn sau start + respond |
| 5 | Phản hồi đúng câu hỏi | `test_response_linked_to_correct_question` | PASS — ghép đúng question_id; NO_DECISION → WAITING |
| 6 | Cập nhật đúng phạm vi | `test_update_only_in_scope` | PASS — target ngoài session bị từ chối |
| 7 | Lịch sử trước–sau | `test_before_after_history_preserved` | PASS — preview before/after + supersede giữ KU cũ + undo |
| 8 | Mâu thuẫn chưa giải quyết | `test_no_decision_keeps_waiting` | PASS — không tự chọn phía |
| 9 | Chống lặp | `test_no_duplicate_sessions` | PASS — already_open, cùng session_id |
| 10 | Phục hồi lỗi | `test_recovery_after_interrupt` | PASS — close session treo → start mới OK |
| 11 | Không mở rộng ngoài phạm vi | `test_no_scope_expansion` | PASS — 45+ KU trong DB, scope vẫn ≤ 20 |
| 12 | Bảo toàn dữ liệu | `test_db_integrity_preserved` | PASS — integrity ok trước/sau |
| 13 | Giao diện khớp backend | `test_api_payload_matches_backend` | PASS — stats khớp payload; close → COMPLETED |
| + | Bổ sung | `test_close_then_new_session`, `test_unknown_response_kind_rejected`, `test_insufficient_evidence_when_no_units` | PASS |

## B. Live E2E trên brain.db thật (port 8799, sau backup)
| Bước | API | Kết quả |
|---|---|---|
| IDLE check | GET `/api/memory/review/current` | `IDLE` ✅ |
| Lệnh SÀNG LỌC | POST `/api/chat` `SÀNG LỌC` | 336ms, `rev_51dee1568d8a` REVIEW_READY, 20 units / 38 findings / 3 inferences / 32→10 questions ✅ |
| Chống lặp live | POST `/api/chat` lần 2 | `already_open: True`, cùng session_id ✅ |
| Phản hồi | POST `/api/memory/review/respond` | change `chg_17f7a8a22571` PENDING, ghép đúng question ✅ |
| Preview | POST `/api/memory/review/confirm` preview_only | before/after + requires_second_confirm ✅ |
| Confirm | POST `/api/memory/review/confirm` confirm=true | APPLIED supersede v1→v2 ✅ |
| Undo | POST `/api/memory/review/undo` | restored_as v3, chuỗi v1→v2→v3 giữ đủ lịch sử ✅ |
| Close | POST `/api/memory/review/close` | COMPLETED → IDLE ✅ |

## C. UI (IMPLEMENTED — chờ Quanpt1 bấm xác nhận LIVE)
- Nút `+ Sàng Lọc Trí Nhớ` → gọi `/api/chat` `SÀNG LỌC` (cùng quy trình lệnh)
- Panel 4 khu vực + khu thay đổi (preview/confirm/undo) — Test 2/13 render từ payload thật
- Cache-bust `executive.js?v=4.3`; JS `node --check` OK

**Kết luận:** Test 1–12 TESTED + LIVE_VERIFIED (backend). Test 13 (UI số liệu khớp backend) TESTED ở tầng payload; mức LIVE_VERIFIED hoàn tất khi Quanpt1 mở dashboard → tab 🧠 → bấm `+ Sàng Lọc Trí Nhớ`.
