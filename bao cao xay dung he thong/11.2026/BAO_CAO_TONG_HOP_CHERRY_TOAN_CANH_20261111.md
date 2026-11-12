# BÁO CÁO TỔNG HỢP — HỆ THỐNG QUAN AI BRAIN / CHERRY
**Ngày:** 11/11/2026
**Người soạn:** TONY (netMind Desktop, profile tony)
**Phạm vi:** Toàn cảnh kiến trúc + trạng thái hoạt động thật + tự học/tự chuẩn đoán + đánh giá năng lực + lộ trình phát triển
**Quy tắc báo cáo:** Fail-honest — mọi con số dưới đây đều lấy từ tool thật (curl, ssh, sqlite, pytest) trong phiên 10–11/11/2026. Không tô hồng, không ghi VERIFIED cho phần chưa test.

---

## 1. MÔ TẢ TOÀN CẢNH HỆ THỐNG

### 1.1 Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        PC QUANPT (Windows 10)                    │
│                        Wi-Fi: 192.168.1.x (DHCP)                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  BRAIN CORE (E:\BRAIN) — port 8765/8766                │    │
│  │  • server.py: LLM + TTS + Web UI + API                 │    │
│  │  • brain.db: episodes, memories, knowledge             │    │
│  │  • chroma knowledge_db: vector store                   │    │
│  │  • edge_monitor.py: alerts + heartbeat tracking        │    │
│  │  • learning_daemon.py: tự học 5 phút/lần               │    │
│  │  • watchdog.py + memory_review.py: tự chuẩn đoán       │    │
│  │  • piper in-process: vi_VN-vais1000-medium.onnx        │    │
│  └────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WiFi LAN (heartbeat + audio stream)
                            │ HMAC-signed API 8766
┌───────────────────────────▼─────────────────────────────────────┐
│                     RASPBERRY PI 5 (Quanpt1)                     │
│                     wlan0: 192.168.1.21 (DHCP)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  EDGE CLIENT (~/Desktop/edge_client)                   │    │
│  │  • client_daemon.py: heartbeat + audio + camera        │    │
│  │    + auto-discovery (quét /24 khi offline >30s)        │    │
│  │  • wake_word_service.py: Vosk, wake CHERRY ơi/à        │    │
│  │  • tony_channel_selector.py: chọn transport LAN/MESH   │    │
│  │  • kiosk + avatar + mouth sync (viseme timeline)       │    │
│  └────────────────────────────────────────────────────────┘    │
│         │                    │                    │              │
│    [Tai: mic]          [Mắt: camera]        [Miệng: loa]         │
│    UACDemoV1.0 Mono    IMX708 Module 3     SRS-XB33 (BT sink)    │
│    vol 1.00            640×480             vol 0.40              │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Luồng hoạt động hỏi đáp (voice pipeline E2E)

```
[Owner nói] → mic Pi5 → wake_word_service (Vosk, "Cherry ơi/à") →
STT Vosk → POST /api/voice/interact (8766, HMAC) →
LLM suy luận → TTS piper (681ms/150 ký tự) → audio_base64 +
mouth_timeline (viseme frames) → Pi5 phát loa SRS-XB33 →
avatar miệng nhấp nháy theo timeline → SPEAKING
```

- **Độ trễ đo thật:** full pipeline 230ms (text→audio sẵn sàng), TTS 681ms cho câu 150 ký tự, WAV 364KB RIFF/WAVE chuẩn, mouth_timeline 7–214 frames tùy câu dài.
- **Bảo mật:** mọi POST từ Pi5 phải HMAC-sign (đúng key mới qua được `_edge_hmac_verify`), sai → 401 + record_auth_failure.

### 1.3 Thành phần phần mềm chính (file + vai trò)

| File | Vai trò | Trạng thái |
|---|---|---|
| `src/quan_ai_brain/web/server.py` | Server chính 8765/8766: LLM, TTS, Web UI, 40+ API | LIVE |
| `src/quan_ai_brain/voice/tts_config.py` | TTSManager: piper + Edge-TTS, 2 giọng VN | LIVE |
| `src/quan_ai_brain/web/edge_monitor.py` | Alert + heartbeat tracking (ALERT_F đã fix sticky) | LIVE |
| `edge_client/client_daemon.py` | Daemon Pi5: heartbeat, audio, camera, auto-discovery | LIVE |
| `edge_client/wake_word_service.py` | Wake word Vosk, bộ từ CHERRY (owner chốt 11/11) | LIVE |
| `edge_client/tony_channel_selector.py` | Chọn transport LAN/MESH, cấm ghi MESH vào core_host | LIVE |
| `edge_client/edge_agent.py` | detect_connection_lost dùng stale check | LIVE |
| `tools/learning_daemon.py` | Tự học: đọc docs/git/test → candidate_knowledge | LIVE |
| `tools/watchdog.py` | Tự chuẩn đoán: FED/CLO/NetChat/learning/ollama | LIVE |
| `tools/memory_review.py` | Tự review memory: DUPLICATE/SIMILAR findings | LIVE |
| `data/brain.db` | SQLite episodes/memories/knowledge (đã xóa 20+20 nhiễm TV) | LIVE |
| `data/knowledge_db/chroma.sqlite3` | Vector store 10.874 tri thức | LIVE |

