# QUAN AI BRAIN — BÁO CÁO AUDIT VÀ THIẾT KẾ KIẾN TRÚC KẾT NỐI ĐA HỆ THỐNG
# (UNIVERSAL SOFTWARE INTEGRATION & CONTROLLED AUTONOMOUS OPERATIONS ARCHITECTURE)
## Theo Master Prompt V6 Addendum — Giai đoạn 1: Audit & Proposal Thiết kế

**Chủ sở hữu:** Anh Quân — Quanpt1  
**Hệ thống:** QUAN AI BRAIN (PC Core + Raspberry Pi 5 Embodiment)  
**Trạng thái đề xuất:** `PENDING_OWNER_SIGNOFF` (Chờ Anh Quân phê duyệt trước khi sửa code)  
**Ngày lập:** 21/10/2026  
**Mục tiêu:** Mở rộng QUAN AI BRAIN thành trợ lý điều hành số có năng lực kết nối đa hệ thống phần mềm, dịch vụ API, database, web/desktop và thiết bị biên, học cấu trúc, vận hành có kiểm soát, chủ động phát hiện vấn đề và tự giải quyết trong phạm vi ủy quyền an toàn tuyệt đối.

---

## I. KẾT QUẢ AUDIT CODEBASE HIỆN TẠI (EXISTING ASSETS & REUSE MATRIX)

Tuân thủ nguyên tắc cốt lõi: **"Tái sử dụng các thành phần hiện có, không tạo hệ thống connector thứ hai nếu có thể mở rộng kiến trúc hiện tại"**.

| Thành phần hiện có trong Codebase | Module đường dẫn | Năng lực sẵn có | Phương án tái sử dụng & Mở rộng cho V6 |
| :--- | :--- | :--- | :--- |
| **`ToolRegistry`** | `src/quan_ai_brain/tools/registry.py` | Quản lý danh mục `ToolDefinition`, kiểm tra kiểu dữ liệu & schema tham số, chống duplicate tool ID | **Tái sử dụng 100%**: Mọi operation được khai báo từ connector ngoài sẽ được compile thành `ToolDefinition` chuẩn và đăng ký trực tiếp vào `ToolRegistry`. Không tạo registry thực thi thứ hai! |
| **`SafeToolSandbox`** | `src/quan_ai_brain/tools/sandbox.py` | 10 bước kiểm soát an toàn: Schema -> PathGuard -> Sensitive Files -> PolicyEngine -> STOP/FREEZE -> Consent Gate -> Dry-run -> Execute -> Quota -> Redacted Audit | **Tái sử dụng 100%**: Mọi hành động của connector đều đi qua sandbox này. Kế thừa toàn bộ chốt chặn STOP/FREEZE, kiểm duyệt file nhạy cảm và nhật ký JSONL. |
| **`ApprovalGate`** | `src/quan_ai_brain/tools/approval.py` | Quản lý vòng đời phê duyệt (`pending`, `approved`, `consumed`, `revoked`), mã hóa dấu vân tay hành động SHA-256, chống replay attack | **Tái sử dụng 100%**: Áp dụng cho các thao tác ngoài mức ủy quyền (A3) hoặc rủi ro R4. |
| **`DelegationRegistry`** | `src/quan_ai_brain/tools/delegation.py` | Quản lý `DelegationGrant`, giới hạn thời gian (TTL), hạn mức số lần gọi (call budget), trần rủi ro tối đa (Risk ceiling &le; R2), cấm tuyệt đối ủy quyền R4/R5 | **Tái sử dụng 100%**: Đây chính là nền tảng cho cấp độ **A2 — DELEGATED ACTION** trong Master Prompt V6! |
| **`OutputGuardrails`** | `src/quan_ai_brain/core/guardrails.py` | Khử rò rỉ credential, token, key; lọc thẻ script injection; che giấu đường dẫn nhạy cảm; phân tích grounding | **Tái sử dụng 100%**: Kiểm duyệt toàn bộ dữ liệu trả về từ hệ thống ngoài trước khi đưa vào bộ nhớ hoặc gửi cho người dùng. |
| **`PolicyEngine`** | `src/quan_ai_brain/governance/policy.py` | Phân cấp rủi ro R0–R5, R5 hard-blocked (`BLOCKED`), R4 yêu cầu chủ sở hữu duyệt | **Tái sử dụng 100%**: Khóa cứng mọi hành vi rủi ro cao từ hệ thống ngoài. |
| **`ExecutiveCoordinator` & `TaskPlan`** | `src/quan_ai_brain/planning/` | Phân rã mục tiêu thành DAG dependencies, phát hiện chu trình lặp (cycle detection), giải thích kế hoạch `explain()` | **Tái sử dụng 100%**: Đóng vai trò `ActionPlanner` lập kế hoạch đa hệ thống. |
| **`DurableTaskRegistry` & `PlanOrchestrator`** | `src/quan_ai_brain/orchestration/` | Bền vững hóa task trên SQLite WAL (`data/tasks.db`), chống trùng lặp `idempotency_key`, khôi phục tiến trình khi crash (`recover_in_flight_tasks`) | **Tái sử dụng 100%**: Theo dõi và lưu vết trạng thái của từng bước kết nối đa hệ thống. |
| **`ConsultationStore`** | `src/quan_ai_brain/governance/consultation_inbox.py` | Hộp thư tham vấn chủ sở hữu với các nút duyệt (`APPROVE`, `REJECT`, `DIRECT`) tại Port 8766 | **Tái sử dụng 100%**: Nơi tiếp nhận yêu cầu phê duyệt cho các hành động A3 / R4. |
| **`MemoryStore`** | `src/quan_ai_brain/memory/sqlite_store.py` | Lưu trữ bộ nhớ dài hạn với 6 loại (`SEMANTIC`, `PROCEDURAL`, `CANDIDATE`) và trạng thái xác minh (`OBSERVED`, `VERIFIED`, `INFERRED`) | **Tái sử dụng 100%**: Lưu giữ `SystemKnowledgeProfile` và `OperationalPlaybook` sau khi đã kiểm chứng. |

