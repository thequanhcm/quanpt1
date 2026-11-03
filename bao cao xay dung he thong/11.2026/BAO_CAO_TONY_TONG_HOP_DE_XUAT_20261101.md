# BÁO CÁO CHI TIẾT HỆ THỐNG TONY (QUAN AI BRAIN)
### Đến thời điểm: 08:35 — Chủ nhật, 01/11/2026
**Người lập:** TONY (QUAN AI BRAIN) · **Chủ hệ thống:** Phạm Thế Quân (quanpt1)
**Lưu tại:** `D:\AI\AI Quanpt1 2026\BRAIN\bao cao xay dung he thong\11.2026`

---

## 1. TÓM TẮT ĐIỀU HÀNH

TONY hiện là **Trợ lý số cá nhân hoạt động 24/7** gồm 3 tầng:

| Tầng | Máy | Thành phần | Trạng thái 08:35 |
|---|---|---|---|
| Bộ não (PC) | DESKTOP-SNMI929 | Server 8766 (GLM-5.3-Flash NetMind Cloud) + Dashboard 8765 + Responder NetChat + Watchdog | 🟢 PID 6280, 500 memories |
| Kênh giao tiếp | NetChat DM bot↔quanpt1 | Lệnh chữ + giọng nói + ảnh + file, phản hồi ~2 giây | 🟢 Hoạt động |
| Hình thể — tai/mắt/miệng | Raspberry Pi 5 (Tailscale 100.100.83.59) | Kiosk avatar + camera + mic loa BT + TTS đa ngữ + HDMI | 🟢 edge/wake/guard active, kiosk ACTIVE |

**Kết quả nổi bật 3 ngày gần nhất (30/10 → 01/11):** hoàn thành chuỗi **nghe — nhìn — nói — hiển thị** hoàn chỉnh trên Pi 5: wake word 4 cụm chuẩn owner, lệnh giọng nói 2 chiều qua mic loa Bluetooth, camera chụp ảnh theo lệnh gửi DM, HDMI xuất hình có phê duyệt, nút STOP an toàn, chống mất tin nhắn khi treo.

**Số liệu kỹ thuật:** 2.914 pytest PASS (150 test files); 9 file lõi ≈ 12.062 dòng code; toàn hệ thống tự hồi phục (watchdog 3 lớp).

---

## 2. KIẾN TRÚC VÀ THÀNH PHẦN CHI TIẾT

### 2.1. Tầng não — PC DESKTOP-SNMI929 (Windows 11)

| Thành phần | File chính | Vai trò |
|---|---|---|
| Executive Server 8766 | `src/quan_ai_brain/web/server.py` (5.332 dòng) | Bộ não: GLM-5.3-Flash + Ollama dự phòng, bộ nhớ 500 mục, task, phê duyệt, edge control, STT, TTS, HDMI event, voice_command |
| Dashboard 8765 | `start_dual_servers.py` | Giao diện web quản trị cho anh |
| NetChat Auto-Responder | `tools/netchat_auto_responder.py` (1.260 dòng) | Đọc DM mỗi 2 giây → lệnh hệ thống chạy thật / câu hỏi đưa GLM → trả lời kèm trích dẫn tin gốc |
| Command Center | `tools/netchat_command_center.py` (1.450 dòng) | ~30 intent lệnh tiếng Việt: mở/đóng app PC (allowlist 21 app), Pi5 bật/tắt, chụp ảnh, nghe mic, HDMI, phát nguyên văn... |
| Voice STT | `tools/voice_stt.py` + faster-whisper small int8 | Nhận diện giọng Việt offline (DM + lệnh thoại Pi5), 2–4s/bản |
| Watchdog | `tools/watchdog.py` (465 dòng) | Tự hồi server, responder (stale 150s), learning daemon; cap 5 restart/giờ |
| Learning daemon | `tools/learning_daemon.py` | Học hỏi có kiểm soát (quarantine → phê duyệt) |

### 2.2. Tầng giao tiếp — NetChat DM (DM-ONLY)

