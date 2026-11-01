# BÁO CÁO AUDIT — V3 SPRINT 3: INFORMATION GAP AWARENESS ENGINE

**Mã hồ sơ:** TASK-V3-SPRINT3
**Thời điểm:** 27/10/2026
**Phạm vi:** Audit kiến trúc hiện tại trước khi xây InformationGapAnalyzer (Master Prompt V3 Sprint 3, Phần 2).

---

## 1. CHUỖI PIPELINE HIỆN TẠI (cognitive_loop.py)

```
RECEIVED → CONTEXT_BUILDING → UNDERSTANDING → PLANNING → RISK_ASSESSMENT
```

`submit_task()` chạy tự động hết chuỗi trên. **Chưa có cơ chế dừng ở UNDERSTANDING
khi thiếu thông tin** — đây là khoảng trống chính mà Sprint 3 phải lấp.

## 2. TRẠNG THÁI THÔNG TIN (nơi gắn phân loại theo V3 §3.1)

`context_builder.py` — `ContextInfo.status`:

| Status | Ý nghĩa | Khớp V3 |
|---|---|---|
| `VERIFIED` | đã xác minh | ✅ "đã được xác minh" |
| `OWNER_PROVIDED` | chủ nhân cung cấp | ✅ "do chủ nhân cung cấp" |
| `RETRIEVED` | nguồn được cấp quyền | ✅ "truy xuất từ nguồn được cấp quyền" |
| `INFERRED` | suy luận | ✅ "thông tin suy luận" |
| `ASSUMPTION` | giả định | ✅ "đang giả định" |
| `UNKNOWN` | chưa biết | ✅ "chưa biết" |
| `CONFLICTED` | mâu thuẫn → **bắt buộc dừng hỏi (V3 §5.1)** | ✅ |

→ Phân loại 7 trạng thái thông tin V3 §3.1 **đã có sẵn trong ContextInfo** —
Sprint 3 không cần tạo enum mới, chỉ cần dùng đúng + đọc được chúng khi phân tích.

## 3. CÁC THÀNH PHẦN ĐỐI CHIẾU

| Thành phần | Hiện trạng | Đánh giá Sprint 3 |
|---|---|---|
| `ContextInfo.status` (context_builder) | 7 trạng thái đủ V3 §3.1 | **Tái sử dụng** — không tạo enum cạnh tranh |
| CognitiveLoop `TaskSpec` | validate spec; submit chạy thẳng tới PLANNING | **Mở rộng** — thêm điểm dừng NEEDS_OWNER_INPUT sau UNDERSTANDING |
| TaskStatus (orchestration/models.py) | PENDING, IN_PROGRESS, WAITING_APPROVAL, APPROVED, COMPLETED, FAILED, CANCELLED, OUTCOME_UNKNOWN, BLOCKED | **Bổ sung additive:** WAITING_FOR_OWNER_INPUT + 3 trạng thái chờ của V3 §8 (không đụng trạng thái cũ) |
| ConsultationStore (consultation_inbox.py) | Ticket PENDING_REVIEW/APPROVED/REJECTED/DIRECTED, 6 category | **Mở rộng additive** — category mới `INFO_REQUEST` để phân biệt 3 loại yêu cầu (V3 §10) |
| ApprovalCardStore (approval_cards.py) | card lưu TRƯỚC khi post; state machine đầy đủ; R5 chặn 2 lớp; consume-once | **GIỮ NGUYÊN** — information request KHÔNG dùng approval card (V3 §3.2 nhóm I, §10) |
| ApprovalGate | grant_approval consume-once | **GIỮ NGUYÊN** |
| NetChatApprovalAdapter | parse DUYỆT/TỪ CHỐI/SỬA/CHI TIẾT + "Duyệt" trần; chỉ quanpt1 | **Mở rộng** — route info-request qua kênh riêng của logic mới, không trộn card |
| DurableTaskRegistry | trạng thái bền vững theo task | **Tái sử dụng** — persistence + phục hồi sau restart |
| PlanOrchestrator | R4 → WAITING_APPROVAL | **GIỮ NGUYÊN** |
| PolicyEngine R0–R5 | R5 hard-block | **GIỮ NGUYÊN** (V3 §14: không sửa) |
| ConsultationCategory | 6 category cũ | **Thêm INFO_REQUEST (additive)** |

## 4. KHOẢNG TRỐNG CẦN LẤP (đích xây dựng Sprint 3)

1. **Task Specification V3 §3.1** — 15 trường có cấu trúc, trường chưa biết ghi
   UNKNOWN/MISSING, không điền tưởng tượng.
2. **Phân loại 9 nhóm thiếu** (V3 §3.2 A–I) — nhóm I (phê duyệt) tách riêng qua
   ApprovalOrchestrator hiện có, không trộn.
3. **Quyết định 3 trạng thái READY / NEEDS_OWNER_INPUT / NEEDS_VERIFICATION**
   trước PLANNING (V3 §5) + 9 điều kiện bắt buộc dừng (§5.1).
4. **Sinh câu hỏi có cấu trúc** (V3 §6): question_id, reason, why_it_matters,
   options ≤3, gom nhóm ≤5, ưu tiên.
5. **Format tin nhắn [CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]** 5 mục + dòng trạng
   thái kết thúc (V3 §7) — khác biệt rõ với Approval Card.
6. **Persistence trạng thái chờ + phục hồi restart** (V3 §8): mã nhiệm vụ, câu
   hỏi đã gửi, phần đã nhận/còn thiếu, message id — dùng DurableTaskRegistry.
7. **Tiếp nhận trả lời từng phần** (V3 §8.1): map câu trả lời → khoảng trống,
   cập nhật TaskSpec, phân tích lại; trả lời ≠ phê duyệt.
8. **Kinh nghiệm đặt câu hỏi** (V3 §11) — bài học candidate qua learning pipeline.
9. **Bộ test 18 tình huống** (V3 §12) + chỉ số nghiệm thu (§13).

## 5. NGUYÊN TẮC THIẾT KẾ

- **Không viết lại** CognitiveLoop, ApprovalOrchestrator, PolicyEngine.
- Thay đổi **additive**: enum bổ sung phần tử mới, hàm mới tách file, tích hợp
  bằng hook tại 1 điểm duy nhất trong submit_task.
- Module mới `information_gap_analyzer.py` — đã kiểm tra: chưa có module tương
  đương (grep toàn workspace), tên chức năng đúng như Master Prompt đề xuất.
- Format tin nhắn + trạng thái chờ của V3 áp dụng **nguyên văn**, tiếng Việt.
- Mọi hành vi chặn phải test được: im lặng ≠ duyệt, trả lời ≠ duyệt, restart
  khôi phục chờ, R5 vẫn chặn cứng.
