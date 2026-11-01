# V9 — DEEP MEMORY ACTUAL STATE AUDIT
**Ngày:** 28/10/2026 · Audit trên dữ liệu THẬT + mã nguồn thật, trước mọi thay đổi (PHẦN II MASTER PROMPT V9)

## 1. Bức tranh DB

| DB | Kích thước | Nội dung thật |
|---|---|---|
| **data/brain.db** | 89.3 MB | **CANONICAL** — toàn bộ dữ liệu sống ở đây |
| data/memory.db | 0.1 MB | Vỏ rỗng (4 bảng, 0 rows) — schema trùng lặp legacy |
| data/tasks.db | 11.9 MB | durable_tasks + episodes rỗng (vỏ legacy) |

Bảng trong brain.db (5): `episodes` 1.620 · `candidate_knowledge` 2.767 · `semantic_memory` 1.841 · `memories` 1.709 · `candidate_knowledge_archive`.

## 2. Schema từng bảng (thực đo)

- **episodes**: id, created_at_utc, kind, summary, source_ref, status, metadata_json. Phân bố kind: chat_turn **1.506**, experience_lesson 113, task 1. metadata_json chat_turn chứa session_id + user_query + assistant_reply.
- **memories** (nền TỐT nhất): id, memory_type (EPISODIC 1.689 / SEMANTIC 9 / CANDIDATE 7 / PREFERENCE 2 / PROCEDURAL 2), content, source_ref, **verification_status** (OBSERVED 1.506, UNVERIFIED 113, VERIFIED 72, USER_PROVIDED 11, CANDIDATE 7), confidence_score, project_scope, tags_json, lifecycle_status (active 1.589 / quarantined 50 / superseded 70), **version, superseded_by**, created/updated, metadata_json.
- **candidate_knowledge**: statement, source_ref, rationale, status (approved 85 / quarantined 2.682), decision_note.
- **semantic_memory**: statement, source_ref, approved_by, regression_passed — **nhiễm rác ingest**: 166× statement `#!/bin/bash`, 85× `version = "0.1.0"` (ingest_skill_folder nuốt nội dung file như tri thức).

## 3. Vì sao giao diện chỉ thấy CHAT_TURN phẳng (câu hỏi trọng tâm của đề bài)

`server.py:993 _handle_api_list_memories` → chỉ gọi `store.list_episodes(limit=100)` → trả episodes. Giao diện không có view nào khác của trí nhớ ngoài card "Kinh nghiệm" (lessons) + pill đếm. **Kết luận: không phải hệ thống thiếu dữ liệu — thiếu lớp ánh xạ tri thức + API + UI view.** 1.506 chat_turn ĐANG được lưu (persist_chat_turn, Sprint 16 lọc system_prompt), nhưng không được trích xuất thành đơn vị tri thức có quan hệ.

## 4. Những gì ĐÃ có (tái sử dụng — không tạo trùng)

| Thành phần | Vị trí | Trạng thái |
|---|---|---|
| MemoryStore CRUD + search (LIKE) + supersede + trace_source (vòng superseded chain) | memory/sqlite_store.py | TESTED, đang chạy |
| CognitiveClaim / ContradictionRecord / HypothesisItem / freshness | cognition/cognitive_state.py | TESTED — nhưng chỉ RUNTIME, **không persist** |
| Dense retrieval BGE-M3 + keyword hybrid | cognition/document_rag.py, retrieval.py, experience_semantic.py | TESTED (S14 dense real 10/10) |
| Experience lesson extract/promote + promotion policy + quality scanner | memory/experience_consolidation.py, promotion_policy.py, knowledge_quality.py | TESTED |
| Info-gap (câu hỏi chờ chủ + nhắc qua NetChat) | cognition/information_gap_analyzer.py + governance/netchat_info_gap_adapter.py | LIVE (Sprint 3/4) |
| Teach pipeline (chủ dạy → memory) | cognition/teach_pipeline.py | LIVE_VERIFIED (V8) |
| Approval cards + session memory persist | governance/approval_cards.py, cognition/session_memory.py | LIVE |

## 5. Những gì THIẾU (khoảng trống V9 phải lấp)

1. **Lớp quan hệ bền vững** — không có bảng relations nào; CONTRADICTS/SUPPORTS/DERIVED_FROM... chỉ tồn tại runtime trong CognitiveState, mất khi restart.
2. **Đơn vị tri thức chuẩn §IV** (subject/predicate/object/status/scope/validity...) — memories gần nhất nhưng thiếu subject-predicate cấu trúc + valid_from/until + review_status.
3. **Trích xuất tri thức từ chat_turn** — 1.506 bản ghi chưa được khai thác thành FACT/OPINION/QUESTION/RULE.
4. **Suy luận có kiểm chứng** (loại A/B/C, chống vòng tròn, ghi giả định) — chưa có.
5. **Chu kỳ sàng lọc có checkpoint** — chưa có; chỉ có CLO session (học tập tổng quát).
6. **Câu hỏi cho chủ theo cấu trúc A–G** — info-gap có khung câu hỏi nhưng chưa gắn với mâu thuẫn/candidate tri thức.
7. **Exchange protocol + chống vòng lặp** — chưa có event log giữa các phân hệ trí nhớ.
8. **Giao diện Deep Memory** (overview/explorer/review/timeline) — chưa có.
9. **Dọn rác semantic_memory** — 251+ dòng rác ingest; phải ARCHIVE không DELETE (Test I).

## 6. WAL / transaction / backup
- tasks.db: journal=wal; brain.db: journal=delete (audit 28/10). Ghi MemoryStore dùng `with self._lock, self._connection` (transaction từng thao tác).
- Backup hiện có: tools/run_backup.bat 2AM + bản pre-sprint thủ công trong backups/.

## 7. Ràng buộc an toàn xác nhận
- Không ALTER/xoá bảng cũ — chỉ CREATE TABLE IF NOT EXISTS bổ sung (additive migration).
- R0–R5 + approval cards giữ nguyên; câu trả lời làm rõ tri thức của chủ ≠ phê duyệt production (PHẦN VIII.4).

Chi tiết kế hoạch: `V9_DEEP_MEMORY_IMPLEMENTATION_PLAN.md` · Mô hình dữ liệu: `V9_MEMORY_DATA_MODEL.md`.