---

## II. KHOẢNG TRỐNG KIẾN TRÚC HIỆN TẠI (ARCHITECTURAL GAPS)

Mặc dù hạ tầng governance, sandbox và task registry rất hoàn chỉnh, hiện tại codebase còn các khoảng trống kỹ thuật sau cần được bổ sung để đáp ứng Master Prompt V6:

1. **Thiếu Lớp Mô Tả Hệ Thống Ngoài (`ConnectorManifest` & `IntegrationScope`):**
   - Hiện tại `ToolDefinition` chỉ mô tả một hàm đơn lẻ trong Python, chưa có khái niệm một "Hệ thống phần mềm / Dịch vụ bên ngoài" (như JIRA, GitHub, Database, REST API service, MCP server) với phiên bản, endpoint, loại xác thực, hạn mức tốc độ (rate limit), và danh mục các thao tác được phép.
2. **Thiếu Giao Diện Adapter Thống Nhất (`BaseConnectorAdapter`):**
   - Chưa có interface chuẩn định nghĩa các hàm: `connect()`, `disconnect()`, `health_check()`, `discover_schema()`, `execute_operation()`, và `verify_target_state()`.
3. **Thiếu Hồ Sơ Tri Thức Hệ Thống (`SystemKnowledgeProfile`) & Quy Trình Vận Hành (`OperationalPlaybook`):**
   - Chưa có cấu trúc dữ liệu chuẩn để ghi nhận sơ đồ cấu trúc của một phần mềm ngoài (endpoint, bảng dữ liệu, quy trình, quyền hạn, lỗi thường gặp) với phân loại 3 cấp độ: `OBSERVED`, `VERIFIED`, `INFERRED`.
4. **Xác Minh Kết Quả Mới Ở Mức Công Cụ (`ResultVerifier` Gap):**
   - Hiện tại `PlanOrchestrator` chỉ kiểm tra `result.get("status") == "success"` (ACK của tool), chưa có cơ chế truy vấn ngược lại hệ thống đích để xác minh xem trạng thái thực tế đã thực sự thay đổi hay chưa.
5. **Thiếu Chu Trình Tự Vận Hành Chủ Động Đa Hệ Thống (`ProactiveOperationsLoop`):**
   - Chưa có vòng lặp định chuẩn: `MONITOR → DETECT → DIAGNOSE → RESEARCH → PROPOSE → AUTHORIZE → EXECUTE → VERIFY → REPORT → LEARN` gắn liền với 4 mức tự chủ A0–A3.

---

## III. THIẾT KẾ KIẾN TRÚC TỐI THIỂU: UNIVERSAL CONNECTOR ARCHITECTURE

Để đáp ứng trọn vẹn yêu cầu mà không làm phức tạp hóa hệ thống, chúng tôi đề xuất gói module mới: **`src/quan_ai_brain/integration/`** với kiến trúc phân tầng sạch:

