# XỬ LÝ 3 VẤN ĐỀ AUDIT (duyệt owner 06/11 "xử lý theo thứ tự 1/2/3")

Owner đã đọc `reports/AUDIT_FULL_CHERRY_PI5_20261106.md` và duyệt xử lý cả 3.

## 1. ✅ Backup 2AM + Morning Report 8AM (StartWhenAvailable)
- Task Scheduler: `QUAN_AI_BRAIN_BACKUP_2AM` + `QUAN_AI_BRAIN_MORNING_REPORT_8AM`
  bật `StartWhenAvailable=True` (đọc lại verify: True/True).
- Chạy bù ngay 1 lần backup theo yêu cầu: schtasks /Run → LastRun 23:27:27
  Result=0 → file `backups/brain_20261106_162736.db` (101.7MB) tồn tại ✓.
- Từ nay: PC bật lại muộn thì task vẫn chạy bù thay vì bỏ lỡ.

## 2. ✅ Wake false-positive (siết matcher _fuzzy_hit)
- File `edge_client/wake_word_service.py` (PC + Pi5, sha256 khớp
  `07d46a28…`): 'ơi' phải là token ĐỘC LẬP (không tách giữa từ); bỏ
  'toi'/'tôi' khỏi danh sách has_name (cụm "tôi ơi" vẫn khớp qua WAKE_PHRASES
  substring + fuzzy cụm 1 lỗi — giữ nguyên wake thật).
- Test 22 case trên code FILE THẬT: 12 wake thật (cherry/tony/biến thể Vosk
  lệch 'chery ơi') → WAKE ✓; 10 TV noise ("ngoài khơi…", "và soát sắp xếp
  ngoài khơi vừa khẳng định") → KHÔNG wake ✓.
- Pi5: backup file cũ, scp, verify sha256, `sudo -n systemctl restart
  quan_ai_wake` → active, journal "sẵn sàng — lắng nghe CHERRY ơi".

## 3. ✅ shared_secret ra khỏi git (bước 1 — nơi đọc, chưa rotate)
- `edge_client/config.py` `load_from_file`: ưu tiên file
  `edge_secret_local.txt` (NGOÀI git, chmod 600) cạnh config.json;
  config.json chỉ là fallback. Không đổi giá trị secret (rotate = việc riêng
  chờ owner duyệt — làm lúcmaintenance để không gãy 2 máy).
- .gitignore thêm `edge_secret_local.txt`. Pi5: backup config.py, scp (sha256
  `eece98f4…` khớp 2 máy), tạo file secret 64 bytes chmod 600 (hash khớp
  config `e81366f2` — cùng giá trị hiện hành), restart quan_ai_edge active.
- PC server đã đọc `data/edge_hmac_secret.txt` ngoài git từ trước — không đổi.
- Git đàng hoàng: lần commit tới config.json vẫn track (fallback) nhưng giá
  trị trong đó sẽ bị thay bằng placeholder khi owner duyệt rotate.

## VERIFY E2E sau cả 3 fix
- Edge link PC: READY, paired, RTT 28–30ms, misses=0, kiosk_running=True
  (restart edge làm guard dựng lại kiosk trong 1 chu kỳ — bình thường).
- Pi5 units: edge/wake/kiosk_guard active; chromium 10 proc; mic Jieli −18dB.
- Tests: edge_client + edge_monitor 17/17 PASS.

## Còn lại (không thuộc 1/2/3, chờ duyệt riêng)
- TTSManager fallback piper (22 timeout/24h) — đề xuất Q-3 cũ.
- Rotate shared_secret thật + bỏ key khỏi config.json track (bước 2 của mục 3).
- HDMI mirror (labwc từ chối enable HDMI-A-2) — báo cáo riêng HDMI_MIRROR_BUG.
