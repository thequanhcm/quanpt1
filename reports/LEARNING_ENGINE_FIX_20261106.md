# KẾT NỐI ĐỘNG CƠ TỰ HỌC (PHASE F) — FIX LỖI CHU KỲ 500 (06/11/2026)

## Bối cảnh
Owner bấm "⚡ Chạy Một Chu Kỳ Tự Học Mẫu" trên tab Động Cơ Tự Học (8765) → lỗi:
`Learning cycle error: TaskOutcome.__init__() missing 1 required positional
argument: 'request_id'`. Owner yêu cầu "kết nối phần này để xây dựng năng lực
tự học cho cherry".

## Root cause (2 lỗi trong `_handle_api_learning`, server.py)
1. `TaskOutcome(...)` thiếu `request_id` (bắt buộc theo contract/models.py).
2. `engine.create_upgrade_proposal(...)` gọi với kwargs cũ không tồn tại
   (pros/cons/risk_assessment/files_to_modify/new_candidate_ids) — lệch signature
   17 điểm chuẩn trong learning/engine.py (đúng chuẩn: new_knowledge_refs,
   expected_benefits, advantages, disadvantages_and_risks, impact_scope,
   test_results, security_evaluation, compatibility_assessment, measured_metrics,
   rollback_plan, recommendation, confidence_score, uncertainties).
   Lỗi 1 xảy ra trước nên lỗi 2 chưa lộ — sửa xong lỗi 1 sẽ gặp lỗi 2 ngay.
   (Đối chiếu reference implementation chuẩn trong periodic_reporter.py.)

## Fix (smallest safe — chỉ sửa handler, không đổi contract)
- Thêm `request_id=f"req_{uuid4.hex}"`.
- Gọi lại `create_upgrade_proposal` đúng 17 điểm, map nội dung cũ vào đúng chỗ;
  `new_knowledge_refs=[research:{id}, cand_rec.id]` (MemoryRecord.id — không phải
  memory_id như code cũ).

## E2E thật sau fix (23:23)
- POST /api/learning → 200 success.
- Gap: `gap_4f7714b5` (repeated_error — Ollama unreachable simulated).
- Dossier: `res_1f1d8e74`, 3 nguồn có kiểm (System Baseline, Local LLM Client,
  Python StdLib), confidence 0.88.
- Candidate: `14014b15…` status CANDIDATE vào learning_sandbox.db (quarantined).
- Proposal: `prop_8c12c2e4`, status=proposed, recommendation=apply, chờ owner.
- Audit log 4 event mới: learning_gap_detected → research_dossier_created →
  candidate_knowledge_quarantined → upgrade_proposal_created.
- Tests: 273/273 PASS (6 dàn learning + web_server).

## KẾT NỐI VỚI CÁC NGUỒN TỰ HỌC HIỆN CÓ (đúng kiến trúc, chờ owner duyệt mới chạy)
1. Speech corpus (hôm nay): 516 câu hội thoại Vosk → candidate_knowledge
   (brain.db, quarantined) — nguồn văn phong.
2. Learning daemon 5': 5.868 facts/cycle → quarantine 4.793 (brain.db).
3. Phase F engine: gap → research → quarantine → proposal 17 điểm
   (learning_sandbox.db) — nguồn nâng cấp code.
→ 3 luồng CÙNG mẫu hình an toàn: tự học → quarantine → owner duyệt mới có hiệu
lực (Learning is not deployment; V3 governance; R4 riêng cho apply code).

## Đề xuất bước tiếp theo (chờ duyệt)
A. Đưa SpeechQA/voice style vào Phase F: gap "văn phong thiếu tự nhiên" →
   research từ speech corpus → proposal few-shot prompt (nhưng vẫn quarantine).
B. UI: hiển thị số candidate + proposal đang chờ ngay trên tab Động Cơ Tự Học.
C. Định kỳ: learning daemon đã chạy 5'/cycle — bổ sung event Phase F khi phát
   hiện gap thật (không còn simulated) qua periodic_reporter.
