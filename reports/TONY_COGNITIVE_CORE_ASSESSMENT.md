# TONY COGNITIVE CORE ASSESSMENT — Đánh giá bộ não trung tâm
**Cập nhật:** 01/11/2026 16:45 · PHẦN IV (ưu tiên cao nhất) · Bằng chứng: source + runtime + tests

## 4.1. Cognitive Kernel — 8 thành phần

| Thành phần | Module | Runtime? | Bằng chứng |
|---|---|---|---|
| Central State Manager | server.py state + brain.db | ✅ | 19 bảng live, episodes ghi 16:30 |
| Event Bus | cognition + edge events | ✅ (partial) | edge events có alert_id; chat turn session_ref |
| Module Registry | 34 subpackage load qua server | ✅ | inventory 230 modules |
| Task Lifecycle Manager | task_registry.py | ✅ | M4 audit; states NEW→COMPLETED |
| Runtime Supervision | watchdog.py | ❌ **MISSING** | 0 process 16:33 — rủi ro P1 |
| Unified Orchestration | cognitive_loop.py :1669-1690 | ✅ 1/5 | M2 audit — 4 engine còn ORPHAN |
| Context Management | session_manager + conversation_state | ✅ | M5: TTL 10', per-channel, 27/27 tests |
| Error Recovery | watchdog + self-care | ⚠️ | watchdog off; server tự phục hồi qua KHOI_DONG |

**Trả lời 8 câu bắt buộc:**
1. Cognitive Core điều phối toàn bộ? — **CÓ 1 lõi chính** (cognitive_loop trong server), chưa nuốt được 4 engine rời.
2. Hay nhiều engine độc lập? — Vẫn còn 4 ORPHAN (đã đặt tên, có kế hoạch tích hợp P2).
3. Luồng xử lý thống nhất? — CÓ cho chat/task/edge; voice pipeline tách tiến trình trên Pi5 (đúng thiết kế embodiment).
4. Trạng thái xuyên suốt? — CÓ: brain.db + session TTL + seen_state.
5. Nhiều nhiệm vụ đồng thời? — CÓ: task_registry + learning daemon + responder poll song song.
6. Khôi phục sau gián đoạn? — CÓ: catch-up 12h tin nhắn; learning checkpoint; NOT full task resume (P2).
7. Phát hiện nhiệm vụ kẹt? — CÓ: CLO-stall alert edge-trigger (M5, gửi DM thật khi kẹt >24h).
8. Kiểm soát mọi đường thực thi? — CÓ ở HTTP (HMAC gate fail-closed) + approval; watchdog đường phụ tắt → ghi nhận P1.

## 4.2. Cognitive Loop — 10 bước

| Bước | Module phụ trách | Runtime verified | Test |
|---|---|---|---|
| PERCEIVE | health_monitor + edge telemetry + netchat poll | ✅ | test_monitoring_health |
| UNDERSTAND | command_center detect_intent + GLM | ✅ (fix P0 16:13) | test_netchat_command_center |
| REMEMBER | memory engines + brain.db | ✅ | M4/M5 suites |
| REASON | GLM + CriticalThinker ⚠️ORPHAN | ⚠️ partial | chưa E2E riêng |
| PLAN | planning/ + decision/ | ✅ | test planning |
| GOVERN | governance/ + R0-R5 + HMAC gate | ✅ | test_m6b1_hmac (6/6) |
| EXECUTE | execution/ + tools executor | ✅ | 155 test files |
| VERIFY | health checks + verify_request HMAC | ✅ | E2E Pi5 120s 0-fault |
| LEARN | continuous_learning_engine + reflection ⚠️bug | ⚠️ | M2 bug chờ fix |
| COMMUNICATE | netchat responder + TTS + dashboard | ✅ | log greeting 16:13 |

**TONY có dùng trí nhớ trước nhiệm vụ quan trọng?** — CÓ ở luồng chat (memories + semantic lookup trước trả lời); chứng minh: episodes 2.685 + Self-QA grounded. **Có kiểm chứng kết quả trước khi tuyên bố hoàn thành?** — CÓ ở pipeline kỹ thuật (verify + regression 3.002); câu trả lời LLM vẫn cần giám sát owner.

## 4.3. Reasoning Engine

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| Hiểu ngữ cảnh | ✅ Cấp 2 | conversation_state + anaphora (M5) |
| Phân tích logic | ✅ Cấp 2 | GLM + command router |
| Nhận diện giả định / mâu thuẫn | ⚠️ Cấp 1 | CriticalThinker 574 LOC có, CHƯA tích hợp |
| Phân biệt FACT/INFERENCE/HYPOTHESIS/UNKNOWN | ⚠️ Cấp 1 | schema có cờ; reflection.py bug làm mất hypothesis (M2) |
| Tự nhận thiếu dữ liệu | ✅ Cấp 2 | "UNKNOWN" policy trong health + audit |

**Điểm Cognitive Core: CẤP 2 (làm được việc thật) — 8/10 bước chạy runtime, 2 bước (REASON sâu, LEARN-reflection) đang gắn mũi tên chờ M2/P2.**

## 4.4. Khoảng trống hành động

1. **M2 fix reflection.py** (`:195-199 source_type`) — đã duyệt trong backlog, chờ chủ nhân nhả slot.
2. **Tích hợp CriticalThinker** vào cognitive loop (P2, 8h) — sau P0.
3. **Bật lại watchdog** — xem SYSTEM_HEALTH_ASSESSMENT (R-new01).
