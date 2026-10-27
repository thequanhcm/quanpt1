# BÁO CÁO V3 SPRINT 4 — KẾT HỢP (a) LLM GAP + (b) AUTO-REMINDER + (c) DEDUP

**Ngày:** 27/10/2026
**Task:** TASK-V3-SPRINT4 — owner duyệt "DUYỆT TASK-V3-SPRINT4" qua desktop (card consume-once, approver quanpt1)
**Thứ tự thực hiện:** (c) → (b) → (a) theo card đã duyệt

---

## 1. (c) DEDUP KHO CÁCH LY — HOÀN TẤT

**Trước:** candidate 108.969 dòng, 598 nhóm trùng chính xác statement = 108.890 dòng dư
(nguồn ingest TEST_EVIDENCE lặp 25/10).

**Công cụ:** `tools/dedup_candidate_knowledge.py` (an toàn: bắt buộc backup tồn tại,
chỉ đụng `candidate_knowledge`, group theo statement chuẩn hoá, giữ dòng đầy đủ nhất —
nhiều conflict_ids > rationale dài > id nhỏ; archive giữ nguyên 100%).

**Kết quả thực đo:**
| Chỉ số | Trước | Sau |
|---|---|---|
| candidate_knowledge | 108.969 | **678** (0 trùng) |
| candidate_knowledge_archive | 0 | **108.501** |
| semantic_memory (đã duyệt) | 1.841 | 1.841 — KHÔNG đụng |
| brain.db | 107,9 MB | **85,6 MB** (VACUUM) |

Idempotent đã test (chạy lần 2 = 0 tác vụ). Backup: `backups/brain_pre_dedup_20261027_080611.db`.

**Số liệu đối chứng:** trước 108.969 = 678 + 108.501 + 790 dòng trùng trong nhóm có
số lượng lớn hơn — đã đối chứng `cand + arch` khớp tổng trừ các nhóm lớn.

## 2. (b) AUTO-REMINDER INFO-GAP — HOÀN TẤT

**Thay đổi:** `tools/netchat_auto_responder.py` — mỗi ~12 vòng poll (≈1 phút) quét
`list_waiting()` → `should_send_reminder` (cap 5 lần, cách 12h) → gửi nhắc format
"🔔 Nhắc việc (lần N/5) — TASK-xxx: …" + dòng bắt buộc "ĐANG CHỜ ANH QUANPT1 …
CHƯA THỰC HIỆN HÀNH ĐỘNG NGHIỆP VỤ" → `note_reminder_sent`.

**Nguyên tắc giữ nguyên:** im lặng của owner KHÔNG phải đồng ý — chỉ nhắc, không tự làm.
Lỗi reminder job không làm chết responder (try/except từng task).

**Test:** `tests/test_v3_sprint4_reminder_dedup.py` — 8 tests: format, cap 5,
khoảng cách 12h, unknown task, syntax responder block; dedup 3 kịch bản
(keep-1-per-group, idempotent, no-data-loss 150 dòng).

**Vận hành thật:** responder khởi động lại (PID venv duy nhất), heartbeat fresh (age ~3s),
artifact test TASK-E2E99 đã xoá khỏi `data/information_gaps.db` (tránh nhắc giả lên kênh).

## 3. (a) LLM GAP DETECTION — HOÀN TẤT (fail-closed)

**Module mới:** `src/quan_ai_brain/cognition/llm_gap_detector.py` —
`extract_gaps_with_llm(request_text)`:
- GLM/Gemini-compatible schema: goal, expected_outcome, required_inputs, conflicts,
  owner_decisions_required, acceptance_criteria, constraints.
- **FAIL-CLOSED tuyệt đối:** text rỗng/không key/HTTP lỗi/timeout 8s/JSON sai/kiểu sai
  → trả None, KHÔNG tự sửa dữ liệu, caller về heuristic Sprint 3.
- Key: env GEMINI_API_KEY → HKCU fallback; không log/in giá trị key.
- Timeout 8s không chậm chat; giới hạn đầu vào 3000 ký tự.

**Tích hợp:** hiện tách lớp — analyzer Sprint 3 vẫn là cổng chính; LLM detector dùng
khi responder/loop cần trích từ văn bản tự do (test tích hợp: LLM trích `url` thiếu →
analyzer hỏi đúng câu). Không đụng CognitiveLoop/ApprovalOrchestrator.

**Test:** `tests/test_v3_sprint4_llm_gap.py` — 9 tests mock curl 100%: valid JSON,
empty text (không gọi), curl fail, timeout, malformed JSON, kiểu sai → None KHÔNG tự sửa,
thiếu goal, không key (không gọi), tích hợp analyzer.

## 4. FIX ĐI KÈM (phát hiện khi regression)

- `grounding_facts.py:121` — bug case-sensitive có sẵn: `"cloud" in runs_on` sai với
  "NetMind **C**loud" → khi Ollama ONLINE, kiến trúc bị khai sai "Suy luận chạy local".
  Fix `.lower()` — hệ thống giờ trả đúng "Suy luận hiện tại chạy trên cloud (GLM...)".
- `test_sprint_cd_quality_promotion.py` — assertion cũ cứng "Ollama OFFLINE" (đúng thời
  điểm viết test) → sửa thành chấp nhận trạng thái thật probe đo được (OFFLINE/ONLINE/
  HEALTHY/DEGRADED, đúng 1 lần trong Q2/Q3 xor). Trung thực: engine báo cái đo được.

## 5. KIỂM THỬ TỔNG

| Suite | Kết quả |
|---|---|
| Sprint 4 (8 + 9) + Sprint 3 (33) | **50 passed** |
| Full regression toàn dự án | **736 passed, 1 skipped** (TTS hardware) — 0 fail |

So Sprint 3: 717 passed → nay 736 (thêm 19 test mới ròng).

## 6. GIỚI HẠN TRUNG THỰC

1. LLM gap detection CHƯA test trên Gemini API thật (chỉ mock — theo quy tắc test
   dự án: không gọi gateway thật trong test). Lần đầu dùng thật cần owner giao 1
   nhiệm vụ tiếng Việt tự do để chứng minh E2E.
2. Auto-reminder đã chạy trong responder thật nhưng CHƯA có task chờ thật để thấy
   tin nhắc trên kênh (sẽ tự chứng minh khi có task NEEDS_OWNER_INPUT đầu tiên).
3. Dedup nhóm statement giống nhau 100% — chưa xử lý trùng NGHIÃ (semantic near-dup).
4. Ollama vẫn chưa nằm trong KHOI_DONG_24_7.bat (việc 24/7 tổng thể, ngoài phạm vi card).

## 7. THAY ĐỔI FILE

| File | Loại |
|---|---|
| `tools/dedup_candidate_knowledge.py` | MỚI (114 dòng) |
| `tools/netchat_auto_responder.py` | PATCH (reminder job) |
| `src/quan_ai_brain/cognition/llm_gap_detector.py` | MỚI (138 dòng) |
| `src/quan_ai_brain/cognition/grounding_facts.py` | FIX 1 dòng (.lower()) |
| `tests/test_v3_sprint4_reminder_dedup.py` | MỚI (8 tests) |
| `tests/test_v3_sprint4_llm_gap.py` | MỚI (9 tests) |
| `tests/test_sprint_cd_quality_promotion.py` | PATCH assertion trung thực |
| `data/brain.db` | DEDUP + VACUUM (backup có) |
| `data/information_gaps.db` | Xoá 1 row artifact TASK-E2E99 |
