# TONY_XIAOZHI_ARCHITECTURE_GAP_ANALYSIS — SPRINT 0 (MASTER PROMPT V9.0)

> **Sprint:** 0 — Architecture Audit · **Ngày:** 06/11/2026 · **Thực hiện:** TONY (netMind Desktop)
> **Nguyên tắc:** AUDIT FIRST — chỉ đọc code, không sửa thiết kế lõi. Mọi trạng thái đều có bằng chứng (file/test/verify thật).
> **Mô hình tham chiếu:** XiaoZhi AI (`78/xiaozhi-esp32`, Apache-2.0) + ESP-SR v2.1 + MCP Spec 2025-06-18.

---

## 1. Bảng audit 10 thành phần lõi

| # | Thành phần | File thực tế | Trạng thái xây dựng | Trạng thái kiểm chứng | Gap so với V9.0 |
|---|---|---|---|---|---|
| 1 | LLMRouter | `src/quan_ai_brain/llm/router.py` (class `LLMRouter`, `RoutingDecision`) + `netmind_provider.py` | **IMPLEMENTED** | UNIT_TESTED (baseline 3609+) | Chưa đo streaming first-token latency thật; chưa có routing 3 mode FAST/STANDARD/DEEP |
| 2 | SessionMemoryManager | `src/quan_ai_brain/memory/session_manager.py` + `cognition/session_memory.py` | **IMPLEMENTED** | UNIT_TESTED | Đáp ứng §VII; cần benchmark hội thoại dài (Sprint 6) |
| 3 | Voice Interface | `voice/azure_asr.py` (streaming recognize), `voice/azure_tts.py` (synthesize_stream) | **IMPLEMENTED** | UNIT_TESTED | Chưa đo ASR/TTS latency E2E; chưa chứng minh partial transcript thời gian thực |
| 4 | Audio Processing | `voice/audio_vad_pipeline.py` (WebRTC VAD), `voice/audio_capture.py` | **PARTIALLY_IMPLEMENTED** | UNIT_TESTED | **Không có AEC/NS/AGC** — hands-free full-duplex sẽ tự-ngắt; chỉ VAD |
| 5 | Barge-in | `voice/barge_in_handler.py` (`BargeInDetector`, TurnState/TurnEvent) | **IMPLEMENTED** | UNIT_TESTED + có route `/api/voice/barge-in` | Chưa đo barge-in response time thật (mục tiêu ≤200 ms) |
| 6 | State Machine hội thoại | `voice/state_machine.py` (`VoiceStateMachine`) | **IMPLEMENTED** | UNIT_TESTED | 9 trạng thái đầy đủ (DISABLED/STANDBY/WAKE_DETECTED/LISTENING/TRANSCRIBING/THINKING/SPEAKING/INTERRUPTED/ERROR) — cần đồng bộ sự kiện `voice_state_changed` lên QEP telemetry (Sprint 4) |
| 7 | Pi5 Client | `edge_client/client_daemon.py` (+20 kiosk API: camera/audio/media/estop) | **IMPLEMENTED** | **LIVE_VERIFIED 06/11** (5/5 services active, kiosk core_connected, camera IMX708 E2E) | LAN chết 2 chiều — phụ thuộc mesh DERP 51–189 ms; chưa có ESP32 để điều phối |
| 8 | Wake Word | `edge_client/wake_word_service.py` (openWakeWord) | **PARTIALLY_IMPLEMENTED** | UNIT_TESTED | KHÔNG phải ESP-SR WakeNet; chưa chạy offline trên device thật; chưa đo FA/FR |
| 9 | Device Registry | `src/quan_ai_brain/web/device_store.py` (`DeviceStore`) | **IMPLEMENTED** | UNIT_TESTED | Chưa theo QEP (13 thành phần §VI); chưa có registration + capability discovery chuẩn |
| 10 | Governance | `governance/approval_service.py` (`ApprovalCardService`), `governance/authority_protocol.py` (`AuthorityGovernor`), `security/rbac.py` (`RBACEngine`, `ABACPolicy`) | **IMPLEMENTED** | UNIT_TESTED (E2E confirm-gate 2 bước qua DM) | Chưa gắn Risk Level R0–R5 vào từng tool của MCP registry (Sprint 2) |

### Thành phần ngoài bảng audit ban đầu (phát hiện thêm khi audit)

