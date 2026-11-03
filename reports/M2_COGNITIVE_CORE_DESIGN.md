# M2 — THIẾT KẾ LÕI NHẬN THỨC THỐNG NHẤT (Cognitive Event Bus + Vòng Nhận Thức Đích)

**Dự án:** QUAN AI BRAIN — Workspace: `D:\AI\AI Quanpt1 2026\BRAIN`
**Ngày lập:** 01/11/2026 · **Bản chất tài liệu:** THIẾT KẾ ONLY — **chưa cài đặt**, chưa có line code nào được thêm/sửa.
**Điều kiện ràng buộc:** AGENTS.md (R4 cần phê duyệt owner đã xác minh; R5 hard-block; Learning is not deployment; không thêm executor thật khi chưa được duyệt).

---

## 1. Kiểm tra trước: hệ ĐÃ có cơ chế bus tương đương chưa?

Quy tắc đặt ra: **không tạo bus thứ 2 nếu hệ đã có cơ chế tương đương.** Kết quả rà soát code thật:

| Cơ chế hiện có | Bằng chứng | Đủ làm Cognitive Event Bus? | Kết luận |
|---|---|---|---|
| `AuditLogger` → `logs/audit.jsonl` | core/audit.py:12-29 — `record(event_type, details)` ghi JSONL append-only, redact qua `redact_value` | Ghi tốt, nhưng **fire-and-forget**: không subscriber, không truy vấn, không correlation, không retry, không trạng thái xử lý | ❌ Chỉ dùng làm **audit sink**, không phải bus |
| `InMemoryMessageBroker` (topics, pub/sub, consumer group, ack/nack, retry→DLQ) | gateway/message_queue.py:128; `publish` :167; `subscribe` :180; `nack`+DLQ :238-303 | Ngữ nghĩa bus tốt nhất hiện có (at-least-once + DLQ), **NHƯNG tự khai trong docstring**: "in-memory broker simulation… no persistence… All state… dies with the process" (message_queue.py:3-13); grep toàn src: **0 caller runtime**, chỉ `tests/test_v28_enterprise_modules.py` dùng | ⚠️ Có thể **tận dụng ngữ nghĩa ack/nack/retry/DLQ** làm tham chiếu hành vi, nhưng bản thân nó không bền vững → không đủ làm bus chính |
| `governance_events` (SQLite, event_id PK, event_type, timestamp, entity, details_json, risk_level, outcome) | state_store.py:231-241 | Đã là **bảng event bền vững có schema gần đúng ý tưởng** — nhưng phạm vi chỉ governance, chỉ ghi trongGovernanceStateStore | ✅ **Mẫu tham chiếu schema tốt nhất** — bus thiết kế dưới đây tái dùng pattern này, mở rộng correlation/idempotency |
| `info_gap_events` (SQLite) | information_gap_analyzer.py:316 | Phạm vi hẹp riêng gap-analyzer | ❌ Giữ nguyên, không hợp nhất |
| `emotion_events` (SQLite) | emotional_memory.py:82 | Phạm vi riêng emotional memory | ❌ Giữ nguyên, không hợp nhất |
| Bảng `durable_tasks` + `get_by_idempotency_key` | task_registry.py:56, :190 | Idempotency đã có ở **tầng task**, chưa có ở **tầng event** | ➕ Bổ sung idempotency ở tầng event |

**Phán quyết:** Hệ **CHƯA có** một bus thống nhất; nhưng **đã có 3 mảnh ghép** (audit JSONL, broker in-memory có retry/DLQ, bảng governance_events bền vững). Vì vậy thiết kế dưới đây là **bus thứ 3 thế hệ mới thay thế vai trò điều phối** — không xóaAuditLogger, không xóa InMemoryMessageBroker (chuyển thành tùy chọn in-process), **tái sử dụng pattern schema của governance_events** để tránh tạo chuẩn dữ liệu thứ hai. Bus mới **không trùng chức năng** AuditLogger (bus = điều phối có trạng thái; audit = ghi nhật ký bất biến).

