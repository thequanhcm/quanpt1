# TASK A — CURRENT SYSTEM RE-INSPECTION (11/11/2026 tối)
**Mục đích:** xác định những điểm ĐÃ THAY ĐỔI kể từ báo cáo baseline `BAO_CAO_TONG_HOP_CHERRY_TOAN_CANH_20261111.md` (soạn 11/11 chiều). Mọi số liệu đo bằng tool thật trong phiên này (execute_code/terminal: curl, sqlite, powershell, pytest) — không suy đoán.

---

## 1. Kết quả đo nhanh

### 1.1 Git & PR
- HEAD nhánh `fix/edge-alertf-sticky-recovery` = `348622b` "feat(voice): chọn nhiều giọng tiếng Việt chuẩn + piper offline tự fallback" (commit MỚI sau báo cáo chiều).
- PR #19: **OPEN, 5 commits** (1842364 → 47c65af → a760ff3 → 0019c6c → 348622b), head=348622b, **mergeable: true** (GitHub API check 11/11 tối).
- Working tree còn: 3 file data runtime modified (conversation_state, fed_alert_last, chroma.sqlite3 — không commit, đúng quy tắc) + file tạm/report mới chưa track.

### 1.2 Dịch vụ PC
| Thành phần | Trạng thái đo 11/11 tối | Bằng chứng |
|---|---|---|
| Server 8765 | HTTP 200 (0.02s) | curl /api/health |
| Server 8766 | HTTP 200 (0.02s) | curl /api/health |
| overall_status | **DEGRADED** | ollama_daemon=DISABLED (đã gỡ theo quyết định owner 02/11 — cảnh báo cũ, KHÔNG phải sự cố mới) |
| brain_db | HEALTHY — 3.054 episodes / 5.052 semantic | /api/health components |
| task_registry | HEALTHY (pending 0) | /api/health |
| Processes | dual servers (19536/22168), watchdog (13452/11788), learning ×2 instance (8380/15348 + 18440/21920) | Get-CimInstance cmdline |

### 1.3 Pi5
- edge status: **DISCONNECTED, paired=False, kiosk=False, last_heartbeat=None** — `/api/executive/edge/alerts` trả ALERT_A_PI5_NOT_CONNECTED (WARNING).
- ping 192.168.1.21: không phản hồi. → **Không đổi so với báo cáo chiều: offline vật lý từ 10/11 13:31, chờ owner kiểm tra phần cứng.**

### 1.4 Learning / watchdog / memory
- learning_daemon.log (stdout): cycle mới nhất **13.3s, "6459 facts ingested, 0 consolidated", quarantine 6.230→6.231 chờ duyệt, total 10.930** — chu kỳ 5 phút sống.
- **PHÁT HIỆN MỚI: 2 instance learning_daemon song song** (PID 8380+15348 cũ và 18440+21920 mới — mỗi cái là cặp venv+system python từ 2 cách spawn khác nhau) → gấp đôi rác nạp.
- watchdog.log: 0.62MB, mtime 14 phút trước — LIVE.
- memory_review: session mới nhất **07/11** (rev_77e4b6aa98f9, COMPLETED); review_runs mới nhất 27/10 — **vẫn tắc, changes_applied=0**.

### 1.5 Dữ liệu tri thức (sqlite read-only)
| Chỉ số | Giá trị đo | So với báo cáo chiều |
|---|---|---|
| candidate_knowledge quarantined | **6.231** | 6.175 → +56 (~4h pace ~340/ngày) |
| approved | 1.491 | không đổi |
| semantic_memory | 5.052 | không đổi |
| chroma embeddings | 4.790 | — |
| **Rác lặp trong quarantine** | "Test suite: 3648 passed" × **695**; "3556" × **488**; "3442" × **311** → tổng ~1.494 | Xấu hơn số cũ (160/ngày) |
| **Semantic dup** | **88 nhóm statement trùng** | MỚI phát hiện |
| knowledge_units (kho V9 reasoning) | **148 EXTRACTED + 210 relations** | MỚI phát hiện — gần trống |

### 1.6 Backup / restore
- backups/: DB mới nhất `brain_20261109_190001.db` (102.6MB, **44.2h trước**) — **đêm 10-11/11 không có file**.
- Task `QUAN_AI_BRAIN_BACKUP_2AM`: LastRun 20:00 11/11, **LastTaskResult=2147946720 (≠0)**, NextRun 12/11 02:00 → cần đọc log/fix ở COG-0.
- **Integrity check bản 09/11: ok** — episodes 3.034, semantic 5.052, quarantined 5.884 (đọc đúng cấu trúc).
- Mirror F: theo lịch 02:30 (không verify trong phiên này — NOT VERIFIED).

### 1.7 Test baseline (full regression)
- `pytest tests/ -q -p no:cacheprovider`: **3669 passed / 6 failed / 28 skipped / 12:16** — phân loại từng fail trong `baseline/pytest_baseline_20261111.json`:
  - 2× test contract cũ thiếu "DISABLED" (ollama) — honesty runtime ĐÚNG, test hẹp.
  - 1× backup cũ >24h — vấn đề vận hành thật (đúng như §1.6).
  - 3× test cũ lạc hậu sau commit đa giọng + intro CHERRY (preference persist hoạt động đúng; caption chuẩn owner; self-intro mới).

### 1.8 Năng lực nhận thức đo thật (đầu vào gap analysis)
- `CognitiveSelfAssessment.assess_system()` → EVIDENCE_BOUNDED, invariants R4/R5 active, Pi5 hardware `hardware_verified=false` — TRUNG THỰC đúng trạng thái.
- `SelfModelEngine` → 12 nhóm self-model + SelfQA 11 câu hoạt động.
- `LogicalReasoningEngine.answer_question("Pi5 kết nối với PC qua gì?")` → conclusion **C "Không đủ bằng chứng"**, evidence=0 — hành vi fail-honest ĐÚNG nhưng **retrieval chỉ thấy 148 knowledge_units** (kho V9), không thấy 5.052 semantic + 4.790 chroma → gap lớn nhất Phase 2.

## 2. Danh sách "khác biệt kể từ báo cáo 11/11 chiều"
1. +1 commit `348622b` (đa giọng) push vào PR #19 (4→5 commits).
2. Quarantine 6.175→6.231 (+56) — tắc tiếp diễn.
3. Learning daemon: phát hiện dual instance (không nêu trong báo cáo chiều).
4. Semantic dup 88 nhóm + rác 1.494 hàng — nêu rõ số hơn báo cáo chiều.
5. Backup 2AM: file 09/11 là mới nhất; task result≠0 — vấn đề mới.
6. Health tổng: báo cáo chiều không nêu → giờ đo là DEGRADED (ollama DISABLED — cũ, giải thích được).
7. Còn lại (tai/mắt/miệng — TTS/voice/wake config) — không đo lại trong phiên này vì không có thay đổi code liên quan và Pi5 offline (E2E edge BLOCKED).

## 3. Điều kiện dừng kiểm tra (master prompt §13)
- Không có tình huống nào buộc dừng toàn bộ: DB không mất/nhiễm mới (dup có từ trước, có backup 09/11), không nguy cơ phá core (chưa sửa gì), Pi5 offline đã ghi rõ, mọi thay đổi đang chờ duyệt.
- FULL regression: 6 fail đều đã phân loại — 5/6 không phải bug production; 1 (backup) là việc COG-0.

---
*Tài liệu TASK A — số liệu lấy từ tool thật, file evidence: baseline/pytest_baseline_20261111.json + các output trong phiên.*
