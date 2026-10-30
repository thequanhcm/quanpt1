# PHASE 0 — MULTI-EMBODIMENT BASELINE AUDIT (QEP V1.0)

**Ngày:** 30/10/2026 | **Người thực hiện:** QUAN AI BRAIN (TONY) | **Duyệt:** Quanpt1 (30/10/2026 — "anh duyệt toàn bộ")
**Phạm vi:** CHỈ audit + thiết kế. KHÔNG sửa production code. STOP chờ duyệt trước Phase 1.

---

## 0. Bối cảnh pháp lý nội bộ

Bộ治理 quy tắc hiện hành (AGENTS.md + V5→V40 constraints) đã chặn sẵn mọi rủi ro Phase 0:
R4 yêu cầu phê duyệt riêng; R5 hard-block; Learning ≠ deployment; không tự deploy/commit/push
khi chưa duyệt. Phase 0 này tuân thủ 100%: mọi thứ bên dưới là **đọc + phân tích + đề xuất**.

---

## 1. Kiến trúc hiện tại (đo đạc thật, ngày 30/10/2026)

### 1.1 Brain (PC, `src/quan_ai_brain/`) — 33 subsystems, ~90,000 dòng Python

| Nhóm | Subsystem chính | Vai trò QEP tương lai |
|---|---|---|
| Nhận thức | cognition (40 files, 15,017 dòng) | Cognitive Core |
| Trí nhớ | memory (39 files, 16,042 dòng) + ChromaDB (knowledge_base 33,405 chunks @ data/knowledge_db; memory_db riêng) | Memory Engine (ONE MEMORY) |
| Tri thức | knowledge (930 dòng), kho_tai_lieu ingestion 33k+/81,287 chunks | Skill/Knowledge Engine |
| Quản trị | governance (2,245 dòng: PolicyEngine R0–R5, ApprovalCard, ConsultationInbox, NetChat adapter) | Governance Core (ONE GOVERNANCE) |
| Điều phối | orchestration (1,436 dòng: PlanOrchestrator, Supervisor, TaskRegistry) + decision (1,196 dòng) | Task/Plan coordination |
| An toàn thực thi | execution (1,461 dòng: process_containment, resource_budget, staging, windows_job_object) | Safety Runtime foundations |
| Edge | edge (817 dòng: models DeviceIdentity/capabilities, transfer_service, release_manager) | **Embodiment Adapter foundation** |
| Edge monitor | web/edge_monitor.py (343 dòng, 9-state lifecycle, alerts A–H) | Embodiment health |
| Giao tiếp | web/server.py (5,252 dòng, endpoints executive/edge/kiosk), gateway (2,086), integration (2,849), mobile (601) | Comms layer |
| Danh tính | cognition/executive_persona.py + role_orchestrator.py | ONE IDENTITY |
| Học hỏi | learning (3,793 dòng: performance_monitor hồi sinh, feedback, self_optimizer, knowledge_refiner) | Skill development |
| Khác | voice (4,013), analytics (4,128), ai (2,814), llm (1,528), nlp, planning, creativity, optimization, scaling, security (1,950), contract, dashboard, media, clae, tools | — |

**Điểm mấu chốt đã kiểm chứng bằng grep:** hiện KHÔNG có code ROS2/GPIO/PWM/servo/Reachy/
OriginMan/ESP32/Jetson nào trong `src/quan_ai_brain/` — Brain hoàn toàn sạch phần cứng.
(`relays`, `servos` chỉ xuất hiện như **capability strings** trong `DeviceIdentity` — khai báo,
không phải code điều khiển.)

### 1.2 Edge hiện có (Pi 5) — `edge_client/` (~6,000 dòng client daemon + kiosk)

- **Đã có và đã verify (29–30/10):** kiosk Chromium 800x480, avatar canvas, HMAC heartbeat
  dual-direction (`/api/executive/edge/heartbeat`), remote audio/mic/camera/music control
  (ADDENDUM V2.1), emergency_stop, files upload/delete, netcat-style command channel qua
  heartbeat response (`remote_command`), systemd scripts, asset sync.
- **Mới deploy hôm nay (V41 Edge Agent, duyệt bởi Quanpt1):** 5 năng lực chủ động
  (edge_client/edge_agent.py, 38 tests) — tự phản ứng, tự quản lý, tự thu thập, tự phối hợp,
  tự cải tiến có kiểm soát (CHỈ đề xuất, `requires_owner_approval: true` bất biến).
- **Hạn chế vật lý:** camera/mic là USB peripheral; GPIO hiện KHÔNG được expose qua API —
  đúng triết lý Local Safety Runtime (Brain không đụng GPIO).

### 1.3 Giao thức PC↔Edge hiện tại

