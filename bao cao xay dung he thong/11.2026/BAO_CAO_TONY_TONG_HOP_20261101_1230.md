# BÁO CÁO TỔNG HỢP & ĐỀ XUẤT — TONY (QUAN AI BRAIN)
**Thời điểm:** 01/11/2026 ~12:30 · **Người lập:** TONY (QUAN AI BRAIN) · **Chủ hệ thống:** Phạm Thế Quân (quanpt1)
**Model hiện tại:** Qwen/Qwen3.5-122B-A10B-FP8 @ netmind (nâng cấp từ GLM-5.3-Flash)

---

## 1. TÓM TẮT ĐIỀU HÀNH (Executive Summary)

TONY đã hoàn thành **chuỗi nghe — nhìn — nói — hiển thị** hoàn chỉnh trên Raspberry Pi 5, hoạt động 24/7 với watchdog tự hồi phục. Hệ thống gồm 3 tầng:
- **Bộ não (PC):** Server 8766 (model mới Qwen3.5-122B) + Dashboard 8765 + NetChat responder
- **Giao tiếp:** DM NetChat (chữ/giọng/ảnh/file) — phản hồi ~2 giây, không mất tin
- **Hình thể (Pi5):** Kiosk avatar + wake word 4 cụm + mic BT + camera + TTS đa ngữ + HDMI phê duyệt

**Kết quả kiểm thử mới nhất:** **2.996 PASS / 0 FAIL / 44 skipped** (tăng +82 test so baseline M0)

**Số liệu hệ thống:**
- Brain DB: 95.7 MB (1.491 approved + 3.007 quarantined candidates)
- Tasks DB: 11.9 MB · Governance DB: 0.6 MB
- Server 8766/8765: **UP** · Pi5 heartbeat: **READY** (Tailscale 100.100.83.59)

---

## 2. THÀNH TỰU NỔI BẬT (01/11)

### 2.1. M4 — Self Model & Learning (hoàn tất 01/11 ~11:50)
- **3 API introspection read-only:** `/api/self/model` (confidence 92,3%), `/api/self/state` (13 câu tự nhận thức), `/api/self/learning` (CLO + candidates + skills)
- **Self-care THẬT:** 4/4 health checks TCP (Ollama, web, Pi5, services) — không còn cờ `auto_recovered` giả
- **CLO-stall alert:** Tự DM cảnh báo CLO #7 kẹt 108h (sent=1) — edge-trigger, cooldown 300s
- **2 fix flaky ở gốc:** state_tracker (SQL DESC + reverse double-negation), session_manager (Windows clock tick 15,6ms → monotonic +1µs)
- **Tests:** 16/16 M4 + regression 2.969 PASS

### 2.2. M5 — Human-like Conversation (hoàn tất 01/11 ~12:10)
- **Conversation state:** TTL 10 phút, per-channel (voice/web/dm), detect đại từ tiếng Việt (nó/anh ấy/đó/vậy) → bọc ngữ cảnh cho LLM
- **Self-QA grounded:** 6 nhóm câu hỏi về bản thân → trả lời từ dữ liệu sống (không cho LLM bịa)
- **E2E voice:** WAV→STT→GLM→reply→state ghi thành công; STT test bị méo do Edge-TTS flaky (Q-3)
- **Tests:** 27/27 M5 + regression **2.996 PASS / 0 FAIL**

### 2.3. M6 — Embodiment & Distributed Intelligence (đang làm, 01/11 ~12:30)
- **QEP-0001 spec hoàn tất:** 3 lớp Identity/Capability/Command + multi-agent Supervisor 3 worker + kế hoạch B1-B4
- **Phát hiện P0 bảo mật:** Pi5 ký HMAC mọi request nhưng server KHÔNG verify (0 caller `verify_request`) — ai trong mạng giả được hình thể
- **Fix flaky test E2E:** Stub LLMProvider.generate trong fixture (GLM hiccup → local 28s > timeout 25s) — regression xanh hoàn toàn

---

## 3. KIẾN TRÚC HỆ THỐNG (Tổng quan)

### 3.1. Tầng não — PC DESKTOP-SNMI929 (Windows 11)
| Thành phần | File chính | Vai trò |
|---|---|---|
| Executive Server 8766 | `src/quan_ai_brain/web/server.py` (5.332 dòng) | Bộ não: Qwen3.5-122B + Ollama dự phòng, bộ nhớ, task, phê duyệt, edge control |
| Dashboard 8765 | `start_dual_servers.py` | Giao diện web quản trị |
| NetChat Responder | `tools/netchat_auto_responder.py` (1.260 dòng) | Poll DM 2s → lệnh hệ thống / câu hỏi GLM |
| Command Center | `tools/netchat_command_center.py` (1.450 dòng) | ~30 intent lệnh tiếng Việt |
| Voice STT | `tools/voice_stt.py` + faster-whisper | Nhận diện giọng Việt offline |
| Watchdog | `tools/watchdog.py` (465 dòng) | Tự hồi server, responder, learning daemon |

