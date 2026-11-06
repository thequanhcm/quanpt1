# ĐẢM BẢO "TOÀN BỘ CÂU HỎI DM ĐƯỢC PHẢN HỒI" — WATCHDOG LỚP 2 + LOG CLEAN (06/11)

**Owner (19:39):** "toàn bộ các câu hỏi của anh DM em đều phải phản hồi"

## Hành động (tiếp nối fix _NO_WIN 19:31)

### 1. Watchdog lớp 2 — phát hiện "im lặng có lý do" (tools/watchdog.py:204-243)
Trước: watchdog chỉ đọc mtime heartbeat → responder NameError vẫn được coi LIVE (mù lòa).
Sau: `check_netchat_bot()` thêm **lớp 2** — heartbeat LIVE nhưng stdout log có
**≥3 fatal error lặp lại trong 5 phút gần nhất** (`is not defined`/`SyntaxError`/
`AttributeError`/`Traceback`) → coi như unhealthy → `ensure_daemon_alive` tự restart
(cap 5 lần/giờ như chuẩn server).

- Verify test: chèn 114 lỗi "not defined" vào tail → check trả **False** với log
  `[ERROR] heartbeat LIVE nhưng stdout có 118 fatal error lặp lại — coi như unhealthy`
- Log sạch → check trả **True**

### 2. Sửa pattern đếm lỗi
Lần đầu đếm `"NameError"` = 0 hit dù 114 lỗi — vì `print(f"...{e}")` in `str(e)`
("name '_NO_WIN' is not defined") **không chứa tên class**. Đổi pattern theo text thật.

### 3. Dọn log stdout (86.200 → 200 dòng sạch)
71.743 dòng test/lỗi cũ tích tụ từ 30/10 (mỗi vòng poll × 2 nguồn × lỗi) — xóa để
lớp 2 không false-positive và log đọc được.

### 4. Restart watchdog để nạp code lớp 2
Watchdog cũ (PID 19220/9160) → mới (15648/17416) — đang chạy, spawn lại dual servers 8765+8766.

## Verify cuối (bằng chứng thật)

| Check | Kết quả |
|---|---|
| Responder process | PID 18536→15240 ổn định (không restart-loop sau 60s) |
| Heartbeat | 1s — LIVE |
| `check_netchat_bot()` | True (không lỗi fatal trong tail) |
| Tin test gửi DM qua bot | 19:47:17 gửi OK (confirm gate 2 bước token 5b17800c6675) |
| Dual servers 8765+8766 | DEGRADED (chỉ ollama đã gỡ) — core/db/task HEALTHY |

## Cam kết phản hồi DM (thiết kế sau hôm nay)

1. Tin owner vào DM → responder poll ≤10s → AI xử lý → trả lời (auto-confirm token)
2. Responder chết → heartbeat stale → watchdog restart ≤150s
3. Responder "sống nhưng câm" (fatal lặp) → lớp 2 phát hiện → restart ≤ health_check_interval
4. Sau restart: `CATCHUP_WINDOW_MIN=720` quét lại **mọi tin 12 giờ qua chưa trả lời** — không bỏ lỡ tin nào

## Trạng thái: FIXED + LIVE_VERIFIED
