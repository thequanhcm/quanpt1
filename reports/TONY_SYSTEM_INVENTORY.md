# TONY SYSTEM INVENTORY — Kiểm kê toàn bộ thành phần (AS-BUILT)
**Cập nhật:** 01/11/2026 16:45 · Nguồn: đếm trực tiếp workspace + runtime live

## 1. CodeBase — đếm thật (16:33)

| Nhóm | Số lượng | Nguồn xác minh |
|---|---|---|
| Modules Python `src/quan_ai_brain` | **230 file .py / 34 subpackage** | os.walk 16:33 |
| Subpackage lớn nhất | cognition: 41 · memory: 38 · voice: 14 · integration: 15 · monitoring: 11 · tools: 11 | Counter |
| Scripts `tools/` | **126** | listdir |
| Test files `tests/` | **155** | listdir |
| Tests PASS | **3.002 / 44 skipped / 0 FAIL** (125s) | TEST_RUN_LATEST.txt 16:31 |
| Databases | brain.db (19 bảng, 91 MB) + health_alerts.db + kèm 2 DB tasks/consultations | sqlite live |
| Báo cáo | 305+ file reports/ | audit 12:30 |

## 2. Subpackage bản đồ nhanh

| Subpackage | File | Vai trò | Runtime? |
|---|---|---|---|
| web | 2 | server.py (dual 8765/8766) + dashboard | ✅ LIVE (HTTP 200 ×2) |
| cognition | 41 | cognitive_loop, self_model, reflection, critical_thinker… | ⚠️ 1/5 INTEGRATED (M2 audit) |
| memory | 38 | episodic/semantic/procedural + review + consolidation | ✅ (DB ghi sống) |
| voice | 14 | wake word, STT, TTS pipeline | ⚠️ Pi5 (đang chờ audio) |
| monitoring | 11 | health_monitor, alert_engine (+owner-ACK MỚI) | ✅ LIVE |
| governance | 6 | approvals, emergency STOP/FREEZE, R0-R5 | ✅ enforced |
| edge | 3 | telemetry, HMAC auth (M6-B1) | ✅ LIVE (READY, RTT 220ms) |
| learning | 10 | continuous_learning_engine + daemon | ✅ LIVE (16:13) |
| gateway | 5 | GLM/ncom gateway | ✅ |
| integration | 15 | netchat, outlook, netmind bridge | ✅ responder LIVE |
| tools | 11 | tool registry/executor | ✅ |
| security | 7 | R0-R5 enforcement | ✅ |
| api | 1 | contracts | ✅ |
| orchestration | 4 | supervisor | ⚠️ partial |
| execution | 4 | executors (giới hạn an toàn) | ✅ |
| llm / ai | 7+7 | GLM client, embeddings (Ollama BGE-M3) | ✅ |

## 3. Dịch vụ đang chạy thật (16:32)

| Service | PID (cặp launcher→child) | Start | Trạng thái |
|---|---|---|---|
| Dual servers 8765+8766 | 17952→19380 | 16:13:10 | HTTP 200 ×2 |
| NetChat responder | 17512→16356 | 16:13:10 | Chạy sạch 0 router-error |
| Learning daemon | 14348→18748 | 16:13:10 | 1 cycle OK (4.565 knowledge) |
| **Watchdog** | — | — | ❌ **MISSING (0 process)** |
| Pi5 edge daemon | quanpt1@100.100.83.59 | 15:40 | pgrep=1, READY |

## 4. Data sống (16:33)

| Bảng | Rows | Ghi chú |
|---|---|---|
| candidate_knowledge | 4.579 | 1.491 approved + 3.088 quarantined |
| candidate_knowledge_archive | 110.962 | lịch sử promote |
| episodes | 2.685 | episodic (mới nhất 16:30 test E2E) |
| memories / semantic_memory | 2.141 / 1.842 | trí nhớ dài hạn |
| knowledge_units / relations | 150 / 210 | |
| feedback | 408 | |
| memory_review_runs/sessions | 1 / 2 | lần SÀNG LỌC gần nhất 27/10 |
| review_findings / questions / inferences | 76 / 42 / 6 | |
| health_alerts (DB riêng) | 187 | bt_speaker sent=0 sau ACK 16:10 |

## 5. Backup & Mirror

| Thành phần | Trạng thái |
|---|---|
| Backup 2AM brain_*.db | ⚠️ **12 file, mới nhất 28/10 — DỪNG 4 NGÀY** (Task Scheduler cần kiểm tra) |
| Backup knowledge_approval | 31/10 ✅ |
| **Mirror F:\BRAIN** | ✅ MỚI 16:32 — 47.051 file / 6,21 GB, verify 3 lớp, tự chạy 02:30/ngày (task QUAN_AI_BRAIN_MIRROR_F) |
| backups/path_migration_20261030 | ✅ (lịch sử di trú PC cũ) |

## 6. Phân loại kiến trúc (PHẦN 3.2)

- **Lõi:** web/server.py, cognition (loop/registry), memory engines, edge + auth, monitoring
- **Nghiệp vụ:** learning, knowledge, planning, decision, analytics
- **Giao tiếp:** integration (netchat), voice, dashboard
- **Quản trị:** governance, security, contract
- **Thử nghiệm:** tests/ (155), tools/_test_import_repro.py
- **Trùng lặp/chưa dùng:** .venv_broken_backup (1,1 GB — có thể dọn sau duyệt), mobile/ (2 file, chưa wire)
- **Không xóa gì trong đợt audit** — chỉ ghi nhận.