> **Kênh chống lệch chuẩn dữ liệu:** bus sẽ nằm trong `data/brain.db` hiện hữu (bảng `events` mới) thay vì tạo DB mới, để cùng transaction domain với memory.

---

## 2. Thiết kế Cognitive Event Bus (CHỈ THIẾT KẾ — chưa cài)

### 2.1. Schema dataclass (Python stdlib, không dependency mới)

```python
# THIẾT KẾ — KHÔNG phải code đã cài. Đặt tại (đề xuất) src/quan_ai_brain/core/event_bus.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

class EventStatus(str, Enum):
    PENDING = "pending"          # vừa ghi, chưa handler nào nhận
    PROCESSING = "processing"    # handler đang chạy (lease giữ chỗ)
    DONE = "done"                # handler ack
    FAILED = "failed"            # hết retry, vào DLQ logic
    SKIPPED = "skipped"          # handler chủ động bỏ qua

class EventPermissionScope(str, Enum):
    R0_READONLY = "R0"   # phát/nhận không đổi trạng thái hệ
    R2_WORKSPACE = "R2"  # event dẫn tới ghi trong workspace
    R4_OWNER = "R4"      # event cần phê duyệt owner — bus KHÔNG tự thực hiện,
                         # chỉ chuyển tiếp sang ConsultationStore/ApprovalCard

@dataclass
class CognitiveEvent:
    # --- Định danh ---
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    event_type: str = ""                    # ví dụ "cognitive_loop.task_registered"
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}")
    causation_id: str | None = None         # event_id của event cha (truy dây chuyền)
    source: str = ""                        # "cognitive_loop" | "self_care_engine" | ...
    # --- Thời gian ---
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # --- Dữ liệu ---
    payload_json: str = ""                  # JSON đã qua redact_value trước khi ghi
    permission: EventPermissionScope = EventPermissionScope.R0_READONLY
    # --- Trạng thái xử lý ---
    status: EventStatus = EventStatus.PENDING
    attempt: int = 0
    max_retries: int = 3
    last_error: str | None = None
    # --- Idempotency ---
    idempotency_key: str | None = None      # UNIQUE; handler dùng để chặn xử lý 2 lần
    # --- Audit soi ngược ---
    audit_ref: str | None = None            # dòng logs/audit.jsonl tương ứng (nếu có)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

Nguyên tắc schema:

1. **Event ID** — `evt_` + uuid4 16 ký tự, PK (:đề xuất).
2. **Correlation ID** — sinh tại **điểm vào đầu tiên** của một yêu cầu (chat/NetChat/tick); mọi event downstream cùng `correlation_id`, khác `causation_id` → dựng được toàn dây chuyền PERCEIVE→LEARN từ một correlation.
3. **Source** — tên module phát, trùng tên trong ma trận M2 (báo cáo kèm theo).
4. **Timestamp** — ISO-8601 UTC (đồng bộ với `created_at_utc` đang dùng khắp hệ, ví dụ task_registry.py:56).
5. **Payload** — JSON **đã redact** bằng `redact_value` (core/redaction.py, đang được AuditLogger dùng tại audit.py:24-25) — không bao giờ chứa secret (R5 của AGENTS.md).
6. **Permission context** — scope R0/R2/R4 nhúng trong event; scope R4 **không bao giờ** tự thực thi: bus chỉ đẩy event sang `ConsultationStore.create_ticket` (consultation_inbox.py:224) để owner phê duyệt, khớp `PolicyEngine` (policy.py:49-67).
7. **Processing status** — 5 trạng thái enum; `PROCESSING` kèm lease (xem 2.2) chống 2 handler đồng thời.
8. **Idempotency** — `idempotency_key` UNIQUE; Caller chọn key ổn định (ví dụ `f"{source}:{task_id}:{step}"`) — tái dùng kinh nghiệm `idem_cogloop_` đã có ở cognitive_loop.py:235, :257 và kinh nghiệm chống 108k dòng trùng của `skip_duplicates` (knowledge_ingestion.py:148-152).
9. **Retry** — `attempt/max_retries/last_error`; hết số lần → `FAILED` (tương đương DLQ của InMemoryMessageBroker, message_queue.py:287-303, nhưng **persist trên sqlite**).
10. **Audit** — `audit_ref` trỏ dòng audit.jsonl; bus GHI sự kiện điều phối, AuditLogger GHI sự kiện an toàn — hai lớp, không thay thế nhau.

### 2.2. Bảng SQLite `events` (trong data/brain.db hiện hữu — chỉ THIẾT KẾ)

```sql
-- THIẾT KẾ — chưa tạo. Thêm vào _create_schema của MemoryStore (sqlite_store.py:46)
CREATE TABLE IF NOT EXISTS events (
    event_id         TEXT PRIMARY KEY,
    event_type       TEXT NOT NULL,
    correlation_id   TEXT NOT NULL,
    causation_id     TEXT,
    source           TEXT NOT NULL,
    created_at_utc   TEXT NOT NULL,
    payload_json     TEXT NOT NULL,            -- đã redact
    permission       TEXT NOT NULL DEFAULT 'R0',
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK(status IN ('pending','processing','done','failed','skipped')),
    attempt          INTEGER NOT NULL DEFAULT 0,
    max_retries      INTEGER NOT NULL DEFAULT 3,
    last_error       TEXT,
    idempotency_key  TEXT UNIQUE,
    audit_ref        TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_corr   ON events(correlation_id);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status, created_at_utc);
