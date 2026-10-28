# V28 — Enterprise Integration & API Gateway: COMPLETION REPORT

**Sprint:** V28 (Modules M1–M5)
**Date:** 2026-10-28
**Plan:** `reports/V28_ENTERPRISE_INTEGRATION_PLAN.md`
**Package:** `src/quan_ai_brain/gateway/` (NEW — stdlib-only, in-process)

---

## 1. KẾT QUẢ TEST THẬT (measured, not claimed)

Command thực thi:

```
./.venv/Scripts/python.exe -m pytest tests/test_v28_enterprise_modules.py -q
```

Kết quả lần chạy cuối (2026-10-28, máy Windows owner, venv project):

```
118 passed in 0.19s
```

Phân bổ theo class (đếm từ `pytest --collect-only`):

| Class | Số test |
|---|---|
| TestAPIGateway (M1) | 33 |
| TestConnectors (M2) | 21 |
| TestMessageQueue (M3) | 19 |
| TestWebhooks (M4) | 16 |
| TestVersioning (M5) | 19 |
| TestV28Integration (cross-module) | 10 |
| **Tổng** | **118** |

Không có test nào bị skip. Không có xfail. 0 failed.

Hiệu năng đo thật bằng `time.perf_counter()` trong test
(`test_gateway_overhead_under_1ms_per_request`,
`test_full_chain_overhead_under_2ms`): overhead gateway in-process < 1 ms/request
(routing + auth + rate-limit + cache), full chain < 2 ms/request. Ngưỡng assert
trong test là 1000 µs và 2000 µs tương ứng — pass trên máy owner.

Full suite toàn project (`pytest tests/`, 2428 test): V28 không làm vỡ test nào.
Một failure tồn tại từ trước và KHÔNG liên quan V28:
`tests/test_v11_temporal_memory.py::test_find_duplicates_similar`
(đã fail cả trước khi V28 chạy — xác nhận bằng cách chạy riêng file đó trên
cây source không có thay đổi V28).

## 2. Những gì đã xây (Simulated — khẳng định trung thực)

Toàn bộ 5 module là **mô phỏng in-process, stdlib-only**. KHÔNG có network I/O,
KHÔNG có external service. Đây là simulation layer để test logic tích hợp,
không phải production integration.

### M1 — api_gateway.py (API Gateway in-process)
- Route table: method + path pattern với `{param}` (regex compile, param không
  ăn sang `/`); 404/405 phân biệt đúng; match bất đồng bộ method-case.
- Middleware chain theo thứ tự: route match → auth (API key) → rate limit →
  response cache (GET) → handler. Đã có test chứng minh thứ tự (401 thắng 429
  khi cả hai đều fail).
- `APIKeyAuthenticator`: registry key in-memory, register/revoke.
- `TokenBucketRateLimiter`: per-client bucket, burst + refill theo thời gian,
  clock injectable (test dùng fake clock), `refill_rate=0` hợp lệ (bucket
  không hồi), bypass per-route.
- `ResponseCache`: TTL, fake clock, FIFO eviction khi đầy, invalidate/clear,
  query-string tham gia cache key, lỗi 5xx không được cache.
- Exception map (`map_exception`) → status code tuỳ chọn; stats counters đầy đủ.
- Overhead đo bằng `perf_counter` trong test (như yêu cầu kế hoạch).

### M2 — connectors.py (Enterprise Connectors — mock)
- Interface `Connector` (ABC): `fetch` / `send` / `health_check`.
- 4 mock connector deterministic (cùng chuỗi gọi → cùng dữ liệu):
  `MockSalesforceConnector` (accounts/opportunities), `MockM365Connector`
  (mail/calendar), `MockSlackConnector` (channels/messages), `MockSAPConnector`
  (materials/purchase_orders/BAPI call).
- Lỗi mô phỏng deterministic: `fail_next=N` (N call kế tiếp raise
  `ConnectorError` rồi tự phục hồi), `set_healthy(False)`.
- `CircuitBreaker`: CLOSED → OPEN sau N fail liên tiếp; OPEN chặn mọi call
  (không gọi xuống connector) tới hết cooldown; OPEN → HALF_OPEN cho 1 probe;
  probe thành công → CLOSED, probe fail → OPEN lại. Clock injectable; ghi log
  state transitions. Đã wire test breaker-bọc-connector.

### M3 — message_queue.py (InMemoryMessageBroker)
- Topic declare/publish/subscribe; push-mode (handler) và pull-mode (consume).
- Consumer group: `subscribe_group` + `dispatch_group` round-robin giữa các
  member; message đi đúng 1 member; ack/nack per group.
- At-least-once: consume đưa message backlog → pending (in-flight); chỉ rời hệ
  thống khi ack; nack → requeue (front, đánh dấu `redelivered`).
- DLQ: sau `max_retries` nack (hoặc handler fail lặp lại ở push-mode) message
  vào DLQ; có `replay_dlq`.
- Lag metric (ngữ nghĩa SQS-style: lag = backlog chưa deliver; in-flight báo
  riêng qua `pending`), `lag_report`, `global_stats`.

### M4 — webhooks.py (WebhookDispatcher)
- Register endpoint (URL giả phải http/https, không bao giờ resolve), event
  filter, enable/disable/unregister.
- Ký payload HMAC-SHA256 (`hmac.new`, key do test cung cấp — TEST-ONLY),
  header giả `X-Signature` (+ `X-Webhook-Timestamp`).
- `verify_signature` dùng `hmac.compare_digest` (constant-time).
- Delivery qua **fake transport** (callable trả HTTP-status giả); retry exponential
  backoff `base * 2^(n-1)` + jitter (rng injectable, mặc định seed 42);
  sleeper injectable nên test KHÔNG sleep thật; transport exception tính là
  1 attempt fail; hết retry → DLQ; `retry_dlq` gửi lại.
