# DEOM M1 — TÀI LIỆU 2/4: PERMISSION MATRIX (Ma trận quyền 13 quyền DEOM §5.1)

**Ngày:** 01/11/2026 · **Trạng thái:** THIẾT KẾ — cài đặt ở M4 (nối RBAC + policy.py)

---

## 1. Ma trận 13 quyền × vai trò

Quyền dạng `resource:action` — tương thích `security/rbac.py` (Permission/Role/RBACEngine deny-by-default, **đã có sẵn, chưa nối vào task flow**).

| # | Quyền | TONY (mặc định) | Ghi chú thực thi |
|---|---|---|---|
| 1 | `system:read` | ALLOW | health, log, inventory — nhận thức tự do |
| 2 | `memory:read` | ALLOW | unified_memory 5 lớp |
| 3 | `memory:write` | ALLOW (workspace) | episodes, semantic — có audit |
| 4 | `task:create` | ALLOW | registry + intake NL (M2) |
| 5 | `task:execute` | CONDITIONAL | R0–R2 tự; R3 notice; R4 phải có approval_id; R5 không bao giờ |
| 6 | `task:cancel` | ALLOW (task của mình) | task do owner giao → chỉ owner hủy |
| 7 | `file:write` | CONDITIONAL | PathGuard workspace-only (`path_guard.py`), outside → DENY |
| 8 | `net:send` | CONDITIONAL | DM NetChat qua responder; email draft chỉ soạn (email_drafts/) |
| 9 | `config:change` | APPROVAL | R4 — approval_verifier fail-closed |
| 10 | `db:migrate` | APPROVAL | M2 migration tasks.db — backup + ADD COLUMN + verify 578 records |
| 11 | `knowledge:promote` | APPROVAL | Q-4 verifier — quarantined → approved có bằng chứng |
| 12 | `deploy:execute` | APPROVAL | không tự deploy; restart dịch vụ = quy trình chuẩn có kiểm |
| 13 | `approve:action` | **DENY vĩnh viễn** | CHỈ Quanpt1; AI tự phê duyệt = vi phạm charter nặng nhất |

## 2. Vai trò khởi tạo (seed vào RBACEngine ở M4)

```
Role "tony":        #1–8 theo bảng trên (6,8 CONDITIONAL), #9–12 = APPROVAL_REQUIRED, #13 DENY
Role "owner":       toàn bộ 13 quyền ALLOW (Quanpt1)
Role "tony-escalate": tạm thời giữ trong lúc chạy task đã duyệt — scope thu hẹp theo approved_scope_json của task
```

- `RBACEngine.check()` deny-by-default → quyền không liệt kê = từ chối (an toàn mặc định).
- `ABACEngine` bổ sung điều kiện ngữ cảnh: giờ yên tĩnh, owner-vắng, resource budget.

## 3. Tích hợp 3 lớp (thiết kế resolver M4)

```
Yêu cầu hành động
  1. PolicyEngine (policy.py R0–R5)  → gate rủi ro (R5 BLOCK, R4 APPROVAL_REQUIRED, R2 path-guard)
  2. PermissionResolver (mới, M4)    → RBAC role + ABAC ngữ cảnh + permission_scope của task
  3. ApprovalVerifier (Q-4)          → với R4: HMAC token fail-closed, 1 token 1 lần
→ Kết quả: ALLOW / ALLOW_WITH_NOTICE / APPROVAL_REQUIRED / BLOCKED (denied reasons đầy đủ vào audit.db)
```

**Chống lệnh trái (DEOM §11):** agent nhận lệnh từ agent khác vẫn phải qua 3 lớp trên — không có "ủy quyền chuỗi".

## 4. Bằng chứng nền đã có (M0 audit)

- `governance/policy.py` 67 dòng đọc toàn bộ: R5→BLOCKED, R4→APPROVAL_REQUIRED, R3→ALLOW_WITH_NOTICE, R2 path-guard, R0/R1→ALLOW.
- `approval_verifier.py` fail-closed — 3.209 tri thức promoted Q-4 qua nó.
- approval_cards: 20 APPROVED / 1 CANCELLED, 0 PENDING.
- `security/rbac.py`: RBACEngine + ABACEngine hoàn chỉnh, deny-by-default — chưa wire (M4).

---
*TONY — DEOM M1 · Permission Matrix thiết kế theo 13 quyền DEOM §5.1.*