CREATE INDEX IF NOT EXISTS idx_events_type   ON events(event_type, created_at_utc);
```

Đặc tính vận hành (tham chiếu pattern có sẵn):

- **Bền vững** như `governance_events` (state_store.py:231-241) — sống qua restart, khắc phục InMemoryMessageBroker.
- **Lease an toàn đa tiến trình**: chuyển `pending→processing` bằng một `UPDATE ... WHERE event_id=? AND status='pending'` và kiểm tra `rowcount==1` — pattern khóa an toàn đã dùng trong `GovernanceStateStore` (RLock + WAL + integrity check, state_store.py:83-123).
- **Retry**: khi handler ném exception → `attempt+1`, `last_error`; `attempt > max_retries` → `failed` (ngữ nghĩa nack→retry→DLQ của message_queue.py:238-247, chuyển sang sqlite).
- **Khôi phục sau restart**: sự kiện kẹt `processing` quá hạn lease → trả về `pending` (tham chiếu `recover_in_flight_tasks`, task_registry.py:267).
- **Ghi-đọc qua MemoryStore hiện hữu** — không tạo connection pool mới, không DB mới.

### 2.3. API đề xuất của bus (chỉ chữ ký, chưa cài)

```python
# THIẾT KẾ — class CognitiveEventBus (đề xuất đặt src/quan_ai_brain/core/event_bus.py)
class CognitiveEventBus:
    def __init__(self, store: "MemoryStore") -> None: ...
    def publish(self, event_type: str, source: str, payload: dict,
                *, correlation_id: str | None = None, causation_id: str | None = None,
                permission: EventPermissionScope = EventPermissionScope.R0_READONLY,
                idempotency_key: str | None = None) -> CognitiveEvent: ...
    def subscribe(self, event_type: str, handler: Callable[[CognitiveEvent], None],
                  *, consumer_name: str) -> None: ...
    def dispatch(self, max_events: int = 50) -> int:   # chạy trong thread/cron tick
        ...
    def replay_failed(self, limit: int = 20) -> int:   # tương đương replay_dlq
        ...
