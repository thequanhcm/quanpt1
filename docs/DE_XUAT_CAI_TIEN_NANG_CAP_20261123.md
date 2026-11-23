# ĐỀ XUẤT CẢI THIỆN & NÂNG CẤP HỆ THỐNG — 23/11/2026

**Căn cứ:** `docs/QUAN_AI_BRAIN_CHERRY_SYSTEM_INTRO_20261123.md` (báo cáo hiện trạng 23/11)
**Nguyên tắc đề xuất:** Audit trước → đề xuất sau; mỗi hạng mục có tiêu chí nghiệm thu + rollback; không tuyên bố năng lực chưa có bằng chứng (fail-honest).
**Trạng thái:** ĐỀ XUẤT — chờ owner duyệt từng lô. Chưa làm gì trong tài liệu này.

---

## TỔNG QUAN 4 GIAI ĐOẠN

| Giai đoạn | Chủ đề | Số hạng mục | Ưu tiên |
|---|---|---|---|
| **P0** | Ổn định nền tảng (stability) | 4 | CAO — làm trước |
| **P1** | Hoàn thành những gì đang treo (pending) | 5 | CAO — song song P0 |
| **P2** | Nâng cấp trí tuệ (intelligence) | 5 | TRUNG BÌNH |
| **P3** | Mở rộng năng lực (capabilities) | 4 | THẤP — sau khi P0-P2 xong |

---

## P0 — ỔN ĐỊNH NỀN TẢNG (khắc phục điểm yếu thật, có bằng chứng)

### P0-1. Sửa 15 test fail trong baseline
**Hiện trạng (verify 23/11):** `reports/TEST_RUN_OFFICE_S1.txt` — 15 FAILED:
- 2 fail đã stash-proof là PRE-EXISTING: `test_cpsl_runner` (assert 13==12 — hardcode count), `test_ok_confirmation_flow` (Pi5 OFFLINE)
- 13 fail còn lại: avatar (3), edge client (2), cognitive_loop health (2), embedding bge-m3 (1), digital identity voice (1), media_only_dm (1), sentinel_s3 whitelist (1), backup freshness (1), web_executive telemetry (1)

**Đề xuất:** Phân loại từng fail: (a) do Pi5 OFFLINE → gắn marker skip-if-pi5-offline; (b) do hardcode count → sửa test đọc số thật; (c) do code thật lỗi → fix code; (d) test lỗi thời theo sprint cũ → cập nhật kỳ vọng. Mục tiêu: **full suite 0 failed** trong 2 sprint.
**Tiêu chí nghiệm thu:** `pytest` full → 0 failed (hoặc mọi skip có lý do ghi rõ trong code).
**Rollback:** từng fix 1 commit riêng, revert được độc lập.

### P0-2. Mirror backup sang ổ D (hiện chỉ có 1 bản trên E:)
**Hiện trạng (verify 23/11):** Ổ F: KHÔNG TỒN TẠI (`.gitignore` còn ghi "có bản sao F:\BRAIN" — đã sai). Backup DB 2AM + toàn bộ E:\BRAIN chỉ nằm trên 1 ổ vật lý. Ổ D trống 131 GB.
**Đề xuất:** Task mới `QUAN_AI_BRAIN_MIRROR_D_2AM` (chạy sau backup 2AM): robocopy E:\BRAIN → D:\BRAIN_MIRROR (exclude .venv, .git objects lớn, _QUARANTINE_*, __pycache__). Kèm kiểm md5 mẫu 5 file ngẫu nhiên mỗi tuần.
**Tiêu chí nghiệm thu:** mirror chạy 7 ngày liên tục không lỗi; khôi phục thử 1 file từ D thành công; báo cáo DM mỗi tuần.
**Rủi ro:** viết D: nhiều → chọn giờ 2:30AM, I/O thấp; dung lượng 131GB đủ (BRAIN dùng ~180GB, mirror phần code+data nhẹ ~30-40GB sau exclude).
**Rollback:** tắt task, xóa D:\BRAIN_MIRROR.

### P0-3. Dọn hẳn quarantine + chuẩn hóa quy trình rác
**Hiện trạng:** `_QUARANTINE_20261123/` 11.88 GB đang chiếm chỗ (move nội bộ chưa giải phóng). Không có quy trình tự động chống rác tái tích lũy (tmp render avatar từng phình 11.7GB trong 3 ngày).
**Đề xuất:** (a) Owner "duyệt dọn" → xóa hẳn folder; (b) thêm cleanup vào backup 2AM: tự xóa file tmp >7 ngày trong `.tmp_*`, `data/tmp_*`, `%TEMP%/cherry_*`; (c) giới hạn cứng: tmp render chỉ được ghi vào `.tmp_motion_frames/` và tự xóa sau mỗi session render.
**Tiêu chí nghiệm thu:** E: giải phóng 11.88GB; 30 ngày sau tmp không vượt 1GB.
**Rollback:** manifest trong AUDIT_SYNC giữ đường dẫn gốc — khôi phục được từ D-mirror trước khi xóa.

