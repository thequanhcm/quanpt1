# BÁO CÁO SPRINT 3 — MEMORY-ADAPTER (TASK-VMAIL-S3)

**Ngày**: 24/11/2026 · **Owner duyệt**: "duyệt" → Sprint 3 MEMORY-ADAPTER (chat 24/11)
**Vị trí trong lộ trình §17**: 1 VmailConnector ✅ → 2 Thread Analyzer ✅ → **3 MEMORY-ADAPTER ✅ (báo cáo này)** → 4 Reply Draft → 5 Workflow → 6 Dashboard

---

## 1. Mục tiêu sprint

Master prompt §6 (CHERRY VMAIL INTELLIGENCE — Memory Adapter):
- **§6.1** Bộ nhớ hiện có (các loại) — KHÔNG tạo database trí nhớ độc lập, PHẢI dùng Memory Service hiện có của QUAN AI BRAIN qua adapter.
- **§6.2** Entity linking: PROJECT/PEOPLE/TASK/DEADLINE/EMAIL.
- **§6.3** Memory Retrieval Policy: ưu tiên nguồn xác thực, đối chiếu mâu thuẫn, phân biệt sự kiện/nhận định/đề xuất, giữ nguồn truy xuất.
- **§6.4** Memory Update Policy: chỉ tạo Memory Candidate khi có giá trị dài hạn (quyết định/cam kết/deadline/thay đổi trạng thái/nhiệm vụ mới); KHÔNG lưu toàn bộ email; candidate đi qua cơ chế ghi nhớ, xác minh, phân quyền hiện có — KHÔNG tự xác minh.

## 2. Audit-trước-sửa (kết quả quyết định thiết kế)

| Thành phần hiện có | Trạng thái audit | Dùng cho S3 |
|---|---|---|
| `MemoryFacade` (memory/unified_memory.py) | LIVE: 3.107 records (3020 OBSERVED + 13 USER_PROVIDED + 72 VERIFIED) + 3.767 episodes; `search()` hoạt động | Đường ĐỌC (retrieval) |
| `QuarantineStore` (memory/quarantine_store.py, `data/quarantine.db`) | Sẵn sàng: add_knowledge/list_pending/approve/reject/expire_stale, PENDING_REVIEW + expires 30 ngày | Đường GHI (candidate) |
| `ExperienceStore` (memory/experience_store.py, `data/brain.db`) | LIVE; enum thật TASK/UNKNOWN | Lesson path |
| `LessonLearner` | Sẵn sàng (search_lessons, extract_lessons...) | Tiêu thụ experiences |

**Phát hiện quan trọng (fix kiến trúc)**: `MemoryFacade()` mặc định `quarantine=None` → `facade.add(memory_type='candidate')` rơi thẳng vào **semantic** với fact_level INFERENCE — hỏng bất biến §6.4. Adapter phải tự wire `QuarantineStore` trực tiếp và TỪ CHỐI ghi khi thiếu quarantine.

## 3. Module: `src/quan_ai_brain/office/memory_adapter.py` (~350 lines)

`CherryMemoryAdapter` — lớp mỏng, KHÔNG db mới, KHÔNG core thứ 2:

- **Retrieval (§6.1/§6.3)**: `retrieve_context`, `retrieve_email_history`, `retrieve_project_history`, `retrieve_decisions`, `retrieve_related_tasks` — tất cả qua `MemoryFacade.search`. Sort VERIFIED/FACT (tier 0) > OBSERVED (1) > INFERRED (2) > CANDIDATE/UNVERIFIED (3). **Phát hiện mâu thuẫn**: 2 hit "tin được" cùng chủ đề (token bỏ dấu tiếng Việt ≥4 ký tự) khác nội dung → trả CẢ HAI kèm nguồn, KHÔNG chọn hộ. Mỗi hit giữ `fact_level + verification + source_ref + score` để owner kiểm tra được.
- **Update (§6.4)**: `create_memory_candidate(content, source_email_id, thread_key, confidence, category_hint)`:
  - Regex `_CANDIDATE_WORTHY`: chỉ quyết định/cam kết/deadline/nhiệm vụ/thay đổi trạng thái.
  - Regex `_CANDIDATE_BANNED`: mật khẩu/token/spam → TỪ CHỐI.
  - Email thô/quá ngắn (<12 ký tự) → TỪ CHỐI ("không lưu toàn bộ email").
  - Ghi qua `QuarantineStore.add_knowledge` → `data/quarantine.db` status **PENDING_REVIEW**, metadata đầy đủ (source_email_id, thread_key, extracted_at, confidence, adapter).
  - **KHÔNG BAO GIỜ tự promote** — owner duyệt qua `QuarantineStore.approve(id)`; quarantine=None → TỪ CHỐI ghi (fail-honest, không fallback semantic).