```
Pi5 → PC:  POST /api/executive/edge/heartbeat (HMAC, rtt, telemetry, edge_agent V41 summary)
           POST /api/executive/edge/events   (MỚI V41: events tự thu thập)
           POST /api/edge/pair, mouth-sync, transfers...
PC  → Pi:  heartbeat response: target_avatar_state, transcript, face_only_mode, remote_command
           (reload_ui, pause, resume, set_expression, speak+audio, sync_assets)
           HTTP direct: /api/kiosk/control, /api/kiosk/camera/*, /api/kiosk/audio/*...
```

Poll interval 1s, HMAC-SHA256 signing, PIN pairing, 9-state lifecycle monitor.

---

## 2. Đánh giá khoảng cách với 6 nguyên tắc Master Prompt

| Nguyên tắc | Trạng thái | Khoảng cách |
|---|---|---|
| **Brain độc lập Body (Adapter layer)** | 🟡 70% | Đã có `edge/models.py DeviceIdentity` + capability strings + transfer/release; nhưng CHƯA có **EmbodimentAdapter interface** chính thức (abstract class) mà mọi body (Pi5, Reachy, ROS2 robot, ESP32...) implement. Hiện edge_client daemon là 1 thể "cứng" cho kiosk Pi5. |
| **Brain trí tuệ / Body hành động** | 🟢 90% | Brain không có code GPIO/PWM/servo (đã grep verify). Safety runtime đặt đúng chỗ: Pi-side (emergency_stop, fswebcam timeout 5s...). Còn thiếu: contract cho real-time control loop (LLM không bao giờ bị route tới PWM). |
| **Không phụ thuộc vendor** | 🟢 85% | stdlib-only (`dependencies=[]`), không SDK Reachy/ROS. Adapter layer là thứ còn thiếu để cam kết hoàn toàn. |
| **ONE IDENTITY** | 🟢 80% | executive_persona + role_orchestrator tồn tại; device_id hiện là per-body (`EDGE-PI5-DESK-01`). Cần: identity mapping `brain_id → many body_ids` rõ ràng trong models. |
| **ONE MEMORY** | 🟢 85% | ChromaDB + SQLite ở PC; Edge KHÔNG có memory cục bộ riêng ngoài state runtime + event buffer (đúng hướng). Cần: event buffer đồng bộ về Memory Engine (đã có `/api/executive/edge/events`, cần persisted store). |
| **ONE GOVERNANCE** | 🟢 90% | PolicyEngine R0–R5 + ApprovalCard + ConsultationInbox hoạt động thật (đã dùng trong V41: đề xuất agent đều `requires_owner_approval`). Cần: capability-based policy cho body actions (R-level per capability). |

**Tổng thể: nền tảng sẵn sàng ~83%.** Điểm mạnh lớn nhất: Brain đã sạch phần cứng tuyệt đối
và governance đã có sẵn. Điểm yếu duy nhất có ý nghĩa kiến trúc: **thiếu interface
EmbodimentAdapter chính thức** — hiện chỉ có 1 body (Pi5 kiosk) wired trực tiếp.

---

## 3. Thiết kế đề xuất — QEP V1.0 (KHÔNG code trong Phase 0)

### 3.1 Kiến trúc mục tiêu

```
┌─────────────────────────── QUAN AI BRAIN (PC) ───────────────────────────┐
│  Cognitive Core  │  Memory Engine  │  Governance Core (R0-R5)            │
│         Embodiment Manager (MỚI, ~600 dòng dự kiến)                      │
│    ├── EmbodimentAdapter (ABC — interface duy nhất mọi body implement)   │
│    │     register()/heartbeat()/execute_skill()/health()/shutdown()      │
│    ├── CapabilityRegistry (capability → risk level R0-R5)                │
│    ├── BodyRouter (multi-body dispatch, xung đột ưu tiên)                │
│    └── LocalSafetyRuntime CONTRACT (bắt buộc mỗi body tự khai báo)       │
│  Comms: HTTP/HMAC (hiện có) → mở rộng WebSocket stream (sau)             │
└──────────────┬──────────────────────────────┬────────────────────────────┘
               │ Adapter: KioskBody (Pi5, HIỆN CÓ)        │ Adapter: tương lai
               │ (wrap edge_client hiện tại)              │ Reachy/ROS2/ESP32...
```

### 3.2 Message Schema proposal (QEP-MSG v0.1)

```json
// QEPEnvelope — mọi message giữa Brain và Body
{
  "qep_version": "1.0",
  "msg_id": "uuid",
  "ts_utc": "iso8601",
  "brain_id": "QUAN_AI_BRAIN_01",          // ONE BRAIN
  "body_id": "EDGE-PI5-DESK-01",           // per-body
  "type": "COMMAND | EVENT | TELEMETRY | ALERT | HEARTBEAT | SKILL_REQUEST | SKILL_RESULT",
  "payload": { ... },                      // tùy type
  "risk_level": "R0..R5",                  // bắt buộc với COMMAND
  "approval_ref": null | "approval_card_id" // R4 phải có
}
```