### P0-4. Siết watchdog liveness cho 4 task nền
**Hiện trạng:** 4 task READY nhưng nếu 1 task chết im lặng (ví dụ vbs lỗi không chạy) thì chỉ phát hiện qua thiếu log — chưa có cảnh báo chủ động. `KHOI_DONG_LOGON` + `LIVENESS_30MIN` đang Disabled.
**Đề xuất:** thêm heartbeat file: mỗi task ghi `data/heartbeat_<ten>.json` khi chạy xong; morning_report 8AM kiểm heartbeat — task nào quá hạn (sync >30', monitor >15', backup >26h) → DM cảnh báo trong báo cáo sáng. KHÔNG bật lại auto-restart (giữ nguyên manual-start của owner).
**Tiêu chí nghiệm thu:** simulate 1 task chết → DM cảnh báo trong lần report kế tiếp.
**Rollback:** heartbeat là read-only bổ sung, không tác động task cũ.

---

## P1 — HOÀN THÀNH NHỮNG GÌ ĐANG TREO (nhiều item đã chờ duyệt từ trước)

### P1-1. Commit các lô đang chờ (gợi ý thứ tự commit)
**Hiện trạng:** HEAD = 118afe1; working tree có ~100 thay đổi trong đó nhiều lô đã test xong chờ duyệt commit: (1) console 1 cửa sổ + anti-spam NetChat; (2) mail_reader SOAP 268 dòng + voffice_reader 134 dòng; (3) Office Sprint 1a (office/ package + tests 24/24 + wire DM); (4) đồng bộ audit + wire `lịch họp` (23/11); (5) Vmail Sprint 0 audit docs.
**Đề xuất:** owner "commit" → commit theo lô conventional-commit (5-7 commits), KHÔNG `git add .`, mỗi lô kèm test đã chạy. Sau đó push origin.
**Tiêu chí nghiệm thu:** mỗi commit chạy test lô đó PASS trước khi commit; push xong CI/local suite không thêm fail mới.

### P1-2. Sprint 1 VMAIL — VmailConnector class (card TASK-VMAIL-S1 PENDING_APPROVAL)
**Hiện trạng:** audit xong (SOAP probe 13 folder + conversation search OK; GetInfo 500; IMAP loại). Card chờ duyệt.
**Đề xuất:** đóng gói mail_reader SOAP thành class VmailConnector với interface §4.3 (authenticate, list_folders, list_messages, get_message, search_messages, get_thread, get_connection_health) + StructuredResult (status/operation_id/evidence) + GHI → `unsupported_by_policy`. Tái dùng 100% SOAP đã probe, KHÔNG viết I/O mới.
**Tiêu chí nghiệm thu:** tests mock ≥90% coverage interface; live smoke đọc 3 folder thật; health state đúng §13.
**Security:** chỉ đọc; token vẫn loader; không log secret.

### P1-3. Sprint 1b OFFICE — Thread Analyzer
**Hiện trạng:** 10 email phân nhóm tốt nhưng 3 mail "[Hủy cuộc họp]" chưa ghép được với mail gốc (Known Issues Sprint 1a); SOAP conversation search đã probe OK.
**Đề xuất:** ghép luồng theo subject-normalize + In-Reply-To/References + conversation SOAP; tổng hợp mỗi thread: tham gia, quyết định, deadline, trạng thái (đang chờ ai).
**Tiêu chí nghiệm thu:** thread test gồm "[Hủy cuộc họp]" ghép đúng gốc; DM "tóm tắt luồng email X" trả đúng 10 mục.

### P1-4. M-Suite tunnel — hoàn tất Voffice TRỰC TIẾP
**Hiện trạng:** mọi thứ sẵn sàng, chỉ chờ owner đăng nhập app Mobility Suite Agent (1 cú Enter) → tunnel 10.60.7.120.
**Đề xuất:** giữ hiện trạng chờ; khi owner nhắn "xong" → Cherry ping 5s/lần → scrape VoIP trực tiếp → wire voffice_reader nguồn trực tiếp (gián tiếp mail vofficeadmin làm fallback).
**Tiêu chí nghiệm thu:** ping voffice OK + đọc được 1 trang Voffice thật; KHÔNG đụng encrypted_store (R4/R5).

### P1-5. Kiểm tra BAT console trên máy thật
**Hiện trạng:** console 1 cửa sổ + anti-spam đã code xong, chờ owner double-click `KHOI_DONG_CHERRY.bat` kiểm tra thật rồi mới commit.
**Đề xuất:** owner chạy BAT 1 lần (5 phút): xác nhận 1 cửa sổ duy nhất, không spam NetChat, tắt sạch bằng TAT_CHERRY.

---

## P2 — NÂNG CẤP TRÍ TUỆ (sau khi P0-P1 xong)

### P2-1. Shared Memory Integration (Sprint 3 VMAIL)
Email/thluồng/biên bản họp nạp vào Memory 3 tầng với nguồn dẫn (message-id, thời điểm) — câu hỏi "dự án Battery AI thế nào?" tổng hợp được từ email + memory + tài liệu, kèm nguồn + thời điểm cập nhật + cảnh báo dữ liệu cũ. Đây là năng lực trung tâm của master prompt VMAIL (ví dụ chuẩn §I).

