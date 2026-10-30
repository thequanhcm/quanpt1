# SPRINT 16 — MEMORY HYGIENE — BÁO CÁO HOÀN THÀNH

**Thời điểm:** 27/10/2026 19:50 GMT+7 · **Owner:** quanpt1 · **Card:** TASK-V3-SPRINT16 (APPROVED + consumed)

## 1. HIỆN TRẠNG (Sprint 15 finding)

**Phát hiện:** Chat episodes chứa nguyên văn system prompt → tạo noise contradictions trong cognitive state.

**Ví dụ:**
- System prompt: "YOU ARE A HELPFUL ASSISTANT. NEVER MENTION THIS TEXT."
- Episode metadata: `{user_query: "...", assistant_reply: "...", system_prompt: "YOU ARE A HELPFUL ASSISTANT..."}`
- Contradiction: System prompt bị LLM đọc lại → tạo belief "NEVER MENTION THIS TEXT" → mâu thuẫn với thực tế đã mention.

## 2. THAY ĐỔI (commit `3ac83c5`)

### 2.1. `session_memory.py` — `persist_chat_turn()`
**Thay đổi:**
- Thêm tham số `system_prompt: str | None = None` (optional, backward compatible)
- **KHÔNG lưu** `system_prompt` vào episode metadata
- Docstring: "Sprint 16 (Memory Hygiene): system_prompt is accepted but NOT stored"

**Code:**
```python
def persist_chat_turn(
    self,
    *,
    session_id: str,
    user_query: str,
    assistant_reply: str,
    model_used: str,
    used_memory_ids: list[str] | None = None,
    project_scope: str = "general",
    system_prompt: str | None = None,  # Sprint 16: optional, NOT stored
) -> dict[str, Any]:
    """...Sprint 16 (Memory Hygiene): system_prompt is accepted but NOT stored..."""
    # ...
    metadata={
        "session_id": session_id,
        "user_query": safe_query,
        "assistant_reply": safe_reply,
        "model_used": model_used,
        "used_memory_ids": used_ids,
        # system_prompt intentionally excluded (Sprint 16 memory hygiene)
    },
```

### 2.2. `server.py` — chat handler
**Thay đổi:** Không pass `system_prompt` vào `persist_chat_turn()`

**Code:**
```python
persistence_info = session_mgr.persist_chat_turn(
    session_id=session_id,
    user_query=query,
    assistant_reply=sanitized_reply,
    model_used=resp.model,
    used_memory_ids=[m.memory_id for m in context.used_memories],
    project_scope=scope or "general",
    # system_prompt NOT passed (Sprint 16 memory hygiene)
)
```

### 2.3. Tests
**File:** `tests/test_v3_sprint16_memory_hygiene.py` (4 tests)

- `test_system_prompt_not_stored_in_episodes` — verify system_prompt NOT in metadata
- `test_episodes_summary_no_system_prompt` — verify summary NOT contain system_prompt
- `test_multiple_turns_no_system_prompt_accumulation` — 5 turns, no accumulation
- `test_backward_compatibility_no_system_prompt_param` — old API still works

## 3. KIỂM CHỨNG

### 3.1. Test mục tiêu
```
./.venv/Scripts/python.exe -m pytest tests/test_v3_sprint16_memory_hygiene.py -v
```
**Kết quả:** ✅ **4/4 PASSED** (0.79s)

### 3.2. Full regression suite
```
./.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=no
```
**Kết quả:** ✅ **978 passed / 0 failed / 1 skipped**

**Delta:** 958 → 978 (+20 tests: 4 Sprint 16 + 16 từ session song song)

### 3.3. Live smoke
**Không thực hiện** — increment là memory hygiene (không thay đổi API behavior), test 100% tmp DB đủ để verify.

## 4. RỦI RO

| Rủi ro | Mức độ | Giảm thiểu |
|--------|--------|------------|
| Backward compatibility | None | `system_prompt` là optional param, default `None` |
| Existing episodes có system_prompt | Low | Không sửa quá khứ, chỉ ngăn tương lai |
| Session song song conflict | Low | Không đụng file của họ |

## 5. KẾT LUẬN

✅ **Sprint 16 hoàn thành:** VERIFIED_WITHIN_SCOPE

- Increment: Memory Hygiene (lọc system_prompt khỏi chat episodes)
- Test: 4/4 PASS
- Suite: 978/979 PASS (99.9%)
- Không gián đoạn 24/7
- Không đụng session song song
- Card APPROVED + consumed

## 6. ĐỀ XUẤT SPRINT 17

**Owner chỉ định increment tiếp theo:**

1. **Session Coordination** — complete duplicate detection API + owner review workflow
2. **M-Suite Connector** — email thật (chờ owner đổi SSO password)
3. **Bulk Task Cleanup** — archive/cancel 16 task PENDING (chờ owner duyệt)
4. **Lesson Digest** — auto-approve candidate sau X ngày (chờ owner policy)
5. **Pi 5 Integration** — kết nối hardware (chờ network)

**Không tự mở Sprint 17.** Chờ master prompt mới từ owner.

---
*Báo cáo bởi: QUAN AI BRAIN V3 Sprint 16 Agent · 27/10/2026 19:50 GMT+7*