```
src/quan_ai_brain/integration/
├── __init__.py                  # Public exports
├── manifest.py                  # ConnectorManifest, ConnectorOperation, IntegrationScope, ConnectorType, AuthType
├── adapter.py                   # BaseConnectorAdapter (Protocol & Abstract Base Class)
├── registry.py                  # IntegrationRegistry (Cầu nối giữa Connectors và ToolRegistry)
├── profile.py                   # SystemKnowledgeProfile (Bản đồ cấu trúc hệ thống, OBSERVED/VERIFIED/INFERRED)
├── playbook.py                  # OperationalPlaybook (13 trường chuẩn theo Section V)
├── policy.py                    # IntegrationPolicy (Allowlist, rate limits, read-only discovery, secret isolation)
├── verifier.py                  # ResultVerifier (Xác minh trạng thái thực tế trên hệ thống đích)
├── health.py                    # ConnectorHealthMonitor (Đo RTT, phát hiện timeout, circuit breaker)
├── proactive.py                 # ProactiveOperationsLoop (Chu trình 10 bước, A0-A3)
└── connectors/
    ├── __init__.py
    ├── system_telemetry.py      # Connector mẫu chuẩn: Local System & OS Telemetry (Read-only, R0, Zero credentials)
    └── mock_service.py          # Connector kiểm thử: Mock REST & Database Service (Kiểm thử 20 kịch bản Section XII)
```

### 1. Hợp đồng dữ liệu `ConnectorManifest` (`manifest.py`)
Mô tả một hệ thống phần mềm được phép kết nối:
```python
class ConnectorType(str, Enum):
    REST_API = "REST_API"
    GRAPHQL = "GRAPHQL"
    MCP_SERVER = "MCP_SERVER"
    DATABASE = "DATABASE"
    CLI_SDK = "CLI_SDK"
    UI_AUTOMATION = "UI_AUTOMATION"
    EDGE_SYSTEM = "EDGE_SYSTEM"

class AuthType(str, Enum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    HMAC_SHA256 = "HMAC_SHA256"
    MUTUAL_TLS = "MUTUAL_TLS"

class AutonomyLevelScope(str, Enum):
    A0_OBSERVE = "A0_OBSERVE"
    A1_RECOMMEND = "A1_RECOMMEND"
    A2_DELEGATED = "A2_DELEGATED"
    A3_OWNER_APPROVAL = "A3_OWNER_APPROVAL"

@dataclass(frozen=True)
class ConnectorOperation:
    operation_id: str
    name: str
    description: str
    action_type: str            # "read", "analysis", "write"
    risk_level: RiskLevel       # R0 to R5
    autonomy_level: AutonomyLevelScope
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = field(default_factory=dict)
    side_effects: bool = False
    requires_approval: bool = True
    supports_dry_run: bool = True
    timeout_seconds: float = 10.0

@dataclass
class ConnectorManifest:
    system_id: str
    system_name: str
    system_type: ConnectorType
    version: str
    description: str
    auth_type: AuthType
    base_endpoint: str
    operations: list[ConnectorOperation]
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 15.0
    read_only_default: bool = True
    environment: str = "local"   # "local", "staging", "production"
    owner_signoff_required: bool = True
```

### 2. Cầu nối Adapter Thống Nhất (`adapter.py`)
Mỗi hệ thống triển khai `BaseConnectorAdapter`:
- `health_check() -> HealthStatus`
- `discover_schema() -> SystemKnowledgeProfile`
- `execute_operation(operation_id: str, params: dict[str, Any]) -> ConnectorResponse`
- `verify_target_state(operation_id: str, params: dict, response: ConnectorResponse) -> VerificationResult`

### 3. Đăng ký & Tích hợp vào `ToolRegistry` (`registry.py`)
`IntegrationRegistry` quản lý các connector được phê duyệt.
**Điểm đột phá kỹ thuật:** Khi đăng ký một `ConnectorManifest`, `IntegrationRegistry` tự động chuyển đổi từng `ConnectorOperation` thành một `ToolDefinition` và đăng ký thẳng vào `ToolRegistry` hiện tại!
- Tên công cụ dạng namespace: `{system_id}__{operation_id}`.
- Handler gọi qua adapter với cơ chế đóng băng token, timeout và kiểm duyệt đầu ra.
- Do đó, mọi hành động từ bên ngoài **tự động chịu sự kiểm soát của `SafeToolSandbox`, `ApprovalGate`, `DelegationRegistry` và `PathGuard`** mà không cần viết lại một dòng code governance nào!

