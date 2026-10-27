# BÁO CÁO — V3 SPRINT 3: INFORMATION GAP AWARENESS ENGINE

**Mã hồ sơ:** TASK-V3-SPRINT3
**Thời điểm:** 27/10/2026
**Yêu cầu:** Master Prompt V3 Sprint 3 — "Tự nhận biết thông tin còn thiếu — Chủ động hỏi chủ nhân — Chờ chỉ đạo — Chỉ tiếp tục khi đủ căn cứ"
**Quy trình:** đúng 10 bước V3 §14 (audit → thiết kế → schema → NetChat → persistence → approval tách biệt → test → regression → báo cáo → trình duyệt).

---

## 1. ĐÃ XÂY DỰNG

### 1.1. `src/quan_ai_brain/cognition/information_gap_analyzer.py` (MỚI, ~570 dòng)

- **TaskSpecification V3 §3.1** đầy đủ 15 trường + questions/readiness/waiting_state;
  trường chưa biết giữ `UNKNOWN`/`MISSING` — không tự điền; round-trip giữ nguyên.
- **9 nhóm thiếu V3 §3.2** (GapCategory A–I). Nhóm I (phê duyệt) KHÔNG tạo
  information request — chỉ đánh dấu `approval_gate_needed` để chuyển
  ApprovalOrchestrator (tách biệt V3 §10, test `test_approval_group_I_separate`).
- **EvidenceKind 7 trạng thái V3 §3.1**: VERIFIED, OWNER_PROVIDED, RETRIEVED,
  INFERRED, ASSUMPTION, UNKNOWN, CONFLICTED.
- **Readiness 3 trạng thái V3 §5**: READY / NEEDS_OWNER_INPUT /
  NEEDS_VERIFICATION + 9 điều kiện dừng V3 §5.1 (mục tiêu mơ hồ, thiếu dữ liệu
  quyết định, xung đột nguồn, thiếu quyết định chủ nhân…).
- **Không hỏi lại** thông tin đã có VERIFIED/OWNER_PROVIDED/RETRIEVED (V3 §4)
  — test T06/T06b.
- **Câu hỏi có cấu trúc V3 §6**: question_id, reason, why_it_matters,
  expected_answer_type, required_or_optional, impact_if_unanswered, options ≤3.
- **Persistence bền vững V3 §8**: SQLite `data/information_gaps.db` (bảng
  `info_gap_tasks` + `info_gap_events` audit); lưu mã nhiệm vụ, spec JSON,
  câu hỏi đã gửi, trạng thái phản hồi, message id, reminder count.
- **Tiếp nhận từng phần V3 §8.1**: `record_owner_reply` map câu trả lời → câu
  hỏi OPEN, nguồn = OWNER_PROVIDED, phân tích lại còn thiếu/báo đủ; **trả lời
  ≠ phê duyệt** (note trung thực trong kết quả).
- **Nhắc việc có giới hạn V3 §9**: tối đa 5 lần, cách nhau 12 giờ mặc định;
  im lặng KHÔNG đồng ý; timeout không cấp quyền tiếp tục.
- **Format tin V3 §7 nguyên văn**: `[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]` 5 mục
  + dòng kết thúc bắt buộc; phiên bản ngắn khi ≤2 câu hỏi.

### 1.2. Tích hợp CognitiveLoop (không viết lại)

- `submit_task()` thêm bước **gap_check (mặc định BẬT)** sau validate, TRƯỚC
  đăng ký task: thiếu thông tin thiết yếu → trả `NOT_SUBMITTED`, task_id=None,
  kèm `info_request_text` — **KHÔNG có hành động nào được thực hiện**.
- Metadata mới đọc từ TaskSpec: `required_inputs`, `conflicts`,
  `owner_decisions_required`, `constraints`, `available_resources`.
- TaskSpec.validate() fail-closed cũ GIỮ NGUYÊN (acceptance rỗng vẫn từ chối).

### 1.3. NetChat (kênh hiện có, KHÔNG tạo bot mới)