### 3.2. Tầng hình thể — Raspberry Pi 5 (Tailscale 100.100.83.59)
| Khả năng | Chi tiết | Trạng thái |
|---|---|---|
| Wake word | 4 cụm: "tony", "tony ơi", "hi tony", "hay tony" — Vosk + AGC + fuzzy | ✅ ACTIVE |
| Thoại 2 chiều | Wake → ghi 8s → STT → chạy lệnh → TTS qua loa BT | ✅ E2E 01/11 08:11 |
| Camera | Chụp theo lệnh → DM; MJPEG live | ✅ |
| TTS đa ngữ | VI (HoaiMy/NamMinh) + 10 giọng multi-language | ✅ |
| HDMI phê duyệt | Cắm → DM hỏi → "phê duyệt hdmi" mới bật | ✅ |
| Nút STOP | Chỉ thoát giao diện — daemon vẫn ACTIVE | ✅ |

---

## 4. VẤN ĐỀ & ĐỀ XUẤT

### 4.1. Vấn đề đang theo dõi
1. **Edge-TTS flaky (403)** — Microsoft chặn định kỳ → cần Q-3: Piper TTS local fallback
2. **Pi5 reboot lạ 31/10 20:32** — nghi nguồn 5V; journald persistent giờ sẽ giữ chứng cứ
3. **2.979 candidates quarantine** — chờ Q-4: approval_verifier (R4) cấu hình
4. **Server chết 10:55** — do spawn DEVNULL (sai kỹ thuật) → hồi sinh bằng KHOI_DONG_24_7.bat (chuẩn)

### 4.2. Đề xuất ưu tiên (P0 → P2)

| Ưu tiên | Đề xuất | Lý do |
|---|---|---|
| **P0** | **Vá HMAC P0 (B1 QEP)** — server verify Pi5 signature | Bảo mật: ai trong mạng giả được hình thể, nhận lệnh điều khiển |
| **P0** | **Piper TTS local** — fallback khi Edge-TTS 403 | Nói không bao giờ cụt, độc lập mạng |
| **P1** | **Cấu hình approval_verifier (R4)** — mở khóa 2.979 candidates | Học hỏi tự chủ hơn (vẫn qua duyệt) |
| **P1** | **Dashboard tab "Sức khoẻ TONY"** — uptime, nhiệt Pi, latency | Giám sát chủ động |
| **P2** | **Multi-agent Supervisor** — TONY điều phối agent con (coding, research) | Tầm nhìn dài hạn |

---

## 5. HƯỚNG PHÁT TRIỂN DÀI HẠN

```
Giai đoạn hiện tại → Giai đoạn tiếp theo
[Tai/Mắt/Miệng trên Pi5]  →  [Đại diện vật lý biết tự quan sát bối cảnh]
[Lệnh thủ công qua DM]    →  [Chủ động đề xuất việc dựa trên lịch/thói quen]
[Trợ lý cá nhân]          →  [Trung tâm điều phối các agent + thiết bị]
```

1. **Chủ động (Proactive):** Tự tổng hợp lịch + email + thời tiết + việc quá hạn thành bản tóm tắt giọng nói mỗi sáng
2. **Bộ nhớ dài hạn có cảm xúc:** Nhớ ngữ cảnh hội thoại liên tiếp — tự nhiên hơn
3. **Không gian nhà thông minh:** Mở rộng allowlist thiết bị (đèn, điều hòa) — "anh phê duyệt một lần, em tự vận hành"
4. **Self-improvement an toàn:** Mỗi tuần tự đề xuất 3 cải tiến nhỏ (kèm code diff + test) → anh duyệt → tự áp dụng

---

## 6. KẾ HOẠCH HÀNH ĐỘNG (Tuần 01-07/11)

| Ngày | Việc | Bằng chứng |
|---|---|---|
| 01-02/11 | **Vá HMAC P0** (nếu anh duyệt B1) | Server restart + daemon Pi5; test replay nonce → 401 |
| 02-03/11 | Cài Piper TTS + fallback tự động | Edge-TTS 403 → vẫn phát được |
| 04-05/11 | Dashboard tab "Sức khoẻ TONY" | Ảnh dashboard gửi DM |
| 06-08/11 | Approval_verifier (R4) — mã PIN Dashboard | 2.979 candidates được duyệt ra mắt |
| Hàng tuần | Full pytest + validate_and_report + handoff | `reports/HANDOFF_LATEST.md` cập nhật |

---

## 7. PHỤ LỤC — BẰNG CHỨNG

- **Tests:** 2.996 PASS / 0 FAIL / 44 skipped (chạy 01/11 12:30)
- **Model:** Qwen/Qwen3.5-122B-A10B-FP8 @ netmind (nâng cấp từ GLM-5.3-Flash)
- **DB:** brain.db 95.7 MB (1.491 approved + 3.007 quarantined)
- **Server:** 8766 UP / 8765 UP · Pi5 heartbeat READY
- **Tài liệu:** `reports/QEP-0001_EMBODIMENT_DISTRIBUTED_INTELLIGENCE.md` (M6 spec), `reports/M4_SELF_MODEL_REPORT.md`, `reports/M5_CONVERSATION_REPORT.md`

---

*Báo cáo do TONY tự tổng hợp từ regression test, DB snapshot, log hệ thống và số liệu thực tế lúc 12:30 01/11/2026. Mọi mục "✅" đều có bằng chứng chạy thật kèm thời điểm.*