### 4. Hồ sơ tri thức hệ thống (`profile.py`) & Quy trình vận hành (`playbook.py`)
- `SystemKnowledgeProfile`: ghi nhận cấu trúc hệ thống, danh sách endpoint/bảng, dependencies, chức năng đã xác minh, thao tác bị cấm, với 3 nhãn phân định:
  - `OBSERVED`: Hệ thống đã tự quan sát.
  - `VERIFIED`: Đã có bằng chứng thực nghiệm kiểm chứng.
  - `INFERRED`: Suy luận lý thuyết, chưa được xác nhận.
- `OperationalPlaybook`: Chứa 13 thuộc tính theo chuẩn Section V. Lưu vào `MemoryStore` dưới dạng `MemoryType.PROCEDURAL` và `LifecycleStatus.ACTIVE` (nếu VERIFIED) hoặc `LifecycleStatus.QUARANTINED` (nếu CANDIDATE/INFERRED).

### 5. Cơ chế Xác Minh Kết Quả Thực Tế (`ResultVerifier` trong `verifier.py`)
Không dừng lại ở việc kiểm tra HTTP 200 hay tool output thành công. `ResultVerifier` thực hiện:
1. **Kiểm tra ACK:** Tool chạy không ném ngoại lệ, trả mã thành công.
2. **Truy vấn trạng thái đích (Target State Query):** Đọc lại trạng thái thực tế từ hệ thống đích (ví dụ: sau khi ghi cấu hình, thực hiện đọc lại xem giá trị mới đã được áp dụng hay chưa).
3. **Kiểm tra bất biến (Invariant Check):** Đảm bảo hệ thống không bị suy giảm hiệu năng, không xuất hiện cảnh báo lỗi phát sinh.
4. **Tạo Evidence Record:** Lưu vết bằng chứng với timestamp, hash và chữ ký vào nhật ký kiểm toán.

### 6. Chu trình Vận hành Chủ động (`ProactiveOperationsLoop` trong `proactive.py`)
Vòng lặp 10 giai đoạn tuân thủ phân cấp tự chủ A0–A3:
- **A0 (OBSERVE):** Quét định kỳ trạng thái các connector (sử dụng `ConnectorHealthMonitor`).
- **A1 (RECOMMEND):** Phát hiện bất thường (độ trễ cao, lỗi lặp lại, dữ liệu lệch), phân tích nguyên nhân và chuẩn bị phương án khắc phục, lập kế hoạch DAG.
- **A2 (DELEGATED ACTION):** Nếu hành động nằm trong `DelegationGrant` còn hiệu lực (R0-R2, chi phí thấp, có thể rollback), tự động thực hiện và xác minh kết quả.
- **A3 (OWNER APPROVAL):** Nếu hành động có rủi ro cao hoặc vượt hạn mức, tạo vé tham vấn trong `ConsultationStore`, gửi thông báo lên Cockpit (Port 8766) và avatar Pi 5, dừng chờ Anh Quân phê duyệt.

---

## IV. LỰA CHỌN CONNECTOR MẪU BAN ĐẦU: GIÁ TRỊ CAO, RỦI RO THẤP

Theo chỉ thị: *"chọn một connector có giá trị cao, rủi ro thấp để làm mẫu. Ưu tiên một connector chỉ đọc có tài liệu rõ ràng. Hoàn thiện toàn bộ chu trình từ khám phá, hiểu cấu trúc, kiểm tra quyền, lập kế hoạch, truy vấn, xác minh, lưu tri thức đến báo cáo trước khi mở rộng"*.

Chúng tôi đề xuất **`SystemTelemetryConnector` (Trình kết nối Giám sát Trạng thái Hệ thống & Phần cứng Cục bộ)**:
1. **Lý do lựa chọn:**
   - **Rủi ro bằng 0 (R0 / Read-only):** Chỉ đọc thông số CPU, RAM, ổ đĩa, tiến trình được phép và lưu lượng mạng cục bộ. Tuyệt đối không ghi tệp, không sửa đổi cấu hình, không mở port mạng mới.
   - **Không cần Secret bên ngoài:** Không phụ thuộc vào token hay mật khẩu bên thứ ba, loại trừ hoàn toàn nguy cơ rò rỉ credential.
   - **Giá trị thực tế rất cao:** Giúp QUAN AI BRAIN tự chủ giám sát sức khỏe của chính PC Core và Raspberry Pi 5; phát hiện quá tải RAM/CPU hoặc nghẽn mạng để cảnh báo tức thời lên giao diện Điều hành 8766 và phát giọng nói trên Pi 5.
   - **Đầy đủ 10 bước chu trình:** Cho phép triển khai trọn vẹn từ Khám phá (`discover_schema`), Tạo hồ sơ (`SystemKnowledgeProfile`), Lập kế hoạch kiểm tra (`TaskPlan`), Đọc dữ liệu qua Sandbox, Xác minh thực tế (`ResultVerifier`), Cập nhật tri thức (`MemoryStore`), đến Tự chủ đề xuất tối ưu (`ProactiveOperationsLoop`).
