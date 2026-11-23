# BÁO CÁO BỔ SUNG SKILL MỚI CHO CHERRY — 18/11/2026

## Tổng quan
Bổ sung 3 skill mới dựa trên dữ liệu SỐNG trong brain.db + chromadb + Pi daemon, đăng ký vào registry V7 và viết test đầy đủ (17/17 PASS).

## 3 skill đã bổ sung

### 1. MEMORY_HEALTH_AUDIT — `memory_health_audit(workspace_root)`
- **Trigger**: "sức khỏe trí nhớ", "memory health", "audit trí nhớ"
- **Status**: TESTED (18/11)
- **Nguồn dữ liệu**: brain.db (memories, episodes), chromadb (semantic_memory_v1)
- **Output**:
  - `conclusion`: HEALTHY / PARTIAL / UNKNOWN
  - `audit`: memories_total, semantic_memory_total, episodes_total
  - `anomalies`: list (memories_empty, semantic_low_coverage) + severity
  - `sources_accessed/blocked`: chi tiết truy cập từng nguồn
- **Verify trên data sống (18/11)**: HEALTHY | 3138 memories / 6578 semantic / 3565 chat episodes

### 2. LESSON_MINING — `lesson_mining(workspace_root, limit=5)`
- **Trigger**: "bài học kinh nghiệm", "tổng hợp bài học", "lesson mining"
- **Status**: TESTED (18/11)
- **Nguồn dữ liệu**: brain.db episodes WHERE kind='experience_lesson'
- **Output**: top lessons sorted by confidence (trích từ metadata_json)
- **Fail-honest**: confidence < 0.4 → verified=False → Cherry phải hỏi owner trước khi dùng
- **Verify trên data sống**: EXTRACTED | 113 experience_lessons total

### 3. SYSTEM_STATUS_SUMMARY — `system_status_summary(workspace_root)`
- **Trigger**: "trạng thái hệ thống", "system status", "tổng quan hệ thống"
- **Status**: TESTED (18/11)
- **Nguồn dữ liệu**: skill_registry.json + brain.db + Pi daemon (http://192.168.1.21:8768/api/kiosk/status, timeout 2s, fail-open)
- **Output**: skills count by status, memories/episodes/lessons totals, Pi kiosk status (kiosk_running, avatar_state, core_connected, embodiment_mode)
- **Verify trên data sống**: OK | 9 skills (1 AVAILABLE + 8 TESTED) | Pi reachable: True, avatar_state: SLEEPING, embodiment_mode: ACTIVE

## Test
- `tests/test_v7_skills_expansion.py`: 17 test PASS (mock LLM + live DB)
- 10 lớp test bắt buộc §3.5: input hợp lệ, invalid, dữ liệu thiếu, timeout, fail-open, schema đổi, edge case, idempotent, fail-honest, integration

## Wire vào /api/chat
- **Wire progress_check (skill cũ TASK_STATUS_RECONCILIATION)**: dict `_v7_extras` khai báo ở đầu `_handle_api_chat`, gán key khi match trigger, splat vào response. Wire về cơ bản OK (no 500).
- **Wire 3 skill mới vào /api/chat**: CHƯA work do debug phức tạp (response_data scope, pycache stale, server restart race). Sprint sau sẽ wire qua endpoint riêng `/api/v7/skill/<name>`.
- **Fallback**: 3 skill gọi được TRỰC TIẾP qua Python API (import `from quan_ai_brain.cognition.v7_skills import memory_health_audit`).

## Quy trình V7 lifecycle đã áp dụng
1. PROPOSED (18/11 16:30) — đăng ký vào skill_registry.json với trigger_patterns + description
2. IMPLEMENTED_IN_SANDBOX (18/11 17:00) — code trong v7_skills.py, chạy trực tiếp OK
3. TESTED (18/11 17:15) — 17/17 test PASS, transition bằng SkillRegistry.update_status()
4. AVAILABLE — CHƯA nâng (chờ wire /api/chat xong ở sprint sau, fail-honest)

## Bài học kinh nghiệm (Cognitive V1.0)
1. **Schema assumption sai = silent fail**: episodes có `kind` chứ không có `episode_type`/`confidence` col — phải đọc PRAGMA table_info trước khi viết SQL. Đã sửa sau 1 lần smoke test fail.
2. **Pycache race condition trên Windows**: xóa `__pycache__/server.cpython-311.pyc` mỗi lần restart, không chỉ kill PID.
3. **Local var scope trong function lớn**: `_v7_extras = {}` đặt trong try → nếu code trước raise → NameError. Phải khai báo ngay đầu function, ngoài try lớn nhất.
4. **Splat dict trong call**: phải truyền key qua `**_v7_extras` chứ không được `response_data[...]` (response_data chỉ là biến nội bộ).
5. **Watchdog + Start-Process race**: watchdog không restart start_dual_servers → phải spawn thủ công. Background dev nên có script riêng cho dual servers.

## File thay đổi
- `src/quan_ai_brain/cognition/v7_skills.py` — thêm 3 hàm (~170 dòng)
- `src/quan_ai_brain/web/server.py` — wire _v7_extras dict (comment về V7 expansion wire trong tương lai)
- `tests/test_v7_skills_expansion.py` — 17 test mới (271 dòng)
- `data/skill_registry.json` — 3 skill PROPOSED → TESTED (file local, .gitignore)

## Commit
- Commit `197ef50` trên branch `feat/v6-m6-memory-truth`
- Push origin OK
- CHƯA tạo PR (chờ user duyệt nội dung, fail-honest về wire /api/chat chưa xong)

## Sprint sau (chờ user duyệt)
1. Wire `/api/v7/skill/<name>` để gọi 3 skill qua HTTP API (bypass /api/chat)
2. Wire V7 expansion trigger trong /api/chat (debug kỹ _v7_extras scope)
3. Nâng 3 skill lên AVAILABLE sau khi wire ổn định
4. Sprint bổ sung từ `Skill/` folder: phân tích skill mới cherry có thể học (BAT/, OCR/, UC/, ai_native_company-main, vibe-aiworkforce)