- **`src/quan_ai_brain/governance/netchat_info_gap_adapter.py` (MỚI)**:
  `send_info_request` (2 bước CONFIRM-REQUIRED đúng skill bot-netchat),
  `handle_owner_info_reply` (map trả lời theo mã TASK → câu hỏi OPEN),
  `has_waiting_task` (phân biệt info-gap task với approval task).
- **`netchat_command_center.route_message()`**: bước 0.5 — tin có mã TASK
  đang chờ thông tin → `info_gap_reply` cập nhật trạng thái; lệnh
  DUYỆT/TỪ CHỐI/SỬA **vẫn ưu tiên Approval Card** (đã verify E2E).
- **`netchat_approval_adapter`**: khi tin chứa mã TASK không khớp lệnh duyệt
  và task đang chờ info-gap → trả '' (route tiếp) thay vì báo sai
  "CHƯA HIỂU LỆNH".

## 2. BỘ KIỂM THỬ — 18/18 tình huống bắt buộc V3 §12

`tests/test_v3_sprint3_information_gap.py` — **23 passed** (18 bắt buộc + 5 bổ sung):

| # | Tình huống | Kết quả |
|---|---|---|
| 1 | Yêu cầu đầy đủ: không hỏi thừa | ✅ PENDING bình thường, 0 câu hỏi |
| 2 | Thiếu đường link | ✅ NOT_SUBMITTED + hỏi đúng format V3 §7 |
| 3 | Thiếu dữ liệu đầu vào | ✅ liệt kê cụ thể từng item + lý do |
| 4 | Mục tiêu mơ hồ | ✅ hỏi làm rõ kết quả mong muốn |
| 5 | Thiếu tiêu chí nghiệm thu | ✅ hỏi cách xác định hoàn thành |
| 6 | Tự tìm trước khi hỏi | ✅ VERIFIED/OWNER_PROVIDED không hỏi lại |
| 7 | Không có quyền | ✅ báo nguồn đã kiểm tra, không giả vờ |
| 8 | Nguồn mâu thuẫn | ✅ NEEDS_VERIFICATION, không tự chọn |
| 9 | Trả lời một phần | ✅ cập nhật phần nhận, hỏi phần còn thiếu |
| 10 | Thông tin ≠ phê duyệt | ✅ READY_FOR_PLANNING, approval gate giữ nguyên |
| 11 | Đổi phương án | ✅ chỉ đạo lưu OWNER_PROVIDED, readiness cập nhật |
| 12 | Restart khi chờ | ✅ instance mới khôi phục đầy đủ từ DB |
| 13 | Im lặng ≠ đồng ý | ✅ vẫn chờ + nhắc có giới hạn (≤5 lần) |
| 14 | Chỉ dẫn giả mạo | ✅ FAKE question_id bị từ chối, trạng thái không đổi |
| 15 | Nhiều câu hỏi | ✅ gom 1 tin, ≤5 câu, có ưu tiên |
| 16 | Trả lời không rõ | ✅ ghi nguyên văn, không tự đoán (0 ASSUMPTION tự sinh) |
| 17 | Duyệt sai task | ✅ question của task khác bị từ chối |
| 18 | R5 chặn cứng | ✅ đủ thông tin vẫn không có quyền thực thi |

`tests/test_v3_sprint3_netchat_info_gap.py` — **10 passed**: routing 3 loại
giao tiếp không trộn lẫn; send 2 bước có confirm; lỗi mạng báo trung thực;
READY không gửi tin; subprocess mock 100% (không gọi NetChat thật trong test).

## 3. CHỈ SỐ NGHIỆM THU V3 §13 (đo từ bộ kiểm thử)

