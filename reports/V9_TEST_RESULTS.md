# V9 — TEST RESULTS
**Ngày:** 28/10/2026 · Sprint V9 Deep Cognitive Memory & Logical Knowledge Governance

## 1. Unit + Integration tests (pytest, tmp_path 100%)

| Suite | Số test | Kết quả | Map §XIII |
|---|---|---|---|
| tests/test_v9_deep_memory.py | 16 | **16/16 PASS** | A, B, G, I, K + redaction + checkpoint CRUD + junk report |
| tests/test_v9_logical_reasoning.py | 12 | **12/12 PASS** | D, J, K + chống vòng tròn §V.3 + mâu thuẫn §V.4 |
| tests/test_v9_memory_review_cycle.py | 8 | **8/8 PASS** | E, C, G, H + batch limit §XII.7 |
| tests/test_v9_owner_feedback.py | 8 | **8/8 PASS** | F, L + §IX.7-8 + idempotency audit |
| **Tổng V9** | **44** | **44/44 PASS** (2.3s) | |

Chi tiết tiêu chí 12 test A–L:
- **A** Trích xuất: `_classify` phân biệt QUESTION/FACT/RULE/OPINION đúng tiếng Việt (dấu "?" normalize, marker "tôi nghĩ/có lẽ/luôn/phải"). ✅
- **B** Liên kết: mọi quan hệ đều có `basis`; token-overlap → `is_speculative=1`; chống double-link đối xứng; cách ly scope. ✅
- **C** Mâu thuẫn: cùng subject + polarity ngược → CONTRADICTS, cả hai phía mark CONFLICTED + confidence hạ; **không tự chọn phía** (`auto_resolution=None`). ✅
- **D** Suy luận: kết luận B lưu evidence_refs + steps + confidence_breakdown; INFERRED không bao giờ đủ điều kiện loại A. ✅
- **E** Owner review: câu hỏi đủ A–G (problem/evidence/current_view/interpretations ≥2/question?/impact/scope_hint); CONTEXT_DIFFERENCE (khác scope) không hỏi. ✅
- **F** Feedback: SUPERSEDES giữ lịch sử — KU cũ SUPERSEDED (không xoá), KU mới derived_from cũ + version 2; câu hỏi đóng ANSWERED. ✅
- **G** Chống vòng lặp: extract lần 2 = 0 units mới; owner question không hỏi lại OPEN; exchange log UNIQUE. ✅
- **H** Khôi phục: gián đoạn giữa stage → resume từ checkpoint đúng, stages_completed đủ 10. ✅
- **I** Không mất dữ liệu: bảng cũ giữ nguyên count + schema sau migration additive. ✅
- **J** Truy xuất nhiệm vụ mới: engine truy KU theo token overlap + subject-head; câu hỏi không liên quan → C + missing_info. ✅
- **K** Truy vết: trace về được episode nguồn; ref chưa phân giải được ghi nhận `unresolved_refs` (không mất dấu). ✅
- **L** Bảo vệ quyền hạn: `production_approved=False` luôn; module feedback không đụng approval_cards (bảng không tồn tại trong test DB). ✅

## 2. Regression toàn bộ (sau khi ghép V9)

Baseline trước sprint: **1109 passed, 1 skipped** (proc_d1dfdad1cbd4, 91.80s).
Kết quả sau V9: **1153 passed, 1 skipped** (proc_c0ecff50a316, 83.00s) = 1109 cũ + 44 test V9 mới, **0 test nào vỡ**. 1 skip duy nhất = test Pi5 phần cứng (điều kiện thường, không liên quan V9).

## 3. Live smoke trên brain.db THẬT (sau backup 89.4MB)

Server test instance riêng port 8799 (không đụng PID 8216 production):
| Bước | Kết quả |
|---|---|
| GET /api/memory/deep/stats | HTTP 200 — 0 units (chưa extract), **50 junk candidates** phát hiện trong semantic_memory |
| POST /api/memory/deep/extract (limit 40) | **148 units từ 40 chat_turn thật** (83 FACT, 60 QUESTION, 4 RULE, 1 OPINION), scope đúng theo session |
| POST /api/memory/deep/review (batch 20) | run_e284a6c4afcd COMPLETED đủ 10 stage — **208 quan hệ** (173 RELATED_TO, 35 REFINES), 0 mâu thuẫn tự chọn, 0 câu hỏi khi chưa có căn cứ |
| GET /units | Dữ liệu thật: "Anh Quân — Quanpt1, chủ sở hữu của em." (9 quan hệ), câu hỏi, conf 0.75 |
| GET /questions?status=OPEN | 0 câu hỏi — đúng (chưa có mâu thuẫn cùng scope trong dữ liệu thật) |
| GET /timeline | 16 sự kiện thật (runs + KU updates) |
| POST /answer q_fake | HTTP 400 "question not found" — validation đúng |
| Extract lần 2 (idempotency thật) | **0 units mới, 40/40 skipped_already_logged** ✅ |

## 4. Bug tìm thấy trong live smoke + đã sửa
- `do_GET` truyền `parsed_query` (biến không tồn tại) → sửa `parsed.query` — bắt được nhờ live test, không có trong unit test (unit test không qua HTTP layer). Đã AST check + restart + verify lại toàn bộ API.

## 5. Vai trò từng thành phần
- Extraction deterministic (không LLM) — mọi unit kiểm chứng được về episode nguồn.
- Relations có basis — speculative được đánh dấu vàng trên UI.
- Reasoning A/B/C — INFERRED ≠ VERIFIED được bảo đảm ở code path `_decide`.
- Review cycle 10 stage + checkpoint — batch limit chống xử lý vô hạn.
- Owner feedback — SUPERSEDES + audit trail, không đụng R0–R5.
