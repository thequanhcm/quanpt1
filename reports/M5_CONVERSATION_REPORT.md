# TONY COGNITIVE EVOLUTION — M5: HUMAN-LIKE CONVERSATION (Phần 1)

**Người thực hiện:** TONY (netMind Desktop) · **Ngày:** 01/11/2026 · **Phê duyệt:** "BẮT ĐẦU M5" (anh Quân, 01/11)
**Workspace:** `D:\AI\AI Quanpt1 2026\BRAIN` · **Execution mode:** AUDIT-FIRST / READ-ONLY / OWNER-GOVERNED
**Phạm vi:** M2/M3 vẫn PENDING. Gộp M4-B (learning health) + M4-C (Self-Q&A) vào M5 vì cùng nền tảng. KHÔNG barge-in, KHÔNG đổi voice pipeline (giữ nguyên VAD daemon Pi5).

---

## 1. Audit-first — hiện trạng hội thoại trước khi sửa

| Kênh | Ngữ cảnh lượt trước (G-22) | Trả lời câu hỏi về bản thân (G-12) |
|---|---|---|
| Voice Pi5 (`/api/executive/edge/voice_command`, `/converse`) | ❌ STATELESS — mỗi câu WAV xử lý riêng; "nó/vậy/thế" mất ngữ cảnh | ❌ LLM tự phỏng đoán |
| Web chat `/api/chat` | ✅ SessionMemoryManager (persist episodes) | ❌ LLM tự phỏng đoán |
| NetChat DM | ✅ Responder catch-up + prefix trích dẫn | ❌ LLM tự phỏng đoán |

Nền tảng tái sử dụng (không tạo mới): SessionMemoryManager (brain.db episodes 2.573 rows), GLM 8765, AlertEngine (cooldown 300s), skill_registry.json convention.

---

## 2. Đã xây + kiểm chứng

### 2.1 ConversationStateManager (`cognition/conversation_state.py`) — G-22

- Per-channel state (`voice`/`web`/`dm`): last_user_text + last_reply + intent + TTL **10 phút**; lưu `data/conversation_state.json` (atomic write, corrupt → khởi lại, không crash).
- `_ANAPHORA_PATTERN`: đại từ tiếng Việt (nó, anh ấy, đó, vậy, thế, nãy, vừa rồi, cũng, tiếp...).
- `build_contextualized_query`: chỉ khi (có đại từ) VÀ (state còn hạn) VÀ (có câu hỏi trước) → bọc `[NGỮ CẢNH lượt trước...]` cho LLM; không bao giờ tự bịa.

### 2.2 SelfQA (`cognition/self_qa.py`) — G-12 / M4-C

6 nhóm regex tiếng Việt (khớp em/bạn/TONY, không khớp "tôi" — anh hỏi về mình): identity / capabilities / location / health / learning / limits. Trả lời **grounded**:
- identity/location từ SelfModelEngine live scan; capabilities đếm verified/unverified thật; health từ snapshot monitoring thật (liệt kê cảnh báo đang có); learning từ CLO checkpoints + candidate_knowledge counts + skill registry; limits từ known_limitations.
- Fail-honest: lỗi đọc dữ liệu → "Em chưa đọc được dữ liệu tự nhận thức lúc này (lỗi: ...)".
- **E2E 5/5 câu trả lời đúng dữ liệu sống**, ví dụ learning: "7 phiên CLO, vòng #7 RUNNING từ 2026-10-27. Tri thức: 1.491 mục anh đã duyệt, 2.979 mục chờ anh duyệt (Q-4). Kỹ năng: 6 đăng ký, 1 sẵn sàng."

### 2.3 Wired vào 2 handler thoại

Thứ tự xử lý mới: **Self-QA → intent (command center) → GLM (có bọc ngữ cảnh nếu có đại từ) → fallback**. Sau khi trả lời: `ConversationStateManager.update("voice", stt_text, reply, intent)` (fire-and-forget). Cả `/voice_command` (wake→mic loa BT) và `/converse` (vòng VAD liên tục) đều có đủ 3 tầng.