| Chỉ số | Mục tiêu | Kết quả thực tế |
|---|---|---|
| Phát hiện đúng thông tin thiết yếu còn thiếu | cao | 23/23 tình huống phát hiện đúng (T02–T05, T08) |
| Tỷ lệ hỏi thừa | thấp | 0 — T01/T01b/T06: đủ thông tin → 0 câu hỏi |
| Câu hỏi được trả lời xong cập nhật đúng | 100% | T09: trả lời từng phần đúng trạng thái |
| Nhiệm vụ hiểu sai do thiếu thông tin | giảm | T04/T16: mơ hồ → hỏi, KHÔNG tự đoán |
| Khôi phục đúng sau restart | 100% | T12: DB khôi phục đầy đủ, không tự chạy tiếp |
| Info request nhầm thành approval | 0 | 0 — T17 + test_approval_group_I_separate |
| **Hành động nghiệp vụ khi thiếu điều kiện** | **0** | **0** — T02: NOT_SUBMITTED, task_id=None |
| **Hành động khi đang chờ chỉ đạo** | **0** | **0** — T13/T14: chờ = không làm |
| **Tự suy đoán thông tin chưa biết thành sự thật** | **0** | **0** — T16: nguyên văn, 0 ASSUMPTION tự sinh |

Trường hợp sai & nguyên nhân được lưu trong `info_gap_events` (audit trail).

## 4. FULL REGRESSION

- **716 passed, 2 skipped, 2 failed** — cả 2 fail **KHÔNG phải hồi quy**:
  đã verify bằng `git stash` (fail cả khi GỠ toàn bộ code Sprint 3):
  1. `test_keep_warm_pulse` — Ollama 11434 OFFLINE (fail cũ đã biết).
  2. `test_grounding_block_contains_truth_rules` — Pi 5 RỚT LAN thật lúc
     22:43 đêm trước (ping unreachable, heartbeat 14.453s = ~4 giờ).
     Test cũ thiếu 1 trạng thái trung thực thứ 3. **Đã sửa assertion** cho
     phép "chưa xác minh" — đúng hành vi trung thực đã duyệt của fix
     `f92b32a` (KHÔNG beautify Pi 5 đang mất kết nối). 67 passed trong cụm
     test liên quan sau sửa.
- Chạy lại full regression lần 2 sau sửa — kết quả ghi tại phần 7.

## 5. GIỚ HẠN TRUNG THỰC

- Gap analysis hiện là **luật khai báo + heuristic** (required_inputs,
  conflicts, decisions từ TaskSpec.metadata) — CHƯA dùng LLM suy luận khoảng
  trống từ văn bản tự do (đề xuất sprint sau: LLM-assisted gap detection với
  output có cấu trúc, vẫn fail-closed).
- Danh tính owner reply cấp-1 = tài khoản NetChat (như Sprint 2, chưa sinh-trắc-học).
- Phục hồi sau restart đã bền vững ở mức DB; việc auto-responder gọi
  `handle_owner_info_reply` trên tin nhắn thật đã E2E qua `route_message()`
  (TASK-E2E99 → cập nhật đúng), chưa test qua process responder 24/7 thật.

## 6. ĐỀ XUẤT SPRINT TIẾP THEO

1. LLM-assisted gap detection từ yêu cầu tự do (vẫn fail-closed, UNKNOWN khi không chắc).
2. Auto-responder 24/7: đọc info-gap chờ quá hạn → gửi nhắc đúng chính sách V3 §9.
3. OwnerSignatureVerifier (thừa kế GAP Sprint 2) cho reply thông tin quan trọng.

## 7. KẾT QUẢ CHẠY LẠI LẦN 2 (sau sửa test grounding)

- **717 passed, 2 skipped, 1 failed** — fail duy nhất `test_keep_warm_pulse`
  (Ollama OFFLINE — fail môi trường cũ đã biết, không liên quan Sprint 3).
- Sprint 3 + Sprint 2 + honest report: 67/67 passed. +33 test mới (23 info-gap
  + 10 netchat routing), 0 hồi quy.

---
**Trạng thái: ĐÃ HOÀN THÀNH PHẦN XÂY DỰNG + TEST. Chờ anh Quânpt1 duyệt hồ sơ
TASK-V3-SPRINT3 trước khi commit lên master.** KHÔNG tự commit khi chưa có
phê duyệt (V3 §14 bước 10 + quy tắc chủ sở hữu).
