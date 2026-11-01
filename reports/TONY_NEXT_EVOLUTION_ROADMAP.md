# TONY NEXT EVOLUTION ROADMAP — Lộ trình sau tổng kiểm toán (PHẦN XVIII)
**Cập nhật:** 01/11/2026 16:45 · Mỗi hạng mục: mục tiêu/hiện trạng/giá trị/chi phí/dependency/rủi ro/quyền duyệt/nghiệm thu/test/rollback

## Tuần 1 (02–08/11) — ĐÓNG RỦI RO VẬN HÀNH + P0 ĐÃ DUYỆT

### 1.1 Bật lại Watchdog (R-new01)
- Mục tiêu: tự hồi phục server/responder/learning vĩnh viễn.
- Hiện trạng: 0 process; logic có sẵn (cap 5 restart/h, per-daemon).
- Giá trị: MTTR ↓ từ giờ → phút; trị giá ngay khi PC reboot.
- Chi phí: 15'. Dependency: duyệt. Rủi ro: restart-loop nếu bug mới → cap 5/h chống.
- Nghiệm thu: watchdog process sống + 1 bài test kill-responder → tự hồi.
- Test: kill responder thật → 90s sống lại. Rollback: pkill watchdog.

### 1.2 Bật lại Backup 2AM (R-new02)
- Mục tiêu: mốc phục hồi brain.db hằng ngày.
- Hiện trạng: task dừng từ 28/10 (nguyên nhân cần schtasks /Query kiểm tra).
- Giá trị: RPO 24h → kết hợp mirror F = 2 lớp.
- Chi phí: 30'. Nghiệm thu: brain_YYYYMMDD mới lúc 02:05. Rollback: disable task.

### 1.3 Q-3 Piper TTS (đã duyệt)
- 4h · nghiêm thu: TTS nói tiếng Việt offline không 403; rollback: tắt fallback.

### 1.4 Q-4 Approval verifier (đã duyệt)
- 6h · nghiêm thu: batch verify có evidence + owner duyệt lô; rollback: giữ quarantine.

## Tuần 2 (09–15/11) — P1
- 09/11: AUDIO (nếu anh duyệt + có thiết bị) · 10/11: M2 fix reflection.
- 11–12/11: review-owner loop (#7) · 13–15/11: fail-over test + self-model ops-state.

## Tuần 3 (16–22/11) — P2
- 16–18/11: CriticalThinker integration (sau M2) · 19–20/11: KPI collector + dashboard.
- 21–22/11: auto tool-factory prototype (Q-4 đã chạy ổn).

## Tuần 4 (23–30/11) — P3 + nghi thức
- Tách server.py blueprint · logs rotation · dọn .venv_broken_backup (duyệt riêng).
- Test A email-progress thật với anh.

## Nguyên tắc lộ trình
1. Không đụng thứ đang chạy tốt (health, governance, memory, mirror).
2. Mỗi việc: evidence trước khi "DONE" — theo đúng AS-BUILT discipline.
3. Mọi hạng mục NHÓM C có duyệt riêng; em chỉ bắt đầu khi anh nhắn "DUYỆT <ID>".