2. **Kèm theo `MockServiceConnector` trong test suite:**
   - Để kiểm thử toàn diện 20 kịch bản bảo mật (Section XII) bao gồm: token hết hạn, sai quyền, timeout, rate limit, prompt-injection từ hệ thống ngoài, và STOP/FREEZE khẩn cấp.

---

## V. MA TRẬN 20 KỊCH BẢN KIỂM THỬ NGHIỆM THU (SECTION XII COMPLIANCE)

Bộ kiểm thử mới `tests/test_universal_integration.py` sẽ bao phủ toàn bộ 20 tình huống bắt buộc:

| STT | Kịch bản kiểm thử | Mô tả & Điều kiện đạt | Phân loại |
| :---: | :--- | :--- | :--- |
| 1 | Connector hợp lệ | Khởi tạo, xác thực manifest, kết nối và đọc dữ liệu thành công | Unit / Mock |
| 2 | Connector không được đăng ký | Thao tác trên connector chưa đăng ký bị chặn fail-closed | Unit |
| 3 | Credential hết hạn | Phát hiện xác thực thất bại, chuyển trạng thái AUTH_FAILED, không retry vô hạn | Unit / Mock |
| 4 | Sai quyền / Vượt scope | Gọi thao tác ngoài phạm vi đăng ký bị chặn từ chối ngay tại Policy | Unit |
| 5 | Endpoint thay đổi | Schema mismatch hoặc URL 404 được ghi nhận và báo cáo trung thực | Unit / Mock |
| 6 | Schema không tương thích | Dữ liệu đầu vào hoặc đầu ra sai kiểu bị từ chối bởi schema validator | Unit |
| 7 | Timeout xử lý | Vượt quá `timeout_seconds` kích hoạt ngắt kết nối an toàn | Unit / Mock |
| 8 | Rate limit | Vượt quá `rate_limit_per_minute` bị hoãn và báo lỗi có cấu trúc | Unit |
| 9 | Dữ liệu đầu ra độc hại | Phản hồi chứa mã độc/script bị `OutputGuardrails` thanh lọc | Unit |
| 10 | Prompt injection từ hệ thống ngoài | Payload cố gắng giả mạo chỉ thị ghi đè quyền của Anh Quân bị cô lập hoàn toàn | Unit |
| 11 | ACK nhưng không đổi trạng thái | Hệ thống trả OK nhưng `ResultVerifier` kiểm tra thấy trạng thái chưa đổi -> Báo FAILED | Integration |
| 12 | Hành động thành công nhưng verify thất bại | Bước xác minh không đạt tiêu chuẩn nghiệm thu -> Đánh dấu FAILED và cách ly | Integration |
| 13 | Workflow đa hệ thống gián đoạn | Lỗi ở hệ thống trung gian kích hoạt dừng an toàn các bước phụ thuộc tiếp theo | Integration |
| 14 | Mất kết nối Core–Pi | Pi 5 tự chuyển trạng thái OFFLINE an toàn, Core ghi nhận cảnh báo | Mock / Edge |
| 15 | STOP/FREEZE khẩn cấp | Kích hoạt STOP/FREEZE lập tức phong tỏa toàn bộ connector đang chạy | Integration |
| 16 | Approval hết hạn hoặc bị thu hồi | Phiếu duyệt quá hạn hoặc bị thu hồi không thể tái sử dụng | Unit |
| 17 | Tri thức vận hành mâu thuẫn | Hai nguồn thông tin trái ngược được đánh dấu CONFLICT, không tự chọn 1 làm chân lý | Unit |
| 18 | Tự động retry vượt giới hạn | Sau `max_retries` thất bại, dừng retry và chuyển sang xin ý kiến con người | Unit |
| 19 | Tác vụ bị chạy trùng | Cùng một `idempotency_key` bị từ chối thực thi lặp lại | Unit |
| 20 | Sandbox cách ly hoàn toàn | Connector chạy trong môi trường giả lập, không tác động môi trường production | Integration |

