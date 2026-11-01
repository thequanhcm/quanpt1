# V5 — IMPLEMENTATION PLAN

**Increment:** Cognitive Evidence Integration — Tích hợp Cognitive State vào chat context

**Vấn đề có bằng chứng:**
- Audit Phase A+B: Cognitive State được build trong `ExecutiveCoordinator.plan()` nhưng KHÔNG được truyền vào chat context
- Chat response không có evidence traceability — không biết thông tin đến từ đâu (VERIFIED/OBSERVED/CANDIDATE)
- Sprint 15 smoke phát hiện: system prompt gây noise contradictions (đã fix Sprint 16)

**Nguyên nhân gốc:**
- `PromptContextBuilder` không có param `cognitive_state`
- Chat handler không pass `cognitive_state` từ coordinator vào context
- Retrieval chỉ trả về memories, không có verification_status + source_ref trong response

**Increment được chọn:**
1. Thêm `cognitive_state` param vào `PromptContextBuilder.build_context()`
2. Pass `cognitive_state` từ chat handler (nếu có)
3. Context hiển thị evidence với `verification_status` + `source_ref`
4. CANDIDATE không được treat as VERIFIED
5. Mâu thuẫn được giữ lại (không auto-resolve)

**File dự kiến sửa:**
- `src/quan_ai_brain/cognition/context_builder.py` — thêm cognitive_state param
- `src/quan_ai_brain/web/server.py` — pass cognitive_state vào context (nếu có)

**API/schema bị ảnh hưởng:**
- Không thay đổi API signature (cognitive_state là optional param)
- Không thay đổi DB schema

**Invariant phải giữ:**
- CANDIDATE knowledge không được treat as VERIFIED fact
- Mâu thuẫn không được auto-resolve
- Backward compatible (cognitive_state = None vẫn hoạt động)

**Test cần bổ sung:**
- Context chứa evidence với verification_status
- CANDIDATE không được render as VERIFIED
- Mâu thuẫn được giữ lại trong context
- Backward compatibility (no cognitive_state)

**Phương án rollback:**
- Revert commit — cognitive_state là optional param, không breaking change

## Timeline

| Phase | Thời gian | Ghi chú |
|-------|-----------|---------|
| Implement | 15-20 phút | 2 files, ~50 lines |
| Test mục tiêu | 5 phút | 4-6 tests |
| Full suite | 2 phút | 978 tests |
| Live smoke | 5 phút | Chat + verify context |
| Handoff | 5 phút | Reports + commit |

**Tổng:** ~30-40 phút

---
*Plan bởi: QUAN AI BRAIN V5 Agent · 27/10/2026 19:26 GMT+7*