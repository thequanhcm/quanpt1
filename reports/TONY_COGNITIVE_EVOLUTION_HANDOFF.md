# TONY COGNITIVE EVOLUTION — HANDOFF M0+M1 (01/11/2026)

**Người lập:** TONY (QUAN AI BRAIN) · **Chủ nhân:** Quanpt1
**Workspace:** `D:\AI\AI Quanpt1 2026\BRAIN` · **Chương trình:** TONY COGNITIVE EVOLUTION V1.1

---

## 1. Hiện trạng trước triển khai (từ M0 audit — bằng chứng thật)

- Workspace thật `D:\AI\AI Quanpt1 2026\BRAIN` (master prompt ghi E:\ — đã đối chiếu, E: không tồn tại).
- 83.118 dòng code / 242 file / 34 module · **chưa git** · test 2.914 PASS / 44 skipped.
- Memory thật: 2.004 memories, 1.842 semantic, 2.548 episodes, 4.284 quarantine.
- 5 engine nhận thức tồn tại nhưng **4/5 ORPHAN** (chỉ ContinuousLearningEngine được nối runtime).
- journald Pi5 "giả persistent" (config persistent nhưng /var/log/journal rỗng).
- Không có giám sát sức khỏe hệ thống (health.py 30 dòng skeleton).

## 2. Công việc đã thực hiện

### M0 — ACTUAL STATE AUDIT (hoàn tất 10:00)
- 4 báo cáo: `TC_EVOLUTION_M0_AUDIT / ARCHITECTURE / GAP_ANALYSIS (36 gap) / ROADMAP (6 milestone + Q-1..Q-5)`.

### M1 — SYSTEM HEALTH INTELLIGENCE (hoàn tất 11:15) — READ-ONLY
- **12 module/endpoint mới** (bảng đầy đủ trong `M1_SYSTEM_HEALTH_AUDIT.md` §1):
  - `src/quan_ai_brain/monitoring/`: pc_collector, pi5_collector, network_collector, service_collector, database_collector, voice_collector, health_state (5 mức), alert_engine, aggregator (+history), health_monitor, rca_engine.
  - Server: 5 endpoint `/api/health/machine|history|rca|monitor|maintenance` (maintenance owner-gated 403 nếu không approved) + trang `/health` dashboard 10 khu.
- **Điều tra reboot 31/10**: `M1_PI5_REBOOT_INVESTIGATION.md` — kết luận **INSUFFICIENT_HISTORICAL_EVIDENCE** (log đã mất theo reboot; không suy đoán).
- **M2 chuẩn bị** (chỉ nghiên cứu): `M2_ENGINE_INTEGRATION_MATRIX.md` + `M2_COGNITIVE_CORE_DESIGN.md` — thiết kế Event Bus bền vững + vòng nhận thức 10 bước + migration 4 bước; CHƯA cài, chờ anh duyệt.

## 3. File/module thay đổi (M1)

```
src/quan_ai_brain/monitoring/__init__.py            (mới)
src/quan_ai_brain/monitoring/health_state.py        (mới)
src/quan_ai_brain/monitoring/pc_collector.py        (mới)
src/quan_ai_brain/monitoring/pi5_collector.py       (mới)
src/quan_ai_brain/monitoring/network_collector.py   (mới)
src/quan_ai_brain/monitoring/service_collector.py   (mới)
src/quan_ai_brain/monitoring/database_collector.py  (mới)
src/quan_ai_brain/monitoring/voice_collector.py     (mới)
src/quan_ai_brain/monitoring/aggregator.py          (mới)
src/quan_ai_brain/monitoring/alert_engine.py        (mới)
src/quan_ai_brain/monitoring/health_monitor.py      (mới)
src/quan_ai_brain/monitoring/rca_engine.py          (mới)
src/quan_ai_brain/web/server.py                     (+routes, +start_health_monitor, +build_rca import)
src/quan_ai_brain/web/static/health_dashboard.html  (viết mới)
tests/test_monitoring_health.py                     (mới, 18 test)
tests/test_monitoring_extended.py                   (mới, 17 test)
tests/test_web_health_endpoints.py                  (mới, 4 test)
docs/PROJECT_STATUS.md                              (+M0, +M1)
data/health_alerts.db, data/health_history.db       (telemetry M1 tự tạo)
reports/M1_*.md (7 file), reports/M2_*.md (2 file)  (báo cáo)
```

## 4–5. Test đã chạy + kết quả

