# AUDIT TỔNG THỂ CHERRY — 12/11/2026 16:45

## 1. KẾT QUẢ AUDIT (probe thật, không bịa)

### ✅ KHỎE (10/14 thành phần)
| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| Dual servers 8765/8766 | HEALTHY | /api/health 200, executive 105KB |
| brain.db | HEALTHY | health endpoint |
| Pi5 edge | READY | heartbeat 0.4s trước, RTT 29ms, paired |
| Pi5 kiosk 8768 | UP | HTTP 200 qua SSH |
| Pi5 RAM/disk | OK | 948/4049 MB used, disk 14% |
| Pi5 WiFi watchdog timer | ACTIVE | systemctl is-active=active, up 2h58m |
| PC watchdog | RUNNING | log cập nhật 16:38 (1m trước) |
| Responder heartbeat | LIVE | age 1s (threshold 150s) |
| Backup 2AM | PASS | Last Result 0, chạy 02:00:01 |
| Morning report 8AM | PASS | Last Result 0, chạy 08:00:01 |
| Task registry | HEALTHY | health endpoint |
| Learning daemon | ĐANG CHẠY | iteration 10, 6696 facts |

### ⚠️ PHÁT HIỆN VẤN ĐỀ (4)
1. **SPAM GREETING** — 10 tin "XIN CHÀO ANH QUANPT1" giống hệt nhau 14:01-14:23.
   Gốc: send_greeting_message() chạy MỖI lần responder start (line 1176) + restart loop.
   Restart loop do watchdog thấy heartbeat stale (289s > 150s) lúc 14:20:57.
   **ĐÃ DỪNG tự nhiên** từ 14:23 (responder ổn định lại, heartbeat LIVE).

2. **WATCHDOG RESTART LOOP** — watchdog "Watchdog Starting" 11 lần 14:01→14:21.
   KHOI_DONG_LOGON LastRun 14:15:54 trùng thời điểm — có thể user logon lại
   hoặc spawn_detached loop. KHÔNG tái diễn từ 14:21 (2h+ ổn định).

3. **Learning daemon log stale 39-75m** — watchdog báo DEGRADED/OFFLINE
   nhưng process vẫn chạy (iteration 10). Log ghi thưa → false alarm giám sát.

4. **ollama_daemon DISABLED** — BGE-M3 embedding không chạy (theo health endpoint).
   Ảnh hưởng: semantic search fallback, không critical (GLM cloud là chính).

## 2. NĂNG LỰC ĐIỀU KHIỂN QUA DM HIỆN TẠI (Command Center)
- 20 intents được hỗ trợ: approval_card, duty_roster_query, emergency_stop_device,
  pc_lock, pc_screenshot, todo_add, tony_analyze_image(_pro), tony_hdmi_approve,
  tony_music_stop, tony_pi_listen/photo/screenshot/video, tony_reverse_prompt,
  tony_speak_verbatim, tony_standby, ok_confirm, ok_silent, info_gap_reply
- 2 chiều: owner DM → detect_intent → route_message → thực thi → DM phản hồi
- Lịch sự: "Em ..." prefix được bỏ; câu hỏi '?' không trigger lệnh trừ khi bắt đầu bằng keyword

## 3. ĐÁNH GIÁ "TỰ VẬN HÀNH CHỦ ĐỘNG"
### Đã có (passive + scheduled proactive)
- Responder 2 chiều 24/7 (passive — chờ DM)
- Morning report 8AM (proactive 1 lần/ngày — scheduled)
- Pi5 monitor DM cảnh báo mất mạng >5min (proactive event-driven)
- Learning daemon tự học 5 phút/lần (proactive internal)
- Backup 2AM tự động

### Thiếu (gap để "cherry tự vận hành chủ động quản trị")
- **KHÔNG có proactive decisions**: Cherry không tự đề xuất việc cần làm
- **KHÔNG có health-driven actions**: phát hiện bất thường → tự hành động (restart, fix)
  mà chỉ DM báo (trừ Pi5 monitor)
- **KHÔNG có daily autonomous audit**: Cherry không tự audit hệ thống định kỳ
- **Greeting spam**: mỗi restart gửi greeting — cần dedupe/rate-limit

## 4. ĐỀ XUẤT PHƯƠNG ÁN TỰ VẬN HÀNH (chờ owner duyệt)
Xem section 5 — thiết kế "CHERRY AUTONOMOUS MODE" 3 lớp an toàn.


## 5. AUTONOMOUS MODE — ĐÃ TRIỂN KHAI (12/11, theo lệnh owner)

### Kiến trúc 3 lớp an toàn
- **LỚP 1 AUTO** (tự làm, không cần duyệt): restart servers khi chết 2 probe liên tiếp;
  restart responder khi heartbeat stale >300s; DM cảnh báo Pi5 mất >5 phút.
  Budget: tối đa 2 restart/thành phần/giờ — vượt → chuyển LỚP 2.
- **LỚP 2 PROPOSE** (DM xin duyệt 2 bước token): Ollama chết → đề xuất;
  disk >80% → đề xuất dọn. Cherry KHÔNG TỰ làm — owner trả lời mới thực thi.
- **LỚP 3 NEVER** (hard-block, có test guard): DROP/DELETE DB, rmtree, netsh,
  router, executive.js, secrets — KHÔNG BAO GIỜ.

### Chống spam (bài học 14:01-14:23 hôm nay)
- Greeting: chỉ gửi nếu lần trước >60 phút (data/greeting_last_sent.txt)
- Alert: rate-limit 30 phút/loại (data/cherry_autonomous_state.json)
- Restart: budget 2/giờ/thành phần

### Files
- tools/cherry_autonomous.py — daemon chính (chu kỳ 300s)
- tools/run_cherry_autonomous.bat + run_cherry_autonomous_hidden.vbs — launcher
- Task Scheduler: QUAN_AI_BRAIN_CHERRY_AUTONOMOUS (5 phút, idempotent qua marker)
- tests/test_cherry_autonomous.py (12 test) + tests/test_greeting_guard.py (3 test)

### E2E verify 12/11
- DM 2 bước token: PASS (message asei99e5i3drzfttgzq8qojxxy)
- DM propose thật: PASS 16:56:28 ("CHERRY đề xuất: Ollama không phản hồi...")
- Daemon ổn định: pid 3968 sống liên tục, probe chu kỳ 300s (state mtime 17:07:06)
- Marker idempotent: Task Scheduler trigger 5 phút KHÔNG spawn thêm instance

### Điều khiển bằng DM (đã có sẵn qua Command Center)
20 intents: approval_card, pc_lock, pc_screenshot, todo_add, tony_pi_photo/screenshot/
video/listen, tony_analyze_image(_pro), tony_reverse_prompt, duty_roster_query,
emergency_stop_device, tony_music_stop, tony_standby, tony_hdmi_approve,
tony_speak_verbatim, ok_confirm... — owner DM từ quanpt1 → detect_intent → thực thi.