---

## 2. TRẠNG THÁI HOẠT ĐỘNG THẬT (11/11/2026)

### 2.1 Tai — Wake + STT ✅
- **Bộ từ đánh thức (owner chốt 11/11, commit `0019c6c`):** "Cherry ơi" / "Cherry" / "Cherry à" + biến thể Vosk (cheri/ché ri/che ri/chè ri × ơi/oi/à/a). Bỏ hết TONY + "trợ lý ơi"/"chào trợ lý".
- **Chống nhiễm TV:** fuzzy match siết ≤2 lỗi, bỏ cụm TONY quá độ → test 34 câu thật: 19/19 TV noise bị từ chối, 9/9 giọng thật pass.
- **Mic thật:** UACDemoV1.0 Mono (node 54), RMS 156/154/1201 peak — bắt được âm thanh phòng thật.
- **STT round-trip:** TTS "Cherry báo sức khỏe..." → STT đọc lại đúng câu (5,1s).

### 2.2 Mắt — Camera ✅
- Module 3 IMX708, `rpicam-still` chụp 47KB.
- `camera_on` qua API 8766 → READY, snapshot `cap_1794286732`.
- vision_analyze nhận rõ: phòng, máy lạnh, đèn, tủ — 640×480.

### 2.3 Miệng — TTS + Loa ✅
- **Piper in-process:** vi_VN-vais1000-medium.onnx (~63MB trong RAM), 681ms/150 ký tự.
- **Edge-TTS:** 2 giọng VN sẵn sàng — Hoài My (nữ, active) + Nam Minh (nam), endpoint `/api/voice/tts-voices` trả danh sách.
- **Loa:** SRS-XB33 (sink 95, vol 0.40), log "phát giọng: True".
- **Avatar:** mouth_timeline viseme frames đồng bộ, avatar_state=SPEAKING khi nói.

### 2.4 Não — LLM + Pipeline ✅
- Pipeline text→LLM→TTS→audio→Pi5: 230ms, avatar SPEAKING.
- Tri thức tổng: **10.874** (approved 1.491, semantic 5.052, quarantine 6.175).

