# DEOM M3 — KẾ HOẠCH THIẾT KẾ: AGENT DISPATCHER + DEPENDENCY MANAGER

**Ngày:** 02/11/2026 · **Cơ sở:** DEOM §6.3 + §7.2 + GAP #6/#7 (M0) + schema M2 thật · **Trạng thái:** THIẾT KẾ — 0 code thay đổi trong bước này

---

## 1. Phạm vi M3 (từ GAP ANALYSIS + DEOM M1)

| Thành phần | Hiện trạng (đã đọc code thật) | M3 bổ sung |
|---|---|---|
| Work Queue | `task_registry.work_queue()` — đã có ORDER BY priority + deadline + chống learning (M2) | Giữ nguyên — M3 KHÔNG đụng |
| Agent Dispatcher | CHƯA CÓ: supervisor luôn tự chạy mọi task (1 "bộ não"), không chọn agent | `AgentDispatcher` — chọn agent theo capability + workload + quyền |
| Dependency Manager | `dependencies_json` đã lưu (M2) nhưng KHÔNG ai kiểm khi chọn task | `DependencyManager` — chặn task chưa đủ điều kiện, mở khóa chuỗi |
| Anti-conflict | chưa có | 1 agent 1 task đồng thời; correlation_id xuyên suốt |
| Correlation ID | `correlation_id` có sẵn trong TaskRecord | Đảm bảo mọi assignment ghi transition `actor=agent_id` |

**Nguyên tắc §2.1:** KHÔNG tạo service/daemon mới — Dispatcher là module trong `orchestration/`, gọi từ supervisor loop hiện có.

## 2. Thiết kế AgentDispatcher (`orchestration/agent_dispatcher.py` — MỚI)

### 2.1. AgentProfile (dataclass)
```
agent_id        : str            # "tony-core" | "tony-pi5" | "tony-research" | worker tên riêng
capabilities    : list[str]      # khớp required_tools_json của task
max_concurrent  : int = 1        # mặc định 1 — anti-overload
current_tasks   : list[str]      # task_id đang giữ
allowed_risks   : list[str]      # ["R0","R1","R2"] mặc định — R3+ không bao giờ tự nhận
source_filter   : list[str] | None   # None = nhận mọi nguồn
```

### 2.2. Thuật toán chọn (deterministic, không AI)
```
dispatch(task) → agent | None
1. Lọc agent có ĐỦ capabilities ⊇ required_tools (thiếu → skip)
2. Lọc agent allowed_risks chứa task.risk_level (R3/R4/R5 → KHÔNG ai tự nhận)
3. Lọc agent còn chỗ (len(current_tasks) < max_concurrent)
4. Nếu task.source == "learning" → chỉ agent có "learning" trong capabilities
5. Chọn agent workload thấp nhất → hòa thì theo thứ tự đăng ký
6. Không có ai đạt → trả None (task ở lại READY — không ép chạy)
```

### 2.3. Assignment (audit đầy đủ qua M2 transition log)
- `dispatcher.assign(task_id, agent_id)` → ghi `assigned_agents_json` + transition
  `actor=dispatcher, reason="assigned to <agent_id>"`, correlation_id giữ nguyên
- Hoàn tất task → `dispatcher.release(task_id)` dọn current_tasks
- **Chống lệnh trái ngược:** 1 task chỉ 1 agent giữ; agent đang giữ task X không nhận task Y có `parent_task_id`=X hoặc trùng goal tiền tố (conflict check)

## 3. Thiết kế DependencyManager (`orchestration/dependency_manager.py` — MỚI)

```
eligible(task) → (bool, reason)
1. dependencies_json rỗng → True
2. Mọi dep task_id phải tồn tại (dep mất → BLOCKED + transition reason="missing dependency")
3. Mọi dep phải TERMINAL_OK (COMPLETED/COMPLETED_VERIFIED/COMPLETED_PARTIALLY)
   — COMPLETED_UNVERIFIED KHÔNG đủ (fail-honest: phụ thuộc chưa có bằng chứng)
4. Deadline của task phải ≥ deadline muộn nhất của deps (nếu cả hai có)
```

- `unblock_dependents(task_id)` — khi task COMPLETED_VERIFIED/PARTIALLY, gọi trong supervisor sau verify: task phụ đang BLOCKED vì thiếu nó → chuyển về READY + transition reason="dependency satisfied".
- **Phát hiện vòng (cycle)**: DFS trên đồ thị dependencies khi register — có vòng → từ chối đăng ký task mới (ValueError, không tự cắt).

## 4. Tích hợp supervisor (sửa `supervisor.py` — điểm duy nhất)

- `SELECTING_TASK`: thay `list_tasks(status=PENDING, limit=1)` bằng:
  `work_queue()` → lọc qua `dependency_manager.eligible()` → `dispatcher.dispatch()`
  → không ai nhận → IDLE (giữ hành vi cũ).
- Sau verify (COMPLETED_*): gọi `unblock_dependents` + `dispatcher.release`.
- Mọi thay đổi vẫn qua `update_task_status` → transition log tự động (không ghi đè).

## 5. Nghiệm thu M3

1. Tests mới `tests/test_deom_m3_dispatcher.py`:
   - dispatch chọn đúng agent theo capability/risk/workload
   - R3+ không agent nào nhận; learning chỉ vào agent learning
   - agent đầy chỗ → task ở lại READY
   - dependency: dep chưa xong → không eligible; dep UNVERIFIED → không đủ; xong → unblock
   - cycle detection từ chối; missing dep → BLOCKED
   - anti-conflict: 1 agent 1 task; conflict goal → từ chối
2. Regression: backbone 64/64 + FULL ≥ 3.071 PASS / 0 FAIL.
3. E2E: đăng ký chuỗi 3 task phụ thuộc + 2 agent → dispatch đúng thứ tự, audit transition đầy đủ.
4. HANDOFF + REGISTER; commit conventional `feat(orchestration): add DEOM M3 agent dispatcher + dependency manager`.

## 6. Biên an toàn (không đổi)

- R4/R5 vẫn phải approval_verifier — Dispatcher KHÔNG tự giao task R3+ cho ai (kể cả "agent đặc biệt").
- `approve:action` DENY vĩnh viễn — Dispatcher không liên quan approval.
- Không daemon mới, không port mới — chạy trong supervisor loop + watchdog hiện có.
- Hoàn tác: revert commit (schema không đổi — 2 module mới thuần code + tests).
