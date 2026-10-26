# DIGITAL EMPLOYEE BRAIN — THIẾT KẾ CHI TIẾT (docs)

**Mã tài liệu:** DSG-QAB-DEB-20261026
**Đối tượng đọc:** kỹ sư phát triển QUAN AI BRAIN + chủ sở hữu `quanpt1` (duyệt kiến trúc)
**Quan hệ với tài liệu khác:** AUD (hiện trạng đo thật) → ARC (kiến trúc mục tiêu) → PLAN (kế hoạch sprint) → tài liệu này (thiết kế chi tiết từng thành phần mới)

---

## 1. Nguyên tắc thiết kế bất biến

1. **WRAP + EXTEND + ORCHESTRATE + INTEGRATE** — module mới chỉ bọc và điều phối module cũ; không reimplement PlanOrchestrator/DurableTaskRegistry/PolicyEngine.
2. **Tách biệt 7 vai trò:** model reasoning | policy enforcement | data access | execution | memory persistence | approval | evaluation. LLM không nắm vai trò nào khác ngoài reasoning + tổng hợp ngôn ngữ.
3. **Mọi trạng thái phải có bằng chứng:** mỗi trường trạng thái đi kèm {source, evidence_ref, verification_status, last_verified_at}; UNKNOWN/UNVERIFIED là trạng thái hợp lệ, không bịa HEALTHY.
4. **Fail-closed ở mọi biên:** provider, approval, grant, connector — thiếu thông tin → từ chối, không đoán.
5. **Audit append-only.**

## 2. Thiết kế CognitiveLoop (Sprint B1)

### 2.1. Vị trí và quan hệ

```
quan_ai_brain/cognition/cognitive_loop.py   (MỚI, ~300 dòng)
    ├── dùng  orchestration.plan_orchestrator.PlanOrchestrator   (lập DAG)
    ├── dùng  orchestration.task_registry.DurableTaskRegistry    (checkpoint bền vững — tasks.db)
    ├── dùng  orchestration.supervisor.Supervisor                (giám sát bước)
    ├── dùng  governance.policy.PolicyEngine                     (RISK_ASSESSMENT độc lập LLM)
    ├── dùng  llm.netmind_provider.NetMindProvider               (chỉ reasoning)
    ├── dùng  core.audit.AuditLogger                             (mọi chuyển trạng thái)
    └── dùng  execution.process_containment.ContainedExecutionRunner (thực thi có kiểm soát, Inert backend)
```

### 2.2. State machine

```
RECEIVED → CONTEXT_BUILDING → UNDERSTANDING → PLANNING → RISK_ASSESSMENT
→ WAITING_APPROVAL? → EXECUTING|SIMULATING → VERIFYING → REFLECTING
→ LEARNING_CANDIDATE → terminal{COMPLETED|PARTIALLY_COMPLETED|BLOCKED|FAILED|NEEDS_APPROVAL}
```

- Bỏ qua bước hợp lệ theo chính sách nhưng PHẢI ghi audit lý do (Master Prompt 3.1).
- Checkpoint: mỗi chuyển trạng thái ghi 1 dòng vào durable_task_steps (đã có bảng).
- Khôi phục sau restart: loop đọc durable_tasks status != terminal → tiếp tục từ checkpoint cuối; task quá tuổi → EXPIRED (policy GAP-R7).

### 2.3. Interface (dự thảo)

```python
class CognitiveLoop:
    def submit_task(self, task_spec: TaskSpec) -> str: ...           # task_id
    def resume_incomplete(self) -> list[str]: ...                    # sau restart
    def tick(self, task_id: str) -> TaskState: ...                   # 1 bước tiến (daemon gọi định kỳ)
    def approve(self, task_id: str, approval_nonce: str) -> bool: ...# cần policy cho phép
    def cancel(self, task_id: str, reason: str) -> bool: ...
```

TaskSpec bắt buộc: goal, context_refs, acceptance_criteria, risk_hint, deadline. Thiếu acceptance_criteria → trả NEEDS_APPROVAL ngay (không đoán tiêu chí).

## 3. Thiết kế ReflectionLoop (Sprint B2)

- Nguồn dữ liệu ĐỘC LẬP với LLM: durable_tasks + durable_task_steps (kế hoạch vs thực tế), logs/audit.jsonl (hành động thật), episodes (kết quả), semantic_memory (tri thức đã dùng).
- 12 câu hỏi Master Prompt 3.2 trả lời bằng truy vấn + số đo; riêng câu "quyết định nào sai" phải có dữ liệu outcome, không có → trả "CHƯA CÓ DỮ LIỆU ĐỦ".
- Đầu ra: `ReflectionReport{task_id, answers[12], lessons_verified[], lessons_hypothesis[], proposals_need_approval[]}` → lessons_verified vào episodic memory, lessons_hypothesis vào candidate (quarantine).
- Chống tự phong thành công: report chỉ khẳng định điều gì có evidence; phần còn lại là hypothesis.

## 4. Thiết kế Self-Model verify (Sprint C1)

- Mỗi câu trả lời trong 12 câu Master Prompt 2.2 phải chạy probe thật tại thời điểm hỏi (không cache quá 60s cho trạng thái runtime):
  - Component ONLINE check: socket/HTTP probe với timeout ngắn.
  - Dữ liệu: đếm SQL thật, không dùng số hardcode.
  - verification_status ∈ {VERIFIED_LIVE, VERIFIED_CACHED(t<60s), UNVERIFIED, STALE}.
