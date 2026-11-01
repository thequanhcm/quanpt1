# M1 — TEST RESULTS

**Người lập:** TONY · **Ngày:** 01/11/2026 · **Baseline M0:** 2.914 passed / 44 skipped

## Kết quả chạy thật

| Suite | Kết quả | Thời gian |
|---|---|---|
| `tests/test_monitoring_health.py` | **18 passed** | 0,65s |
| `tests/test_monitoring_extended.py` | **17 passed** | ~2s |
| `tests/test_web_health_endpoints.py` | **4 passed** | 1,3s |
| **Regression toàn bộ** `tests/` | **2.953 passed, 44 skipped, 0 failed** | 2:55 |

So baseline: **+39 test mới, +0 fail, +0 skip** — không regression.

## Phủ 15 yêu cầu test (master prompt §V)

| # | Yêu cầu | Test |
|---|---|---|
| 1 | PC telemetry | `TestPcCollector.test_collect_returns_schema` (đo thật, đọc-only) |
| 2 | Pi5 telemetry | `TestPi5CollectorMock.test_parse_temp` (SSH mock) |
| 3 | Network telemetry | `TestNetworkCollector.*` (ping mock: ok/lost/crash + ngưỡng) |
| 4 | Service monitoring | `TestServiceCollector.test_http_probe_real_localhost_closed` + ngưỡng down/stale |
| 5 | Database monitoring | `TestDatabaseCollector.test_real_db_readonly_quick_check` (DB tmp) |
| 6 | Voice monitoring | `TestVoiceCollector.test_schema_and_fail_honest` |
| 7 | Health classification | `TestAggregator.test_apply_thresholds_classification` + classify tests |
| 8 | Unknown state | `test_no_data_is_unknown`, `test_missing_db_is_unknown`, `test_missing_value_unknown` |
| 9 | Historical data | `test_history_pruned`, history trong snapshot mock |
| 10 | Dashboard integration | `TestHealthPage.test_health_page_served` + endpoint tests (server thật port random) |
| 11 | Read-only enforcement | DB collector dùng `mode=ro`; test DB tmp riêng; không test nào gọi SSH/ping/DM thật |
| 12 | Error handling | `test_ping_crash_is_unknown`, `test_send_failure_recorded_not_swallowed` |
| 13 | Disconnection handling | `test_ping_lost_is_warn_not_normal`, `test_ssh_unreachable_is_unknown_not_crash` |
| 14 | Reconnection handling | network collector đo lại mỗi chu kỳ + `_last_result` (E2E: CRITICAL giả sau restart tự hết ở cycle sau) |
| 15 | No data mutation | collectors read-only; 2 DB telemetry do M1 tạo riêng trong `data/` (alert + history), không đụng brain.db/tasks.db |

## Kiểm chứng "không tác động hệ thống" (chạy trong phiên)

- Không `git init`/commit ✓ · không lệnh sudo ghi trên Pi5 ✓ · không cài package ✓ · không sửa cấu hình PC/Pi5 ✓ · không restart service TONY ngoài server của em (đúng chu trình deploy) ✓ · Q-1→Q-5 nguyên vẹn PENDING ✓

## Ghi chú trung thực

- `tools/validate_and_report.py` lần chạy 10:46 báo 2.936 passed — chênh 2.953 vì số test được collect thay đổi nhẹ giữa 2 lần chạy (test runtime + monitoring), **không có fail nào**.
- 44 skip giữ nguyên bản chất (phần cứng chưa có/pytesseract thiếu/Azure SDK thiếu).
