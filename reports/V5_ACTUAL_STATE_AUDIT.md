# V5 — ACTUAL STATE AUDIT

**Thời điểm:** 27/10/2026 19:26 GMT+7 · **Branch:** master · **HEAD:** `3ac83c5` (Sprint 16)

## 1. HIỆN TRẠNG (xác minh live, không tin baseline)

### 1.1. Runtime & Git
| Hạng mục | Giá trị |
|----------|---------|
| Python | 3.11.9 x64 |
| Branch | master |
| HEAD | `3ac83c5` (Sprint 16 Memory Hygiene) |
| Working tree | Có thay đổi chưa commit (session song song: coordinator.py, models.py) |

### 1.2. Test suite
```
./.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=no
```
**Kết quả:** ✅ **978 passed / 0 failed / 1 skipped**

- **1 skipped:** `test_vietnamese_tts.py` — Pi 5 hardware offline
- **Flaky test:** `test_end_to_end_chat.py::test_web_server_e2e_multi_turn_chat` — PASS khi chạy đơn lẻ, FAIL khi chạy cùng suite (contention Ollama/DB)

### 1.3. Live state (chỉ đọc)
| Endpoint | Status | Chi tiết |
|----------|--------|----------|
| `/api/health` | ✅ HEALTHY | core_server, ollama_daemon, brain_db, task_registry |
| `/api/executive/overview` | ✅ OK | persona: QUAN AI BRAIN, capability_count: 9 |
| `/api/executive/tasks` | ⚠️ 0 active | DB có 24 PENDING, API trả 0 (filter bug?) |
| `/api/executive/edge/status` | ⚠️ None | Pi 5 chưa kết nối |

**DB counts:**
- Episodes: 1343
- Semantic memory: 1841
- Task PENDING: 24 (session song song)
- Task archived: 4 (em archive trước đó)
- Task COMPLETED: 2

### 1.4. Cognitive Integration audit
| Module | Tồn tại | Tích hợp vào chat | Ghi chú |
|--------|---------|-------------------|---------|
| `cognitive_state.py` | ✅ | ❌ | API tồn tại, chưa dùng trong context |
| `session_memory.py` | ✅ | ✅ | persist_chat_turn hoạt động |
| `context_builder.py` | ✅ | ⚠️ | Không refs cognitive_state |
| `retrieval.py` | ✅ | ✅ | CognitiveRetriever hoạt động |
| `coordinator.py` | ✅ | ✅ | create_plan dùng cognitive_state |

**Phát hiện:** Cognitive State được build trong `ExecutiveCoordinator.plan()` nhưng **KHÔNG được truyền vào chat context**. Chat chỉ dùng Session Memory + Retrieval, không có evidence traceability.

## 2. THAY ĐỔI CHƯA NGHIỆM THU

- **Session song song:** `coordinator.py`, `models.py` — chưa commit, đang sửa live
- **24 task PENDING:** Session song song tạo liên tục — không được archive/cancel

## 3. INCREMENT ĐỀ XUẤT

**Hướng A — Cognitive Evidence Integration**

**Vấn đề:** Chat response không có evidence traceability — không biết thông tin đến từ đâu (VERIFIED/OBSERVED/CANDIDATE).

**Increment:** Tích hợp Cognitive State vào `PromptContextBuilder` — context hiển thị verification_status + source_ref.

**File sửa:**
- `cognition/context_builder.py` — thêm cognitive_state param
- `web/server.py` — pass cognitive_state từ coordinator vào context

**Test:**
- Context chứa evidence với verification_status
- CANDIDATE không được treat as VERIFIED
- Mâu thuẫn được giữ lại (không auto-resolve)

**Không sửa:**
- Session song song files
- 24 task PENDING
- Pi 5 integration

## 4. RỦI RO

| Rủi ro | Mức độ | Giảm thiểu |
|--------|--------|------------|
| Session song song conflict | Medium | Không đụng file của họ |
| Context quá dài | Low | Cap evidence count |
| Backward compatibility | Low | cognitive_state là optional param |

## 5. TIẾN ĐỘ

- [x] Phase A — Audit actual state
- [x] Phase B — Audit cognitive integration
- [ ] Phase C — Chọn increment + implementation plan
- [ ] Phase D — Implement
- [ ] Phase E — Test
- [ ] Phase F — Live smoke
- [ ] Phase G — Governance check
- [ ] Phase H — Handoff

---
*Audit bởi: QUAN AI BRAIN V5 Agent · 27/10/2026 19:26 GMT+7*