# DIGITAL EMPLOYEE BRAIN — KẾ HOẠCH TRIỂN KHAI

**Mã tài liệu:** PLAN-QAB-DEB-20261026
**Thứ tự ưu tiên bắt buộc (Master Prompt Phần 12):** GROUND TRUTH → SYSTEM RELIABILITY → COGNITIVE LOOP → SELF-MODEL → MEMORY & LEARNING ASSURANCE → DC CONNECTORS → INCIDENT INTELLIGENCE → CONTROLLED EXECUTION → BOUNDED AUTONOMY

---

## Trạng thái xuất phát (đo thật 2026-10-26)

- Ground truth: ✅ xong (AUD-QAB-DEB-A) — 546/1/2 tests, 4 DB, 502 audit lines.
- Giữ nguyên mọi chức năng đang chạy: Server 8765, NetChat bot, Learning daemon, Watchdog, KHOI_DONG_24_7.bat.

## Sprint A-fix — System Reliability (tiếp nối audit, ước tính 1 phiên)

| Task | File | Loại | Tiêu chí nghiệm thu |
|---|---|---|---|
| A1. Watchdog giám sát Ollama + NetChat bot + disk | `tools/watchdog.py` | PATCH | watchdog log ghi trạng thái 11434 mỗi cycle; không restart vô hạn (circuit breaker ≥3 fail → DEGRADED + alert NetChat) |
| A2. Health endpoint chuẩn `/api/health` | `web/server.py` | PATCH | HTTP 200 JSON {components:[{component_id, observed_value, status, observed_at, source, evidence_ref, verification_status, last_verified_at}]} |
| A3. Hướng dẫn bật Ollama autostart (owner chạy, 1 lần) | `docs/` | NEW doc | Ollama 11434 ONLINE sau reboot; test_keep_warm_pulse PASS |
| A4. Backlog policy cho 109 durable_tasks PENDING | `orchestration/task_registry.py` hoặc daemon | PATCH | task quá hạn → EXPIRED theo chính sách; không khôi phục hàng loạt |
| A5. Task Scheduler Admin (chờ owner cấp quyền 1 lần) | `setup_24_7_full.bat` | chạy lại khi có Admin | schtasks /Query thấy 4 task QUAN_AIBRAIN_* |

**Rào cản chờ owner:** A3 (bật Ollama), A5 (quyền Admin). A1, A2, A4 làm được ngay không cần quyền mới.

## Sprint B — Cognitive Loop (2–3 phiên)

| Task | File | Nghiệm thu |
|---|---|---|
| B1. `cognitive_loop.py`: state machine 11 trạng thái, checkpoint vào DurableTaskRegistry | MỚI + tái dùng orchestration/ | test: nhiệm vụ đi đủ vòng; process kill giữa chừng → khôi phục đúng trạng thái |
| B2. `reflection.py`: 12 câu hỏi phản tư, nguồn = tasks.db + audit.jsonl + episodes (KHÔNG LLM tự kể) | MỚI | test: phản tư phát hiện đúng 1 fail thật trong fixture; phân biệt bài học xác minh vs giả thuyết |
| B3. Chất lượng quyết định: gắn decision outcome vào episodes | PATCH sqlite_store | test: truy xuất lịch sử quyết định theo task_id |
| B4. Tích hợp nhẹ vào server `/api/task/lifecycle` | PATCH web/server.py | test HTTP mock (không gateway thật) |

**Chính sách:** mọi test HTTP dùng io.BytesIO mock, không gọi gateway thật, không đọc API key (ràng buộc Sprint 0).

## Sprint C — Self-Model & Deep Memory (2 phiên)

- C1. SelfModelEngine trả lời 12 câu hỏi Master Prompt 2.2 bằng probe thật (không cấu hình) — mỗi trường có evidence_ref + verification_status.
- C2. Phát hiện tri thức mâu thuẫn/lỗi thời trong semantic_memory (720 items) — báo cáo, không tự xóa.
- C3. Thẩm định quarantined theo lô có chính sách (37,716 items): chấm điểm liên quan DC, đề xuất lô cho owner duyệt.
- C4. Benchmark memory: precision@k, MRR (mở rộng memory/benchmark.py đã có).

## Sprint D — Learning Assurance (2 phiên)

- D1. Chuẩn hóa candidate schema (12 bước Master Prompt 6).
- D2. Promotion policy theo lớp tri thức — chỉ lớp có owner duyệt trước mới tự thăng cấp; regression pass bắt buộc; rollback test.
- D3. Learning effectiveness report: tỷ lệ candidate hữu ích, false promotion.

## Sprint E — DC Domain Intelligence (2–3 phiên, CẦN owner cung cấp endpoint)

- E1. Connector read-only BATTERY AI V4 (điều kiện: endpoint + auth + schema thật).
- E2. Telemetry normalize + quality flags.
- E3. Incident intelligence: triage, SOP match (tri thức SOP 4-phase đã duyệt 10/10), RCA hypothesis có bằng chứng phản bác.
- E4. Daily Digest qua NetChat.
- E5. DC benchmark độc lập ≥85% trước khi tin vào triage ≥90%.

## Sprint F — Controlled Execution (2–3 phiên)

- F1. Sandbox nâng cấp theo thiết kế Sprint 5/6 (executor staging đã có tài liệu signoff).
- F2. Approval Card đầy đủ 13 trường qua NetChat; chống replay (consumed_nonces đã có bảng).
- F3. Dry-run ≥10 lần thành công cho mỗi hành động mới; kill-switch drill thật.
- F4. Production chỉ mở sau phê duyệt riêng.

## Sprint G — Bounded Autonomy (2 phiên)

- G1. DelegationGrant engine (governance/db đã có bảng).
- G2. Hành động đầu tiên được ủy quyền: rủi ro thấp, phạm vi hẹp (ví dụ: restart learning daemon, refresh health snapshot).
- G3. Tự thu hồi khi vi phạm; đánh giá tuần trước khi mở rộng.

## Mốc phê duyệt

| Mốc | Cần quanpt1 duyệt |
|---|---|
| Kết thúc Sprint A-fix | diff + test kết quả |
| Trước Sprint B commit | tiêu chí nghiệm thu B |
| Trước khi nối connector thật (E1) | endpoint + credentials scope (KHÔNG đọc secret) |
| Trước production execution (F4) | phê duyệt riêng theo R4 |
| Trước mỗi DelegationGrant (G) | grant scope + TTL |

## Rủi ro & rollback

- Mỗi sprint: nhánh thay đổi nhỏ, test trước/sau, có thể rollback bằng git revert commit sprint (không reset --hard).
- DB migration: chỉ thêm bảng/cột, không xóa; script rollback đi kèm.
- Không động vào: Skill/ (read-only), bot-netchat skill, BATTERY AI V4, DC-COMMAND, os_kernel.
