# CHERRY COGNITIVE GAP ANALYSIS — hiện trạng 11/11/2026 vs mục tiêu Cognitive Core
**Phương pháp:** số liệu đo THẬT ngày 11/11 (TASK A re-inspection) + đọc code trực tiếp (không dùng số cũ nếu khác).
**Quy ước:** ✅ có bằng chứng đo được | 🟡 có nền nhưng thiếu | ❌ chưa có.

---

## A. Re-inspection nhanh (khác gì báo cáo 11/11)

| Hạng mục | Báo cáo 11/11 | Đo thật 11/11 tối (lần này) | Đánh giá |
|---|---|---|---|
| PR #19 | OPEN 4 commits | **OPEN 5 commits** — head `348622b` (feat đa giọng + fallback piper) mới push; mergeable=true | Đã cập nhật |
| Pi5 | Offline từ 10/11 13:31 | Vẫn DISCONNECTED, ping .21 không phản hồi, ALERT_A WARNING active | Không đổi |
| Dual servers | LIVE | 8765/8766 HTTP 200 (2 lệnh riêng biệt — 2 bản sống) | OK |
| Health tổng | HEALTHY (trước) | **DEGRADED** — `ollama_daemon: DISABLED` (đã gỡ theo quyết định owner 02/11 — cảnh báo cũ, không phải sự cố mới) | Ghi nhận |
| Learning daemon | LIVE PID 8380/15348 | **4 PID** (8380, 15348, 18440, 21920) — **2 instance trùng** (venv + system python), mỗi cycle 13.3s, `6459 facts ingested / 0 consolidated` | ⚠ Phase 0 dọn |
| Watchdog | LIVE | LIVE (log 14 phút trước, PID 13452/11788) | OK |
| Quarantine | 6.175 | **6.231 quarantined** (+56 trong ~4h), approved 1.491, semantic 5.052 | Tắc tiếp diễn |
| Nạp lặp rác | "3648 passed" 160 lần/ngày | **"Test suite: 3648 passed" × 695 + "3556" × 488 + "3442" × 311** trong quarantine | Xấu hơn số cũ |
| Semantic dup | ~chưa đo | **88 nhóm statement trùng** trong semantic_memory | Mới phát hiện |
| Backup | có 2AM | Task chạy 20:00 (manual?) result=2147946720 (không phải 0 — cần xem log); backup DB mới nhất **09/11** (102.6MB, integrity=ok, 3.034 episodes) | ⚠ gap 2 ngày |
| knowledge_units (V9) | chưa nêu | **148 EXTRACTED** — kho riêng của reasoning V9, GẦN TRỐNG so với 10.874 | Gap lớn Phase 2 |
| Tests | 27 passed TTS | full suite đang chạy (199 file) — kết quả ở TASK A report | Đang chạy |

## B. Ma trận gap 8 thành phần Cognitive Core

### 4.1 Perception Engine — 🟡 50%
- ✅ Có: voice/STT/camera/system input pipeline đầy đủ; timestamp + nguồn có ở telemetry.
- ❌ Thiếu: `PerceptionFrame` chuẩn hoá; phân biệt DIRECT vs INFERRED tại biên; **speaker assumption=UNKNOWN** (wake = owner đang là mặc định ngầm → nguyên nhân La La School).

### 4.2 Source & Trust Engine — 🟡 40%
- ✅ Có: FactLevel 6 bậc (`taxonomy.py`: FACT/USER_PROVIDED/VERIFIED/OBSERVED/INFERENCE/QUARANTINED); promotion fail-closed R4; HMAC xác thực Pi5; SOURCE REFERENCES AUDIT trong context builder.
- ❌ Thiếu: trust level 6 bậc master prompt (OWNER_VERIFIED…UNTRUSTED) chưa map — taxonomy hiện dùng "verification" chứ không phải "trust nguồn"; không có Source ID + trust tag đi kèm memory voice; **voice interact không hỏi "ai nói"** (0 hits speaker/voiceprint trong wake_word_service).

### 4.3 Working Memory — 🟡 45%
- ✅ Có: `session_memory.py` + ConversationStateManager (multi-turn DM + voice đã wire); cognitive_state.py có CognitiveState in-memory (claims/hypotheses/uncertainties).
- ❌ Thiếu: working memory SESSION-scoped chuẩn (pending questions, contradictions, decisions, expiry, persist/recovery ra disk); chưa nối CognitiveState vào từng lượt chat/voice thật.

### 4.4 World Model — ❌ 15%
- ✅ Có: dữ liệu thô nhiều nguồn (edge status, health, devices snapshot qua EdgeAgent UDR-1).
- ❌ Thiếu: mô hình entity thống nhất (people/devices/modules/network/events), state_current vs state_last_verified, quan hệ sự kiện. Chưa có file nào tên world_model.

### 4.5 Self Model — 🟡 65% (mạnh nhất hiện có)
- ✅ Có: `self_model_engine.py` (562 dòng) + SelfQA 11 câu wired DM thật; CognitiveSelfAssessment trả EVIDENCE_BOUNDED + invariants R4/R5 thật (đo 11/11); phân biệt verified/unverified capabilities.
- ❌ Thiếu: self_state_monitor chu kỳ (theo dõi liên tục); UNKNOWN vs LAST_VERIFIED tường minh từng module; "chờ owner quyết định" mới đọc approvals chứ chưa đọc quarantine backlog; phản biện bằng chứng trái nhận định cũ chưa test.