```

Hợp đồng an toàn: `publish` không bao giờ ném làm gãy luồng chính (fail-open cho publisher, fail-closed cho handler — handler lỗi chỉ ảnh hưởng trạng thái event); mọi payload qua `redact_value`; scope R4 chỉ tạo consultation ticket, **không thực hiện hành động** (AGENTS.md: R4 cần approval verifier đã xác minh — nếu chưa cấu hình thì không hiện thực hóa phê duyệt).

---

## 3. Vòng nhận thức thống nhất đích — ánh xạ engine HIỆN CÓ

Nguyên tắc: **không tạo engine trùng, không đổi tên module đang tốt.** Mỗi bước chỉ gán một "chủ nhà" đã tồn tại; bước TRỐNG mới đề xuất bổ sung nhỏ.

| Bước | Trạng thái hiện nay | Chủ nhà HIỆN CÓ (path:line) | Ghi chú thiết kế |
|---|---|---|---|
| **1. PERCEIVE** — tiếp nhận tín hiệu | Có 2 cửa vào rời rạc: chat web (server.py:1660+) và health probe ORPHAN (self_care_engine.py:123-247) | `web/server.py` (chat) + `SelfCareEngine` (probe) | Không tạo module mới. SelfCareEngine được "cắm vào vòng": chạy định kỳ, phát event `self_care.health_alert` vào bus thay vì chỉ logger |
| **2. UNDERSTAND** — hiểu yêu cầu | Gap-check đã chạy trong submit_task (cognitive_loop.py:161-226) | `InformationGapAnalyzer` qua `CognitiveLoop.submit_task` | Kích hoạt lại CognitiveLoop làm cổng vào chuẩn; CriticalThinker bổ sung điểm chấm quality trong REFLECT (bước 8), không đưa vào đây để tránh chồng |
| **3. REMEMBER** — truy xuất trí nhớ | MemoryStore đầy đủ API (sqlite_store.py:274) | `MemoryStore.search_memories` | Bus event `memory.recall_requested` (R0); kết quả gắn `correlation_id` vào payload context — KHÔNG sửa chữ ký API MemoryStore |
| **4. REASON** — suy luận | PlanOrchestrator + planning.models; LLM provider rời | `PlanOrchestrator` (plan_orchestrator.py:63) | Giữ nguyên; CognitiveLoop chỉ điều phối. CriticalThinker đứng cạnh như bộ kiểm chứng lập luận khi có tranh chấp evidence |
| **5. PLAN** — lập kế hoạch | submit_plan + placeholder plan an toàn (cognitive_loop.py:230-258) | `PlanOrchestrator.submit_plan` + `DurableTaskRegistry.register_task` (task_registry.py:110) | Đã tốt — không đụng. Event `plan.registered` phát ra sau khi đăng ký |
| **6. GOVERN** — kiểm tra quyền | PolicyEngine R0–R5 + ticket + NetChat approval (policy.py:49-67; plan_orchestrator.py:249, :270-277; netchat_approval_adapter.py:53) | `PolicyEngine` + `ConsultationStore` + `GovernanceStateStore` | Đã mạnh. Bus chỉ **đọc** kết quả (event `governance.approval_required`) — quyền quyết vẫn ở governance, không chuyển sang bus |
| **7. EXECUTE** — thực hiện | Chỉ sandbox dry_run=True (cognitive_loop.py:275-280); R5 block (plan_orchestrator.py:249) | `PlanOrchestrator.execute_lifecycle` | **Giữ nguyên sandbox-only** cho đến khi có kế hoạch kiểm thử + phê duyệt owner. Bus không tự execute bao giờ |
| **8. VERIFY** — xác minh | ReflectionLoop evidence-based (reflection.py:47-132) | `ReflectionLoop.reflect_task` | **Bổ sung nhỏ (đề xuất)**: tại reflection.py:245-259 nơi chấm lessons, thêm tùy chọn gọi `CriticalThinker.evaluate_evidence` để chấm evidence từng lesson — nối CriticalThinker (hiện ORPHAN) vào vòng, không đổi chữ ký hàm |
| **9. LEARN** — ghi nhận học tập | Hai đường song song: persist_lessons→episodes/quarantine (reflection.py:134-166) và CLE Type A–E→candidate_knowledge (continuous_learning_engine.py:144-464) | `ReflectionLoop.persist_lessons` + `ContinuousLearningEngine` | **Hợp nhất bằng event, không gộp code**: persist_lessons phát event `learning.lessons_extracted`; CLE subscribe event đó để vào pipeline Type B — hai đường vẫn giữ module riêng, chỉ nối bằng bus. Đề xuất Type E vẫn bắt buộc đi ApprovalCard/consultation |
| **10. COMMUNICATE** — phản hồi owner | Chat reply (server.py), NetChat approval adapter (:53), consultation inbox | `web/server.py` + `NetChatApprovalAdapter` + ConsultationStore | **Bổ sung nhỏ (đề xuất)**: subscribe bus để đẩy `self_care.health_alert` và `governance.approval_required` ra NetChat — lấp khoảng trống #3 của ma trận M2 |

**Bước TRỐNG cần bổ sung:** không có bước nào thiếu hoàn toàn chủ nhà; các **cầu nối** thiếu là: (a) SelfCareEngine→bus (bước 1), (b) CriticalThinker→reflection (bước 8), (c) ReflectionLoop→CLE (bước 9), (d) bus→NetChat (bước 10). Đây đều là **wiring**, không phải engine mới.

---

## 4. Kế hoạch migration 4 bước nhỏ (mỗi bước có test, nghiệm thu, hoàn tác)

> **Tuyên bố an toàn:** KHÔNG tự triển khai khi chưa có kế hoạch kiểm thử phù hợp và phê duyệt của owner **Quanpt1**. Mỗi bước là PR nhỏ, độc lập, có điều kiện nghiệm thu rõ ràng và đường hoàn tác.

### Bước 1 — Tạo bảng `events` + `CognitiveEventBus` ghi/đọc cơ bản

- **Phạm vi:** thêm `_create_events_table` vào `MemoryStore._create_schema` (sqlite_store.py:46); file mới `src/quan_ai_brain/core/event_bus.py` chứa dataclass + `publish/subscribe/dispatch` cơ bản; **không** sửa engine nào.
- **Test mới:** `tests/test_event_bus.py` — publish→dispatch→handler nhận; idempotency (cùng key, 2 lần publish → handler chạy 1 lần); redact payload; crash handler → retry → failed; restart giả lập (mở lại store) → event pending còn nguyên.
- **Điều kiện nghiệm thu:** toàn bộ test mới + `python tools/validate_and_report.py` xanh; không thay đổi hành vi module cũ (grep diff không đụng file khác).
- **Khả năng hoàn tác:** xóa file event_bus.py + bỏ khối CREATE TABLE — không có state nào phụ thuộc; bảng cũ trong brain.db chỉ là bảng trống, có thể DROP.

### Bước 2 — Nối CognitiveLoop: phát event thay vì chỉ ghi audit rời rạc

- **Phạm vi:** CognitiveLoop giữ nguyên chữ ký mọi phương thức; chỉ **thêm** `publish()` song song với các điểm `self._audit.record(...)` hiện có (cognitive_loop.py:158, :205, :228, :260, :291, :338, :350, :362, :380, :406). Bus inject qua constructor tùy chọn (`bus: CognitiveEventBus | None = None`) — None thì hành vi y như cũ.
- **Test mới:** mở rộng `tests/test_cognitive_loop.py` — submit_task có bus → nhận đúng 3 event (received/registered/gap_blocked); không bus → không đổi hành vi.
- **Nghiệm thu:** test cũ + mới xanh; `_audit.record` **không bị xóa** (audit vẫn song song tồn tại); runtime ORPHAN được khắc phục một phần (bus là subscriber đầu tiên).
- **Hoàn tác:** `bus=None` mặc định → hành vi về như cũ; gỡ inject không ảnh hưởng storage.

### Bước 3 — Nối LEARN: ReflectionLoop → ContinuousLearningEngine qua event

- **Phạm vi:** `persist_lessons` (reflection.py:134-166) sau khi lưu thành công thì publish `learning.lessons_extracted` (payload: task_id, số lessons verified/hypothesis); CLE thêm method `handle_lessons_event(event)` đăng ký subscribe — bên trong gọi `learn_type_b_experience(...)` với dữ liệu từ payload. **Không hợp nhất code hai module.**
- **Test mới:** `tests/test_learning_bridge.py` — persist_lessons với bus → CLE nhận Type B report với đúng task goal/kết quả; hypothesis KHÔNG bao giờ vào semantic (quét bảng `semantic_memory` trống tăng 0).
- **Nghiệm thu:** test hai module cũ (test_continuous_learning.py, test_cognitive_loop.py) vẫn xanh; số dòng candidate_knowledge tăng đúng bằng số hypothesis cách ly; audit có 2 event mới.
- **Hoàn tác:** gỡ subscribe; hai đường học quay về độc lập như trước — không data loss vì cả hai đường vẫn ghi DB riêng vốn có.

### Bước 4 — Nối ALERT→OWNER: SelfCareEngine + NetChat

- **Phạm vi:** SelfCareEngine phát `self_care.health_alert` khi `generate_alerts` thấy DOWN/WARNING (self_care_engine.py:249-270); một subscriber mới đẩy alert qua `NetChatApprovalAdapter.send_to_channel` (netchat_approval_adapter.py:68) — chỉ gửi text, **không** thực hiện auto-recovery thật (vẫn simulated tại :279-291, đúng giới hạn AGENTS.md). Persist alerts/incidents vào bảng sqlite mới (hoặc tái dùng events) để hết volatile (:106-108).
- **Test mới:** `tests/test_selfcare_alerting.py` — mock socket DOWN → event sinh ra; handler NetChat được gọi với nội dung đúng; test không phụ thuộc mạng thật.
- **Nghiệm thu:** test_self_care.py cũ xanh; owner nhận được tin nhắn NetChat khi Ollama/web giả lập chết (thử tay 1 lần có owner xác nhận); không request mạng ngoài workspace.
- **Hoàn tác:** gỡ subscriber NetChat → hệ về trạng thái hiện tại (alert chỉ log); bảng persist giữ nguyên không hại.

### Điều kiện chung trước khi bắt Bước 1

1. Owner **Quanpt1** phê duyệt kế hoạch này (báo cáo M2 upload lên phiên ChatGPT làm việc chính).
2. Chọn cửa sổ dừng server an toàn (KHÔNG restart trong phiên làm việc này; migration chỉ chạy schema-additive nên không bắt buộc downtime).
3. Snapshot `data/*.db` trước mỗi bước (thư mục `backups/` đã có sẵn quy trình).
4. Mỗi bước phải chạy `python tools/validate_and_report.py` + cập nhật `reports/HANDOFF_LATEST.md` theo AGENTS.md work procedure.

---

## 5. Tóm tắt quyết định thiết kế

| Câu hỏi | Quyết định |
|---|---|
| Tạo bus thứ 2 không? | Tạo **một** bus mới (`events` trong brain.db) vì hệ CHƯA có bus bền vững; nhưng **tái dùng** pattern schema `governance_events`, ngữ nghĩa retry/DLQ của `InMemoryMessageBroker`, và **giữ nguyên** AuditLogger làm audit sink song song |
| Bus tự thực hiện hành động R4? | KHÔNG. Bus chỉ tạo/chuyển tiếp consultation ticket; executor thật vẫn bị chặn theo AGENTS.md |
| Gộp 2 đường học? | KHÔNG gộp code; nối bằng event `learning.lessons_extracted` |
| Sửa engine nào? | Chỉ thêm wire-in tùy chọn (bus=None mặc định); không đổi chữ ký public; không đổi tên module |
| Khi nào cài? | Sau khi owner Quanpt1 phê duyệt + kế hoạch kiểm thử 4 bước trên được xác nhận |

---

*Người lập: TONY (M2 research subagent)*
*Ngày: 01/11/2026*