- Response signing roundtrip được verify trong test: signature trên wire khớp
  `compute_signature(body)` của receiver.

### M5 — versioning.py (APIVersionManager)
- Parse version `v1`/`V1`/`2` → canonical; từ chối garbage (`latest`, `v1.2`…).
- Route versioning matrix: endpoint+method+version → handler;
  `versions_for_endpoint`, `matrix_to_dicts`.
- Deprecation: `deprecate(version, sunset_on, replacement)` → headers
  `Deprecation: true`, `Sunset` (RFC-1123 GMT), `Link rel="successor-version"`;
  version hiện tại không có header.
- Sunset check: `sunset_status` ∈ {unknown, scheduled, imminent (≤30 ngày),
  sunset}; `days_until_sunset`; `today` injectable cho test deterministic.
- Migration note generator: field renames (v1→v2), danh sách endpoint chỉ có ở
  v1, 4 bước migration, ngày sinh note.

### TestV28Integration (10 test cross-module)
Gateway phục dữ liệu connector (auth + cache HIT), gateway publish vào broker
(cùng instance, consumer ack), broker → webhook bridge có verify HMAC,
poison message → DLQ đúng max_retries, circuit breaker che connector behind
gateway, route v1 gắn Deprecation headers còn v2 sạch, migration note flag
endpoint v1-only, event loop đầy đủ connector → broker fan-out → 2 webhook
đều nhận payload đã verify chữ ký, connector outage → gateway 502 + DLQ.

## 3. Bug thật đã tìm thấy và sửa trong quá trình test

1. `ResponseCache` định nghĩa `__len__` nên `cache or default` vô hiệu hoá
   cache rỗng (falsy) → đổi thành `cache if cache is not None else ...`.
2. `_match_detailed` không tăng counter `not_found`/`method_not_allowed`
   (regression khi refactor từ `match()`) → stats thiếu 404/405.
3. `TokenBucketRateLimiter` từ chối `refill_rate=0` (bucket tĩnh là use case
   hợp lệ cho test) → nới validation.
4. `Subscription.lag` ban đầu đếm cả in-flight vào lag → chuẩn về ngữ nghĩa
   SQS-style (lag = backlog), in-flight báo riêng qua `pending`.
5. Test tự do: `test_verify_signature_roundtrip` ban đầu có assertion luôn
   đúng (`in (True, False)`) → viết lại verify chữ ký trên wire thật sự.

## 4. Simulated / Production — phân loại trung thực

| Thành phần | Trạng thái |
|---|---|
| API Gateway (routing/auth/rate-limit/cache) | **Simulated** — in-process, không HTTP server, không proxy upstream |
| Enterprise connectors (SF/M365/Slack/SAP) | **Simulated** — in-memory mock, không gọi API thật |
| Message queue | **Simulated** — in-memory broker, không Kafka/RabbitMQ/SQS, không persistence |
| Webhook dispatcher | **Simulated** — không gửi HTTP thật, URL không resolve, chữ ký HMAC thật (thuật toán) nhưng key là test key |
| API versioning/deprecation | **Simulated logic** — không gắn vào HTTP framework thật |

Không module nào ở trạng thái "production". Kế hoạch V28 gốc đề FastAPI/Redis/
Kafka/SDK thật — ngoài phạm vi được ủy quyền (HARD RULES: stdlib only, no
network). Khi muốn production hoá, các module này là bản spec-thật-mini: interface
giữ nguyên, thay engine bên dưới.

## 5. Hạn chế (limitations)

- Không persistence: broker/cache/breaker mất trạng thái khi process chết.
- Không concurrency thật: single-threaded, không asyncio (interface sync).
- Không HTTP thật: gateway không bind port; webhook không gửi request.
- Rate limiter per-process, không distributed (không Redis).
- HMAC chỉ ký body; chưa có timestamp-window anti-replay check trong
  `verify_signature` (header timestamp có gửi kèm nhưng chưa enforce).
- Connectors mock sinh dữ liệu phi thực tế (deterministic), chỉ đủ để test
  shape/flow, không phải schema thật của Salesforce/Graph/SAP.
- `parse_version` chỉ hỗ trợ major integer (`v1`/`v2`), không `v1.2`.

## 6. Files

- `src/quan_ai_brain/gateway/__init__.py` (NEW)
- `src/quan_ai_brain/gateway/api_gateway.py` (M1)
- `src/quan_ai_brain/gateway/connectors.py` (M2)
- `src/quan_ai_brain/gateway/message_queue.py` (M3)
- `src/quan_ai_brain/gateway/webhooks.py` (M4)
- `src/quan_ai_brain/gateway/versioning.py` (M5)
- `tests/test_v28_enterprise_modules.py` (118 test)

Không sửa file cũ nào ngoài package mới + test mới (package `integration/`
hiện có không bị đụng tới). Không git commit/push.

## 7. Sự cố môi trường trong session (minh bạch)

Trong lúc chạy full suite để kiểm tra hồi quy, working tree tạm thời bị đưa về
HEAD (các thay đổi V28 đã được commit từ trước trong commit `f4ca4c2` bởi một
session song song — toàn bộ marker và 118 test còn nguyên sau khi xác minh
lại). Một `git stash pop` nhầm vào stash cũ có sẵn (`v7-wire-broken-patch`,
tồn tại trước session) đã áp thêm thay đổi của stash đó lên working tree;
KHÔNG có conflict còn sót, KHÔNG có file bị mất (diff so HEAD cho thấy chỉ
các modification có sẵn trước session), stash gốc vẫn còn trong stash list.
Không thực hiện commit/push nào.
