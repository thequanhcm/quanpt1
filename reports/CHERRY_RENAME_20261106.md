# BÁO CÁO ĐỔI TÊN TRỢ LÝ: TONY PHAM → CHERRY (06/11/2026)

## 1. Lệnh owner
"Em cho đổi tên trợ lý TONY PHAM thành CHERRY. cấu hình từ bây giờ em sẽ tên là CHERRY"

## 2. Phạm vi audit
Quét toàn workspace: 349 file chứa chữ "tony". Phân loại:
- **SỬA** (runtime active): 10 file PC + 4 file Pi5
- **GIỮ NGUYÊN**: docs lịch sử (PROJECT_STATUS, MASTER_PROMPT…), BRAIN_0 (bản cũ đã dừng),
  backups, reports, `backup_pre_udr1_20261106/`, runtime paths `/tmp/tony_*`,
  `tony_media/`, kênh NetChat tên thật "Trợ lý Tony Pham" (giá trị API),
  JS element id `tony-avatar-canvas` (phá vỡ kiosk.js/avatar_engine nếu đổi)

## 3. Đã sửa

### PC (E:\BRAIN)
| File | Nội dung |
|---|---|
| `src/quan_ai_brain/cognition/executive_persona.py` | conversational_name=CHERRY; 4 kịch bản giới thiệu (Mode A/B/C/D); format_for_prompt |
| `src/quan_ai_brain/cognition/context_builder.py` | DEFAULT_SYSTEM_INSTRUCTIONS "You are CHERRY (Official System Name: QUAN AI BRAIN)" |
| `src/quan_ai_brain/cognition/self_model_engine.py` | self-intro + identity dict |
| `edge_client/config.py` + `config.json` | assistant_name=CHERRY; wake_word="CHERRY ơi" |
| `src/quan_ai_brain/voice/wake_word_config.py` | DEFAULT_WAKE_WORDS: Cherry ơi / Hi Cherry (bỏ 3 item TONY cũ; 10→9 items) |
| `edge_client/wake_word_service.py` | WAKE_PHRASES: cherry/chéri/biến thể + GIỮ bộ TONY quá độ; fuzzy matcher cherry+tony |
| `edge_client/client_daemon.py` | greeting "CHERRY online"; 5 transcript "Gọi 'CHERRY ơi'…" |
| `src/quan_ai_brain/voice/voice_pipeline.py` | max_len check + câu "tạm nghỉ" |
| `src/quan_ai_brain/web/static/index.html` | welcome "Em là CHERRY"; tên stage |
| `tools/netchat_command_center.py` | keywords lệnh cherry nói/nghỉ/ngủ/dậy/về/dừng nhạc (song song TONY — backward compat); polite prefixes +cherry; verbatim regex +cherry; toàn bộ reply text CHERRY |

### Pi5 (sync scp + sha256 khớp 4/4)
`wake_word_service.py`, `config.py`, `config.json`, `client_daemon.py` → restart
`quan_ai_wake` + `quan_ai_edge` (sudo -n) — journal xác nhận
`[WAKE] sẵn sàng — lắng nghe 'CHERRY ơi'`

### Bộ nhớ dài hạn
`semantic_memory` ghi biên bản đổi tên (id `rename_cherry_143618763f`,
source_ref `owner_directive_rename_20261106`, approved_by Quanpt1).

## 4. Bằng chứng E2E (LIVE)
- `/api/chat` hỏi "Em tên gì?" → GLM-5.3-Flash: **"Dạ, em là CHERRY — tên hệ thống
  chính thức là QUAN AI BRAIN, trợ lý điều hành số do anh Quân (Quanpt1) tạo ra và sở hữu ạ."**
- Gọi "Cherry ơi" → **"Chào anh! Em CHERRY đây, luôn online và sẵn sàng hỗ trợ anh ạ."**
- 8765 + 8766 restart (start_dual_servers 21:27 cũ serve persona cũ → đã thay)
- Wake Pi5 journal: `sẵn sàng — lắng nghe 'CHERRY ơi'` ✓

## 5. Test
- Test cập nhật theo thiết kế mới (có comment lý do): test_digital_identity_persona.py,
  test_self_awareness.py, test_wake_word_config.py
- **120 passed, 8 warnings (46.6s)** — 11 file test dàn đầy đủ
- Backup PC: `backups/rename_cherry_20261106/` (10 file)
- Backup Pi5: `~/Desktop/edge_client/backup_rename_cherry_20261106/` (6 file)

## 6. Còn lại (không làm — đúng biên)
- **Kênh NetChat** vẫn tên "Trợ lý Tony Pham" — đổi tên kênh là thao tác trên
  NetChat (owner tự đổi trong app; code giữ nguyên tên kênh API để không vỡ lookup)
- **Bot name trên NetChat** ("bot_tony" display name) — owner đổi trong NetChat settings
- Biến thể wake TONY giữ quá độ ~1 tuần — nói "TONY ơi" vẫn dậy được, sau đó bỏ
- Chưa commit git (chờ lệnh owner)