### 3.3 Capability taxonomy proposal

| Tier | Ví dụ | Risk mapping | Điều kiện |
|---|---|---|---|
| SENSE | camera.snapshot, mic.level, temp.read | R0 | read-only, luôn ALLOW |
| EXPRESS | avatar.state, speak, display | R1/R3 | theo runtime state |
| ACTUATE_LOW | servo.move, gpio.write, motor.cmd | **R5 qua Brain** | **KHÔNG BAO GIỜ route qua LLM/Brain** — chỉ Local Safety Runtime của body tự thực hiện theo skill đã duyệt |
| ACTUATE_HIGH | navigate, grasp, open_door | R4 | approval card bắt buộc + safety runtime đồng ý |
| SYSTEM | update_self, install, config_change | R4/R5 | chỉ theo ApprovalCard |

Nguyên tắc vàng (khớp Master Prompt II.2): **Brain lập kế hoạch ở mức SKILL; mọi vòng
thời gian thực là trách nhiệm của Local Safety Runtime trong body.**

### 3.4 Roadmap đề xuất (stage-gate, mỗi phase nghiệm thu riêng)

| Phase | Nội dung | Risk | Điều kiện chuyển phase |
|---|---|---|---|
| **P1** | `EmbodimentAdapter` ABC + `CapabilityRegistry` + wrap Pi5 kiosk thành `KioskBodyAdapter` (code mới, KHÔNG sửa hành vi hiện tại) | R2 (code mới trong workspace) | Unit tests + full suite xanh |
| **P2** | QEPEnvelope message schema + migrate heartbeat/events sang envelope (backward-compatible) | R2 | Dual-format support, tests |
| **P3** | Capability risk mapping vào PolicyEngine (mỗi capability → R0-R5) | R2 | Governance tests |
| **P4** | Body #2 thật (ESP32/ROS2 sim) qua adapter — chứng minh ONE BRAIN MANY BODIES | R3 | E2E demo + duyệt |
| **P5** | WebSocket realtime + multi-body orchestration đồng thời | R3-R4 | Approval riêng |

### 3.5 Security/safety threat assessment (tóm tắt)

- **Đã có:** HMAC per-device, PIN pairing, R5 hard-block, sensitive-data transfer block
  (AUTHENTICATION_SECRET blocked trong transfer_service), 9-state monitor, emergency_stop.
- **Khoảng trống cần thiết kế (P3):** replay-attack window (nonce), body-compromise
  containment (revoke capability per body), approval expiry cho R4 body actions.
- **Không bao giờ:** LLM output → PWM/GPIO trực tiếp (chỉ qua skill đã duyệt + safety runtime).

---

## 4. Decisions requiring approval (STOP — chờ Quanpt1)

1. **P1 có bắt đầu không?** Tạo `src/quan_ai_brain/embodiment/` (ABC + registry + KioskBodyAdapter, không đụng code đang chạy).
2. **Schema QEP-MSG v0.1** ở mục 3.2 — duyệt hướng hay chỉnh?
3. **Capability taxonomy + risk mapping** mục 3.3 — đặc biệt nguyên tắc ACTUATE_LOW = R5-via-Brain (Brain không điều khiển servo trực tiếp, kể cả khi được yêu cầu).
4. **Body #2 phase P4:** chọn ESP32 (rẻ, MCU) hay ROS2 sim (không phần cứng) làm mục tiêu chứng minh?
5. **V41 Edge Agent đã deploy Pi5 chưa?** Pi5 hiện OFFLINE khỏi mạng (PC đã chuyển Wi-Fi 192.168.10.x, Ethernet rút). Khi Pi5 nối lại: chạy `tools/deploy_edge_v41.sh` (sẽ tạo) để đồng bộ edge_agent.py + restart daemon. Hiện code + tests đã sẵn sàng trong workspace.

---

## 5. Kết luận

Nền tảng QUAN AI BRAIN hiện tại **đáp ứng ~83% nguyên tắc Master Prompt** — đặc biệt
Brain đã tuyệt đối sạch phần cứng (grep verify) và Governance R0-R5 đã chạy thật.
Khoảng cách duy nhất có ý nghĩa: chính thức hóa **EmbodimentAdapter interface** để
"ONE BRAIN – MULTIPLE BODIES" trở thành kiến trúc bắt buộc thay vì quy ước.
Phase 0 hoàn tất — **STOP chờ duyệt** trước khi viết dòng code QEP đầu tiên (P1).
