# TONY DEEP MEMORY ASSESSMENT — Đánh giá hệ thống trí nhớ
**Cập nhật:** 01/11/2026 16:45 · PHẦN V · Nguồn: brain.db live (19 bảng) + review logs

## 1. Các lớp trí nhớ — hiện trạng thật

| Lớp | Bảng | Rows (16:33) | Runtime ghi? |
|---|---|---|---|
| Episodic | episodes | 2.685 | ✅ mới nhất 16:30 (chat_turn) |
| Semantic | semantic_memory | 1.842 | ✅ (mới 29/10 manual + daemon) |
| Memories (tổng hợp) | memories | 2.141 | ✅ |
| Knowledge units/relations | knowledge_units / relations | 150 / 210 | ✅ |
| Candidate queue | candidate_knowledge | 4.579 (1.491 approved + 3.088 quarantined) | ✅ daemon tạo |
| Candidate archive | candidate_knowledge_archive | 110.962 | ✅ lịch sử promote |
| Feedback | feedback | 408 | ✅ |
| Memory exchange (multi-embodiment) | memory_exchange_log | 40 | ✅ |
| Review (SÀNG LỌC) | memory_review_runs/sessions + findings/questions/inferences/changes | 1 run / 2 sessions / 76 / 42 / 6 / 1 | ✅ có lịch sử thật |

## 2. Chất lượng trí nhớ — 10 tiêu chí (5.1)

| # | Tiêu chí | Kết luận | Bằng chứng |
|---|---|---|---|
| 1 | Truy xuất đúng dữ kiện | ✅ Cấp 2 | Self-QA grounded M4 (13/13) |
| 2 | Giữ nguồn gốc | ✅ | semantic_memory.source_ref + approved_by (bản ghi "Vợ anh tên là Phương Lan", source manual:family) |
| 3 | Phân biệt dữ kiện vs suy luận | ⚠️ Cấp 1 | schema có; **reflection.py bug làm hypothesis rơi im lặng (M2)** |
| 4 | Phát hiện trùng | ✅ Cấp 2 | review_findings 76 (batches 27/10) |
| 5 | Phát hiện mâu thuẫn | ⚠️ Cấp 1 | có cơ chế, cần review thường xuyên hơn |
| 6 | Xử lý tri thức lỗi thời | ✅ Cấp 2 | archive 110.962 + review_changes rollback có |
| 7 | Liên kết theo thời gian | ✅ | episodes created_at_utc + session_ref |
| 8 | Lưu kinh nghiệm sau nhiệm vụ | ✅ Cấp 2 | candidate_knowledge từ CLO |
| 9 | Tái sử dụng kinh nghiệm | ⚠️ Cấp 1→2 | reuse qua memory lookup; chưa auto-select theo task type |
| 10 | Lịch sử trước–sau | ✅ | review_changes + backup DB |

## 3. Quarantine & xác minh (5.2)

- **Tổng candidate: 4.579 = 1.491 approved (32,6%) + 3.088 quarantined (67,4%)** — tăng từ 4.507 (12:30) vì daemon tiếp tục học.
- 3.088 quarantined KHÔNG được tự mở khóa — đúng governance. Q-4 (approval verifier, ĐÃ DUYỆT) nằm trong hàng đợi: M6-B1 xong → Q-3 → **Q-4**. Đến khi đó, con số này là **đường tồn kho chờ duyệt, không phải "thất bại học tập"**.
- Không dùng % promote làm chỉ số thành công — chất lượng đã kiểm: approved candidates có nguồn gốc + test.

## 4. Memory Review — lệnh SÀNG LỌC (5.3)

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| Tạo phiên sàng lọc | ✅ | memory_review_sessions: rev_51dee1568d8a, rev_e2991750498b (27/10 18:01) |
| Phạm vi dữ liệu | ✅ | scope_json: 20 knowledge ids + selection_reasons |
| Bốn nhóm kết quả | ✅ | findings 76, inferences 6, questions 42, changes 1 |
| Bằng chứng | ✅ | stats_json lưu trong session |
| Câu hỏi cho Quanpt1 | ⚠️ | review_questions 42 rows — **owner_questions = 0 → chưa có câu nào được owner trả lời qua luồng DM** |
| Tiếp nhận phản hồi | ⚠️ | cơ chế có; chưa chạy E2E owner-feedback thật |
| Cập nhật đúng phạm vi | ✅ | review_changes có checkpoint |
| Lịch sử trước–sau + rollback | ✅ | review_changes + archive |

**Đánh dấu trung thực:** SÀNG LỌC = **Cấp 2 (đã chạy thật trên dữ liệu thật)** nhưng **vòng phản hồi owner chưa đóng** (owner_questions=0) → đề xuất P1: đưa câu hỏi sàng lọc vào Morning Report 8h để anh trả lời theo lô.

## 5. Điểm Deep Memory: **CẤP 2 — LÀM ĐƯỢC VIỆC** (9/10 tiêu chí có bằng chứng runtime; điểm nghẽn duy nhất = M2 bug + vòng phản hồi review owner)
