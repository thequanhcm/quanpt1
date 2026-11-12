# SPRINT COG-0 + PHASE A — BÁO CÁO TRIỂN KHAI (11/11/2026, tối)

**Phạm vi duyệt:** Owner đã duyệt "COG-0 + Phase A song song" (Dashboard Phase 1 làm sau).
**Quy tắc:** audit-first, fail-honest, chờ duyệt trước khi phá hủy. **Trạng thái: HOÀN THÀNH — chờ owner 3 quyết định cuối.**

---

## 1. Dual learning daemon — ĐÃ FIX GỐC ✅

**Root cause (audit-first):**
- 2 instance song song: mồ côi PID 8380 (cha 12496 đã chết qua restart watchdog cũ) + instance watchdog-spawn 18440. Không có lock → không gì chặn.
- "4 PID" các phiên trước = 2 instance × 2 PID (venv shim pythonw.exe → python311 thật).

**Fix (2 lớp):**
1. **Single-instance lock** `data/learning_daemon.lock` (msvcrt LK_NBLCK byte 512; PID ở offset 0; mở unbuffered — 3 lần refine vì Windows chặn đọc byte khóa qua buffer; test bắt được cả 2 lỗi thiết kế).
2. **kill 4 PID cũ → nổ 1 instance mới** (PID 20760) bằng đúng lệnh watchdog dùng.

**Verify E2E:** 75s sau khi nổ — pythonw chỉ còn 1 cặp daemon (4612→20760); watchdog KHÔNG respawn thêm; spam 'Test suite%' **2542 không tăng** (trước: +705/2.5h); brain.db mtime 87s.

**Tests:** `test_learning_daemon_single_instance.py` 5 test (lock acquire/exits-quietly/released-on-death + dedupe same-not-ingested/changed-ingested) + 14 test Sprint 7 cũ = **19 passed**.

## 2. Spam học — ĐÃ CHẶN TỪ WRITE-PATH ✅

Root cause: `learning_daemon.py` `ingest_test_results()` gọi `skip_duplicates=False` → mỗi chu kỳ 5' nạp hàng "Test suite: …" mới dù nội dung y hệt.
Fix: `skip_duplicates=True` (idempotent — chỉ nạp khi số passed/failed ĐỔI).
Tồn kho rác hiện tại: **1.841 quarantined + 700 đã lọt semantic_memory** (consolidation cũ trước Sprint 7 auto-promote) → nằm trong kế hoạch dọn §4.

## 3. Backup 2AM — ĐÃ FIX GỐC ✅ (chưa verify đêm nay)

**Root cause (không đoán):** Task `QUAN_AI_BRAIN_BACKUP_2AM` chạy **"Interactive only"** → 2AM máy khóa → Windows từ chối **0x800710E0 "operator or administrator has refused the request"** (Last Result task xác nhận). Đêm 10-11 không có file, không có log.

**Fix (2 lớp):**
1. `tools/backup_database.py`: shutil.copy2 → **sqlite3 backup API + integrity verify ngay khi sinh** (file hỏng bị xóa + báo FAIL).
2. **watchdog `check_daily_backup()`**: sở hữu backup 2AM (chạy 24/7 không phụ thuộc phiên đăng nhập; marker theo ngày lịch; retry 2 lần; fail-honest). Task Scheduler giữ làm dự phòng.

**Verify một phần:** backup manual chạy OK (`brain_20261111_153736.db` + integrity pass); 18 test backup/restore/guard/hardening **pass**. Chưa verify E2E 2AM đêm nay — sẽ tự chạy đêm nay (2h sáng) và owner kiểm tra `logs/watchdog.log` sáng mai.

## 4. Dọn kho tri thức — DRY-RUN XONG, CHỜ OWNER DUYỆT ⏸️

`tools/cleanup_knowledge_spam.py` (dry-run mặc định; `--execute` yêu cầu backup pre-cleanup integrity-pass, verify drift >5% → rollback):

| Cụm | Rows | Bản chất |
|---|---|---|
| A. Spam "Test suite:%" (quarantined) | **1.841** | Rác 100% — chỉ nên xóa |
| B. Spam đã lọt semantic_memory | **700** | Rác 100% — xóa |
| C. Semantic dup (giữ 1/nhóm) | **2.448** | x373 "test suite 2914…", x167 "#!/bin/bash", x85 "version=…"; giữ dòng MỚI nhất |
| **Tổng đề xuất dọn** | **4.989** | |

**KHÔNG đụng** (cần quyết riêng): ~3.847 tri thức docs/code THẬT bị quarantine vì rule chặt (JSON ref — đáng rehabilitate dần); 677 speech_corpus Pi5 (ASR noise); 12 tony_vision.
Export đầy đủ cho owner: `reports/intelligence_maturity/ciee/QUARANTINE_EXPORT_20261111.csv` (6.378 rows).

## 5. Phase A — CIEE Runner V1 (subagent song song) ✅

- `tools/ciee/` 14 files (runner + 8 nhóm probe + data_access read-only + report_writer). E2E 3 lần chạy thật.
- **10 PASS / 2 FAIL / 1 PARTIAL / 1 GAP_KNOWN / 1 NOT_RUN (Chroma)** — so V0: 13/14 giữ outcome; C2 FAIL→PASS do đổi cách đo (đã ghi trung thực); **H2 vẫn FAIL** (spam — data lúc chạy 2.541; đã fix từ gốc sau đó).
- Báo cáo: `reports/intelligence_maturity/ciee/runs/20261111T153748Z/REPORT.md`.

## 6. Trạng thái chạy thật sau COG-0

- Learning daemon: **1 instance (20760)**, chu kỳ 5', spam DỪNG.
- Watchdog 13452: LIVE, có thêm backup guard.
- Servers 8765/8766: LIVE (không đụng).
- Pi5: vẫn offline (đứng ngoài phạm vi COG-0).

## 7. Ba quyết định cần Owner

1. **Duyệt chạy `--execute` dọn 4.989 rows rác** (tool tự backup pre-cleanup + rollback-guard)? Khuyến nghị: DUYỆT (rác 100%, có backup).
2. **Tri thức docs/code thật (3.847)** bị quarantine vì rule chặt — duyệt hướng rehabilitate theo batch có review (sprint sau) hay để nguyên?
3. **Merge PR #19** (5 commits, mergeable — vẫn đang chờ từ trước)?

---
*COG-0 + Phase A: HOÀN THÀNH theo đúng phạm vi duyệt. KHÔNG tự xóa gì. KHÔNG commit — chờ owner duyệt (working tree để owner xem diff).*