### 4.6 Reasoning Engine — 🟡 55% (nền V9 tốt nhưng không ăn được kho lớn)
- ✅ Có: `logical_reasoning.py` V9 — 8/9 bước master prompt có khung (problem→evidence→hypotheses→support/against→missing→conclusion A/B/C→refs); chống vòng tròn bằng chứng cùng nguồn; **đã trả đúng "Không đủ bằng chứng" khi retrieval trống** (E2E thật 11/11); confidence_breakdown cảnh báo không hiệu chuẩn đúng §3.6.
- ❌ Thiếu (gap NGHIÊM TRỌNG đo được): retrieval CHỈ đọc `knowledge_units` (148 rows) — không thấy semantic_memory (5.052) lẫn chroma (4.790 embeddings, 10.874 tri thức) → câu hỏi thật "Pi5 kết nối với PC qua gì?" trả 0 evidence dù kho có dữ liệu liên quan; causal_reasoner riêng chưa có (guard "không kết luận từ đồng thời" chưa viết); uncertainty_estimator chưa có; multi-hypothesis chưa chạy trên vấn đề thật (Pi5 mất kết nối — pipeline tự động) mà chỉ qua API thủ công.

### 4.7 Goal & Planning — 🟡 60%
- ✅ Có: PlanOrchestrator + DurableTaskRegistry + task lifecycle DEOM M2 (11 trạng thái) + Task Verifier fail-honest (COMPLETED_UNVERIFIED mặc định) + work queue 4 bậc + NL intake VN; governance/policy.py R0–R5 thật.
- ❌ Thiếu: action_policy.py tập trung map reasoning-decision → risk level; rollback bắt buộc cho R3; wire "kết quả reasoning có cấu trúc → plan" chưa có.

### 4.8 Metacognition — 🟡 35%
- ✅ Có: `MetacognitiveEvaluation` + `CognitiveState.evaluate_metacognition()` (data model V4); `reflection.py` (317 dòng — nhưng cho CLO learning sessions, không phải per-task); adversarial_cognition tests.
- ❌ Thiếu: engine chạy SAU nhiệm vụ quan trọng theo 10 câu master prompt; lưu reflection có audit; đo "prediction_matched_outcome"; không có chỉ số calibr

ation nào được đo thật.

### Cognitive Loop — 🟡 50%
- ✅ Có: `cognitive_loop.py` 479 dòng + CLO sessions; 4 kết quả hợp lệ có 3 (ANSWER/ASK/WAIT) qua V9; "chưa đủ dữ liệu" hoạt động thật.
- ❌ Thiếu: ACT có permission_check + outcome verification khép vòng; Cognitive Session ID chuẩn `COG-…` chưa có; evidence record per-session chưa có.

## C. Gap kiểm thử & benchmark — ❌ 20%
- ✅ Có: 199 test files; test_cognitive_state_v4; test_adversarial_cognition; test_v31_conflict_duplicate; benchmark_v21_performance (hiệu năng, không phải nhận thức); anti-self-congratulation test (UAIIF S4).
- ❌ Thiếu: CHERRY COGNITIVE BENCHMARK V1 đủ 10 nhóm (source recognition / adversarial audio / memory integrity / contradiction / multi-hypothesis / causal / self-state accuracy / uncertainty calibration / metacognitive reflection / governance safety); test tái lập sự cố TV noise như benchmark case; phân biệt "đúng vì hiểu vs đúng vì ghi nhớ vs may mắn"; bộ dataset test đối kháng riêng.

## D. Gap vận hành (Phase 0 phải dọn trước)
1. **Dual learning daemon** (2 instance × mỗi cái 1 cycle/5 phút) — trùng ingested facts, tạo rác.
2. **Nạp lặp chưa chặn**: 1.494 quarantine hàng "test suite passed" (3648/3556/3442) — dedupe phải ở WRITE path (skill đã ghi pattern `skip_duplicates` của ingestion engine — kiểm chứng Phase 0).
3. **Semantic dup 88 nhóm** — cần dedupe cẩn thận (backup trước, archive không xóa — theo skill pattern 10/27).
4. **Backup gap**: DB backup mới nhất 09/11; task 2AM result≠0 20/11 — verify log + fix nếu chết.
5. **Quarantine 6.231 tắc** — cần batch review UI/flow (Hướng B của báo cáo 11/11, chưa làm).
6. **Memory review changes_applied=0** từ 07/11 (session mới nhất rev_77e4b6aa98f9) — vòng review có findings nhưng không áp dụng.
7. **Pi5 offline vật lý** — mọi test E2E edge phải đánh dấu BLOCKED, không giả.

## E. Ưu tiên gap (đưa vào implementation plan)
| # | Gap | Phase | Lý do ưu tiên |
|---|---|---|---|
| 1 | Retrieval reasoning nối 10.874 tri thức | Phase 2 (đầu tiên nhất) | Không nối → mọi reasoning đều "không đủ bằng chứng" = cognitive core vô dụng trên data thật |
| 2 | Trust engine + memory guard (TV noise case) | Phase 1 | Chặn tái diễn La La School — bài học bắt buộc |
| 3 | Dedupe write-path + dọn dual daemon | Phase 0 | Bỏ rác trước khi xây tầng trên |
| 4 | Working memory session | Phase 1 | Nền cho reasoning đa lượt |
| 5 | Benchmark V1 10 nhóm | Song song Phase 1-2 | Không có thước đo độc lập = không nghiệm thu được |
| 6 | Self-state monitor + UNKNOWN/LAST_VERIFIED | Phase 3 | Self model đã khá — bổ sung nhỏ, giá trị cao |
| 7 | World model | Phase 3 | Cần sau khi trust + working memory xong |
| 8 | Action policy + rollback | Phase 4 | An toàn tự chủ |
| 9 | Metacognition engine + calibration metrics | Phase 5 | Cần benchmark trước để đo |

---
*Tài liệu phân tích — mọi "✅" đều có bằng chứng tool thật ngày 11/11; mọi "❌/🟡" đều nêu thiếu cụ thể.*
