# QEP-0001 — EMBODIMENT REGISTRY & DISTRIBUTED INTELLIGENCE (M6)

**Dự án:** QUAN AI BRAIN · **Workspace:** `D:\AI\AI Quanpt1 2026\BRAIN`
**Ngày lập:** 01/11/2026 · **Trạng thái: DRAFT — CHỜ PHÊ DUYỆT Quanpt1** (roadmap M6: "spec QEP trước khi cài")
**Bản chất:** THIẾT KẾ ONLY — chưa có dòng code nào thêm/sửa. Toàn bộ path:line dưới đây là đọc code thật ngày 01/11/2026.
**Nguyên tắc:** không tạo engine trùng; schema-additive; hoàn tác được từng bước; R4/R5 tuân thủ tuyệt đối (AGENTS.md).

---

## 1. Bằng chứng audit hiện trạng (đọc code thật, không suy đoán)

### 1.1. Đã có sẵn — nền M6 tốt hơn kỳ vọng roadmap

| Thành phần | Bằng chứng | Ghi chú |
|---|---|---|
| Heartbeat HMAC có anti-replay | `edge_client/auth.py:16-104` — sign mọi request, nonce TTL, chống replay, drift 10s | Chờ verify ở B1 (P0) |
| 9-state lifecycle kết nối | `src/quan_ai_brain/web/edge_monitor.py:17-28` (DISCONNECTED→READY→…) | Chuẩn hoá identity được ngay |
| 8 cảnh báo A→H | `edge_monitor.py:31-41` (A mất kết nối, B đứt đột ngột, C kênh xấu, D sync fail, E hồi phục, F bảo mật, G mic, H camera) | Đủ ngữ nghĩa embodiment health |
| Watchdog deadline 4s + RTT degraded 350ms | `edge_monitor.py:80-88` | Tham sốheartbeat 1s/poll (`config.py:26-27`) |
| Kênh lệnh PC→Pi pull-based | `server.py:3293, :3676` — `pending_commands` pop trong heartbeat response | Đã là "capability negotiation" nguyên thủy |
| Agent chủ động 5 năng lực trên Pi | `edge_client/edge_agent.py:1-16` (tự phản ứng/quản lý/thu thập/phối hợp/cải tiến có kiểm soát, fail-closed) | V41 đã duyệt 30/10 |
| Điều phối vai trò 10 roles + persona PC/Pi | `cognition/role_orchestrator.py:118-239` wired `server.py:179`; `cognition/executive_persona.py:109-111` | "MULTIPLE EMBODIMENTS" đã có tư duy |
| Mô hình cơ thể 7 vùng giải phẫu | `core/autonomic.py:26-34` (BRAIN/EARS/VOICE/EYES/SKIN/CIRCULATION/BODY) | Map trực tiếp vào capability registry |
| Pairing PIN + device registry | `server.py:162-163` (PIN 888666; `_GLOBAL_PAIRED_EDGE_DEVICES`) | Xem 1.2.5 |

### 1.2. Lỗ hổng / nợ kỹ thuật phát hiện khi audit (số thứ tự = mức ưu tiên)

| # | Phát hiện | Bằng chứng | Hậu quả |
|---|---|---|---|
| **P0-1** | **Server KHÔNG bao giờ verify HMAC** dù Pi ký mọi request. Grep toàn `src/`: 0 lời gọi `verify_request`. Handler chỉ đọc header device rồi tin ngay | `server.py:3251-3271` (status), `:3650-3689` (heartbeat) | Bất kỳ host nào trong tailnet có thể giả heartbeat nhận `pending_commands` (kể cả audio/speak). Vi phạm đúng tuyên bố "authenticated heartbeat" trong docstring |
| **P0-2** | Chiều PC→Pi (`_send_edge_request`) gửi **không HMAC** | `server.py:283-306` — không header `X-Quan-*` | Pi cũng không verify chiều ngược lại |
| **P0-3** | Secret HMAC là **placeholder nằm trong source** | `edge_client/config.py:25` — `EDGE_EPHEMERAL_DEV_SECRET_DO_NOT_USE_IN_PROD` | R5-adjacent: secret phải vào env/registry, không vào repo |
| N-1 | `edge_ip` mặc định **IP LAN cũ 192.168.1.21** (hiện Pi ở 100.100.83.59 qua Tailscale); chỉ tự sửa sau heartbeat đầu tiên | `server.py:170`, `:285` | Server mới restart + chưa nhận heartbeat → lệnh gửi đi IP chết |
| N-2 | Pairing registry in-memory, mất khi restart | `server.py:163, :3766` | Mỗi restart PC, trạng thái paired reset |
| N-3 | Identity trùng lặp 2 nguồn: config daemon vs EdgeMonitor | `config.py:19-20` vs `edge_monitor.py:84-97` | Nghiệp vụ "đọc từ registry duy nhất" chưa có |
| N-4 | Telemetry kiosk (`screen 1280x720`) sai thực tế DSI 800x480 (V40 đã fix flags kiosk nhưng config chưa) | `config.py:32-33` vs `client_daemon.py:317-318` | Dữ liệu identity lệch |

