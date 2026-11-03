# TONY COGNITIVE EVOLUTION — M0 ROADMAP (KẾ HOẠCH TỔNG)

**Thời điểm lập:** 01/11/2026 09:55, dựa trên audit thực tế (TC_EVOLUTION_M0_AUDIT.md) và gap analysis (TC_EVOLUTION_M0_GAP_ANALYSIS.md).

**Nguyên tắc triển khai:** từng bước nhỏ, có test, có bằng chứng, không gián đoạn hệ thống đang chạy, mọi thay đổi cần phê duyệt đều chờ Quanpt1.

---

## Roadmap 6 milestone (điều chỉnh theo dependency thật)

### MILESTONE 1 — SYSTEM HEALTH INTELLIGENCE *(đề xuất bắt đầu ngay sau khi anh duyệt)*
**Lý do đặt trước:** mọi milestone sau cần dữ liệu sức khỏe thật; 2 vấn đề mở (reboot lạ, Edge-TTS 403) thuộc nhóm này; rủi ro hiện tại cao nhất là thiếu giám sát sâu.

| Việc | Chi tiết | Điều kiện nghiệm thu | Cần anh duyệt? |
|---|---|---|---|
| 1.1 PC Health Monitor | psutil: CPU/RAM/disk/IO/service/port — đọc thật | Endpoint /api/health/machine trả số liệu thật + timestamp | Không (đọc-only) |
| 1.2 Pi5 Health Collector | SSH probe (temp, throttled, RAM, disk, BT, cam, uptime) mỗi 60s, lưu DB | /api/health/pi5 có dữ liệu thật | Không (đọc-only qua SSH key sẵn có) |
| 1.3 journald bền vững Pi5 | mkdir /var/log/journal/<machine-id> + restart journald | journalctl --list-boots ≥ 2 boots sau reboot | **CÓ (thay đổi hệ thống Pi)** |
| 1.4 Health State machine | NORMAL/WARNING/CRITICAL/UNKNOWN + ngưỡng | Trạng thái UNKNOWN khi thiếu dữ liệu; test unit | Không |
| 1.5 Alert Engine | Gộp sự kiện, chống spam, gửi DM NetChat | Test: temp > ngưỡng → 1 DM duy nhất/5 phút | Không |
| 1.6 Piper TTS fallback | Cài Piper trong venv (package được duyệt), engine chọn Edge→Piper tự động | TTS hoạt động khi Edge 403; bộ câu tiếng Việt test | **CÓ (cài package mới)** |
| 1.7 Health Dashboard | Tab Sức khoẻ trong dashboard 8765 | Hiển thị dữ liệu backend thật | Không |
| 1.8 Điều tra G-34 reboot | Sau 1.3: chờ/cài log bền, phân tích crash thật | Báo cáo nguyên nhân hoặc bằng chứng "không tái diễn" | Không |

**Ước lượng:** 3–4 phiên làm việc. Gián đoạn hệ thống: gần như không (đọc-only + 1 restart journald).

### MILESTONE 2 — COGNITIVE KERNEL
| Việc | Chi tiết | Cần anh duyệt? |
|---|---|---|
| 2.1 Cognitive Event Bus | stdlib in-proc pub/sub + persisted event log (sqlite) — không phụ thuộc ngoài | Không |
| 2.2 Central State Manager | Gom state các tầng + checkpoint/restore | Không |
| 2.3 Module Registry động | Đăng ký module kèm health/test/runtime status, đọc từ audit | Không |
| 2.4 Task Lifecycle nâng cấp | Bổ sung WAITING_OWNER/BLOCKED/NEEDS_REVIEW vào task_registry hiện có | Không |
| 2.5 Wire 5 engine rời (cognitive_loop, critical_thinker, self_model, self_care, continuous_learning) vào loop chính qua Event Bus | Một yêu cầu đi qua đúng 1 Cognitive Loop | Không (code trong workspace) |
| 2.6 Governance hook backend | Mọi đường EXECUTE đi qua governance/policy check | Không |

