# UAG_V1_P0_AUDIT.md — P0 Audit Universal Action Gateway (02/11/2026 18:5x)

Phương pháp: probe thật (ping/TCP 11 cổng), import API trực tiếp, đếm tool từ registry live.

## 1. Pi5 thực tế (probe tươi P0)

- Ping 192.168.1.2: **REACHABLE** (latency ~2ms từ P1 QPIG-V2 demo)
- 11 cổng probe (22/80/443/1883/5000/8000/8080/8765/8766/8768/9001): **TẤT CẢ ĐÓNG**
- NodeRegistry: edge_pi5 REACHABLE (caps: kiosk/audio/camera), pc_core_quanpt REACHABLE
- **Kết luận kênh thực thi Pi5: CHƯA KHẢ DỤNG — chờ owner chạy script all_in_one trên Pi.**
  Mọi luồng →PI5 phải fail-honest, không được giả lập.

## 2. Bảng đối chiếu 8 module §III — ĐÃ CÓ / CÒN THIẾU

| Module | Đã có (kiểm chứng bằng import/test thật) | Còn thiếu |
|---|---|---|
| M01 Device Discovery | LanScanner (9 host), NodeRegistry (2 nút, probe_node), QPIG 4 tool Phase 1 live | Inventory bền vững SQLite, state transitions, USB/BT/GPIO discovery |
| M02 Adapter Framework | 7 adapter class (http/ws/mcp/a2a/ssh/mqtt/serial) + AdapterGrant sandbox; 6 PENDING khai thẳng thắn | Transport thật (SSH/MQTT tới Pi5), TLS + device auth |
| M03 QEP Engine | **KHÔNG có mã QEP** (chỉ spec reports/QEP-0001) | **Toàn bộ**: envelope, định danh, phiên, phản hồi chuẩn |
| M04 QPIG Tool Registry | ToolRegistry 25 tool × 10 thuộc tính §2 QPIG-V2, operational trung thực | Health per-tool runtime |
| M05 Action Execution | ActionExecutionEngine 11 bước, evidence tự động | Timeout/retry có giới hạn, idempotency key |
| M06 Sentinel Enforcement | AgentIdentityRegistry, ContainmentEngine, security_monitoring | Bước AUTHENTICATE chèn vào engine flow (hiện chỉ peek UNKNOWN) |
| M07 Approval Gateway | ApprovalCardService (R4, một-lần, fingerprint) + AuthorityGovernor + ApprovalTicket (validate/hết hạn/scope) | Đấu ticket vào engine; DM /approve adapter (netchat_approval_adapter có sẵn — chưa test E2E) |
| M08 Evidence & Recovery | EvidenceStore 11 trường SHA-256, RCStore.rollback, watcher.py, quan_ai_wake.service | Health-check tập trung UAG, watchdog adapter processes |

Kế thừa kiểm chứng (§II): QPIG 25 tool ✓ · SENTINEL S3 38/38 ✓ · SEC-S1 26/26 ✓ ·
CSEF 12/12 ✓ · Evidence UIE-V2 4/4 ✓ · AuthorityGovernor + ApprovalTicket import OK ✓ ·
Tool Registry ✓ · Approval Gateway ✓. **Không module nào tạo bản sao cạnh tranh.**

## 3. Quy trình §IV — ánh xạ bước hiện có

REQUEST→IDENTIFY (QPIG identify) → AUTHENTICATE (**thiếu** → M06 mới) → INSPECT (probe) →
ANALYZE (SENTINEL classify) → CLASSIFY (risk R0-R4) → CHECK PERMISSION (rbac.py có sẵn,
chưa nối) → CHECK APPROVAL (ApprovalCard/Governor ✓) → EXECUTE (engine ✓) → VERIFY
(ACTION_VERIFICATION ✓) → EVIDENCE (EvidenceStore ✓) → REPORT (report generator ✓).

## 4. Ràng buộc phần cứng §VIII

Pi 4GB: không chạy tác vụ nặng — adapter chỉ relay. systemd: hiện chỉ quan_ai_wake.service;
UAG service sẽ ở dạng Release Candidate (CSEF), KHÔNG tự deploy (§X). Không secret văn bản
rõ — auth qua hash channel có sẵn (dm_2step_hash).

## 5. Lộ trình sprint này

- P0 ✓ (báo cáo này)
- Sprint code: M01 inventory + M03 QEP engine + M05 engine timeout/retry/idempotency +
  M06 AUTHENTICATE vào pipeline + M07 đấu AuthorityGovernor + M08 health/rollback hook
- §IX: ≥20 test gồm mất kết nối, thiết bị không phản hồi, agent giả mạo, phê duyệt hết hạn
- Chặn đỏ: luồng →PI5 thật chỉ mở khi owner xác nhận SSH; hiện tại = NOT_ACCESSIBLE