---

## 2. QEP-0001 Spec — chuẩn hoá 3 lớp: IDENTITY · CAPABILITY · COMMAND

### 2.1. Embodiment Identity Contract (lớp 1)

Một "embodiment" = một hình thể số có thể kết nối não PC. Định nghĩa duy nhất, dùng cho Pi5 hiện tại và mọi hình thể sau này (điện thoại, PC khác, robot bàn).

```python
# THIẾT KẾ — đặt tại (đề xuất) src/quan_ai_brain/distributed/embodiment.py
# stdlib-only, schema-additive vào data/brain.db (bảng mới `embodiments`)

@dataclass
class EmbodimentIdentity:
    device_id: str                  # PK, ví dụ "EDGE-PI5-DESK-01"
    label: str                      # "Bàn Làm Việc Quanpt1"
    protocol_version: str           # "qep-1" — bump khi contract đổi
    transport: str                  # "http-heartbeat-pull" (hiện tại)
    regions: list[str]              # subset AnatomicalRegion: ["EARS","VOICE","EYES","SKIN","BODY"]
    capabilities: list[dict]        # xem 2.2 — [{cap_id, params_schema_ref, policy_class}]
    last_seen_utc: str | None       # do server cập nhật khi heartbeat
    lifecycle_state: str            # EdgeConnectionState value (9-state tái dùng)
    paired_at_utc: str | None
    revoked: bool = False           # owner thu hồi hình thể (R2, có audit)
```

Bảng `embodiments` trong **brain.db hiện hữu** (không DB mới — cùng triết lý events của M2):
```sql
CREATE TABLE IF NOT EXISTS embodiments (
    device_id        TEXT PRIMARY KEY,
    label            TEXT NOT NULL,
    protocol_version TEXT NOT DEFAULT 'qep-1',
    transport        TEXT NOT DEFAULT 'http-heartbeat-pull',
    regions_json     TEXT NOT DEFAULT '[]',
    capabilities_json TEXT NOT DEFAULT '[]',
    lifecycle_state  TEXT NOT DEFAULT 'DISCONNECTED',
    paired_at_utc    TEXT,
    last_seen_utc    TEXT,
    revoked          INTEGER NOT DEFAULT 0
);
```
Server-side sync: `_GLOBAL_EDGE_MONITOR.record_heartbeat` (đã chạy mỗi heartbeat, `server.py:3669`) → **thêm 1 hook ghi DB**. Restart không mất (khắc phục N-2). `edge_ip` sống trong `last_telemetry` của registry — khắc phục N-1 (IP gắn với device, không phải biến toàn cục mặc định cứng).

### 2.2. Capability Negotiation Contract (lớp 2)

Mỗi capability = 1 hành vi hình thể có thể nhận lệnh, khai báo có phiên bản, có chính sách quyền rõ ràng:

| cap_id (hiện có trên Pi5) | Bằng chứng | policy_class |
|---|---|---|
| `kiosk.control` (wake/close/face_only/sleep) | `client_daemon.py:1154` → `/api/kiosk/control` | R2 |
| `audio.speak` (phát TTS qua loa) | `:2556-2557` (cmd audio_base64) | R2 |
| `audio.listen` (thu âm mic) | endpoint audio (V41) | R2 + thông báo owner |
| `camera.capture` | `:1166` camera/capture | R2 + thông báo owner |
| `music.stream` | `:1174-1178` | R2 |
| `hdmi.mirror` | `:1052` | R2 |
| `emergency.stop` | `:1135` | **R4** (chỉ owner hoặc TONY khi phát hiện nguy hiểm thực, luôn audit) |

Hợp đồng negotiate: daemon gửi `capabilities` + `protocol_version` trong heartbeat payload (mở rộng `:2592-2605` — field mới, backward-compatible: server cũ bỏ qua). Server so với bảng `embodiments.capabilities_json`:
- **Khớp** → READY, lệnh chỉ dùng cap đã khai báo.
- **Version nhỏ hơn** → SYNCING: server đẩy update config qua `pending_commands` (kênh hiện có).
- **Không khớp/nghi ngờ** → CONNECTED (không READY), chờ owner xem trên dashboard.

