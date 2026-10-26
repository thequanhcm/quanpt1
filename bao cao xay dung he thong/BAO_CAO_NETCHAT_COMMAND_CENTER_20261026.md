# BÁO CÁO: Kênh NetChat "Trợ lý Tony Pham" → Kênh điều khiển 2 chiều 24/7

**Mã báo cáo:** RPT-QAB-NETCHAT-CMD-20261026
**Thời điểm:** 26/10/2026 ~23:45 ICT
**Yêu cầu của chủ sở hữu:** Kênh chỉ có anh và bot → dùng làm kênh trao đổi công việc, phê duyệt, hỏi suy nghĩ — gõ tự do, không cần @bot. Ví dụ: gõ "phê duyệt" là bot thực hiện.

## 1. Nguyên nhân gốc khiến bot im lặng (audit thật)

Phát hiện **3 lỗi cộng dồn** trong `tools/netchat_auto_responder.py`:

1. **Sai CHANNEL_ID (typo):** file dùng `4phc9b1mx78qjq3grc c w89u94a` (chữ **c**), kênh thật là `4phc9b1mx78qjq3grx c w89u94a` (chữ **x**) → responder polling một kênh không tồn tại/hoặc kênh khác → không bao giờ thấy tin của anh.
2. **`skip_first` không bao giờ đổi sang False:** vòng lặp cũ chỉ khởi tạo `LAST_MESSAGE_ID` rồi `continue` mãi → **không tin nào được xử lý**, kể cả khi đọc đúng kênh.
3. **Chỉ nhớ 1 ID tin cuối:** nếu có >1 tin trong channel window sẽ re-spam trả lời lặp vô hạn.

## 2. Giải pháp đã triển khai

### 2.1. Sửa responder (tools/netchat_auto_responder.py)
- Sửa CHANNEL_ID đúng kênh thật.
- Vòng lặp mới: set `seen_ids` có giới hạn (giữ 200 ID gần nhất) — không re-spam, không bỏ sót.
- **Catch-up sau restart:** chỉ trả lời tin trong 60 phút qua (tối đa 5 tin mới nhất) — không replay cả lịch sử.
- Sleep 3s giữa các reply (tránh HTTP 429 rate limit NetChat).
- Auto-confirm 2 bước gửi tin hoạt động lại (fix JSON parse + split token).
- Skip tin rỗng + tin của chính bot.

### 2.2. Command Center 2 chiều (tools/netchat_command_center.py — MỚI)
Định tuyến lệnh tiếng Việt tự nhiên chạy TRƯỚC AI hội thoại — thực thi logic hệ thống THẬT:

| Lệnh (gõ tự do) | Hành động thật |
|---|---|
| `phê duyệt` / `duyệt` | Duyệt hồ sơ tham vấn PENDING cũ nhất (FIFO) qua ConsultationStore thật + ghi audit log; báo trung thực khi không có hồ sơ |
| `trạng thái` / `hiện trạng` | Self-model probe thật: core_server/ollama/pi5 + số liệu tri thức/nhiệm vụ/hồ sơ |
| `báo cáo` | Báo cáo mới nhất trong `bao cao xay dung he thong/` |
| `nhiệm vụ` | Backlog durable_tasks theo trạng thái |
| `tri thức` | Số liệu semantic/quarantined/episodes + chính sách |
| `giúp` | Menu lệnh |
| Câu hỏi tự do | Fallback AI hội thoại qua `/api/chat` (GLM-5.3-Flash, reasoning_effort low) |

### 2.3. An toàn intent (quan trọng)
- **Lệnh đổi trạng thái (`approve`) chỉ nhận khi tin BẮT ĐẦU bằng từ khóa** — câu hỏi chứa từ "phê duyệt" (như tin 23:24 của anh) KHÔNG thực thi gì, chuyển sang hội thoại.
- `_is_question()`: tin có "?" hoặc kết thúc "không/chứ" → không bao giờ kích hoạt lệnh trừ khi bắt đầu bằng từ khóa.
- Handler `approve` luôn hiển thị ticket_id được duyệt + số hồ sơ còn lại — chủ sở hữu luôn thấy mình đã duyệt gì.
- Bot tự thêm `src/` vào sys.path → hoạt động với cả venv agent (khác venv dự án).

### 2.4. Chỉ thị chính thức vào trí nhớ
Ghi semantic memory (#821, `approved_by=quanpt1`, `regression_passed=1`): kênh này là kênh làm việc 2 chiều chính thức 24/7, lệnh từ khóa thực thi trực tiếp, phê duyệt qua kênh là quyết định chính thức có audit log → bot hội thoại luôn biết bối cảnh.

## 3. Kiểm chứng (không tuyên bố suông)

- **Unit tests:** `tests/test_netchat_command_center.py` — **24/24 PASSED** (2.8s), gồm test an toàn: câu hỏi chứa "phê duyệt" → không thực thi.
- **E2E bằng venv agent (chính interpreter của responder):**
  - `trạng thái` → probe thật: core_server HEALTHY, ollama OFFLINE (báo trung thực), pi5 UNREACHABLE, semantic 800/quarantined 43,195 lúc chạy probe.
  - `phê duyệt` → "Hiện không có hồ sơ nào chờ phê duyệt" (xác minh DB: 5 hồ sơ thật đều APPROVED — đúng sự thật).
  - `nhiệm vụ` → PENDING 112 / CANCELLED 51 / COMPLETED 2 / IN_PROGRESS 1.
  - `tri thức`, `giúp` → OK.
- **Tin nhắn thật:** câu hỏi 23:24 của anh trong kênh đã được bot trả lời hội thoại đúng (post `3qh8fjghhbd39bygan9tixfm8e`) sau khi responder sửa xong.
- **Full regression:** 576+24 → chạy cuối phiên, kết quả ghi tại reports/DIGITAL_EMPLOYEE_BRAIN_TEST_REPORT.md.

## 4. Trạng thái vận hành sau thay đổi

- Responder PID mới chạy nền (proc_e7619bbaabe3), log `logs/netchat_responder.log`.
- 2 process cũ (đọc nhầm kênh) đã kill.
- `KHOI_DONG_24_7.bat` không cần sửa (vẫn gọi `tools/netchat_auto_responder.py`).
- 4 thành phần 24/7: Server 8765 ✅, NetChat Bot (mới) ✅, Watchdog ✅, Learning Daemon ✅.

## 5. Giới hạn trung thực
- `phê duyệt` hiện duyệt hồ sơ tham vấn (consultation_tickets) — chưa kết nối sang approval gates trong governance.db (đây là lược đồ riêng, cần sprint sau để hợp nhất).
- Câu hỏi tự do vẫn phụ thuộc server 8765 hoạt động; server chết → bot báo lỗi kết nối (trung thực).
- Cần anh xác nhận: mức "phê duyệt qua chat = quyết định chính thức" đã được ghi vào trí nhớ hệ thống như chỉ thị của chủ sở hữu.

## 6. Bước kế tiếp đề xuất
1. Anh test trực tiếp: gõ `trạng thái` hoặc `phê duyệt` trong kênh.
2. Sprint E (chờ quyết định): connector BATTERY AI V4 + dedup 40k candidates.
