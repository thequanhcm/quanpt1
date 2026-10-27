# SPRINT 15 — TEST RESULTS (GIAI ĐOẠN C+D)

**Thời điểm chạy:** 27/10/2026 18:25–18:40 GMT+7

## 1. Test mục tiêu (lệnh + exit code thật)

```
./.venv/Scripts/python.exe -m pytest tests/test_v3_sprint15_cognitive_evidence.py tests/test_cognitive_state.py tests/test_adversarial_cognition.py -q -p no:cacheprovider
→ exit 0 · 33 passed in 0.84s (13 Sprint15 + 12 cognitive_state + 8 adversarial)
```

Bảng ánh xạ §V master prompt → test:
| # | Trường hợp | Test | Kết quả |
|---|---|---|---|
| 1 | Claim có nguồn hợp lệ | test_state_persisted_in_checkpoint (source_ref giữ nguyên) | PASS |
| 2 | Claim thiếu nguồn / no-context | test_no_cog_state_still_persists_flag_false | PASS |
| 3 | Nguồn không tồn tại | test_missing_task_404 | PASS |
| 4 | Claim cũ (task trước S15) | test_old_task_honest_false | PASS |
| 6 | Mâu thuẫn cùng đối tượng | test_has_state_with_needs_review (giữ 2 nguồn, UNRESOLVED) | PASS |
| — | Mâu thuẫn khác phạm vi | test_resolved_contradiction_not_needs_review (CONTEXT_DIFFERENCE) | PASS |
| 7 | Không tự nâng xác minh | test_candidate_stays_hypothesis_low_confidence | PASS |
| 9 | Candidate không vào trusted | (nhờ test trên + cognitive_state test suite 12/12 của nhánh song song) | PASS |
| 12 | DB lỗi / truy vấn thất bại | test_fail_open_on_registry_error + handler 500 trung thực | PASS |
| 16 | Persistence sau lưu | test_state_persisted_in_checkpoint (đọc lại từ DB) | PASS |
| 17 | API trung thực khi lỗi | test_missing_task_404 / test_missing_param_400 / test_remote_403 | PASS |
| — | Replay không ghi đè bằng chứng | test_idempotent_replay_does_not_overwrite_checkpoint | PASS |
| — | Status không đổi khi persist | test_status_unchanged_by_checkpoint_write | PASS |
| 5,8,10,11,13,14,15 | STOP/FREEZE, R4, R5, secrets, injection | NGOÀI PHẠM VI increment (không đụng policy/approval); hồi quy qua full suite + adversarial suite hiện có (8/8 pass) | N/A-REGRESSED |

## 2. Toàn bộ suite

```
./.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=short
→ exit 0 · 940 passed, 1 skipped in 92.60s (0:01:32)
```
- Không hard-code 927: số thực tế sau +13 test = 940.
- Skip duy nhất: Pi5 phần cứng (BLOCKED cố hữu — cùng lý do mọi sprint).
- 0 fail — không xóa test, không hạ bảo vệ.

## 3. Live smoke (Giai đoạn D — an toàn, có kiểm soát)

Chuẩn bị: respawn dual server bằng venv python theo đúng cơ chế watchdog hiện hành (không đổi scheduler/watchdog/NetChat/Pi5). PID mới 6928.

| # | Hành động | Kết quả thật |
|---|---|---|
| S1 | POST `/api/executive/tasks/create` (luồng thật, dry_run) goal smoke S15 | success=True, 62s (LLM thật), task `task_dc83a2e05667`, risk R1 |
| S2 | GET `/api/executive/tasks/cognitive-state?task_id=task_dc83a2e05667` | has_state=**True**, persisted 2026-10-27T11:20:43Z, **6 beliefs** (1 fact_user + 5 inference), **4 contradictions UNRESOLVED → needs_review=True** (cả 2 nguồn mỗi mâu thuẫn được giữ) |
| S3 | Task cũ checkpoint rỗng | has_state=**False** + lý do trung thực "đăng ký trước Sprint 15" |
| S4 | Task lạ / thiếu param | **404 / 400** đúng mã |
| S5 | Edge/Pi5 | READY, hb 0.03s, RTT 17.7ms, 0 alert — không gián đoạn |
| S6 | Workbench overview | success=True — dashboard hoạt động bình thường |
| S7 | NetChat | Không đụng (responder daemon sống, không restart) |
| S8 | Log secrets | Handler/serialize đều qua redact_text; checkpoint qua redact_text/redact_value; không ghi credential vào log/báo cáo |

**Ghi nhận từ smoke (finding, không phải regression):** chat episodes lưu nguyên văn system prompt (do mock-era test session) tạo noise contradictions khi retrieve. Đây là chất lượng dữ liệu memory hiện hữu — KHÔNG thuộc phạm vi S15, khuyến nghị làm việc tiếp theo (dọn/giới hạn episode ingestion), cần card riêng.

## 4. Kết luận
- UNIT_TESTED: 33/33 mục tiêu · INTEGRATION_TESTED: 940/941 (1 skip Pi5) · LIVE_SMOKE_VERIFIED cho toàn bộ increment.
- PARTIALLY_VERIFIED chung sprint CHỈ ở các mục NGOÀI phạm vi đã liệt kê — không có mục nào của increment ở NOT_VERIFIED.
