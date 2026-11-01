# TONY COGNITIVE EVOLUTION — M0 GAP ANALYSIS

**Thời điểm:** 01/11/2026 09:50. Ma trận đối chiếu hiện trạng audit với kiến trúc đích TONY COGNITIVE EVOLUTION V1.0.

---

## Ma trận tổng hợp

| # | Thành phần kiến trúc đích | Trạng thái | Phân loại | Ghi chú bằng chứng |
|---|---|---|---|---|
| G-01 | Cognitive Event Bus | **CHƯA CÓ** | Chưa có | Module giao tiếp qua gọi hàm/DB trực tiếp |
| G-02 | Central State Manager | **MỘT PHẦN** | Đã có chưa hoàn thiện | `cognitive_state.py`, `state_tracker.py`, `system_state.py` tồn tại; chưa thấy restore-after-restart thống nhất |
| G-03 | Module Registry động (health/test/runtime) | **MỘT PHẦN** | Đã có chưa hoàn thiện | `capability_registry.py` static; `system_inventory.py` chưa wired |
| G-04 | Task Lifecycle đầy đủ (WAITING_OWNER/BLOCKED...) | **PHẦN LỚN CÓ** | Đang hoạt động | durable_tasks 578 rows; trạng thái phụ cần đối chiếu schema |
| G-05 | Runtime Supervision | **MỘT PHẦN** | Đã có chưa hoàn thiện | `supervisor.py` 352 dòng; watchdog hoạt động ở tầng process, chưa ở tầng event/task |
| G-06 | Memory 5 lớp API thống nhất | **CÓ VẬT CHẤT** | Đang hoạt động (phân tán) | 5 bảng riêng; CognitiveRetriever chỉ hợp nhất một phần |
| G-07 | Memory Consolidation pipeline | **MỘT PHẦN** | Đã có chưa hoàn thiện | `experience_consolidation.py`, `duplicate_detector.py`, `conflict_detector.py` — chưa thấy chạy định kỳ |
| G-08 | Evidence Registry / provenance | **MỘT PHẦN** | Đã có chưa hoàn thiện | `provenance_tracker.py` + cột source_ref/verification_status trong DB |
| G-09 | Owner Memory Review (`SÀNG LỌC`) | **CÓ KHUNG** | Đã có chưa hoàn thiện | memory_review_sessions=2, review_findings=76, review_questions=42, review_changes=1 — đã chạy 2 đợt thật |
| G-10 | Reasoning Engine 3 cấp độ FACT/INFERENCE/HYPOTHESIS | **CHƯA RÕ RÀNG** | Đã có chưa hoàn thiện | `critical_thinker.py` 575 dòng + `causal_engine.py` — chưa thấy gắn nhãn 3 cấp trong câu trả lời |
| G-11 | Multi-perspective reasoning | **CHƯA CÓ** | Chưa có | Có `collaboration.py` (multi-agent inbox) nhưng chưa thành quy trình phân tích đa góc |
| G-12 | TONY Self Model cập nhật realtime | **MỘT PHẦN** | Đã có chưa hoàn thiện | `self_model_engine.py` 507 dòng + `system_inventory.py` 440 dòng — chưa wired vào Q&A "em có năng lực gì" |
| G-13 | Self Assessment định kỳ | **CHƯA CÓ** | Chưa có | — |
| G-14 | Learning Cycle đầy đủ (OBSERVE→...→PROMOTE) | **BỊ CHẶN TẦNG PROMOTE** | Bị chặn bởi quyền | 4.284 candidates kẹt vì `approval_verifier=None` (AGENTS.md: R4 cần verifier đã cấu hình) |
| G-15 | Tool/Skill/Agent Registry | **MỘT PHẦN** | Đã có chưa hoàn thiện | `skill_registry.py` + /api/skills; Tool registry riêng lẻ; Agent registry chưa thấy |
| G-16 | Tool/Skill Factory (tự tạo candidate) | **CHƯA CÓ** | Chưa có | Continuous Learning Engine có khung Sprint 5 — chưa thấy pipeline tạo tool thật |
| G-17 | Health PC deep (CPU/RAM/disk/process/service) | **CHƯA CÓ** | Chưa có | health.py 30 dòng; /api/health 4 components cơ bản |
| G-18 | Health Pi5 deep (temp/throttled/BT/cam/…) | **CHƯA CÓ** | Chưa có | Em probe tay qua SSH — chưa có monitor tự động |
| G-19 | Network Health đo đạc liên tục | **MỘT PHẦN** | Đã có chưa hoàn thiện | edge telemetry rtt_ms + history; chưa đo STT/LLM/TTS latency |
| G-20 | Health State machine (NORMAL/WARNING/CRITICAL/UNKNOWN) | **CHƯA CÓ** | Chưa có | Chỉ HEALTHY tĩnh |
| G-21 | Alert Engine chủ động | **CHƯA CÓ** | Chưa có | (Milestone 1 mục tiêu) |
| G-22 | Dialogue State Manager | **MỘT PHẦN** | Đã có chưa hoàn thiện | Voice conversation loop có state cơ bản (LISTENING/THINKING); chưa có quản lý chủ đề/turns dài |
| G-23 | Barge-in | **CHƯA CÓ** | Chưa có | Đã xử lý echo bằng đóng mic; chưa cho phép anh ngắt lời em |
| G-24 | TTS Prosody Engine + fallback đa engine | **MỘT PHẦN** | Đã có chưa hoàn thiện | Edge-TTS chính + retry; chưa có Piper/local fallback; chưa có prosody |
| G-25 | QEP — QUAN EMBODIMENT PROTOCOL | **CHƯA CÓ TÊN GỌI** nhưng có nền | Đã có chưa hoàn thiện | Daemon↔Server đã có HMAC + heartbeat + telemetry; chưa chuẩn hoá thành protocol spec + capability negotiation |
| G-26 | Embodiment Registry đa thiết bị | **CHƯA CÓ** | Chưa có | 1 hình thể (Pi5), device_id cứng trong code |
| G-27 | Governance kiểm soát backend mọi đường thực thi | **LỚN CÓ** | Đang hoạt động | R0–R5 + guardrails + audit; approval_cards 346 dòng CHƯA DÙNG (0 rows) |
| G-28 | Approval Protocol đầy đủ (ID/phạm vi/rollback…) | **KHUNG CÓ** | Đã có chưa hoàn thiện | approval_cards.py có schema nhưng chưa wired vào NetChat |
| G-29 | STOP/FREEZE phân tầng (learning/tool/voice riêng) | **MỘT PHẦN** | Đã có chưa hoàn thiện | Có emergency state kiosk + STOP nút màn; chưa có freeze theo phân hệ |
| G-30 | Dashboard "TONY COMMAND & COGNITIVE CENTER" 8 khu | **CHƯA CÓ** | Chưa có | dashboard 354 dòng — far from spec |
| G-31 | Version control (git) | **CHƯA CÓ** | Chưa có (RỦI RO CAO) | 83k dòng code không git |
| G-32 | journald bền vững Pi5 | **LỖI CẤU HÌNH** | Có nhưng trùng lặp/lỗi | Storage=persistent nhưng /var/log/journal rỗng |
| G-33 | Edge-TTS 403 flaky | **ĐANG CHẠY VẤN ĐỀ** | Có nhưng đang trùng lặp/lỗi | Retry ×2 đã giảm tác động; cần engine local fallback (Piper) |
| G-34 | Reboot lạ Pi5 | **CHƯA RÕ NGUYÊN NHÂN** | Cần nghiên cứu thêm | Không có log quá khứ (G-32); boot hiện tại ổn định |
| G-35 | Reply-thread NetChat | **BỊ CHẶN NỀN TẢNG** | Bị chặn bởi quyền | Gateway Bot bỏ root_id; đã thay bằng prefix trích dẫn |
| G-36 | Pi5 tự nghe chính giọng mình (echo loop) | **ĐÃ GIẢM** | Đang hoạt động | Đóng mic khi phát + chờ 1,5s; câu 4 test E2E vẫn bị nhiễm một lần |