### 2.3. Command Envelope (lớp 3)

Chuẩn hoá `pending_commands` hiện tại thành envelope có audit, không đổi cơ chế pull:

```json
{
  "cmd_id": "cmd_<uuid16>",
  "cap_id": "audio.speak",
  "policy_class": "R2",
  "correlation_id": "corr_<uuid12>",
  "issued_at_utc": "...",
  "expires_at_utc": "...",     // lệnh hết hạn không giao được → DROP + audit (không dồn ứ)
  "payload": { ... },
  "issued_by": "server|owner_dm|tony_autonomous"
}
```
Daemon trả receipt trong heartbeat kế tiếp: `{"cmd_receipts": [{"cmd_id":..., "status":"done|failed|expired"}]}` → server ghi vào audit + `events` (khi M2-B1 đã làm). Mọi lệnh R4 (`emergency.stop`) bắt buộc `issued_by=owner_dm` hoặc có ticket phê duyệt — PolicyEngine vẫn là gate duy nhất, envelope chỉ đóng gói.

---

## 3. Multi-Agent Coordination (phần "distributed intelligence")

### 3.1. Kiến trúc: SUPERVISOR + AGENT-WORKERS quyền hạn giới hạn

**Không tạo process mới, không tạo LLM call mới.** Agent-worker = **luồng công việc có danh tính**, chạy trong server hiện có, dùng CognitiveLoop làm đường vào duy nhất (đúng thiết kế M2-B2 "một yêu cầu đi qua đúng 1 Cognitive Loop"):

```
Owner / Event Bus ──► CognitiveLoop.submit_task(TaskSpec)          [cổng duy nhất]
                          │
                  ┌───────▼─────────────────────────────┐
                  │ AgentSupervisor (mới, ~200 LOC)     │
                  │ - đăng ký worker: {name, regions,   │
                  │   policy_classes, concurrency=1}    │
                  │ - phân công theo capability khớp    │
                  │ - deadline + heartbeat mỗi worker   │
                  │ - chặn: worker chết → task BLOCKED  │
                  │   (không tự retry ngoài sandbox)    │
                  └───────┬─────────────────────────────┘
        ┌─────────────────┼──────────────────┐
   Worker: pi5-embodiment  Worker: knowledge-  Worker: audit-
   (gửi lệnh cap qua      worker (M3           trimmer (R2, chạy
   pending_commands, R2)   consolidation, R2)   định kỳ trong sandbox)
```

Quy tắc an toàn (ràng buộc cứng trong code, không phải chỉ docstring):
1. Worker **không có quyền network ra ngoài** trừ cap_id đã đăng ký (R2 target trong workspace / cap Pi5 đã negotiate).
2. Mọi task của worker đi qua **CognitiveLoop.submit_task với acceptance_criteria bắt buộc** (fail-closed sẵn có `cognitive_loop.py:64-67`).
3. Worker **không tự phê duyệt**: R4 chỉ tạo ticket ConsultationStore (pattern `plan_orchestrator.py:270-277`).
4. Supervisor expose `/api/executive/agents` (read-only) — dashboard thấy được agent nào đang làm gì, giống `/api/self/*` của M4.

### 3.2. Worker đầu tiên (thực chiến, không trang trí)

| Worker | Việc thật | Lý do chọn |
|---|---|---|
| `embodiment-worker` | Gói 2.3 envelope + dispatch lệnh Pi5 hiện có (speak/photo/listen/kiosk) thành đường chuẩn có audit receipt | Thay các call rải rác `_send_edge_request` bằng 1 điểm có kiểm soát |
| `memory-consolidation-worker` | Chạy việc consolidation M3 (dedupe/provenance) trong khung có supervision thay vì cron rời | M3 đang chờ — dùng chung khung |
| `audit-trimmer` | Cắt `logs/audit.jsonl` + ring buffer EdgeMonitor (>100 alerts, `edge_monitor.py:308`) theo chính sách lưu | Nợ kỹ thuật có thật, R2, sandbox được |

---

## 4. Bảo mật (thứ tự ưu tiên tuyệt đối — B1 làm TRƯỚC mọi thứ khác)