---

## VI. DANH SÁCH TỆP DỰ KIẾN TẠO MỚI & CHỈNH SỬA

### 1. Tệp tạo mới:
- `src/quan_ai_brain/integration/__init__.py`: Package export cho Universal Connector Architecture.
- `src/quan_ai_brain/integration/manifest.py`: Khai báo các mô hình dữ liệu `ConnectorManifest`, `ConnectorOperation`, `ConnectorType`, `AuthType`, `AutonomyLevelScope`.
- `src/quan_ai_brain/integration/adapter.py`: Giao diện cơ sở `BaseConnectorAdapter` và các cấu trúc phản hồi `ConnectorResponse`, `VerificationResult`.
- `src/quan_ai_brain/integration/registry.py`: `IntegrationRegistry` quản lý danh mục connector và liên kết trực tiếp vào `ToolRegistry`.
- `src/quan_ai_brain/integration/profile.py`: `SystemKnowledgeProfile` và các trạng thái `OBSERVED`, `VERIFIED`, `INFERRED`.
- `src/quan_ai_brain/integration/playbook.py`: `OperationalPlaybook` với 13 trường tiêu chuẩn.
- `src/quan_ai_brain/integration/policy.py`: `IntegrationPolicy` kiểm soát allowlist, hạn mức tốc độ, và cách ly credential.
- `src/quan_ai_brain/integration/verifier.py`: `ResultVerifier` xác minh kết quả đa tầng trên hệ thống đích.
- `src/quan_ai_brain/integration/health.py`: `ConnectorHealthMonitor` theo dõi độ trễ RTT, tính khả dụng và circuit breaker.
- `src/quan_ai_brain/integration/proactive.py`: `ProactiveOperationsLoop` điều phối chu trình 10 bước và 4 cấp độ tự chủ A0–A3.
- `src/quan_ai_brain/integration/connectors/__init__.py`: Export các connector cụ thể.
- `src/quan_ai_brain/integration/connectors/system_telemetry.py`: Connector mẫu đọc trạng thái OS & Telemetry (R0, read-only).
- `src/quan_ai_brain/integration/connectors/mock_service.py`: Connector kiểm thử phục vụ 20 kịch bản nghiệm thu.
- `tests/test_universal_integration.py`: Bộ 20 bài kiểm thử tự động toàn diện.

### 2. Tệp hiện có dự kiến tích hợp bổ sung (Backward Compatible):
- `src/quan_ai_brain/cognition/capability_registry.py`: Bổ sung năng lực `universal_software_integration` vào danh mục năng lực để LLM nhận thức đúng ranh giới thực tế.
- `src/quan_ai_brain/cli.py`: Bổ sung subcommands CLI: `integration-list`, `integration-health`, `integration-profile` để kiểm tra trực tiếp từ dòng lệnh.

---

## VII. CAM KẾT AN TOÀN VÀ RANH GIỚI BẢO MẬT (SAFETY CONSTRAINTS)

1. **Tuyệt đối không sửa code trước khi có phê duyệt:** Toàn bộ bản thiết kế này được trình để Anh Quân đánh giá và phê duyệt.
2. **Bảo tồn các hệ sinh thái lân cận:** Giữ nguyên vẹn `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `DC-COMMAND`, BOT projects. Không sửa đổi hay can thiệp.
3. **Bảo mật bí mật (Secret Isolation):** Không lưu mật khẩu, API key vào prompt, log hoặc bộ nhớ dài hạn. Mọi dữ liệu trả về đều đi qua `OutputGuardrails`.
4. **R5 luôn bị khóa cứng:** Bất kỳ thao tác nào bị xếp vào R5 hoặc cố tình vượt quyền đều bị hủy bỏ lập tức.
5. **R4 đòi hỏi phê duyệt 2 kênh:** Chỉ có chữ ký số của Anh Quân mới mở được hành động R4.
6. **Không kích hoạt production executor:** Toàn bộ giai đoạn này duy trì chạy trong môi trường sandbox nội bộ được kiểm soát.

---

**KÍNH TRÌNH CHỦ SỞ HỮU ANH QUÂN (Quanpt1):**
Bản thiết kế kiến trúc kết nối đa hệ thống Universal Connector Architecture đã hoàn thành rà soát và thiết kế chi tiết. Kính mời Anh xem xét để phê chuẩn bước sang Giai đoạn 2 (Triển khai Foundation & Connector mẫu).