| Thành phần | File | Trạng thái | Ghi chú |
|---|---|---|---|
| Deep Memory V9 | `memory/deep_memory.py` (`DeepMemoryStore`) | **IMPLEMENTED** + LIVE (Tab 10) | 06/11: +`list_units`, `answer_owner_question`, `review_timeline`, 6 route `/api/memory/deep/*` — 7 test mới PASS |
| Memory Review Cycle | `cognition/memory_review_cycle.py` (10 stage) | **IMPLEMENTED** | Idempotent, checkpoint/resume, không tự nâng trạng thái (PHẦN XV) |
| Tool Registry | `tools/registry.py` (`ToolRegistry`, `ToolDefinition`) | **IMPLEMENTED** | Nền cho MCP Registry (Sprint 2 mở rộng 15 trường) |
| MCP Client/Server | — | **MISSING** | Chưa có implementation chuẩn MCP |
| QEP | — | **MISSING** (spec-only) | 13 thành phần §VI chưa có code |
| ESP32 ecosystem | — | **MISSING** | Chưa có board thật; firmware chưa khảo sát trên phần cứng |

---

## 2. So sánh với kiến trúc XiaoZhi (theo từng lớp)

| Lớp | XiaoZhi | TONY hiện tại | Quyết định V9.0 |
|---|---|---|---|
| Wake word | WakeNet9 trên ESP32-S3, offline | openWakeWord trên PC/Pi5 | Sprint 3: chuyển ESP32-S3; tạm thời giữ openWakeWord |
| Audio front-end | AFE (AEC+NS+BSS) trên chip | WebRTC VAD trên PC, không AEC | Sprint 1: thêm AEC phía PC/Pi5 trước khi mở hands-free |
| ASR/TTS | Server XiaoZhi (cloud) | Azure Speech streaming trên PC | Giữ; đo latency + đánh giá model realtime mới (Sprint 1) |
| Device protocol | WebSocket riêng + MQTT+UDP | HTTP API + HMAC edge auth | Sprint 4: QEP поверх; giữ HMAC gate |
| MCP | MCP client trong firmware | Không có | Sprint 2: MCP ở **Cognitive Core**, không trong firmware |
| UI nhúng | LVGL trên S3 | Web dashboard (kiosk) | Sprint 5: tùy chọn LVGL khi có S3 |
| Governance | Không có (server chủ quản) | Approval/RBAC/Authority đầy đủ | **Lợi thế TONY** — giữ nguyên, mở rộng cho MCP/QEP |

---

## 3. Rủi ro kiến trúc phải xử lý trước Sprint 3

1. **AEC thiếu** (gap #4): mở hands-free bây giờ → TONY tự ngắt lời chính mình. Bắt buộc Sprint 1.
2. **LAN PC↔Pi5 chết 2 chiều** (router chặn): mọi traffic qua mesh DERP — ảnh hưởng băng thông audio streaming; cần root-cause trước khi đưa audio qua LAN.
3. **Wake word FA/FR chưa đo**: không có baseline trước khi đổi sang WakeNet → không chứng minh được cải thiện.
4. **Voice loop qua IP cứng đã fix 06/11** (root cause "TONY ơi" im lặng): voice/hdmi/tts URL giờ resolve từ `config.json`; còn lại: phát sự kiện `voice_state_changed` lên QEP telemetry (Sprint 4).
5. **Không có ESP32 thật**: Sprint 3 chỉ có thể làm spec + firmware nghiên cứu; mọi claim "ESP32 OK" là SIMULATED cho đến khi có board.

---

## 4. Kết luận Sprint 0

- **Nền tảng đủ mạnh cho V9.0**: Cognitive Core + Governance + Pi5 channel + Deep Memory đã LIVE; Voice pipeline có khung streaming.
- **3 module MISSING hoàn toàn**: MCP, QEP, ESP32 — đúng như lập kế hoạch Sprint 2/3/4.
- **2 module PARTIAL chặn đường hands-free**: AEC + wake word.
- **Không phát hiện vi phạm kiến trúc**: không có Cognitive Core thứ hai; governance không bị bypass.
- **Đề xuất thứ tự sprint** (không đổi so với V9.0): S1 Voice → S2 MCP → S3 ESP32 → S4 QEP → S5 Pi5 → S6 Benchmark → S7 Audit.

*Báo cáo này là đầu ra duy nhất của Sprint 0 — không sửa code lõi. Bằng chứng file/test được liệt kê trực tiếp trong từng dòng bảng.*