### 2.4 M4-B — Learning Health (CLO stall alert)

`HealthMonitor._evaluate_clo_stall()`: session RUNNING > 24h không tiến triển → alert WARNING **edge-trigger** (chỉ bắn khi chuyển trạng thái kẹt↔bình thường); gửi qua AlertEngine THẬT (cooldown + DB + DM); alert_engine giả (test) → `sent=False + suppressed_reason` — không bao giờ khai gửi khi chưa gửi.

**E2E tự nhiên:** cycle 1 sau restart server, alert `selfcare:clo_stalled` WARNING "CLO #7 RUNNING **108h**" → **DM gửi thành công (sent=1, không suppressed)** — bắt đúng kẹt thật đang có, không spam (edge-trigger verified trong test).

### 2.5 Sửa flaky thời gian (lớp lỗi) — `memory/session_manager.py`

`add_message`/`_transition_state` dùng `datetime.now()` riêng lẻ; Windows tick ~15,6ms → `last_activity_at == created_at` khi cùng tick → test so sánh `>` fail ngẫu nhiên (lộ ra trong regression). Sửa gốc: helper `_now_strictly_after(previous)` — nếu clock chưa nhích quá mốc trước thì +1µs. Chạy 10/10 PASS liên tiếp. (Cùng họ lỗi với state_tracker đã sửa ở M4 — pattern này nên rà thêm các file timestamp khác ở M5 phần 2.)

---

## 3. Sự cố trong phiên (trung thực ghi nhận)

- **Server chết ~10:55:52** ngay sau E2E voice đầu (kill đột ngột, do spawn trước đó bằng Popen + DEVNULL mất stderr — kỹ thuật restart của em có lỗi). **Hồi sinh đúng đường chính thống** `KHOI_DONG_24_7.bat` (idempotent + guard chống trùng): đủ 8765/8766 + responder + watchdog + learning daemon sống lại; verify `/api/status`, `/api/health/monitor` (running, cycles 3+), `/api/self/model` OK, responder heartbeat 0s.
- **Edge-TTS flaky toàn đợt (5/5 + 3/3 fail NoAudioReceived)** = G-33 tái diễn — làm chặn E2E loopback audio tiếng Việt sạch; dùng SAPI thay thế nhưng giọng Anh đọc không dấu → STT méo → GLM trả lời trung thực "chưa hiểu". **Bài học: cần Q-3 Piper local fallback**; E2E Self-QA qua mic thật chờ anh test trực tiếp bằng giọng thật (tất cả tầng bên dưới đã verify riêng).

## 4. Tests — bằng chứng số

| Bộ | Kết quả |
|---|---|
| `tests/test_m5_conversation.py` (mới) | **27/27 PASS** |
| Regression FULL | **2.996 passed / 44 skipped / 0 failed (2:38)** — baseline 2.969 → +27 |
| session_manager file (flaky cũ) | 10/10 PASS liên tiếp |

## 5. Ràng buộc tuân thủ

- Không đụng M2 Event Bus, M3, Q-1..Q-5; không tạo DB mới; không đổi voice pipeline/VAD; không barge-in (chờ M5 phần 2 nếu anh duyệt).
- Self-QA chỉ TRẢ LỜI từ dữ liệu — không tự phong trạng thái mới; CLO alert chỉ cảnh báo, không tự sửa learning.
- Không dừng ở tài liệu: 3 module mới + 2 handler wired + 1 fix flaky, tất cả có test + E2E.

## 6. Đề xuất M5 phần 2 (chờ anh duyệt)

1. **M5-B Barge-in** (G-23): cho phép anh ngắt lời em khi em đang phát loa (daemon đóng phát → mở mic).
2. **M5-C Multi-turn memory cho kênh DM**: responder dùng ConversationStateManager để DM cũng hiểu "nó/vậy".
3. **Quan trọng — khuyến nghị duyệt Q-3 (Piper) + Q-4 (R4 verifier)**: Edge-TTS flaky chặn audio thật; 2.979 candidates chờ duyệt đang kẹt nút thắt learning.

Người lập: TONY (netMind Desktop) — 01/11/2026
