# DEOM M4 — KẾ HOẠCH THIẾT KẾ: PERMISSION RESOLVER + APPROVAL WORKFLOW

**Ngày:** 02/11/2026 · **Cơ sở:** DEOM §5.1–5.3 + GAP #8/#9 (M0) + 4 tài liệu M1 + nền thật (policy.py, rbac.py, approval_verifier Q-4, approval_cards) · **Trạng thái:** THIẾT KẾ — 0 code thay đổi trong bước này

---

## 1. Phạm vi M4

| Thành phần | Hiện trạng (đã đọc code thật) | M4 bổ sung |
|---|---|---|
| PolicyEngine (R0–R5) | `governance/policy.py` — gate rủi ro chuẩn, R5 BLOCK / R4 APPROVAL_REQUIRED | Giữ nguyên — lớp 1 |
| RBACEngine + ABACEngine | `security/rbac.py` hoàn chỉnh, deny-by-default — **chưa wire vào task flow** | Wire qua `PermissionResolver` mới — lớp 2 |
| ApprovalVerifier (Q-4) | fail-closed HMAC, 1 token 1 lần, 3.209 promoted | Nối vào resolver — lớp 3 |
| Approval Cards | 20 APPROVED trong governance.db (schema: task_code/title/status/ttl/...) | **ApprovalCardService** — lifecycle PENDING→APPROVED/REJECTED/EXPIRED + 12 trường §5.3 |
| Approval separation | "TONY tạo card tự duyệt" chưa bị chặn bằng code | **Chặn bằng code**: requestor ≠ approver |

## 2. PermissionResolver (`governance/permission_resolver.py` — MỚI)

Hợp nhất 3 lớp thành 1 API duy nhất `resolve(request) → ResolverDecision`:

```
ResolverDecision:
  status: ALLOW | ALLOW_WITH_NOTICE | APPROVAL_REQUIRED | BLOCKED
  layers: [PolicyDecision, RBACDecision, ApprovalDecision]  — vết đầy đủ
  reason : gộp lý do các lớp từ chối (không nuốt)
```

**Thứ tự đánh giá (fail-closed tổng):**
1. **PolicyEngine.authorize** — R5 → BLOCKED dừng ngay; R2 ngoài workspace → DENY.
2. **RBAC role check** — 13 quyền `resource:action` (M1 doc 2/4) seed thành 3 role:
   `tony` (#1–8 theo ma trận: 9–12 APPROVAL_REQUIRED, 13 DENY) · `owner` (full 13) ·
   `tony-escalate` (chỉ sinh trong lúc chạy task đã duyệt, scope = permission_scope_json).
   Không role nào grant → **APPROVAL_REQUIRED hoặc BLOCKED theo risk** (không IMPLICIT allow).
3. **ABAC ngữ cảnh** — deny policy thắng ngay (giờ yên tĩnh, owner-vắng...). Engine có sẵn.
4. **Approval (R4):** `APPROVAL_REQUIRED` trừ khi `ApprovalVerifier.verify(...)` PASS với
   card/token còn hạn — lúc đó ALLOW (scope giới hạn permission_scope_json).

**Bất biến:** suy ra quyền thực thi từ nhận thức là KHÔNG THỂ (resolver chỉ gọi khi có task + action rõ ràng); `approve:action` DENY vĩnh viễn cho mọi subject ≠ quanpt1.

## 3. ApprovalCardService (`governance/approval_service.py` — MỚI)

### 3.1. Card 12 trường (DEOM §5.3) — lưu SQLite `data/approval_cards_v2.db`
```
approval_id, task_id, action_summary, risk_level(R4-only), requested_by,
scope_json, evidence_bundle, expires_at_utc(24h), state(PENDING/APPROVED/
REJECTED/CANCELLED/EXPIRED), decided_by, decided_at_utc, consumed_at_utc
```
DB riêng v2 — KHÔNG đụng governance.db hiện có (an toàn hoàn tác: xoá file).

### 3.2. API
- `create_card(...)` → PENDING; R5 → ValueError (không bao giờ tạo card R5).
- `approve(approval_id, decided_by, *, approval_evidence)` →
  **BLOCK nếu `decided_by == requested_by`** (self-approval — chặn code);
  card hết hạn → EXPIRED + xin lại; PASS → APPROVED (token HMAC qua verifier).
- `reject / cancel / expire_overdue()` — transition log nội bộ (sqlite table `card_events`).
- `consume(approval_id)` — 1 lần: đã consumed → từ chối (nonce).

### 3.3. Luồng (kênh thật đã sống)
DM "🟡 XIN DUYỆT <tóm tắt> — phản hồi: OK <mã>" → owner "OK <mã>" → responder gọi
`approve(decided_by='quanpt1')` → card APPROVED → supervisor thấy APPROVED → chạy.

## 4. Tích hợp (điểm nối tối thiểu)

- **Supervisor** `WAITING_FOR_APPROVAL`: thay passive-poll bằng
  `PermissionResolver.resolve()` — nếu APPROVED qua card còn hạn → RUNNING.
- **PlanOrchestrator** `_check_step_approval`: R4 step phải có card APPROVED + consumed đúng task.
- **Watchdog**: thêm `approval_expiry_sweep()` — card PENDING quá 24h → EXPIRED (nhắc 1 lần/ngày).

## 5. Nghiệm thu M4 (tests bắt buộc từ M1 doc 4/4)

1. self-approval BLOCKED; agent escalation BLOCKED (A không approve giúp B).
2. Token tái dùng → từ chối; hết hạn → EXPIRED; sai HMAC → fail-closed.
3. R5 → BLOCKED mọi đường (resolver không bao giờ hỏi approval cho R5).
4. R4 không card → APPROVAL_REQUIRED; có card hợp lệ → ALLOW; card consumed → lần 2 từ chối.
5. `approve:action` → DENY với mọi subject trừ quanpt1 (kể cả tony-escalate).
6. Owner dừng giữa chừng → PAUSED an toàn, checkpoint giữ nguyên.
7. Regression FULL ≥ 3.111 PASS / 0 FAIL + commit conventional + HANDOFF + Mirror F.

## 6. Biên an toàn (không đổi)

- Không đụng governance.db/approval_verifier hiện có (chỉ ĐỌC qua API có sẵn).
- DB v2 riêng; hoàn tác = xoá 2 module + file DB v2 + revert commit.
- Charter: quyền phê duyệt cuối cùng CHỈ quanpt1 — mọi đường code đều dẫn về đây.
