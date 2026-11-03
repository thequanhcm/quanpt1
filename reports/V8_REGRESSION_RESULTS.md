# V8 — REGRESSION RESULTS
**Ngày:** 27/10/2026 · So sánh trước/sau toàn bộ thay đổi V8

## Số liệu
| Mốc | Suite | Kết quả | Thời gian | Ghi chú |
|---|---|---|---|---|
| Baseline đầu sprint (trước V8, có V7.1) | tests/ | **1071 passed / 0 failed / 1 skipped** | 84.82s | proc_09844ff759bd |
| Sau P1 parity + P2/P3 module + P5 TTS | tests/ (trước khi thêm test V8) | **1071 passed / 0 failed / 1 skipped** | 76.87s | proc_39d6afe456ba — 0 suy giảm |
| Sau + 37 test V8 (suite đầy đủ) | tests/ | **1108 passed / 0 failed / 1 skipped** | 81.79s | proc_180c3214b7ad |
| Chạy độc lập #2 | tests/ | **1108 passed / 0 failed / 1 skipped** | 79.15s | proc_0515f55e13a4 — chuẩn ×2 ĐÓNG |

**Đối chiếu:** 1071 (baseline) + 37 (test_v8_vietnamese_conversation.py) = **1108** ✓ khớp tuyệt đối, 0 test cũ vỡ, 0 suy giảm.

Skip duy nhất: `tests/test_vietnamese_tts.py:266` — Pi 5 chưa nối mạng (đã có từ trước V8, không liên quan).

## Live smoke V8 (LIVE_VERIFIED)
- Teach-via-stream: `nhớ rằng: marker smoke V8 V8-SMOKE-2710-1793119929...` qua `/api/chat/stream` →
  final frame có `teach_note` + `progress_check` + episode `a69c2c12-5145-46c5-a196-f6b8a12ff625` persist vào brain.db (before=0 → after=1).
- Model: `zai-org/GLM-5.3-Flash` · frames: meta → 12×delta → final.
- Server: HEALTHY sau restart với code V8 (PID mới, proc_9a314653326e).

## Kết luận
Không suy giảm bất kỳ năng lực nào; thêm 37 test bảo hộ; năng lực mới (parity 5 lớp + guidance tiếng Việt + TTS reading) đã LIVE trên cả 2 luồng chat.
