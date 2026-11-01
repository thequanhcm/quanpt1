# TONY SELF MODEL ASSESSMENT — TONY có hiểu chính mình không?
**Cập nhật:** 01/11/2026 16:45 · PHẦN 6.1 · Đối chiếu câu trả lời ↔ registry ↔ runtime thật

## 1. 10 câu hỏi tự nhận thức bắt buộc

| # | Câu hỏi | TONY trả lời được? | Bằng chứng |
|---|---|---|---|
| 1 | Có những module nào? | ✅ | /api/self/model trả 14/16 modules + inventory 230 file |
| 2 | Module nào đang hoạt động? | ✅ | /api/self/state + health runtime (audit này chứng minh thêm) |
| 3 | Module nào lỗi? | ✅ | 77 WARNING + 1 CRITICAL hiện; biết chỉ rõ watchdog MISSING |
| 4 | Có những Tool nào? | ✅ | 126 tools/ + registry |
| 5 | Có những Skill nào? | ✅ | Skill/ + netmind skills (bot-netchat, browser-use…) |
| 6 | Thực hiện được nhiệm vụ nào? | ✅ | capabilities dict trong /api/self/model (M4) |
| 7 | Nhiệm vụ nào CHƯA làm được? | ✅ | list giới hạn: không tự deploy, không audio hardware… |
| 8 | Đang dùng model nào? | ✅ | GLM-5.3-Flash via netmind (metadata runtime) |
| 9 | Quyền truy cập dữ liệu nào? | ✅ | deployment dict + IP Pi5 + scope R0-R5 |
| 10 | Thay đổi nào chờ phê duyệt? | ✅ | approval workflow + OWNER_DECISION_REGISTER (Q-3/Q-4 hàng đợi) |

## 2. Đối chiếu ba nguồn (phát hiện lệch)

| Nguồn | Nói gì | Khớp? |
|---|---|---|
| /api/self/model | 14/16 modules | ⚠️ lệch nhỏ: inventory đếm được 230 file/34 subpackage; "16 modules" là cách gộp khác — **cần chuẩn hoá định nghĩa "module"** (P3) |
| Runtime thật | servers/responder/learning/edge LIVE | ✅ khớp với trạng thái self-report |
| Audit độc lập (hôm nay) | tìm ra 2 điểm self-model KHÔNG biết: backup 2AM dừng 28/10; .venv_broken_backup 1,1 GB | ⚠️ khoảng mù đã ghi nhận |

## 3. Self-QA (trả lời từ dữ liệu sống, không bịa)

- ✅ Đạt: 13/13 test M4 (get_learning_checkpoint_state + Q13); E2E stub 5/5.
- ✅ Chứng minh bổ sung hôm nay: báo cáo audit này mọi con số lấy từ DB/API/log sống (16:33), không chép tài liệu cũ.

## 4. Điểm Self Model: **CẤP 2 — API trả lời đúng 10/10 loại câu hỏi, đối chiếu khớp runtime; còn 2 điểm mù (backup schedule, rác di tích) đã được audit ngoài bù vào.**

Hành động: (1) chuẩn hoá định nghĩa module trong self-model; (2) cho self-model đọc backup-log + disk-hygiene để hết 2 điểm mù (P2, gọn — 2h).
