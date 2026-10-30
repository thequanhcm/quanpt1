# V7 TEST RESULTS — 27/10/2026

## Tóm tắt

| Suite | Kết quả | Thời điểm |
|-------|---------|-----------|
| tests/test_v7_skills.py | **38/38 PASS** | nhiều lần chạy trong phiên |
| tests/test_v6_skill_registry.py (back-compat) | 13/13 PASS | sau schema nâng V7 |
| Full regression | **1071 passed / 0 failed / 1 skipped** (108.06s) | sau khi +38 tests V7 + wire |

Baseline trước V7: 1033/0/1 → sau V7 Cấp 1: 1071/0/1 (delta +38 = chính số test mới, không mất test nào).
Skip duy nhất: `test_vietnamese_tts.py:266` — Pi 5 chưa nối mạng trong phiên tự động (đã biết, không liên quan V7).

## Live smoke Cấp 1+C2 (server production, port 8765)

| Kịch bản | Kết quả |
|----------|---------|
| Query khớp trigger "Kiểm tra tiến độ..." | `progress_check` đầy đủ: chain 4 skill, 58 records (tasks.db + todos.db read-only), RECONCILED_WITH_LIMITS, risk 0, unknowns 116, report 12 mục |
| Query không khớp "hello world test" | `progress_check: null`, success true, không crash |
| Query tiếng Việt qua curl (encoding hỏng) | Không khớp trigger → skip đúng (không crash) — chain vẫn an toàn |

## Bug tìm thấy & đã fix trong phiên (đều có test chứng minh)

1. `skill_registry.transition()` — evidence kèm transition bị kiểm tra trước khi append → APPROVED luôn từ chối dù có evidence mới. Fix: append trước, kiểm tra sau (vẫn fail-closed khi cả hai rỗng).
2. Wire v1 — `response_data` không tồn tại trong handler → NameError toàn chat. Fix: biến `progress_check_block` + thêm field vào `_send_json`.
3. Wire v3 — init biến nằm trong nhánh `create_task` → query thường crash "cannot access local variable". Fix: chuyển block ra scope ngoài (12-space).
4. Wire v4 — xác minh bằng AST + HTTP thật 2 chiều (match/skip).

## Lệnh đã chạy (truy vết được)

```
./.venv/Scripts/python.exe -m pytest tests/test_v7_skills.py -v        # 38/38
./.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=no  # 1071/1
curl POST /api/chat (2 kịch bản)                                        # live smoke
tools/seed_v7_target_skills.py, tools/promote_v7_skills_after_tests.py  # registry thật
tools/wire_v7_progress_chain*.py                                        # AST-checked wiring
```

## Không vi phạm an toàn

- Không thêm package mới; stdlib only (sqlite3, re, json, urllib, dataclasses).
- Không ghi DB production (read-only URI mode=ro; byte-identical test).
- Không tự promote AVAILABLE; 5 skill dừng đúng TESTED.
- Không tự commit trong khuôn khổ V7 (chờ chủ duyệt diff).
- Không secret/token nào trong log/báo cáo.

---
*V7 Test Results bởi QUAN AI BRAIN Agent · 27/10/2026.*
