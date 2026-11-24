# BÁO CÁO VMAIL ĐỌC + TOGGLE BẬT/TẮT — 24/11/2026

**Yêu cầu owner** (ảnh image_be6a17, 09:45): "em cấu hình chức năng đọc vmail và tắt/bật vmail khi anh yêu cầu"
**Kết quả**: ✅ TRIỂN KHAI + TEST — 18/18 detect_intent + 7/7 route E2E + 104/104 focused regression + đọc mail thật 24s.

## 1. Vấn đề thật từ ảnh
- Owner nhắn **"Tóm tắt các nội dung mail"** → CHERRY trả lời *"em chưa có công cụ truy cập hộp thư"* (09:45).
- Nguyên nhân: kw của `email_today` chỉ có chữ **"email"** — câu của anh dùng chữ **"mail"** trơn → `detect_intent` trả `None` → tin rơi vào GLM hội thoại (nên mới nói "chưa có công cụ").
- Thêm: "tắt vmail" trước nay bị nuốt thành `pc_close` (lệnh đóng app PC) — sai an toàn.

## 2. Đã làm (4 việc đã duyệt)
| # | Việc | Kết quả |
|---|---|---|
| 1 | Mở rộng kw `email_today` (+17: đọc mail, mail hôm nay, tóm tắt mail, nội dung mail, đọc vmail, vmail hôm nay, kiểm tra mail/vmail…) | Câu của anh → `email_today` ✓ |
| 2 | Intent mới `vmail_toggle` + `handle_vmail_toggle`: tắt vmail / bật vmail / trạng thái vmail | Ưu tiên TRƯỚC pc_open/pc_close — không bị nuốt |
| 3 | Feature flag `data/vmail_enabled.json` + gate 3 handler đọc (email_today, thread_summary, reply_draft) | Tắt = từ chối đọc + KHÔNG gọi SOAP; R2 chỉ-đọc giữ nguyên |
| 4 | Test + regression + E2E đọc mail thật | PASS toàn bộ |

## 3. Test evidence
- **detect_intent 18/18**: "Tóm tắt các nội dung mail"→email_today; "tắt vmail/bật vmail/trạng thái vmail/tắt đọc vmail/bật chức năng vmail"→vmail_toggle; "đọc mail/mail hôm nay/tóm tắt mail/đọc vmail/vmail hôm nay"→email_today; guard: "tắt nhạc"→tony_music_stop, "tắt pi5"→tony_off, "tắt chrome"→pc_close (đóng app, không phải vmail), "kiểm tra email"→email_today, "tóm tắt email"→thread_summary, "soạn trả lời email báo cáo"→reply_draft, "lịch họp hôm nay"→voffice_meetings, "trạng thái"→status.
- **route_message E2E 7/7**: "trạng thái vmail" → BẬT; "tắt vmail" → OFF + cả 3 handler đọc đều từ chối (không SOAP); "bật vmail" → ON; "tắt chrome" → pc_close vẫn đúng; trạng thái lần 2 → BẬT.
- **Focused regression 104/104 PASS** (5.6s): test_netchat_command_center + test_office_email_connector + test_office_thread_analyzer + test_office_reply_drafter + test_vmail_tool.
- **Live E2E đọc mail thật** (SOAP 24s, exit=0): 10 mail mới, 8 quan trọng (ACTION_REQUIRED 5, URGENT 3, INFORMATION 2) — top: PM GVM gửi báo cáo nguồn ngày đêm 23/11 (priority 72/100).

## 4. Cách dùng cho anh (DM CHERRY)
- **Đọc + tóm tắt**: "đọc mail" / "tóm tắt các nội dung mail" / "mail hôm nay" / "tóm tắt luồng email"…
- **Tắt đọc vmail**: "tắt vmail" → CHERRY ngừng đọc hộp thư (mọi lệnh đọc đều từ chối khéo).
- **Bật lại**: "bật vmail".
- **Xem trạng thái**: "trạng thái vmail".

## 5. Trung thực — giới hạn hiện tại
- E2E qua DM thật chưa tự test được từ phía em: tin test gửi bằng **bot token** bị responder lọc đúng thiết kế (chống echo — BOT_USER_ID guard `netchat_auto_responder.py:1448`). Anh nhắn từ tài khoản owner sẽ ăn ngay (route_message với sender_user_id owner đã verify 3/3).
- Responder đã restart với code mới (pid 21096, 10:42, heartbeat OK).
- Side effect thật khi test: Chrome bị đóng 1 lần lúc verify "tắt chrome"→pc_close (handler thật). Anh mở lại nếu đang dùng.
- Khi BẬT, chế độ vẫn **CHỈ ĐỌC** (R2): không gửi/không đánh dấu đã đọc/không xóa. Gửi mail chỉ khi anh duyệt riêng từng lần.

## 6. Files thay đổi
- `tools/netchat_command_center.py` — kw email_today +17, intent vmail_toggle + handler + flag + gate 3 handler + route 2.5 + help menu.
- `data/vmail_enabled.json` — flag mới (hiện BẬT).
- `docs/PROJECT_STATUS.md` — entry 24/11 ~10:45.
- Chưa commit — chờ anh "duyệt commit".