1. **B1-P0: Server verify HMAC thật** — tại `_handle_api_edge_heartbeat` + status handler: `EdgeHMACAuth.verify_request(headers, payload_bytes)`; sai → `record_auth_failure` (Alert F CRITICAL sẵn có, `edge_monitor.py:204-214`) + HTTP 401 + **không pop pending_commands**. Secret đọc từ biến môi trường/registry User (đúng chuẩn NETMIND_API_KEY đang dùng — không in giá trị, chỉ tồn tại/độ dài), fallback **từ chối khởi động nền transport này** thay vì dùng placeholder.
2. **B1-P0b: PC→Pi ký HMAC** — `_send_edge_request` thêm `create_signed_headers`; daemon verify chiều vào (code verify đã có sẵn bên Pi phía auth.py, chỉ cần wire).
3. **B1-P0c: Xoá secret placeholder khỏi source** — config.py đọc env; giá trị cứng trong git history sẽ thay khi Q-1 (git) được duyệt.
4. Sau B1: capability nào chưa negotiate qua handshake HMAC-valid thì **không nhận lệnh** (fail-closed).

## 5. Kế hoạch triển khai 4 bước (mỗi bước độc lập, có test, có hoàn tác)

| Bước | Phạm vi | Test mới | Nghiệm thu | Hoàn tác |
|---|---|---|---|---|
| **B1 — HMAC 2 chiều** (P0) | `server.py` 2 handler + `_send_edge_request`; `edge_client/config.py` env; daemon wire verify | `tests/test_edge_hmac_enforcement.py`: (a) heartbeat không sig → 401 + không nhận cmd; (b) sig đúng → 200 + nhận cmd; (c) replay nonce → 401; (d) clock drift → 401; (e) PC→Pi có header X-Quan-* | Daemon thật Pi5 heartbeat còn READY sau deploy; Alert F bắn khi test giả sig | revert handler patch — daemon đã ký sẵn nên không mất gì |
| **B2 — Embodiment Registry** | bảng `embodiments` + `distributed/embodiment.py` + hook ghi heartbeat + `/api/executive/embodiments` (read-only) | `tests/test_embodiment_registry.py`: register→heartbeat→READY persist qua "restart" (mở store mới); revoked từ chối negotiate | Dashboard hiển thị đúng EDGE-PI5-DESK-01; restart server registry còn nguyên | DROP TABLE (schema-additive, không đụng bảng khác) |
| **B3 — Capability negotiation + Command envelope** | heartbeat payload thêm capabilities; envelope cmd_id/receipt/expires | `tests/test_capability_negotiation.py`: version mismatch → SYNCING; lệnh hết hạn → expired + audit; receipt ghi nhận | 1 lệnh speak thật qua envelope mới, receipt 'done' trong audit | feature-flag `QEP_ENVELOPE=0` → trả lại format cũ |
| **B4 — AgentSupervisor + 3 worker** | `distributed/supervisor.py` + endpoint read-only + 3 worker mục 3.2 | `tests/test_agent_supervisor.py`: task qua CognitiveLoop; worker chết → BLOCKED; R4 → ticket; không worker nào có quyền ngoài đăng ký | `/api/executive/agents` đúng trạng thái sống; 1 consolidation chạy thật trong sandbox | supervisor=None → hệ như B3, worker dừng sạch |

Điều kiện chung: mỗi bước chạy `python tools/validate_and_report.py` xanh + HANDOFF_LATEST cập nhật; **không restart ngoài cửa sổ an toàn** (B1 bắt buộc restart server mới hiệu lực — chọn lúc owner cho phép như các lần trước).

## 6. Điều còn mở (trung thực)

- Kiểm chứng thực địa B1 cần daemon Pi5 cùng lúc restart (SSH sẵn có, `sudo -n` passwordless) — sẽ xin anh xác nhận thời điểm.
- `protocol_version` "qep-1" chỉ là nhãn v1 — mọi thay đổi tương lai phải bump + migration rõ ràng (bài học events của M2).
- Multi-agent ở đây là **đa worker đơn não** trong 1 server; đa não (nhiều máy PC) ngoài phạm vi QEP này và cần QEP riêng.

## 7. Chờ anh quyết

1. **"DUYỆT QEP"** → em triển khai B1→B4 theo bảng trên (B1 làm trước tiên vì P0 bảo mật).
2. Hoặc duyệt **riêng từng bước**: "DUYỆT B1" (chỉ HMAC), phần sau hỏi tiếp.
3. Q-4 vẫn là nút thắt learning song song — không ảnh hưởng M6, nhưng worker `knowledge-consolidation` (B4) sẽ chỉ sandbox cho tới khi Q-4 mở.

---
*Người lập: TONY (netMind Desktop) · 01/11/2026 · Mọi con số trong spec đều có path:line kèm theo.*
