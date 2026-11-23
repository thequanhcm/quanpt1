# BÁO CÁO SPRINT 4 — REPLY-DRAFT (TASK-VMAIL-S4)

**Ngày**: 24/11/2026 · **Owner duyệt**: "duyệt Sprint 4 REPLY-DRAFT (§17)" (chat 24/11)
**Vị trí trong lộ trình §17**: 1 VmailConnector ✅ → 2 Thread Analyzer ✅ → 3 Memory-Adapter ✅ → **4 REPLY-DRAFT ✅ (báo cáo này)** → 5 Workflow → 6 Dashboard

---

## 1. Mục tiêu sprint (master prompt §7)

- **§7.1 Context-Aware Reply**: 10 bước (đọc email → thread → memory → tài liệu → quyết định → deadline → phát hiện thiếu → phương án → mâu thuẫn → nháp).
- **§7.2 Reply Styles**: 11 văn phong.
- **§7.3 Reply Quality Check**: 8 mục kiểm tra trước khi đưa nháp.
- **§7.4 Send Policy**: Cherry được soạn nháp, KHÔNG tự gửi; gửi cần phê duyệt rõ ràng nội dung + người nhận từng lần.

## 2. Audit-trước-sửa

| Thành phần hiện có | Trạng thái | Dùng cho S4 |
|---|---|---|
| ThreadAnalyzer (S2) | 10 mục + contradictions + subject_display | ReplyContext |
| CherryMemoryAdapter (S3) | retrieve_context LIVE | §7.1.3 memory |
| `src/quan_ai_brain/tools/email_draft.py` (Sprint 8b) | create_draft .eml R2 (X-QAB-* headers) | Đường ghi nháp — KHÔNG làm mới |
| NetMindProvider (llm/) | generate() LIVE | Tùy chọn custom_body (không bắt buộc) |
| VmailConnector | list_messages LIVE | Dữ liệu thread thật |

## 3. Module: `src/quan_ai_brain/office/reply_drafter.py` (~330 lines)

- **ReplyContext.from_thread_analysis()**: recipient (người gửi đầu ≠ owner), subject thêm `RE:`, questions/decisions/deadlines/contradictions — chỉ dữ liệu CÓ THẬT; `thread_cancelled` từ tag [Hủy].
- **ReplyDrafter.build_reply(ctx, style, custom_body)**: style sai → lỗi rõ; thiếu dữ liệu → fail-honest; memory degraded → vẫn soạn; .eml qua email_draft (placeholder To + cảnh báo §7.3.8 nếu chưa có địa chỉ).
- **§7.2**: 11 style — `_GREETING` + `_SIGN_OFF` + `_DEFAULT_BODY` template deterministic; body thật từ ctx.points; questions_pending in riêng phần "chờ làm rõ, không suy diễn".
- **§7.3**: 8 check — §7.3.1 câu hỏi chưa trả lời; §7.3.2 body rỗng; §7.3.3 mâu thuẫn + hủy-vs-xác-nhận; §7.3.5 deadline khớp; §7.3.6 cam kết vượt thẩm quyền; §7.3.7 từ nhạy cảm; §7.3.8 thiếu To. Warnings kèm nháp — owner quyết cuối.
- **§7.4 bất biến**: KHÔNG method send/smtp (test chặn); format_preview() in đầy đủ To/CC/Subject/Body trước khi owner duyệt.

## 4. Runner + Wire DM

- `tools/office_reply_draft_runner.py`: SOAP → threads → kw → recipient from_addr thật → draft + preview + R2 banner.
- `netchat_command_center.py`: intent `reply_draft` ("soạn trả lời email \<kw\> [style]") đặt TRƯỚC thread_summary; handler trích kw + style từ text; subprocess 110s.

## 5. Test

- `tests/test_office_reply_drafter.py` (MỚI): **24/24 PASS** — 11 styles đủ + mỗi style có body; invalid style lỗi; greeting/sign-off; English; context từ ThreadAnalysis; RE: không nhân đôi; tag hủy; 8 mục §7.3 (có case sạch 0 warning); fail-honest thiếu dữ liệu; points thật vào body; placeholder trung thực; custom_body nguyên văn; .eml ghi + X-QAB headers; **không có đường send**; preview; memory gathered + degraded.
- Focused S1-S4 + MAIL_READ: **122/122 PASS**; command_center: **24/24 PASS**.

## 6. Live E2E (SOAP thật, READONLY)

| Luồng | Style | Kết quả |
|---|---|---|
| Khói...CHÁY (7 mail) | chuyên nghiệp | .eml To `khanhnq@viettel.com.vn`, subject RE:, quality 0 warning, body trung thực "chưa đủ dữ liệu — không bịa" |
| Battery AI audit chéo | hành chính | .eml To `anhnt782@viettel.com.vn`, **§7.3.1 bắt đúng câu hỏi "quá hạn audit chéo 20/11 chưa bổ sung tài liệu nào"** + missing_info |
| DM "soạn trả lời email khói chuyen_nghiep" | — | intent → handler → preview đầy đủ ✓ |

Drafts smoke đã dọn sạch sau E2E.

## 7. Trung thực — giới hạn hiện tại

1. Body template deterministic còn thô khi luồng không có decisions/commitments — in trung thực "chưa đủ dữ liệu, không bịa". Nâng cấp GLM soạn body tự nhiên (S4b) chờ anh duyệt riêng.
2. §7.1.4 "truy xuất tài liệu liên quan" chưa có — Knowledge Engine chưa tích hợp (không fake).
3. KPI Reply Relevance ≥90% (§14) chưa đo — cần bộ dữ liệu gán nhãn.
4. **GỬI email KHÔNG có trong code** (§7.4): nháp .eml + owner tự bấm Send; nếu muốn đường gửi có verify (SearchRequest Sent sau gửi) thì làm sprint riêng khi anh phê duyệt SEND.
5. Trạng thái: **TESTED + LIVE_E2E** — không tuyên bố PRODUCTION_VERIFIED.

## 8. Files thay đổi

| File | Loại |
|---|---|
| `src/quan_ai_brain/office/reply_drafter.py` | MỚI ~330 lines |
| `tests/test_office_reply_drafter.py` | MỚI 24 test |
| `tools/office_reply_draft_runner.py` | MỚI runner CLI |
| `tools/netchat_command_center.py` | PATCH intent + handler + route |
| `docs/PROJECT_STATUS.md` | APPEND S4 |

## 9. Kế tiếp

Sprint 5 CROSS-DOMAIN WORKFLOW (§8-9) — chờ owner duyệt. Đề xuất S4b (GLM body tự nhiên) nếu anh muốn trước.
