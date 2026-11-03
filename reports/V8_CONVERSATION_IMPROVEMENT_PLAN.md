# V8 — CONVERSATION IMPROVEMENT PLAN
**Ngày:** 27/10/2026 · Dựa trên V8_VIETNAMESE_CONVERSATION_AUDIT + V8_DIALOGUE_PIPELINE_MAP
**Nguyên tắc:** Reuse trước khi tạo — sửa parity trước, thêm lớp mới sau; mọi cải tiến phải đo được bằng benchmark trước/sau.

## P1 — PARITY FIX (BUG-V8-1/2 — ưu tiên CAO NHẤT, hiệu quả/giá trị cao nhất)
Nâng stream path lên ngang /api/chat:
1. `detect_teaching` + `persist_taught_memory` vào stream handler (trước generation, giữ pattern non-blocking + teach_note như 1164-1187/1526-1527).
2. `collect_grounding_facts` (BỘ SỰ THẬT SỐNG) vào stream (pattern 1211-1218).
3. TTNS lookup + Document RAG vào stream (pattern 1254-1303).
4. Kiểm chứng: stream + non-stream cùng 1 query → cùng evidence blocks trong context.

## P2 — CONVERSATION GUIDANCE LAYER (§3.1/3.2/3.3/5.x)
Module mới `cognition/vietnamese_conversation.py` (stdlib-only):
- `classify_request(query)` → 7 loại: QUESTION_SHORT, WORK_CHAT, TECH_ANALYSIS, DOC_REQUEST, VOICE_CHAT, URGENT, AMBIGUOUS.
- `build_guidance_block(cls)` → block tiếng Việt ngắn ghép vào system_instructions (không đụng nội dung LLM tự viết): quy tắc độ dài (2-5 câu ngắn / có cấu trúc khi cần), xưng Em-gọi-Anh, không lặp yêu cầu, không mở đầu rập khuôn ("Chắc chắn rồi"...), giữ nguyên mã kỹ thuật, nói "chưa đủ dữ liệu" khi thiếu căn cứ.
- `detect_context_dependent(query)` → flag câu ngắn kiểu "làm tiếp đi", "sửa phần đó" → guidance ép dùng [RECENT CONVERSATION HISTORY] làm đối tượng, KHÔNG đoán khi mơ hồ nhiều khả năng.
- Wire vào PromptContextBuilder.build() — chỉ khi query có dấu hiệu tiếng Việt, flag bật/tắt được, backward-compat (mặc định ON cho cả 2 luồng chat qua cùng builder).

## P3 — INPUT NORMALIZATION (BUG-V8-4)
`normalize_vietnamese_input(query)` trong cùng module: bỏ qua-điều-kiện lịch sự trùng lặp, trim filler ("ơi ơi", "à ơi"), KHÔNG đụng tên riêng/mã (giữ nguyên token). Không "sửa dấu" tự đoán — chỉ làm sạch an toàn.

## P4 — SESSION HISTORY DEPTH (BUG-V8-3)
- Nâng history cho chat streams: limit 3→6 (stream + non-stream), verifiable qua test cấu trúc context.
- (Candidate, không commit trong P1-P4 nếu thiếu bằng chứng.) compact history: cắt reply >500 ký tự trong history block để giữ ngữ cảnh dài hơn trong budget.

## P5 — VOICE OUTPUT TTS LAYER (§6.2 — chỉ phần đã tồn tại)
Nâng `sanitize_for_spoken_vietnamese` (voice_pipeline.py):
- Từ điển đọc mã: R0-R5, TASK-xxx, 8766, URL, đơn vị (GB, %, ms) → dạng đọc tự nhiên, KHÔNG đổi nội dung.
- Cắt theo câu (không cắt giữa câu như hiện tại).
- Voice guidance block riêng: câu ngắn ≤2 câu/đoạn khi classify=VOICE_CHAT.

## P6 — BENCHMARK (§VIII) — bằng chứng trước/sau
`tests/test_v8_vietnamese_benchmark.py`: ≥40 case 5 nhóm A-E, tiêu chí khách quan:
- A (tiếng Việt tự nhiên): không mở đầu rập khuôn, độ dài theo loại, giữ mã kỹ thuật.
- B (đa lượt): context guidance xuất hiện khi query phụ thuộc; history depth đủ.
- C (công việc): evidence blocks được inject đúng loại query (TTNS/RAG/external gate).
- D (voice): sanitize output đúng từ điển đọc, không cắt giữa câu.
- E (độ tin cậy): fail-honest cues trong guidance; guardrails còn hoạt động.
Baseline chạy TRƯỚC khi wire P1-P5 (đo hiện trạng), sau đó chạy lại → V8_BASELINE_RESULTS.md + V8_REGRESSION_RESULTS.md.

## P7 — REPORTS
V8_IMPLEMENTATION_REPORT + V8_VIETNAMESE_BENCHMARK + V8_REGRESSION_RESULTS + V8_FINAL_HANDOFF; phân loại DESIGNED/IMPLEMENTED/TESTED/LIVE_VERIFIED/BLOCKED trung thực.

## KHÔNG LÀM (ngoài phạm vi / blocked)
- Không thay LLM (GLM-5.3-Flash giữ nguyên — audit cho thấy bottleneck không ở model).
- Không tích hợp ASR offline (Whisper/Vosk) — cần thiết kế riêng + chủ duyệt (thêm dependency).
- Không sửa `XiaoZhiVoicePipeline` thành LLM path (voice/interact đi role router là thiết kế riêng của Pi edge; parity chỉ áp cho 2 luồng chat chính).
- Không tự học/nhớ toàn bộ hội thoại (§IX — chỉ guidance tĩnh + benchmark data ẩn danh).
- Không đụng governance/approval/permission (giữ nguyên toàn bộ).

## Thứ tự thực thi
P6 baseline trước → P1 → P2+P3 → P4 → P5 → P6 after → regression ×2 → live smoke → P7 reports.