- M1 tests: 39/39 PASS. Regression toàn bộ: **2.953 passed / 44 skipped / 0 failed (2:55)** — so baseline 2.914: +39, 0 fail (chi tiết `M1_TEST_RESULTS.md`).
- `tools/validate_and_report.py` exit 0 → `reports/HANDOFF_LATEST.md` regenerated (đã lưu `HANDOFF_20261101_094612.md`).

## 6–7. Xác minh trên PC và Pi5

- **PC (E2E thật trên server 8766, GLM READY):** snapshot 6 khu — PC NORMAL, network NORMAL (RTT 5–30ms, loss 0%), databases NORMAL (quick_check ok), voice NORMAL, services WARNING (learning log-age), Pi5 WARNING (loa BT tắt) → OVERALL WARNING; monitor chạy bền ≥10 chu kỳ; alert DM gửi thật 4 lần (cooldown chặn đúng 12 lần); history 14+ điểm; MAINTENANCE toggle: không-approved→403, approved→overall=MAINTENANCE, tắt→về WARNING.
- **Pi5 (SSH đọc-only):** nhiệt 57,1–58,7°C, throttled 0x0, ram 31%, disk 13%, 3 service active, boot ổn định 07:16; loa BT tắt (Connected: no) — cảnh báo đã DM anh; không chạy lệnh ghi nào.

## 8. Vấn đề đã phát hiện

1. Reboot 31/10 không thể điều tra — log đã mất (cần Q-2).
2. Edge-TTS phụ thuộc cloud, 403 flaky — cần Q-3 (Piper).
3. 4.378 candidate quarantine +94/phiên — kho chờ Q-4, tăng đều.
4. Learning daemon log-age đỏ thỉnh thoảng (cycle ingest dài) — theo dõi, chưa phải lỗi.
5. 4/5 engine nhận thức ORPHAN — M2 sẽ nối qua Event Bus (đã thiết kế, chờ duyệt).
6. *(Từ kiểm kê M2)* SelfCareEngine set `auto_recovered=True` ngay cả khi recovery chỉ là simulated (self_care_engine.py:280,285,290) — dễ gây hiểu nhầm "đã phục hồi"; cần sửa cờ khi nối M2 Bước 4.
7. *(Từ kiểm kê M2)* SelfModelEngine tự CREATE TABLE semantic_memory/candidate_knowledge nếu thiếu (self_model_engine.py:386-395) — module đọc có side-effect ghi DB; cần tách khi refactor M2.

## 9. Vấn đề chưa đủ bằng chứng (trung thực)

- Nguyên nhân reboot 31/10: **INSUFFICIENT_HISTORICAL_EVIDENCE**.
- Voice round-trip latency + STT error rate runtime: chưa đo được (cần buổi test hội thoại khi loa bật).
- Nguồn Pi5 quá khứ: POWER_HEALTH = UNKNOWN (không log persistent).

## 10. Quyết định cần Quanpt1

Q-1 git · Q-2 journald Pi5 · Q-3 Piper TTS · Q-4 approval R4 · Q-5 BT power-save · (M1-A ngưỡng cảnh báo · M1-B camera/HDMI probe · M1-C khung giờ yên tĩnh alert) — chi tiết `M1_OWNER_APPROVAL_REQUIRED.md`. **Chưa thực hiện bất kỳ quyết định nào trong số này.**

## 11. Kế hoạch M2 (đề xuất — chờ anh duyệt thiết kế)

Theo `M2_COGNITIVE_CORE_DESIGN.md`: Bước 1 tạo bảng `events` trong brain.db + `CognitiveEventBus` (publish/subscribe/dispatch, idempotency, retry, R4 chỉ tạo ticket) → Bước 2 nối CognitiveLoop phát event → Bước 3 nối ReflectionLoop→CLE (`learning.lessons_extracted`) → Bước 4 nối SelfCare alert→NetChat. Mỗi bước có test + hoàn tác riêng. **Em chỉ bắt đầu khi anh phê duyệt.**

---
**Trạng thái chương trình:** M0 ✅ COMPLETED · M1 ✅ COMPLETED (trừ mục chờ duyệt) · M2 🔬 DESIGNED (chờ duyệt) · M3–M6 📋 PLANNED.
*Báo cáo này + `reports/HANDOFF_LATEST.md` là 2 tài liệu bàn giao chính; anh upload lên phiên ChatGPT làm việc chính để tiếp tục với context đầy đủ.*