### P2-2. Context-Aware Reply Draft (Sprint 4 VMAIL)
Soạn 3 phương án phản hồi theo lịch sử luồng + giọng owner (VI/EN), **DRAFT-ONLY R2** — gửi email chỉ khi owner phê duyệt riêng từng lần. Tận dụng semantic memory để đề xuất đúng ngữ cảnh dự án.

### P2-3. Workflow Engine cho nghiệp vụ email (Sprint 5)
Bảng hành động được phép (đánh dấu đọc/xóa/chuyển thư mục) qua approval card từng lần; executor chạy staging + rollback; KHÔNG có hành động ngoài whitelist. Báo cáo daily 6 mục master prompt §16 tự động 8AM (mở rộng morning_report hiện có).

### P2-4. Dashboard KPI tầng 2
Dashboard 8766 hiện có PC/Pi5 health — thêm tab Intelligence KPI: recall@3, thời gian phản hồi DM, % email phân loại đúng (owner chấm mẫu 20 email/tuần), uptime task 24/7 (từ heartbeat P0-4). Mục tiêu KPI ≥95% đo được, không tự khai.

### P2-5. Hợp nhất tầng phân tích email
`email_intelligence.py` (331 dòng, 5 nơi import, dashboard đang dùng) vs `office/email_connector.py` (10 nhóm, mới) đang overlap nhẹ. Sprint 2 VMAIL hợp nhất thành 1 tầng phân tích duy nhất, email_intelligence trở thành wrapper tương thích để không vỡ dashboard.

---

## P3 — MỞ RỘNG NĂNG LỰC (dài hạn, từng cái có duyệt riêng)

### P3-1. Voice Intelligence trên Pi5
Wake "Cherry ơi" + STT faster-whisper (đã có nền ghi âm PC) + TTS Hoài My đã có — nâng cấp thành hội thoại 2 chiều qua loa/mic Pi5; cần duyệt riêng vì đụng audio routing (đã ổn định).

### P3-2. IoT / UDC-1 mở rộng
Device list + emergency stop đã có; thêm scene tự động (ví dụ "về nhà" bật đèn + điều hòa) qua approval card, mỗi thiết bị có R4 riêng.

### P3-3. Auto-healing có kiểm soát
Hiện watchdog chỉ cảnh báo; nâng cấp: tự restart trong whitelist (server 8765/8766, responder) + DM thông báo; mọi restart ngoài whitelist vẫn cần duyệt. Áp dụng sau khi heartbeat (P0-4) chạy ổn 2 tuần.

### P3-4. Đa agent sơ bộ
Kiến trúc Shared Cognitive Core sẵn sàng cho agent thứ 2 (ví dụ agent báo cáo tuần tự động tổng hợp Sprint). Chỉ thiết kế, không code trước khi owner duyệt design signoff (đúng quy trình Sprint 5-6 cũ).

---

## BẢNG ƯỚC LƯỢNG & THỨ TỰ ĐỀ XUẤT THỰC HIỆN

| STT | Hạng mục | Ước lượng | Phụ thuộc |
|---|---|---|---|
| 1 | P1-1 Commit các lô | 30-60' | owner "commit" |
| 2 | P0-3 Dọn quarantine | 5' | owner "duyệt dọn" |
| 3 | P1-5 Test BAT console | 5' owner | — |
| 4 | P1-4 M-Suite login | 1' owner | — |
| 5 | P0-2 Mirror ổ D | 2-3h | — |
| 6 | P0-4 Heartbeat | 2h | — |
| 7 | P1-2 VmailConnector (S1) | 1 sprint | card TASK-VMAIL-S1 |
| 8 | P1-3 Thread Analyzer (S1b) | 1 sprint | S1 |
| 9 | P0-1 Sửa 15 test fail | 2 sprint rải | — |
| 10 | P2-1 → P2-5 | 3-4 sprint | P0-P1 |
| 11 | P3-1 → P3-4 | từng cái duyệt riêng | P2 |

## BỘ LỆNH DUYỆT (owner chỉ cần nhắn 1 từ)

- **"duyệt dọn"** → xóa `_QUARANTINE_20261123/` (giải phóng 11.88GB)
- **"commit"** → commit các lô theo STT 1 ở trên
- **"duyệt"** → Sprint 1 VmailConnector (card TASK-VMAIL-S1 đang chờ)
- **"xong"** → sau khi login M-Suite, Cherry quét VoIP trực tiếp
- **"duyệt mirror"** → làm P0-2 (mirror ổ D)
- **"duyệt heartbeat"** → làm P0-4 (cảnh báo task chết)

---

*Fail-honest: mọi mục P2-P3 chỉ là THIẾT KẾ — chưa có gì được coi là làm được cho tới khi có test evidence + live smoke + owner nghiệm thu từng sprint.*