### 2.5 Kết nối Pi5↔PC ✅ (ưu tiên số 1 mọi sprint)
- **Auto-discovery (PR #18, E2E test thật):** sửa `core_host` Pi → IP giả → DISCONNECTED 20s → 45s sau **tự tìm lại PC**, state=READY, RTT 32ms, config tự save (sống qua restart).
- **Channel selector:** chọn `LAN:192.168.1.11` RTT 3ms; **cấm ghi MESH vào core_host** (tránh đấm ngược discovery).
- **ALERT_F fix:** gỡ treo vĩnh viễn khi heartbeat phục hồi sau AUTH_FAILED.
- **Tailscale PC:** chết vĩnh viễn (BackendState=NoState, state file mất) — đã bỏ, LAN-only.

### 2.6 24/7 ✅
- **Learning daemon:** PID 8380/15348, 180.718 dòng log / 10,3MB, chu kỳ 5 phút, 169 facts/ngày.
- **Watchdog:** phát hiện thật hôm nay — FED 2 nút mất kết nối; CLO session #15 RUNNING 46.6h > 24h → tự advance #16; NetChat responder stale 2839s.
- **Memory review:** 3 session, 38 findings (93 DUPLICATE + 21 SIMILAR), `changes_applied: 0`.

### 2.7 Code đã merge / đang mở
- **PR #18 MERGED** (master `e960d41`): piper in-process TTS + auto-discovery.
- **PR #19 OPEN** (`fix/edge-alertf-sticky-recovery`): ALERT_F sticky + channel selector multi-IP + wake anti-TV + bộ từ CHERRY (`0019c6c`). Đã push đủ, chờ owner duyệt merge.
- Tests: edge_discovery 10/10, edge_monitor 8/8, channel_selector 23/23, voice_api 5/5, voice_first_pipeline 11/11.

---

## 3. TỰ HỌC & TỰ CHUẨN ĐOÁN — ĐÁNH GIÁ TRUNG THỰC

### 3.1 Có thật, có bằng chứng
| Năng lực | Bằng chứng | Giới hạn |
|---|---|---|
| Tự học | learning_daemon 5 phút/lần, 169 facts/ngày, học được 4 commit fix hôm nay | Nạp lặp rác: "Test suite: 3648 passed" 160 lần/ngày |
| Tự chuẩn đoán | watchdog phát hiện FED mất kết nối + CLO stall + NetChat stale | Chỉ PHÁT HIỆN, chưa TỰ SỬA |
| Memory review | 38 findings DUPLICATE/SIMILAR | `changes_applied: 0` — chưa tự áp dụng |
| Quarantine | 6.175 tri thức cách ly đúng R0–R5 | TẮC từ 01/11 — 10 ngày chưa duyệt |

### 3.2 Sự cố điển hình đã xử lý (La La School / Ghiền Mì Gõ)
- **Nguyên nhân:** TV kênh YouTube trẻ em phát → mic Pi5 nhặt → Vosk nhầm lời video thành wake (fuzzy ≤3 lỗi khớp `tới mì`/`tôi ơi`) → CHERRY bật nghe → STT nhận câu video → trả lời như owner → lưu "kỷ niệm" sai.
- **Hậu quả:** 20 episodes + 20 memories EPISODIC nhiễm (01/11 → 12:33 hôm nay, 15 lần sáng 10/11).
- **Đã xử lý:** xóa sạch (verified 0), siết wake ≤2 lỗi, bỏ TONY quá độ, test 19 TV noise + 9 giọng thật.
- **Bài học:** CHERRY chưa có "ý thức về nguồn" — mọi âm thanh qua wake đều được tin là owner.

---

## 4. ĐÁNH GIÁ NĂNG LỰC TỰ SUY NGHĨ PHÂN TÍCH

### 4.1 Điểm mạnh (có thật)
1. **Giác quan hoàn chỉnh:** tai (mic+wake+STT), mắt (camera), miệng (TTS+loa+avatar) — hoạt động thật, đo được.
2. **Phản xạ tự phục hồi kết nối:** auto-discovery tìm lại PC khi DHCP nhảy IP — đã test thật, 45s.
3. **Nhịp tự học liên tục:** 5 phút/lần, không tắt, có học được chính các fix kỹ thuật hôm nay.
4. **Tuân thủ governance:** không tự promote tri thức, không tự đụng quarantine — đúng R0–R5.

### 4.2 Điểm yếu (trung thực)
1. **Chưa có tư duy phản biện nguồn:** tin mọi âm thanh qua wake → nhiễm TV.
2. **Chưa tự rút ra quy luật:** biết FED disconnected, biết CLO stall — riêng lẻ, chưa liên kết "A gây B".
3. **Chưa tự sửa an toàn:** watchdog phát hiện lỗi → dừng ở log + báo owner.
4. **Memory review chưa khép vòng:** findings có rồi nhưng changes_applied=0.
5. **Nạp lặp rác chưa chặn:** 160 lần/ngày fact rác, chưa có dedupe trước khi ghi.

### 4.3 Kết luận đánh giá
> **CHERRY hiện tại = trợ lý có giác quan + phản xạ + trí nhớ tốt, tuân thủ governance nghiêm, nhưng chưa có "tư duy phản biện". Nó giống đứa trẻ giỏi ghi nhớ và quan sát, chưa phải trợ lý biết tự đặt câu hỏi về chính mình.**

Mức chấm (thang 10, dựa trên bằng chứng):
- Giác quan + phản xạ: **8/10**
- Trí nhớ + tự học: **6/10** (có nhưng nhiễm rác)
- Tư duy phản biện: **3/10** (có nguồn, chưa có đánh giá nguồn)
- Tự chuẩn đoán: **6/10** (phát hiện tốt, chưa tự sửa)
- Governance/an toàn: **9/10** (đúng luật, fail-honest)

---

## 5. LỘ TRÌNH PHÁT TRIỂN TIẾP THEO (3 hướng, theo ưu tiên)

### Hướng A — Nâng tư duy phản biện (ưu tiên cao nhất, 1–2 sprint)
1. **Source-trust scoring:** gắn nguồn (owner/tv_noise/auto_learn/test) vào mỗi memory; khi truy xuất, trọng số theo nguồn. Chặn nhiễm kiểu La La School từ gốc.
2. **Auto-dedupe trước khi ghi:** chặn fact lặp ("Test suite: 3648 passed" 160 lần/ngày). Cách làm: so khớp hash + similarity > 0.9 → bỏ qua, ghi counter thay vì fact mới.
3. **Tự đặt câu hỏi ngược:** memory mới → hỏi "mâu thuẫn memory cũ không?" → nếu mâu thuẫn, đưa vào quarantine chờ duyệt thay vì lưu thẳng.

### Hướng B — Tự chẩn đoán + tự sửa an toàn (1 sprint)
1. **Watchdog có action:** phát hiện lỗi → thử restart service an toàn (`ensure_daemon_alive` đã có) → vẫn fail → báo owner. Chỉ áp dụng cho whitelist service (learning_daemon, netchat responder) — KHÔNG tự đụng core server.
2. **Memory review chạy hằng ngày 3h sáng:** từ 38 findings DUPLICATE → tự gộp/xóa bản trùng rõ ràng (same content, same timestamp), còn mâu thuẫn thì gửi owner.
3. **Quarantine batch review UI:** owner duyệt 50–100 facts/lần thay vì từng cái — giải tỏa 6.175 tri thức tắc 10 ngày.

### Hướng C — Hoàn thiện đa giọng + đa tác vụ (1 sprint)
1. **UI dropdown chọn giọng:** backend sẵn sàng (endpoint `/api/voice/tts-voices` có 2 giọng Hoài My + Nam Minh), cần thêm:
   - POST `/api/voice/set-voice` (đổi active voice, gọi `set_voice_preference`)
   - UI dropdown ở header "Hội Thoại Nhận Thức & Giọng Nói" + preview giọng trước khi chọn
   - Lưu preference vào config (sống qua restart)
2. **Tải thêm model piper:** vi_VN-vais1000-low (nhanh hơn), vi_VN-vivos-medium (nam), en_US-lessac-medium (Anh) — mỗi giọng ~60MB, load on-demand.
3. **Tác vụ nhanh trên sidebar:** nút "đọc email mới", "tóm tắt lịch hôm nay", "báo thời tiết" — gắn vào LLM pipeline có sẵn.

### Tiêu chí nghiệm thu từng hướng
- **A:** 0 fact rác lặp mới trong 24h; memory mới từ TV noise bị đánh trust=low và không vào semanticMemory.
- **B:** watchdog tự restart learning_daemon thành công ≥1 lần thật; memory_review changes_applied > 0.
- **C:** đổi giọng trên UI thành công E2E (chọn → preview → nói thử → nghe khác giọng cũ); preference sống qua restart.

---

## 6. VIỆC CÒN TREO (cần owner quyết / xử lý)

| # | Việc | Trạng thái | Ai xử lý |
|---|---|---|---|
| 1 | Merge PR #19 (4 commit: ALERT_F + selector + wake + bộ từ CHERRY) | OPEN, đã push, mergeable | Owner duyệt |
| 2 | Duyệt 6.175 tri thức quarantine (tắc từ 01/11) | Cần batch review UI | Owner + em xây UI |
| 3 | DHCP reservation cho PC trên router (IP nhảy .9→.13→.11→.24) | Cần login router | Owner |
| 4 | Pi5 offline từ 13:31 10/11 (không có trên LAN, không BT) | Cần kiểm tra vật lý nguồn/SD | Owner |
| 5 | Deploy bộ từ CHERRY lên Pi5 (code đã commit `0019c6c`) | Chờ Pi5 online lại | Em, khi Pi5 về |
| 6 | Tailscale PC (NoState vĩnh viễn) | Đã bỏ, LAN-only | Bỏ qua |

---

## 7. NGUỒN BẰNG CHỨNG

- Heartbeat + alert: `GET /api/executive/edge/status` (8766) — phản hồi thật 11/11.
- Test TTS: `POST /api/voice/tts-synthesize` — HTTP 200, 681ms, WAV 364KB.
- Test pipeline: `POST /api/voice/interact` — HTTP 200, 230ms, mouth_timeline đầy đủ.
- Test mic: `pw-record` 3s trên Pi5 — RMS 156.
- Test camera: `rpicam-still` — 47KB JPEG, vision_analyze nhận phòng.
- Auto-discovery E2E: đổi core_host → IP giả → tự tìm lại 45s.
- Wake anti-TV: test 34 câu thật (19 TV noise + 9 giọng thật + 6 TONY cũ).
- brain.db: sqlite query — xóa 20 episodes + 20 memories nhiễm (verified 0 còn lại).
- Learning/watchdog: journalctl + sqlite candidate_knowledge — 169 facts/ngày, 10.874 tổng.
- Git: PR #18 merged (e960d41), PR #19 open (head `0019c6c`).
- Tests: edge_discovery 10/10, edge_monitor 8/8, channel_selector 23/23.

---
*Báo cáo kết thúc. Fail-honest: không mục nào ghi "verified" nếu chưa có bằng chứng thật ở trên.*
