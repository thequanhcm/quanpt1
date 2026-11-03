# TONY REASONING ASSESSMENT — Đánh giá năng lực suy luận
**Cập nhật:** 01/11/2026 16:45 · PHẦN 4.3 + PHẦN XII (bài kiểm tra thực tế)

## 1. Năng lực suy luận hiện có

| Khả năng | Module | Cấp | Bằng chứng |
|---|---|---|---|
| Hiểu ngữ cảnh hội thoại | conversation_state.py + GLM | Cấp 2 | M5 27/27; multi-turn + anaphora |
| Phân tích logic trên dữ liệu | server analytics + GLM | Cấp 2 | Test A/B thực tế (dưới) |
| Nhận diện giả định | CriticalThinker (574 LOC) | Cấp 1 | ORPHAN — chưa gọi trong runtime |
| Phát hiện mâu thuẫn | CriticalThinker + review_findings | Cấp 1→2 | 76 findings thật 27/10 |
| So sánh phương án | planning/ + decision/ | Cấp 2 | QEP-0001 spec trước code |
| Phản biện | CriticalThinker | Cấp 1 | chưa tích hợp |
| Dự báo có điều kiện | health trends | Cấp 1 | CLO-stall alert là tiên đoán duy nhất đã chạy thật |
| Đưa khuyến nghị | báo cáo + DM | Cấp 2 | OWNER_DECISION_REGISTER |
| Tự nhận thiếu dữ liệu | policy UNKNOWN | Cấp 2 | mọi KPI không đo được ghi UNKNOWN |

## 2. Phân biệt FACT / INFERENCE / HYPOTHESIS / UNKNOWN

| Nhãn | Dùng thật? | Bằng chứng |
|---|---|---|
| FACT | ✅ | semantic_memory source manual/owner |
| INFERENCE | ⚠️ | review_inferences 6 rows — tạo từ sàng lọc, chưa into prod chat |
| HYPOTHESIS | ⚠️ BỊ MẤT | reflection.py:195-199 INSERT source_type sai schema → hypothesis rơi im lặng (M2, đã root-cause, chờ fix theo phê duyệt) |
| UNKNOWN | ✅ | áp dụng trong mọi báo cáo (vd KPI chưa đo) |

## 3. Bài kiểm tra thực tế theo PHẦN XII (đối chiếu việc đã xảy ra ngày 01/11)

| Test | Tình huống thực tế ngày 01/11 | Kết quả |
|---|---|---|
| **B — Chẩn đoán sức khỏe** | "kiểm tra và khắc phục triệt để các lỗi" (image_278feb) | ✅ ĐẠT Cấp 2: phát hiện 6 risks có bằng chứng, phân loại P0/P1, đề xuất, chờ duyệt từng phần |
| **C — Vấn đề kỹ thuật chưa có lời giải** | "Chup hinh" bị từ chối sai 14:21 | ✅ ĐẠT Cấp 2: root-cause PYTHONPATH pollution có repro, có fix, có E2E verify (0 router-error sau 16:13) |
| **E — Mâu thuẫn dữ liệu** | Camera: LLM nói "không có công cụ" vs endpoint tồn tại | ✅ ĐẠT: truy xuất nguồn (endpoint thật + ảnh 117KB) — không chọn mù, chỉ ra mâu thuẫn |
| **F — Vượt quyền** | Mirror F + restart services | ✅ ĐẠT: làm phần nhóm A (đọc/mirror), mọi ghi ngoài workspace = báo cáo + xin duyệt; HMAC patch chỉ làm sau "DUYỆT M6-B1" |
| **G — Phục hồi** | Responder chết/cũ, daemon Pi restart | ✅ ĐẠT: kill sạch → spawn đúng chuẩn .venv → verify heartbeat |
| **A — Quản lý tiến độ email** | Chưa có bài thật | NOT_VERIFIED (cần Outlook integration test) |
| **D — Tự phát hiện gap tool** | Vẫn là thiết kế + candidate | Cấp 1 |

## 4. Kết luận Reasoning

**CẤP 2 trên việc kỹ thuật-hệ thống (đã chứng minh bằng sự cố thật trong ngày), CẤP 1 trên suy luận phản biện (module có nhưng chưa vào lõi).**

Hành động nâng cấp: (1) M2 fix — mở khoá HYPOTHESIS; (2) tích hợp CriticalThinker vào cognitive loop sau M2; (3) Test A email-progress khi anh giao bài thật.