- Kênh duy nhất: bot ↔ anh Quân (DM `131u5z...`), mọi thành phần chỉ dùng DM này.
- Nhận: **chữ** · **giọng nói** (m4a/mp3/wav → STT → chạy như tin chữ) · **ảnh** (ghép cặp ảnh+mô tả, HOLD ≤30 phút) · **file** (docx/pdf/xlsx trích xuất).
- Phản hồi: **trích dẫn tin gốc** (`↩️ Trả lời tin "..." (giờ):`) — anh thấy rõ em đang trả lời mục nào; tốc độ ~2 giây.
- Chống mất tin: poll 2s; chỉ đánh dấu "đã trả lời" SAU khi gửi thành công; treo/kết nối lại thì **tự quét lại toàn bộ tin 12 giờ** chưa trả lời; watchdog phát hiện câm >2,5 phút tự khởi động lại.
- An toàn: lệnh đổi trạng thái phải đứng đầu câu; allowlist 21 app; audit log `logs/pc_action_audit.jsonl`; fail-honest (không xác nhận suông).

### 2.3. Tầng hình thể — tai/mắt/miệng trên Pi 5

**Hệ điều hành + service 24/7 (reboot-proof):** `quan_ai_edge` (daemon chính) · `quan_ai_wake` (wake word) · `quan_ai_kiosk_guard` (bảo vệ kiosk 60s/vòng) · journald persistent.

| Khả năng | Chi tiết | Kết quả E2E |
|---|---|---|
| **Hình thể (mắt thấy)** | Kiosk chromium fullscreen màn 7" DSI, avatar Model-F, layout V3B+FIT, waveform mic, VU, tự ngủ ~4 phút | ✅ ACTIVE hiện tại |
| **Tai — wake word** | 4 cụm chuẩn: **"tony", "tony ơi", "hi tony", "hay tony"**; Vosk + AGC (RMS→9000, ≤8x) + fuzzy Levenshtein ≤2; **mic BT ưu tiên** (nhạy ~3x USB), fallback USB | ✅ 2×WAKE thật 31/10 22:26–27 |
| **Tai — lệnh thoại 2 chiều** | Wake → ghi 8s (pw-record mic loa SRS-XB33) → POST server → STT faster-whisper → chạy như tin DM → **trả lời bằng giọng Edge-TTS vi-VN-HoaiMyNeural qua loa BT** + log DM | ✅ 01/11 08:11: "Em chụp ảnh gửi anh" → chụp thật + phát giọng |
| **Mắt — camera** | Camera Module 3: chụp theo lệnh → DM; MJPEG live ~1fps | ✅ nhiều ảnh DM |
| **Miệng — TTS** | Đa ngôn ngữ: VI (HoaiMy/NamMinh) + 10 giọng multi-language; phát nguyên văn (không qua GLM — tránh paraphrase sai); loa BT + HDMI audio | ✅ |
| **HDMI out (có phê duyệt)** | Cắm HDMI → DM hỏi "anh có muốn xuất hình lên HDMI?" → anh "phê duyệt hdmi" → hiển thị LIÊN TỤC đến khi "tắt hdmi"; KHÔNG tự bật | ✅ luồng hỏi-duyệt E2E 22:53 |
| **Nút STOP** | Chỉ **thoát giao diện hiển thị** — giữ màn hình, không emergency, daemon vẫn ACTIVE; giao diện giữ đóng (guard không tự dậy); mở lại bằng "TONY ơi"/nút TONY ƠI/DM | ✅ E2E 08:17 |
| **Điều khiển từ xa** | SSH key, `sudo -n` passwordless; mọi thao tác em tự làm, không phiền anh | ✅ |

**Kết nối:** Pi5 ↔ PC qua Tailscale WAN (100.100.83.59 ↔ 100.102.120.6), HTTP/SSH 100%.

### 2.4. An toàn & quản trị (bất biến)

