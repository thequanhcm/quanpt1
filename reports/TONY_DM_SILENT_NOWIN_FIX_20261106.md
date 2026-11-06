# FIX TONY CÂM DM — _NO_WIN NameError CHẾT POLL LOOP (06/11)

**Owner:** "không thấy phản hồi" — tin DM 18:45 "Anh đã kết nối lại pi5..." không được TONY trả lời.

## Điều tra (audit trước sửa sau)

1. **Heartbeat LIVE** (2s) — watchdog vẫn tưởng responder khỏe → **mù lòa**: heartbeat chỉ chứng minh
   vòng lặp chạy, KHÔNG chứng minh poll đọc tin sống
2. Log stdout thật (`logs/netchat_auto_responder_stdout.log`): lặp vô hạn
   `Error reading dm messages: name '_NO_WIN' is not defined` — **NameError 17 chỗ**
3. Root cause: patch 30/10/2026 (fix UTF-8 tổng lớp) định nghĩa wrapper
   `_subprocess_run_no_window` nhưng **xóa mất hằng `_NO_WIN`** — 17 chỗ gọi
   `creationflags=_NO_WIN` còn nguyên → mỗi lần đọc tin/gửi trả lời đều NameError
4. Loop bắt `except Exception` → print lỗi → chạy tiếp → **process sống, heartbeat LIVE,
   nhưng không đọc được tin nào** → TONY câm hoàn toàn từ patch 30/10
5. Tin 18:45 KHÔNG có trong `answered_ids` (state file) — không hề "đã trả lời"; nó bị nuốt

## Fix

- `tools/netchat_auto_responder.py` dòng 66: khôi phục
  `_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)` (có comment giải thích root cause)
- Syntax OK; kill responder cũ (PID 23432/21156) → start mới (PID 18536→15240)

## Verify E2E (bằng chứng thật)

- Log mới: `[STARTUP] 1 tin nhắn mới trong 720 phút qua — sẽ trả lời` →
  `📩 New message at 11:45:41: Anh đã kết nối lại pi5...` → `🤖 Processing...` → `✅ Response sent!`
- **Đọc lại DM: tin 18:45 đã được trả lời 19:32:25** — "Dạ, em vừa probe lại toàn bộ kết nối:
  Pi 5 (hình thể): HOẠT ĐỘNG..." (probe thật, không bịa)
- Log sạch: không còn `_NO_WIN` NameError

## Bài học (fail-honest)

**Heartbeat LIVE ≠ poll sống.** Watchdog `check_netchat_bot` chỉ đọc mtime heartbeat —
cần bổ sung: grep stdout log cho `NameError|SyntaxError|Traceback` gần nhất → cảnh báo
(im lặng có lý do phải được phát hiện). Đề xuất sprint kế.

## Trạng thái: FIXED + LIVE_VERIFIED (tin cũ được trả lời thật 19:32)
