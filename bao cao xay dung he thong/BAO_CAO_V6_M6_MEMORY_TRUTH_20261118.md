# BÁO CÁO SPRINT MEMORY-TRUTH (P1 + P4) — TASK-MEMORY-TRUTH-M6

**Ngày:** 18/11/2026 | **Card:** TASK-MEMORY-TRUTH-M6 APPROVED + consumed (auth: owner_desktop_chat_directive)
**Owner directive:** "duyệt sprint kế Sprint MEMORY-TRUTH (P1+P4, ~2 sprint nhỏ). merge PR #35 + consume card TASK-SEMANTIC-MEMORY-M6. M6 → chọn (c) duyệt sprint Self-RAG lite + eval trí nhớ em đề xuất từ phân tích vivi-agent"
**Nguồn cảm hứng:** vivi-agent-20261118.zip (selfcheck.py, run_eval.py, hybrid BM25+vector, parent-child chunking, confirm chống injection)

## Tiền đề đã hoàn thành ngay đầu sprint
- **PR #35 MERGED** — merge commit `998517a` trên master (qua GitHub API, git credential fill [REDACTED]).
- **Card TASK-SEMANTIC-MEMORY-M6 consumed** — approval `f8a27d37`, consumed=1 trong governance.db.
- Card mới **TASK-MEMORY-TRUTH-M6** tạo → APPROVED → consumed (duyệt để làm theo chat directive).
- Branch `feat/v6-m6-memory-truth` từ master.

## P1 — Self-RAG lite (`cognition/self_check.py` MỚI, 208 LOC)

Cơ chế (mô phỏng selfcheck.py của vivi-agent, thu gọn cho Cherry):
1. **Chỉ kích hoạt khi câu trả lời có EVIDENCE** (memory_recall block / system_instructions chứa semantic + ttns block). Câu greeting/điều khiển (`chào|mở|đóng|bật|tắt|phát|chụp ảnh…`) **bypass** — không đắt thêm thời gian.
2. **Grader** (GLM-Flash, temp=0, timeout 8s): liệt kê ý KHÔNG có căn cứ, trả JSON strict `{"du_can_cu": bool, "y_khong_co_can_cu": [...]}`.
3. **Repair 1 lần**: viết lại bằng cách **CHỈ XÓA/RÚT GỌN** ý sai — CẤM thêm ý mới. Guard cứng `apply_removal_only_repair`: revised dài hơn 115%+40 ký tự hoặc rỗng → **từ chối trung thực** (REFUSAL_TEXT).
4. **Fail-open tuyệt đối**: LLM lỗi/timeout/JSON hỏng → giữ nguyên câu gốc + ghi warning, không bao giờ làm hỏng đường chat chính.
5. Metadata trả về client: `"self_check": {attempted, ran, revised, claims, error}` + audit `self_check.done/error`.

Wire: `web/server.py` bước 3.9 ngay sau OutputGuardrails, trước persistence; +1 field JSON response.

## P4 — Eval trí nhớ định lượng (`tools/memory_eval.py` MỚI, 180 LOC)

- CSV câu hỏi `data/memory_eval_questions.csv` (8 câu lấy từ hội thoại thật brain.db, owner sửa được) — định dạng `query,answer_must_contain1,…`, biến thể phân tách `|`.
- **HYBRID retrieval** (kỹ thuật vivi-agent BM25+vector): semantic ChromaDB ONNX MiniLM + keyword LIKE (token ≥4 ký tự) trên brain.db mode=ro → hợp nhất kết quả.
- Đo **recall@3** + thời gian trung bình → `data/memory_eval_report.md` + `--json` cho CI.

## Số đo thật (fail-honest)

| Chỉ số | Semantic thuần (trước) | HYBRID (sau) |
|---|---|---|
| recall@3 (8 câu) | 0.625 (5/8) | **1.0 (8/8)** |
| Thời gian TB/câu | 261.6 ms | 234.2 ms |

**Bằng chứng MiniLM miss mà hybrid cứu** (audit thật): câu "anh từng dạy em điều gì quan trọng nhất?" — đúng 10 doc chứa "ngắn gọn" trong collection nhưng semantic query trả 3 episode không liên quan (d=0.77); kênh keyword LIKE ép vào → recall. Đây là lập luận định lượng cho sprint sau: cân nhắc BM25 thật (lexical.py) thay LIKE.

**Ingest bổ sung:** +521 chunks mới (18/11) → collection `semantic_memory_v1` = **6578 chunks** (idempotent: skipped_existing=6057).

## Test & nghiệm thu

| Nhóm | Kết quả |
|---|---|
| `tests/test_self_check.py` (MỚI, 15 test — mock LLM 100%) | **15/15 PASS** |
| memory_recall + semantic (focused) | 17/17 PASS |
| Live E2E self-check sửa ý bịa ("anh dặn giọng nói") | ✅ grader bắt 3 ý không căn cứ → refusal trung thực |
| Live E2E câu có căn cứ ("nguyên tắc trả lời") | ✅ giữ nguyên (không sửa oan), 3.1s |
| Live E2E greeting | ✅ bypass (ran=False), 2.8s |
| Live E2E câu evidence đầy đủ (pi5) | ✅ ran=True revised=False (đúng, không đụng), 5.0s |
| Live E2E injection | ✅ input_shield BLOCK không bị self-check phá, 0.03s |
| Focused regression (memory_recall + semantic + web_server + cognitive_loop) | 38 passed / 3 failed — **3 fail TRÙNG CHÍNH XÁC danh sách 11 PRE-EXISTING** (đã stash-proof + 4 run độc lập cùng kết quả) |

## Deliverables
1. `src/quan_ai_brain/cognition/self_check.py` — MỚI 208 LOC
2. `tools/memory_eval.py` — MỚI ~180 LOC CLI (report md + --json)
3. `data/memory_eval_questions.csv` — 8 câu eval thật (owner sửa được)
4. `tests/test_self_check.py` — MỚI 15 test
5. `src/quan_ai_brain/web/server.py` — +41 dòng (bước 3.9 + field response)
6. `data/memory_eval_report.md` — report số đo (data/, không commit)

## Limitations (trung thực — chưa làm)
- Grader + repair tốn thêm 1-2 LLM call (~0.3-1s) chỉ trên câu evidence-based; greeting/điều khiển không tốn gì.
- Evidence cho grader = nguyên system_instructions (gồm grounding block) — có thể hiểu rộng hơn evidence thuần; bù lại guard xóa-only chặn bịa thêm.
- Self-check chưa wire vào streaming `/api/chat/stream` (chỉ non-stream); DM responder chưa wire (sprint sau nếu owner duyệt).
- Chưa có BM25 thật (lexical.py) — đang dùng LIKE; chưa có synonyms YAML; chưa parent-child chunking (3 kỹ thuật vivi còn lại, chờ duyệt).
- Eval 8 câu là bộ nhỏ làm bằng chứng cơ chế; mở rộng bộ câu là việc owner thêm vào CSV.
- 11 pre-existing fail regression không đổi (đã chứng minh stash + 4 run).
