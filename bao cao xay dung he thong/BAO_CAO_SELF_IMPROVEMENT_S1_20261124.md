# BÁO CÁO SELF-IMPROVEMENT S1 — CHERRY TỰ HOÀN THIỆN, TỰ HỌC — 24/11/2026

**Yêu cầu owner** (ảnh image_e2d705, 10:55): "sao nhiều chức năng khi anh hỏi cherry đều nói chưa có, em hãy xây dựng để cherry tự hoàn thiện bản thân, tự học và tìm mọi cách để học, xây dựng và phát triển"
**Kết quả**: ✅ TRIỂN KHAI S1 — 114/114 focused PASS + E2E vòng tự học verify.

## 1. Vấn đề thật từ ảnh
- **10:55** anh nhắn *"Tóm tắt 5 email gần nhất cho anh"* → CHERRY trả lời *"em chưa có công cụ truy cập hộp thư"* — SAI, vì Sprint TOGGLE 10:42 vừa đọc hộp thư thật được.
- Nguyên nhân gốc: kw tĩnh không phủ câu **có số đếm** ("5 email gần nhất") → `detect_intent` trả None → câu rơi vào GLM hội thoại → GLM không biết năng lực thật của CHERRY nên nói sai.
- Đây là **lớp lỗi thứ 2** (sau lỗi 'mail' vs 'email' sáng nay): câu nói của anh vô cùng đa dạng, không thể liệt kê đủ bằng kw tĩnh.

## 2. Giải pháp 2 tầng

### Tầng 1 — Kw động (fix ngay lớp câu có số)
Regex mới nhận dạng câu lệnh đọc email/luồng/soạn nháp có biến số:
- "Tóm tắt **5 email gần nhất** cho anh" → đọc hộp thư ✓
- "đọc **10 mail mới nhất**" ✓ — "tóm tắt **3 luồng** gần nhất" ✓
- Guard an toàn giữ nguyên: câu hỏi ("5 email gần nhất là gì?") không kích hoạt lệnh.

### Tầng 2 — Vòng tự học S1 (tự ghi nhận → đề xuất → anh duyệt → tự áp)
Module mới `tools/self_improvement.py` + wire vào responder:
1. **Tự ghi nhận**: mỗi câu anh nhắn mà CHERRY không hiểu → lưu vào `data/self_improve/unmatched.jsonl` (không phá chat, không log secret).
2. **Tự phân tích**: khi anh nhắn **"em tự học đi"** → thống kê bigram từ các câu chưa hiểu → tự ĐỀ XUẤT từ khóa mới kèm chức năng phù hợp (PENDING_REVIEW — chưa áp).
3. **Anh duyệt**: **"duyệt học <từ>"** → từ khóa chính thức vào registry.
4. **Tự áp**: từ đó câu chứa từ đó chạy đúng chức năng. Anh xem tiến trình: **"em tự hoàn thiện"**.

**Bất biến an toàn**: CHERRY KHÔNG tự áp gì — mọi thay đổi hành vi phải qua anh duyệt (giống R4 quarantine). Lỗi → báo thật, không fake "đã học".

## 3. Test evidence
- **test_self_improvement.py 10/10 PASS**: log never-raise; bigram stats đúng; propose KHÔNG tự áp; approve 1-lần (duyệt 2 lần → từ chối); kw lạ → fail-honest; detect_intent nhận kw learned; kw tĩnh hệ thống VẪN thắng kw learned.
- **Focused regression 114/114 PASS** (5.1s): + command_center 24/24 + office S1-S4.
- **E2E vòng tự học thật**: 3 câu lạ → "em tự học đi" → 3 đề xuất PENDING → "duyệt học tiến độ" → từ đó "xem tiến độ abc" chạy đúng tasks.
- **14/14 detect_intent**: câu của anh 10:55 + guard không phá lệnh cũ.
- Responder restart pid 2424 với code mới; server 8765 ONLINE.

## 4. Cách dùng cho anh
- **"em tự học đi"** — CHERRY phân tích các câu anh nhắn mà nó chưa hiểu → đề xuất từ khóa mới
- **"duyệt học <từ>"** — duyệt 1 đề xuất (ví dụ "duyệt học tiến độ")
- **"em tự hoàn thiện"** — xem hiện trạng tự học (đã ghi nhận bao nhiêu câu lạ, đã học bao nhiêu từ)
- Từ giờ nếu CHERRY trả lời sai năng lực, anh cứ nhắn lệnh tự nhiên — nó tự ghi nhận và lần sau đề xuất sửa

## 5. Trung thực — giới hạn S1
1. Tự học S1 chỉ học **từ khóa định tuyến** qua anh duyệt — CHERRY **KHÔNG tự sửa code, KHÔNG tự wire intent mới** (đó là Sprint tiếp theo nếu anh duyệt: tự đề xuất + tự sinh code nháp → quarantine → anh duyệt).
2. Đề xuất intent có thể lệch (vd 'tổng hợp' → email_today thay vì tasks) — là đề xuất, anh không duyệt thì không áp, không rủi ro.
3. GLM hội thoại vẫn có thể nói sai năng lực khi câu KHÔNG khớp lệnh nào — giảm dần khi kw động + learned phủ rộng. Fix gốc (bơm danh sách năng lực thật vào system prompt của GLM) là bước tiếp theo.
4. Chưa commit — chờ anh "duyệt commit".

## 6. Files thay đổi
- `tools/self_improvement.py` — MỚI (~280 lines)
- `tools/netchat_command_center.py` — kw động regex + intent self_improve + handler + learned registry
- `tools/netchat_auto_responder.py` — log_unmatched khi route None
- `tests/test_self_improvement.py` — MỚI (10 test)
- `docs/PROJECT_STATUS.md` — entry 24/11 ~11:10
