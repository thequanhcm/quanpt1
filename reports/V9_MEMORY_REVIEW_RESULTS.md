# V9 — MEMORY REVIEW RESULTS (đợt sàng lọc thực tế đầu tiên)
**Ngày:** 28/10/2026 · Chế độ AN TOÀN trên dữ liệu thật (PHẦN XV — không xoá, không merge, không nâng trạng thái tự động)

## 1. Thông tin đợt chạy
- run_id: `run_e284a6c4afcd` · batch_limit 20 · trạng thái **COMPLETED** đủ 10 stage
- Trigger: API POST /api/memory/deep/review (server test 8799) trên brain.db thật sau backup 89.4MB

## 2. Kết quả theo §VII.2

| Nhóm kết quả | Số lượng | Ghi chú |
|---|---|---|
| Tri thức mới (đợt extract trước review) | **148 KU** | từ 40 chat_turn thật: 83 FACT, 60 QUESTION, 4 RULE, 1 OPINION |
| Tri thức được liên kết | **208 quan hệ** | 173 RELATED_TO (có basis), 35 REFINES (chứa statement) |
| Quan hệ suy đoán (speculative) | trong 173 RELATED_TO | đánh dấu `is_speculative=1` + hiển thị vàng trên UI |
| Trùng lặp (jaccard ≥ 0.8) | 0 | chưa có cặp đủ giống trong 148 KU |
| Mâu thuẫn phát hiện | **0 cùng scope** | các cặp polarity ngược chưa xuất hiện trong 40 episodes đầu |
| Tri thức lỗi thời | 0 chưa đánh giá | cần đợt review với batch lớn hơn |
| Giả thuyết mới | 0 | không có mâu thuẫn → không sinh |
| **Câu hỏi chờ Quanpt1** | **0** | đúng nguyên tắc §VIII — KHÔNG hỏi khi không có căn cứ |
| Thay đổi tự động đề xuất | 0 | `_stage_commit` không nâng trạng thái nào (`auto_promoted=0`) |
| Thay đổi thực tế đã thực hiện | chỉ CREATE mới | bảng cũ giữ nguyên — `retained_as_is=148` |

## 3. Phát hiện ngoài KU: rác ingest trong semantic_memory
`report_semantic_junk()` (read-only) phát hiện **50+ dòng rác** trong bảng `semantic_memory` (script shebang, code fragments từ ingest_skill_folder). **KHÔNG xóa** — chờ chủ quyết định chính sách lưu trữ (§VII.2 cuối: dùng quan hệ/chính sách, không xoá gốc). Chi tiết ở V9_DEEP_MEMORY_ACTUAL_STATE_AUDIT.md §2.

## 4. Hiểu đúng về kết quả "0 câu hỏi"
Không có câu hỏi trong đợt đầu KHÔNG phải vì cơ chế hỏng — test E chứng minh cơ chế sinh câu hỏi hoạt động khi có mâu thuẫn cùng scope (test_contradiction_generates_structured_question ✅). Dữ liệu thật 40 episodes đầu chưa chứa cặp mâu thuẫn cùng phạm vi. Các đợt sau với batch lớn hơn (≥100 episodes) sẽ kích hoạt khi gặp mâu thuẫn thật.

## 5. Checkpoint & khả năng phục hồi
Checkpoint lưu sau MỖI stage vào `memory_review_runs.checkpoint_json` — test H chứng minh resume đúng sau gián đoạn. Run hiện tại COMPLETED; các run tiếp theo tạo run_id mới.
