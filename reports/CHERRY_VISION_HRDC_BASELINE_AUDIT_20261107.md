# CHERRY VISION INTELLIGENCE (CVI) + HR/DC OPERATIONS — BASELINE AUDIT (PHASE 0)
**Ngày:** 07/11/2026 • **Theo lệnh owner:** 2 Master Prompt V1.0 (Vision) + V2.0 (HR & Datacenter Ops)
**Nguyên tắc:** AUDIT FIRST – DESIGN SECOND – OWNER APPROVAL – IMPLEMENT – TEST – VERIFY – REPORT

---

## PHẦN A — CHERRY VISION MASTER PROMPT V1.0

### A1. Năng lực ảnh HIỆN CÓ (đã kiểm chứng bằng code + E2E thật)
| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| Mô tả bối cảnh (scene description) | LIVE_VERIFIED | `_scene_description()` GLM-5.3-Flash base64, E2E 07/11: "trong nhà, tủ lạnh, đèn, hồ cá" ✓, 47/47 tests, nhãn "mô tả AI, có thể sai chi tiết nhỏ" |
| OCR | LIVE_VERIFIED | Tesseract 5.4.0 (`C:\Program Files\Tesseract-OCR\tesseract.exe`), vie+eng, max 1200 ký tự |
| Kỹ thuật ảnh (kích thước, mode, dung lượng) | LIVE_VERIFIED | `_image_facts()` |
| Học từ ảnh vào tri thức | LIVE_VERIFIED | `_save_knowledge()` → candidate_knowledge (QUARANTINED chờ duyệt — đúng luật tự học) |
| Ghép ảnh↔mô tả DM | LIVE_VERIFIED | test_netchat_image_pairing (21 pass) |
| Camera Pi 5 chụp theo lệnh DM | LIVE_VERIFIED | 11:07:21 07/11 photo_20261107_110719.jpg ✓ |

### A2. Khoảng cách so với CVI V1.0 (đề xuất SPRINT)
| Sprint | Mục tiêu | Hiện trạng | Đánh giá |
|---|---|---|---|
| S0 Audit | Baseline | **Tài liệu này** | ✅ |
| S1 Universal Understanding | Loại ảnh đa dạng, chủ thể/phụ/bối cảnh | GLM trả mô tả tự do; CHƯA có framework phân lớp (subject/background/spatial), CHƯA tách OBSERVED/INFERRED/UNCERTAIN có cấu trúc | Thiết kế prompt-schema mới |
| S2 Photography Analysis | Bố cục, góc máy, ánh sáng, màu (HEX), quality score | Chưa có | Cần prompt engineering + tự đánh giá có lý do |
| S3 Art Direction | Cảm xúc, ý đồ, storytelling | Chưa có | Phụ thuộc chất lượng GLM |
| S4 Reverse Prompt Engineering | Prompt tái tạo (A/B/C) | Chưa có | Thuần prompt engineering — khả thi cao |
| S5 Multi-Image | So sánh/nhóm/tổng hợp | Chưa có | GLM hỗ trợ nhiều ảnh/lượt |
| S6 Visual Learning | Skill Library, benchmark, feedback loop | Có phần lưu tri thức quarantined; CHƯA có skill registry vision + benchmark | Mở rộng capability_registry |
| S7 Quality Audit | Độ chính xác/ổn định | Chưa có benchmark tập ảnh thật | Cần bộ ảnh test của owner |

### A3. Giới hạn trung thực phải giữ khi triển khai
- GLM-5.3-Flash có thể sai chi tiết nhỏ; không có bounding-box/object detection thật; không có metadata EXIF từ camera Pi.
- Mọi nhãn phải giữ phân lớp OBSERVED/INFERRED/UNCERTAIN/UNDETERMINED (khớp fail-honest V7.0 §2.4 hiện hành).
- Không chấm điểm khi thiếu dữ liệu → N/A.

---

## PHẦN B — CHERRY MASTER PROMPT V2.0 (HR + DATACENTER OPERATIONS)

### B1. Hiện trạng liên quan
- **HR Intelligence:** KHÔNG có module nào. Scan 135 file src/ chỉ trùng từ khoá ngẫu nhiên (OT = "outcome"…), không có workforce/shift/competency/burnout engine.
- **Datacenter Engineering:** KHÔNG có module BMS/DCIM/UPS/cooling. Chỉ có khái niệm SOP rải rác trong governance/memory (quy tắc vận hành nội bộ BRAIN, không phải SOP Datacenter).
- **Có sẵn để tận dụng:** consultation_inbox (duyệt owner), capability_registry (12 năng lực), learning engine (4 luồng, quarantined), DM 4 tầng NetChat, memory review panel, audit trail.
- **Dữ liệu:** chưa có nguồn dữ liệu HR (nhân sự/ca trực) hay BMS/DCIM được cấp quyền kết nối.
- **Protected projects:** E:\AI\DATA CENTER AI OPERATING SYSTEM (được V7.0 §2.5 bảo vệ — CHỈ ĐỌC, phải xin owner hướng dẫn riêng nếu CVI/HR-DC cần dữ liệu từ đó).

### B2. Đánh giá phạm vi
- V2.0 là **master prompt nhân hiệu + khung tư duy** (persona, nguyên tắc, phân cấp quyền L0–L4) → PHẦN NHÂN HIỆU có thể áp dụng NGAY vào lời thoại/persona hiện có (executive_persona.py) KHÔNG cần code mới.
- Các module tính toán (lịch trực, competency, burnout, BMS trend) = **dự án Sprint riêng** cần dữ liệu thật + phê duyệt thiết kế; KHÔNG bắt đầu khi thiếu dữ liệu (tránh bộ khung rỗng).

---

## PHẦN C — ĐỀ XUẤT LỘ TRÌNH CHỜ OWNER DUYỆT
1. **[Áp ngay, không code mới]** Nạp nhân hiệu + nguyên tắc V2.0 vào persona engine & self_qa (định danh CHERRY = Senior HR + DC Ops Intelligence). Cập nhật self_qa tests.
2. **S1 Vision** — prompt-schema phân lớp OBSERVED/INFERRED… cho mọi phân tích ảnh (sửa `_scene_description` prompt + reply builder). Có test với ảnh thật của owner.
3. **S2→S4 Vision** — photography analysis + quality score + reverse prompt (A/B/C) như module trả lời on-demand.
4. **S5→S6 Vision** — multi-image + visual skill registry trong capability_registry.
5. **HR/DC Phase 1→3** — chỉ khởi động khi owner cấp dữ liệu (danh sách nhân sự ca trực / BMS export) hoặc xác nhận dùng mô phỏng sandbox.

**KHÔNG tự triển khai vào production; mọi Sprint chờ "duyệt" theo quy trình hiện hành.**
