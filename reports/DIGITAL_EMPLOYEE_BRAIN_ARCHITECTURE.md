# DIGITAL EMPLOYEE BRAIN — KIẾN TRÚC MỤC TIÊU

**Mã tài liệu:** ARC-QAB-DEB-20261026
**Nguyên tắc gốc:** WRAP + EXTEND + ORCHESTRATE + INTEGRATE — không xây lại từ đầu, không tạo module trùng lặp.
**Cơ sở:** `reports/DIGITAL_EMPLOYEE_BRAIN_AUDIT.md` (đo thật 2026-10-26)

---

## 1. Sơ đồ năng lực 8 lớp (map vào code hiện có)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUAN AI BRAIN — Digital Employee                  │
│                                                                      │
│  [1 Identity]      → docs/IDENTITY.md + system_inventory.py          │
│  [2 Self-awareness]→ self_model_engine.py ← SystemInventory (probe)  │
│  [3 Understanding] → context_builder.py + retrieval.py               │
│  [4 Reasoning]     → cognitive_loop.py (MỚI, Sprint B)               │
│                       ← plan_orchestrator.py + supervisor.py         │
│  [5 Memory]        → sqlite_store.py + knowledge_ingestion.py        │
│                       (episodes/semantic/procedural/decision/pref)   │
│  [6 Learning]      → continuous_learning_engine.py (5 kiểu A–E)      │
│                       + promotion policy theo lô (Sprint D)          │
│  [7 Self-care]     → self_care_engine.py + watchdog.py + backup      │
│  [8 Accountability]→ governance/policy.py (R0–R5) + audit.py         │
│                       + consultation_inbox + Approval Card (NetChat) │
└─────────────────────────────────────────────────────────────────────┘
        │ read-only connectors (Sprint E, có duyệt endpoint)
        ▼
[BATTERY AI V4] [DCIM/VDCIM] [Monitoring] [Network] [Log/Ticket]
   Domain Brain chuyên ngành — QUAN AI BRAIN là bộ điều phối, KHÔNG thay thế
```

## 2. Vòng đời nhiệm vụ (state machine Sprint B)

```
RECEIVED → CONTEXT_BUILDING → UNDERSTANDING → PLANNING → RISK_ASSESSMENT
   → WAITING_APPROVAL (nếu policy yêu cầu)
   → EXECUTING | SIMULATING (Inert backend hiện tại)
   → VERIFYING → REFLECTING → LEARNING_CANDIDATE
   → COMPLETED | PARTIALLY_COMPLETED | BLOCKED | FAILED | NEEDS_APPROVAL
```

- Backend thực thi: tái dùng `ContainedExecutionRunner` + `InertProcessBackend` (process_containment.py) — mọi hành động đặc quyền vẫn qua ApprovalGate.
- Checkpoint/timeout/retry/hủy/khôi phục sau restart: tái dùng `DurableTaskRegistry` (tasks.db, 160 task thật đã chứng minh durability).
- Mỗi bước chuyển trạng thái ghi `logs/audit.jsonl` qua `AuditLogger` (502 dòng hiện có, format đã ổn định).

## 3. CognitiveLoop — thiết kế mở rộng (KHÔNG module trùng lặp)

| Vai trò trong vòng lặp | Thành phần đảm nhiệm | Ghi chú |
|---|---|---|
| Điều phối trạng thái | `cognition/cognitive_loop.py` (MỚI ~300 dòng) | Bọc quanh PlanOrchestrator, KHÔNG thay thế |
| Lưu trạng thái bền vững | `DurableTaskRegistry` (tasks.db) | đã có, test sẵn |
| Lập kế hoạch DAG | `PlanOrchestrator` | đã có |
| Giám sát bước | `Supervisor` | đã có |
| Suy luận | NetMindProvider (fail-closed) | GLM-5.3-Flash / Qwen3.5-122B deep tier |
| Đánh giá rủi ro độc lập | `PolicyEngine` (R0–R5) | đã có, tách biệt LLM |
| Phản tư | `cognition/reflection.py` (MỚI ~250 dòng) | 12 câu hỏi bắt buộc theo Master Prompt 3.2, nguồn dữ liệu = tasks.db + audit.jsonl + episodes, KHÔNG cho LLM tự kể chuyện thành công |
| Học | `ContinuousLearningEngine` | candidate → quarantine → duyệt |

## 4. Ranh giới bảo mật (bất biến, không cấu hình được)

1. `PolicyEngine` R5 hard-block — `governance/policy.py:51-52` (đã xác minh).
2. Provider fail-closed: thiếu `NETMIND_EXTERNAL_DATA_ALLOWED=true` → `NETMIND_DISABLED`, không fallback local âm thầm.
3. PathGuard chặn mọi đường dẫn ngoài workspace.
4. Mọi approval: một lần dùng (consumed_nonces), gắn đúng nội dung hành động, hết hạn theo TTL.
5. Audit ledger chỉ ghi thêm (JSONL append), không xóa/ghi đè.
6. Confidence chưa hiệu chuẩn → mọi ngưỡng 80% chỉ dùng để ĐỀ XUẤT, chưa dùng để tự thực thi.

## 5. DelegationGrant (Sprint G, thiết kế trước)

Schema theo Master Prompt 5.2: `grant_id, owner, scope, allowed_actions, resource_allowlist, risk_class, valid_from, expires_at, max_executions, max_concurrency, preconditions, verification_requirements, rollback_policy, revocation_policy`.

- Lưu trong `governance.db` (bảng `delegation_grants` ĐÃ TỒN TẠI — Sprint G chỉ cần lớp engine + test).
- Hết TTL → tự vô hiệu. Vi phạm precondition → thu hồi ngay. Kill-switch đã có bảng `emergency_states`.

## 6. DC Domain Intelligence (Sprint E)

- Connector đầu tiên: **BATTERY AI V4 API** (read-only) — điều kiện triển khai: endpoint + auth + schema + giới hạn tải được owner cung cấp và xác minh; KHÔNG đoán endpoint.
- Mỗi mẫu telemetry: source, timestamp, đơn vị, quality flag, device_id, evidence_ref.
- Incident pipeline: normalize → dedup/correlate → severity → asset impact → SOP match → RCA hypothesis (bằng chứng ủng hộ/phản bác/missing data) → đề xuất → verify phục hồi → bài học.
- Daily Digest qua NetChat kênh "Trợ lý Tony Pham" (đã hoạt động).

## 7. Tiêu chí nghiệm thu kiến trúc

- Mỗi năng lực: interface + test riêng + evidence + không gộp điểm (Master Prompt Phần 8).
- Không năng lực nào được tuyên bố ACTIVE khi chỉ có code — dùng `IMPLEMENTED_UNTESTED` → `VERIFIED_ACTIVE` sau khi test E2E thật (bài học Sprint 0).