- Kết quảphân biệt HEALTHY / DEGRADED / OFFLINE / UNKNOWN / UNVERIFIED theo quy ước: chỉ HEALTHY khi probe PASS + có evidence_ref; chết probe → OFFLINE; không probe được → UNKNOWN (không suy diễn).

## 5. Thiết kế Promotion Policy (Sprint D2)

| Lớp tri thức | Tự thăng cấp? | Điều kiện |
|---|---|---|
| L0 — general facts không rủi ro | Có thể (chính sách owner duyệt 1 lần) | confidence ≥ ngưỡng + 0 mâu thuẫn + regression pass |
| L1 — nghiệp vụ DC/production | KHÔNG tự — luôn qua owner | đề xuất lô ≤50 items/lần + rationale |
| L2 — SOP/procedure | KHÔNG tự | phải có test thực hành trong sandbox pass |
| L3 — safety/policy | KHÔNG BAO GIỜ tự | chỉ owner sửa, có phê duyệt riêng |

- Rollback: semantic_memory giữ version cũ khi cập nhật (không ghi đè) — GAP-M2.
- Đo hiệu quả: trước/sau promotion chạy memory benchmark (precision@k) → report GAP-M3.

## 6. Thiết kế Connector BATTERY AI V4 (Sprint E1)

```
quan_ai_brain/integration/battery_ai_connector.py  (MỚI, read-only)
  - config từ file YAML owner cung cấp (endpoint, auth profile NAME — không giá trị secret)
  - secret CHỈ đọc từ env var tại runtime, không log, không lưu
  - GET /metrics, GET /alarms (schema xác minh trước bằng sample payload owner duyệt)
  - mỗi mẫu: {source:"battery_ai_v4", ts, device_id, unit, quality_flag, evidence_ref}
  - rate limit tự đặt + circuit breaker (3 lỗi liên tiếp → OPEN 5 phút)
  - KHÔNG có phương thức write; class không chứa POST/PUT/DELETE
```

Điều kiện GO (thiếu 1 → NO-GO, dừng tại approval gate): owner cung cấp endpoint thật; sample auth profile; xác nhận giới hạn tải; schema mẫu; phê duyệt R4 nếu cần cấu hình hệ thống.

## 7. Thiết kế Approval Card (Sprint F2)

13 trường bắt buộc (Master Prompt 4.3): task_id, incident_ref, evidence_summary, analysis+uncertainty, proposed_action, impact_scope, risk_level, dry_run_result, rollback_plan, approval_deadline, authority, execution_status, approval_nonce.
- Gửi qua NetChat; nonce dùng 1 lần (consumed_nonces); content-binding: hash(action payload) kiểm tra lại lúc thực thi — khác hash → từ chối, yêu cầu duyệt lại.

## 8. DelegationGrant (Sprint G1)

- Engine: kiểm tra mọi hành động auto trước khi thực thi: grant tồn tại? còn hạn? scope khớp? risk_class ≤ grant? max_executions chưa vượt? preconditions pass?
- Vi phạm → chặn + thu hồi (revoke) + audit + alert NetChat.
- Kill-switch drill (GAP-X2): test thật chặn hành động mới + thu hồi grant trong 1 lần drill có owner quan sát.

## 9. Chiến lược test

- Mọi HTTP test: mock io.BytesIO, không gateway thật, không đọc/đặt/in API key (ràng buộc Sprint 0 giữ nguyên).
- Mỗi sprint thêm test an toàn theo danh sách 12 kịch bản ở TEST REPORT mục 5.
- Benchmark độc lập: DC benchmark (E5) chạy trên fixture sự cố có đáp án chuẩn (tri thức SOP đã duyệt làm đáp án) — không để LLM tự chấm LLM.

## 10. Tiêu chí hoàn thành tổng thể (ĐÍCH ĐẾN)

| Câu hỏi Master Prompt Phần 11 | Trạng thái mục tiêu |
|---|---|
| Hiểu + tự mô hình hóa gì? | Self-model 12 câu trả lời có evidence, verify liveness probe thật |
| Năng lực nào test độc lập? | Mỗi năng lực 1 benchmark riêng, không gộp điểm |
| Học gì từ trải nghiệm? | Reflection 12 câu → lessons có provenance |
| Phát hiện tri thức sai? | Conflict detection + benchmark trước/sau promotion |
| Chứng minh quyết định đúng? | Decision memory: outcome + evidence truy xuất theo task_id |
| Khi nào được tự hành động? | Chỉ trong DelegationGrant còn hạn + risk thấp + dry-run pass |
| Điều gì bắt buộc owner duyệt? | L1–L3 tri thức, connector mới, production execution, grant mới, policy |
| Bước tới cấp trưởng thành kế? | Gap Register về 0 gap CAO ở nhóm tương ứng + benchmark đạt ngưỡng |

**Tuyên bố trung thực:** tại thời điểm tài liệu này, execution vẫn Inert (đúng thiết kế); hệ thống ở cấp trưởng thành L1–L2 thực chất (Observe + Understand/Recommend); các cấp cao hơn chỉ tuyên bố sau khi benchmark + phê duyệt tương ứng có bằng chứng.