- **extract_candidates_from_thread(analysis, max_items)**: quét buckets decisions → commitments → changes của ThreadAnalysis (S2), trích mail #id từ chuỗi nguồn vào `source_ref=email:<id>`.
- **record_followup_experience**: ExperienceStore với `OutcomeType.UNKNOWN` (chưa có kết quả thật) — dữ liệu cho LessonLearner khi có kết quả.

## 4. Wire DM

`tools/office_thread_summary_runner.py` (DM "tóm tắt luồng email <kw>"): sau `analyze_thread` từng luồng → `extract_candidates_from_thread` (max 2/luồng) → in `🧠 Đã ghi candidate [id] → quarantine R4` + tổng cuối. Exception-safe: lỗi adapter không làm hỏng tóm tắt.

## 5. Test

- `tests/test_office_memory_adapter.py` (MỚI): **24/24 PASS** — mock 100% (không đụng db thật). Phủ: sort tier §6.3, mâu thuẫn có/không, fail-honest facade/quarantine, worthy/banned/short/plain candidate, bất biến không-tự-promote (không có method promote/approve), extract 3 buckets + max_items + mail #id, lesson UNKNOWN + degraded, singleton.
- Focused regression: **98/98 PASS** (24 adapter + 19 thread_analyzer + 42 vmail_connector + 13 vmail_tool).

## 6. Live E2E (máy thật)

| Bước | Kết quả |
|---|---|
| Retrieval "battery" | 3 hits OBSERVED từ memory thật (netchat_auto_responder...) |
| Candidate "Phòng AI chốt hạn nộp báo cáo tuần trước thứ Sáu 25/11" | → quarantine.db **PENDING_REVIEW**, id `43ee2f5c…`, source_ref `email:LIVE_S3_SMOKE`, expires 2026-12-23 |
| Verify `list_pending` | Tìm thấy đúng 1 item ✓ |
| Candidate email thô ("Chào anh, em gửi báo cáo...") | TỪ CHỐI đúng chính sách ✓ |
| Dọn smoke | Xóa record smoke khỏi quarantine + 2 record INFERENCE rác trong brain.db (lúc test facade-quarantine-None) → sạch |
| Runner DM --latest + "khói" | exit 0, tóm tắt đầy đủ, không crash với adapter live |

## 7. Trung thực — giới hạn hiện tại

1. Luồng thật đang có ("Khói...CHÁY" 7 mail) **không tạo candidate nào**: 4 changes là yêu cầu hành động (điều chuyển vật tư) không phải quyết định/cam kết tường minh → đúng chính sách nghiêm ngặt §6.4 (không lưu thì không sai; lưu sai mới nguy hiểm).
2. `MemoryFacade.search` đang chạy đường keyword/in-memory (BGE offline theo quyết định owner 18/11; semantic ONNX MiniLM là hệ riêng `data/vector_db_semantic`) — adapter dùng đúng service hiện có, không tự nâng cấp.
3. Chưa có lệnh DM riêng "duyệt candidate" — owner duyệt qua `QuarantineStore.approve(id, reviewed_by, notes)` khi cần; sẽ wire DM nếu anh yêu cầu.
4. Entity linking §6.2 dạng heuristic (mail #id, thread_key, category) — chưa có entity graph riêng (chỉ xây khi sprint nghiệp vụ cần).
5. Trạng thái: **TESTED + LIVE_E2E (một luồng thật, không candidate phát sinh)** — không tuyên bố PRODUCTION_VERIFIED.

## 8. Files thay đổi

| File | Loại |
|---|---|
| `src/quan_ai_brain/office/memory_adapter.py` | MỚI ~350 lines |
| `tests/test_office_memory_adapter.py` | MỚI 24 test |
| `tools/office_thread_summary_runner.py` | PATCH wire S3 |
| `docs/PROJECT_STATUS.md` | APPEND S3 |

## 9. Kế tiếp

Sprint 4 REPLY-DRAFT (§17) — chờ owner duyệt.
