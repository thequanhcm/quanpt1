# BÁO CÁO V3 SPRINT 7 — CHỨNG MINH ĐỘ BỀN + DỮ LIỆU THẬT

**Ngày:** 27/10/2026
**Task:** TASK-V3-SPRINT7 — owner duyệt "DUYỆT TASK-V3-SPRINT7" qua desktop (card consume-once, approver quanpt1)
**Commit:** `1da1847` | **Regression:** 780 passed / 1 skipped / 0 fail (767 → 780)

---

## TÓM TẮT

Cả 4 hạng mục (a-d) hoàn tất. Trong quá trình thực hiện, audit sâu phát hiện và
sửa **4 lỗi có sẵn** — 2 trong số đó nghiêm trọng (tự-duyệt tri thức + daemon
chết im re); 1 bug RAG làm dense embedding vô hiệu từ trước đến nay.

## (a) REBOOT-PROOF THẬT [Y1+Y3] — HOÀN TẤT

- `tools/post_reboot_verify.py`: kiểm 10 bước probe thật (servers, Pi5 hb, Ollama, responder heartbeat, 2 task, DB, số instance, learning) — **10/10 PASS** sau khởi động sạch.
- Logon trigger: cả 2 task (backup 2AM, report 8AM) giờ có **[DAILY + LOGON]** (Type 2+9, user-level qua COM — `schtasks /SC ONLOGON` bị Access denied, COM thành công). Sau reboot, task chạy ngay khi đăng nhập, không đợi mốc giờ.
- **Chờ anh nhấn restart thật** để chạy verify sau boot (10 phút) — nghiệm thu cuối của (a).

## (b) WATCHDOG MỞ RỘNG + LEARNING DAEMON [Y6] — HOÀN TẤT (13 tests)

Audit phát hiện **learning daemon đã CHẾT lúc 08:09** (`database is locked` khi regression chạy — không có try/except, chết im re 2 giờ):
- Vòng lặp **chứng tử lỗi tạm thời**: 1 vòng fail = log + retry chu kỳ sau, không chết. Crash log riêng `logs/learning_daemon_crash.log`.
- **BỎ tự-duyệt quarantine** ("approve all for now" — vi phạm "Learning is not deployment"): daemon chỉ đếm + log, promote chỉ owner. Smoke test xác nhận: 0 promoted.
- Enum sai `CODE_REVIEW` → `PROJECT_DOCS` (git ingestion trước giờ fail 100%, không ai hay).
- **Idempotent ingest** (`skip_duplicates=True`): chặn đúng gốc lớp lỗi phát sinh 108k dòng trùng (Sprint 4 chỉ dọn hậu quả, chưa vá nguồn). Smoke xác nhận: re-ingest cùng tài liệu → **0 dòng mới**.
- Watchdog thêm `check_learning_daemon` + `ensure_daemon_alive`: **auto-restart responder + learning** khi chết (cap 5/giờ đúng chuẩn server); Ollama giữ probe-only (không sở hữu → không đụng — GAP-R3).

**Sự cố minh bạch:** smoke chạy bản chưa-vá đã tạo 1.244 dòng trùng tạm thời → backup `brain_pre_smoke_cleanup_20261027_104040.db` → dọn sạch, quarantine về đúng 593.

## (c) RAG KHO THẬT [Y2] — HOÀN TẤT (bug thật được sửa)

- Benchmark thêm **`--real` mode dùng BGE-M3 thật qua Ollama** (mock giữ nguyên cho CI).
- Real mode lần đầu chỉ 8/10 → truy vết ra **bug có sẵn**: `document_rag.py` gọi `get_embedding()` nhưng service có method `embed_text()` → AttributeError bị nuốt âm thầm → **dense embedding vô hiệu từ trước đến nay** (toàn bộ retrieval chỉ chạy keyword!). Đã sửa + xác nhận.
- **Real BGE-M3: 10/10 PASSED (100%)**, no-answer honesty 2/2 — lưu `reports/sprint7_rag_benchmark_real.json`.
- Kho vẫn là 3 tài liệu mẫu — khi anh chỉ định thư mục tài liệu thật, re-index + chạy lại `--real` (1 lệnh).

## (d) DỌN TIẾN TRÌNH TRÙNG [Y7] — HOÀN TẤT

- Kill toàn bộ instance trùng (watchdog ×2, dual-servers ×2, responder ×2) → khởi động sạch **1 instance/daemon** (wmic xác nhận: dual=4 dòng=1 cặp venv, watchdog=2, responder=2, learning=2).
- Bước verify số 9 trong `post_reboot_verify.py` giám sát vĩnh viễn.

## KIỂM THỬ

| Suite | Kết quả |
|---|---|
| Sprint 7 mới (daemon 5 + watchdog 8) | **13 passed** |
| Full regression | **780 passed, 1 skipped (TTS hardware), 0 fail** |
| post_reboot_verify | 10/10 PASS |
| RAG benchmark real | 10/10 |

## GIỚI HẠN TRUNG THỰC

1. **Reboot thật CHƯA xảy ra** — verify 10/10 là sau restart sạch các daemon, chưa qua chu kỳ boot Windows thật. Chờ anh restart.
2. Kho RAG vẫn mẫu (3 tài liệu) — cần anh chỉ định thư mục tài liệu thật.
3. Learning daemon giờ chạy bản mới ~50 phút — theo dõi 24h xem có chết lại không (watchdog sẽ restart nếu có).

## THAY ĐỔI FILE

| File | Loại |
|---|---|
| `src/quan_ai_brain/memory/knowledge_ingestion.py` | PATCH (skip_duplicates) |
| `src/quan_ai_brain/cognition/document_rag.py` | PATCH (bug embed_text) |
| `tools/learning_daemon.py` | PATCH lớn (survive + governance) |
| `tools/watchdog.py` | PATCH (auto-restart daemon) |
| `tools/rag_benchmark.py` | PATCH (--real) |
| `tools/post_reboot_verify.py`, `tools/add_logon_triggers.py`, `tools/verify_logon_triggers.py`, `tools/submit_sprint7_approval.py` | MỚI |
| `tests/test_v3_sprint7_*.py` ×2 | MỚI (13 tests) |
| `reports/sprint7_rag_benchmark_real.json` | MỚI |
| Task Scheduler | +logon trigger 2 task |