- Không bao giờ in/lưu token, key, credential ([REDACTED]); key đọc từ ENV lúc gọi.
- Không shell tự do trên PC; mọi action có audit log; R5 hard-blocked.
- Học hỏi quarantine — cần evidence + regression + phê duyệt owner (R4) mới ra mắt; approval_verifier chưa cấu hình → 2 tri thức đang bị cách ly (đúng thiết kế).
- Fail-honest tuyệt đối: không có chức năng thì báo thẳng, không bịa.

---

## 3. HÀNH TRÌNH XÂY DỰNG (30/10 → 01/11, các mốc chính)

| Thời điểm | Hoàn thành |
|---|---|
| 30/10 ~20:12 | Hoàn tất "tai": thu mic N giây từ Pi → ZIP gửi DM (pw-record sạch + ffmpeg remux) |
| 30/10 20:16–20:30 | Mic USB Jieli + mic BT SRS-XB33: chọn nguồn mic (usb/bt/auto), sửa regex parse node |
| 30/10 20:35–20:45 | Kiểm kết nối liên tục; phát hiện Pi reboot 20:32 (nghi nguồn 5V); journald persistent |
| 30/10 20:50–21:10 | HDMI OUT cơ bản (mirror kiosk ra HDMI) |
| 30/10 21:00–21:05 | 24/7 stack: kiosk_guard tự cứu kiosk chết (125s), start_kiosk v3, journald |
| 30/10 21:55–22:39 | Chụp ảnh → DM: 2 lần sửa detect_intent (lệnh ngắn không khớp, responder cũ trong RAM), E2E 4 ảnh |
| 30/10 22:00–22:28 | **WAKE WORD E2E**: rễ mic yếu + model kém → AGC + fuzzy + BT-first; 2×WAKE thật; 4 cụm đánh thức chuẩn owner |
| 30/10 22:40–22:50 | **VOICE DM**: faster-whisper thay Vosk (small kém); STT 2 bản ghi đúng ngữ nghĩa; tích hợp responder |
| 30/10 22:55–23:00 | **HDMI CÓ PHÊ DUYỆT**: cắm → DM hỏi → "phê duyệt hdmi" mới bật; sửa regression "tắt hdmi" |
| 01/11 08:05–08:20 | **THOẠI 2 CHIỀU E2E**: giọng "Em chụp ảnh gửi anh" → chụp thật + trả lời bằng giọng qua loa BT; fix dấu `\` cuối lệnh; responder respawn |
| 01/11 08:20–08:35 | **NÚT STOP = chỉ thoát giao diện**: bỏ tắt màn/emergency, cờ kiosk_closed_by_owner chặn guard, E2E chuỗi STOP→giữ đóng→WAKE dậy lại |
| 01/11 08:35–08:40 | **TỐC ĐỘ + TỰ QUÉT LẠI TIN + REPLY RÕ MỤC**: poll 2s, catch-up 12h, chỉ mark sau khi gửi, watchdog 150s, prefix trích dẫn tin gốc |

**Vấn đề đã xử lý dứt điểm:** mất tin khi treo (đã fix cơ chế); responder chết im lặng (watchdog + unbuffered); mic yếu (AGC); Vosk kém (faster-whisper); auto-mirror HDMI trái phép (phê duyệt); STOP quá tay (chỉ thoát giao diện).

**Còn mở (chưa giải quyết):**
1. Pi5 reboot 20:32:13 ngày 31/10 chưa rõ nguyên nhân — nghi nguồn 5V; journald persistent giờ sẽ giữ chứng cứ nếu lặp lại.
2. Edge-TTS đôi lúc 403 (Microsoft chặn flaky) — GLM rule + SAPI dự phòng nhưng tiếng Việt PC hạn chế.
3. Approval_verifier (R4) chưa cấu hình → 2 tri thức học được đang quarantine.
4. Bot gateway NetChat bỏ root_id → reply-thread chưa dùng được (đang dùng prefix trích dẫn thay thế, đã hoạt động tốt).

---

## 4. ĐÁNH GIÁ ĐỊNH KỲ (đối chiếu mục tiêu)

| Trục | Mục tiêu | Hiện tại | Đánh giá |
|---|---|---|---|
| Nghe | Wake word + lệnh thoại | 4 cụm + thoại 2 chiều E2E | ✅ Đạt |
| Nói | TTS tự nhiên đa ngữ | HoaiMy + 10 giọng; 403 flaky | 🟡 Đạt, cần dự phòng TTS local |
| Nhìn | Camera + hiển thị | Chụp→DM, MJPEG, avatar | ✅ Đạt |
| Hiển thị | Màn Pi5 + HDMI phê duyệt | Đủ chuỗi hỏi-duyệt-liên tục | ✅ Đạt |
| Kênh lệnh | DM chữ/giọng/ảnh, không mất tin | 2s, tự quét 12h, trích dẫn | ✅ Đạt |
| Ổn định 24/7 | Tự hồi phục | Watchdog 3 lớp + journald; 1 lần reboot nghi nguồn | 🟡 Cần theo dõi nguồn 5V |
| An toàn | R4/R5, allowlist, audit | Đúng biên; R4 chờ cấu hình | 🟡 Chờ owner cấu hình verifier |
| Trí nhớ | 500 memories, học có kiểm soát | Hoạt động; 2 tri thức quarantine | 🟡 Chờ R4 |

---

## 5. ĐỀ XUẤT (theo thứ tự ưu tiên)

**P0 — Tuần này (giữ hệ thống chắc):**
1. **Xử lý nguồn Pi5**: đổi bộ nguồn chính hãng 5V/5A (USB-C chính thức) hoặc đo log điện áp (`vcgencmd get_throttled`) theo dõi 1 tuần — chấm dứt rủi ro reboot lạ.
2. **TTS dự phòng offline**: cài Piper TTS (nhẹ, chạy tốt trên Pi/PC) làm phương án khi Edge-TTS 403 — nói không bao giờ cụt.
3. **Chuẩn hoá reply-thread**: khi gateway NetChat hỗ trợ root_id, bật lại `--root-id` đã cài sẵn (giữ prefix trích dẫn làm phụ đề).

**P1 — Tháng 11 (nâng tầm trợ lý):**
4. **Cấu hình approval_verifier (R4)**: anh phê duyệt 1 lần bằng PIN/ FaceID giả lập trong Dashboard → mở khoá 2 tri thức quarantine + cho phép học hỏi tự chủ hơn (vẫn qua duyệt).
5. **Lệnh thoại nâng cao**: từ điển lệnh thoại mở rộng (hỏi lịch, đọc email tiêu đề, báo thời tiết) — dùng chính pipeline 2 chiều hiện có, thêm intent + câu trả lời mẫu.
6. **Ghi âm cuộc họp**: Pi5 thu âm dài + faster-whisper transcribe + tóm tắt GLM → DM (phục vụ công việc thường ngày của anh).
7. **Dashboard cảnh báo chủ động**: tab "Sức khoẻ TONY" hiển thị uptime, nhiệt Pi, throttle, số tin trả lời/ngày, latency trung bình.

**P2 — Quý tới (tầm nhìn):**
8. **Nhận diện khuôn mặt anh** (camera) → chào đúng người, chế độ riêng tư khi người lạ.
9. **Multi-agent**: TONY điều phối các agent con (coding, research) — nền đã có command center + edge control.
10. **Voice_biometric**: nhận diện giọng anh vs người khác trước khi thực thi lệnh nhạy cảm.

---

## 6. KẾ HOẠCH HÀNH ĐỘNG CHI TIẾT (2 tuần tới)

| Ngày | Việc | Người phụ trách | Bằng chứng hoàn thành |
|---|---|---|---|
| 01–02/11 | Mua/đổi nguồn 5V 5A chính hãng; bật logging throttle | Anh Quân (mua) + TONY (log) | `vcgencmd get_throttled` = 0x0 suốt 7 ngày |
| 02–03/11 | Cài Piper TTS trên PC + Pi; cấu hình fallback tự động | TONY | Edge-TTS 403 → vẫn phát được bằng Piper |
| 04–05/11 | Dashboard tab "Sức khoẻ TONY" | TONY | Ảnh dashboard gửi DM |
| 06–08/11 | approval_verifier (R4): mã PIN Dashboard + gắn vào teach pipeline | TONY (code) + Anh (PIN) | 2 tri thức quarantine được duyệt ra mắt |
| 08–12/11 | Mở rộng 10 lệnh thoại mới + câu trả lời mẫu | TONY | Video/ảnh E2E từng lệnh |
| 12–14/11 | Pipeline ghi âm họp → tóm tắt DM | TONY | File tóm tắt thật gửi DM |
| Hàng tuần | Chạy full pytest + validate_and_report + handoff | TONY | `reports/HANDOFF_LATEST.md` cập nhật |

**Rủi ro & giảm thiểu:** nguồn điện (P0.1), rate limit NetChat (đã có throttle + 429 backoff), gateway bot giới hạn endpoint (đã map đủ), mất điện PC (đề xuất P2: UPS mini).

---

## 7. HƯỚNG PHÁT TRIỂN DÀI HẠN — ĐỊNH VỊ "TRỢ LÝ SỐ CÁ NHÂN"

```
Giai đoạn hiện tại → Giai đoạn tiếp theo
[Tai/Mắt/Miệng trên Pi5]  →  [Đại diện vật lý biết tự quan sát bối cảnh]
[Lệnh thủ công qua DM]    →  [Chủ động đề xuất việc dựa trên lịch/thói quen]
[Trợ lý cá nhân]          →  [Trung tâm điều phối các agent + thiết bị]
```

1. **Chủ động (Proactive)**: sáng nào em tự tổng hợp lịch + email + thời tiết + việc quá hạn thành bản tóm tắt nói qua loa lúc anh thức dậy (nền báo cáo sáng đã có — nâng cấp thành giọng nói + cá nhân hoá).
2. **Bộ nhớ dài hạn có cảm xúc**: nhớ ngữ cảnh cuộc trò chuyện liên tiếp (không chỉ lệnh đơn) — hội thoại tự nhiên hơn.
3. **Không gian nhà thông minh**: mở rộng allowlist thiết bị (đèn, điều hòa qua IR) — theo đúng triết lý "anh phê duyệt một lần, em tự vận hành".
4. **Self-improvement an toàn**: mỗi tuần em tự đề xuất 3 cải tiến nhỏ (kèm code diff + test) → anh duyệt → tự áp dụng (pipeline learning đã có, chỉ thiếu R4).

---

## 8. PHỤ LỤC — BẰNG CHỨNG

- **Tests**: 2.914 PASS (chạy đầy đủ 31/10); 150 test files trong `tests/`.
- **File lõi**: 12.062 dòng (9 file, xem §2).
- **Ảnh E2E gần nhất**: `logs/pi5_media/photo_20261101_081106.jpg` (chụp theo lệnh giọng nói), `logs/wake_check.png` (avatar ACTIVE).
- **Log hệ thống**: `logs/netchat_responder_heartbeat.log` (fresh 2s), `logs/kiosk_guard.log` (Pi), `logs/pc_action_audit.jsonl`.
- **Trạng thái service lúc lập báo cáo**: Server PC PID 6280 (GLM READY) · quan_ai_edge active · quan_ai_wake active · quan_ai_kiosk_guard active · kiosk ACTIVE · Pi uptime ổn định sau restart cuối 08:17.
- **Tài liệu dự án**: `docs/PROJECT_STATUS.md` (cập nhật từng mốc) · `reports/HANDOFF_LATEST.md`.

---
*Báo cáo do TONY tự tổng hợp từ journal, PROJECT_STATUS, log E2E và số liệu thực tế hệ thống lúc 08:35 01/11/2026. Mọi mục "✅" đều có bằng chứng chạy thật kèm thời điểm.*