## Nhóm ưu tiên xử lý (theo影响 × rủi ro × giá trị)

### P0 — Nền tảng an toàn + giải phóng nghẽn (M1)
1. **G-31 git init + commit đầu tiên** — bảo toàn 83k dòng. *(cần anh duyệt vì AGENTS.md cẩn thận với workspace; đây là thay đổi hạ tầng thấp rủi ro nhưng phải được đồng ý)*
2. **G-32 fix journald bền vững** — `sudo mkdir /var/log/journal/<machine-id> + systemctl restart systemd-journald` trên Pi5 — điều kiện để điều tra G-34.
3. **G-17/G-18/G-20 Health deep PC+Pi5 + Health State** — nền cho mọi cảnh báo sau này.
4. **G-21 Alert Engine** (qua NetChat DM đã sẵn).
5. **G-33 Piper TTS fallback** — chấm dứt phụ thuộc Edge-TTS flaky.

### P1 — Nhận thức thống nhất (M2–M3)
6. G-01 Event Bus (nhẹ: stdlib in-proc pub/sub + persisted log).
7. G-02/G-03/G-05 State Manager + Module Registry động.
8. G-06/G-07/G-08 Consolidation + provenance định kỳ.
9. G-10 gắn nhãn FACT/INFERENCE/HYPOTHESIS vào câu trả lời.
10. G-12 Self Model wired vào Q&A năng lực.

### P2 — Tự học + hội thoại (M4–M5)
11. G-14 cấu hình approval_verifier **SAU KHI anh duyệt thiết kế R4** (mở khoá 4.284 candidates).
12. G-15/G-16 Tool/Skill/Agent registry + factory sandbox.
13. G-22/G-23/G-24 Dialogue state + barge-in + Piper prosody.
14. G-30 Dashboard Cognitive Center (theo dữ liệu thật).

### P3 — Mở rộng (M6)
15. G-25/G-26 QEP spec + Embodiment registry.

## Rủi ro ghi nhận (đưa vào Risk Register)

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Mất code do không git | CAO | G-31 |
| Mất log điều tra sự cố Pi5 | CAO | G-32 |
| Loa BT power-save/notify owner khi mất | TRUNG-BÌNH | Health Pi5 + alert |
| Voice conversation loop treo nếu pw-record lỗi lạ | TRUNG-BÌNH | Đã có read timeout; cần watchdog thread |
| Ollama mock nhiễm memories (đã xảy ra 639 rows) | TRUNG-BÌNH | Đã xoá + lọc [MOCK]; cần cờ cứng chặn mock ghi memory |
| Single-model dependency GLM | TRUNG-BÌNH | Fallback Ollama có sẵn; cần đánh giá tự động |