**Điều kiện nghiệm thu:** test tích hợp Cognitive Loop; không tạo vòng lặp; khôi phục trạng thái sau restart.

### MILESTONE 3 — DEEP MEMORY & REASONING
- API thống nhất 5 lớp memory (bọc CognitiveRetriever hiện có, không phá DB).
- Consolidation định kỳ (dedupe/conflict/provenance) — chạy learning daemon hiện có.
- Gắn nhãn FACT/INFERENCE/HYPOTHESIS vào /api/chat answer metadata + hiển thị dashboard.
- `SÀNG LỌC` hoàn thiện theo phạm vi nhỏ + owner review (mở rộng memory_review_* đã có).
- **Cần anh duyệt:** không (đọc/ghi trong workspace, không đụng dữ liệu gốc).

### MILESTONE 4 — SELF MODEL & AUTONOMOUS LEARNING
- Self Model tổng hợp từ inventory + health + test + registry (G-12).
- Self Assessment định kỳ → báo cáo bằng chứng.
- Tool/Skill Factory trong sandbox (gov_sandbox.db có sẵn).
- **Cần anh duyệt:** thiết kế approval_verifier R4 (điều kiện mở khoá 4.284 candidates + promotion).

### MILESTONE 5 — HUMAN-LIKE VOICE & CONVERSATION
- Dialogue State Manager (chủ đề, turns, câu hỏi mở).
- Barge-in (nghe ngắt khi em đang nói — cần echo cancellation đơn giản: giảm gain mic khi phát).
- Prosody + pronunciation dictionary (số, mã lỗi, thuật ngữ).
- Personality layer ổn định (điềm tĩnh, thẳng thắn, phản biện có căn cứ).
- **Cần anh duyệt:** không (đều trong workspace; loa/mic đã trong phạm vi vận hành hiện tại).

### MILESTONE 6 — EMBODIMENT & DISTRIBUTED INTELLIGENCE
- QEP spec (chuẩn hoá heartbeat/identity/capability đã có trên daemon↔server).
- Embodiment Registry + capability negotiation.
- Multi-agent điều phối (supervisor + agent workers quyền hạn giới hạn).
- **Cần anh duyệt:** spec QEP trước khi cài.

## Kiểm thử toàn hệ thống (song song các milestone)
- Nhóm A–H theo Phần XVIII master prompt; mỗi test có input/expected/actual/evidence.
- Chạy `python tools/validate_and_report.py` sau mỗi milestone + cập nhật PROJECT_STATUS.

## Các quyết định đang CHỜ ANH (không tự làm)

| # | Quyết định | Tác động nếu duyệt |
|---|---|---|
| Q-1 | Cho phép `git init` + commit đầu tiên trong workspace (G-31) | Bảo toàn 83k dòng code, rollback mọi thay đổi |
| Q-2 | Fix journald bền vững trên Pi5 (G-32, lệnh sudo 2 dòng) | Điều tra được reboot lạ; mất log quá khứ không phục hồi được nhưng chặn mất log tương lai |
| Q-3 | Cài Piper TTS vào venv làm fallback (G-33) | Chấm dứt phụ thuộc Edge-TTS flaky |
| Q-4 | Thiết kế + cấu hình approval_verifier R4 (G-14) | Mở khoá 4.284 tri thức quarantine + promotion tự học |
| Q-5 | (Tuỳ chọn) Bật BT power-save off cho loa SRS-XB33 trên Pi5 | Giảm mất kết nối loa như sáng nay |

## Trật tự thực hiện khi anh nói "BẮT ĐẦU M1"
1. 1.1 → 1.2 → 1.4 → 1.5 (đọc-only, an toàn tuyệt đối)
2. Hỏi anh duyệt Q-2 + Q-3 rồi làm 1.3 + 1.6
3. 1.7 → 1.8
4. Báo cáo M1 + validate_and_report + handoff
