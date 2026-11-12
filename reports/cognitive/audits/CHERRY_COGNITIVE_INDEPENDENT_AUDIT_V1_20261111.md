# CHERRY COGNITIVE BASELINE AUDIT — ĐÁNH GIÁC ĐỘC LẬP LẦN 1 (TASK E)
**Ngày:** 11/11/2026 tối | **Auditor:** TONY (netMind Desktop, profile tony)
**Phạm vi:** tính đúng đắn của BASELINE trước khi cho phép triển khai Cognitive Core.
**Phương pháp:** đo trực tiếp bằng tool (curl/python/sqlite/powershell) trong phiên này — không tin số liệu cũ khi khác thực tế.

---

## 1. Kết luận tổng (fail-honest)

**Baseline ĐẠT Điều kiện khởi đầu Phase 0, KHÔNG ĐẠT điều kiện triển khai ngay Phase 1.**
Phải chạy Sprint COG-0 (ổn định) trước. Lý do: 4 vấn đề vận hành đang làm dữ liệu học nhiễm rác + 1 gap kiểm tra backup — nếu dựng Cognitive Core trên nền này, tầng trust/guard sẽ đo được rác thay vì tri thức.

| Nhóm | Kết quả | Bằng chứng chính |
|---|---|---|
| Dịch vụ lõi (servers/DB) | ✅ ĐẠT | 8765+8766 HTTP 200; brain_db HEALTHY (3.054 episodes, 5.052 semantic); integrity backup ok |
| Vệ sinh dữ liệu học | ❌ KHÔNG ĐẠT | 1.494 quarantine hàng "test suite passed" (695+488+311); dual learning daemon 4 PID; semantic dup 88 nhóm |
| Backup/restore | ⚠️ CẦN XÁC MINH | Backup DB mới nhất 09/11 (hôm qua 2AM thiếu?); task result≠0; integrity bản 09/11 = ok; restore thật CHƯA drill |
| Điểm mạnh nhận thức sẵn có | ✅ ĐẠT | CognitiveState V4, V9 reasoning (fail-honest thật), self_model + SelfQA wired, conflict detector V31, promotion R4 |
| Gap nền tảng lớn nhất | ⚠️ | Reasoning retrieval chỉ thấy 148 knowledge_units — không thấy 10.874 tri thức thật |
| Governance | ✅ ĐẠT | Invariants R4/R5 thật (đo qua CognitiveSelfAssessment); EVIDENCE_BOUNDED; không có dấu hiệu self-promote |

## 2. Kiểm chứng từng điều kiện nghiệm thu Phase 0 (theo master prompt §6)

1. **"Có báo cáo trạng thái thực tế"** → ✅ chính tài liệu này + gap analysis + TASK A report.
2. **"Có backup và khả năng restore đã kiểm thử"** → ⚠️ CẦN LÀM: backup 09/11 integrity=ok (đã check), nhưng (a) backup hằng ngày có thể chết (result 2147946720), (b) chưa drill restore lên DB tạm. Sprint COG-0 phải làm cả hai.
3. **"Có danh sách tồn đọng"** → ✅ gap analysis §D liệt kê 7 mục vận hành.
4. **"Không còn lỗi nghiêm trọng chưa ghi nhận"** → ✅ mọi lỗi phát hiện đều đã ghi (dual daemon, dedupe, backup, retrieval gap, memory review changes_applied=0).
5. **"Các trạng thái chưa xác minh phải ghi rõ"** → ✅ toàn bộ mục NOT VERIFIED được đánh dấu (restore drill, benchmark, E2E edge do Pi5 offline).

## 3. Phát hiện độc lập (một số không có trong báo cáo 11/11)

1. **Dual learning daemon** — 2 cặp PID (8380/15348 + 18440/21920) chạy song song mỗi 5 phút → tăng gấp đôi rác nạp; cycle log "6459 facts ingested / 0 consolidated" là dấu hiệu ingest-dedupe không hoạt động ở write path.
2. **Semantic memory dup 88 nhóm** — tầng "đã duyệt" cũng có trùng; cần dedupe có backup (archive-never-delete).
3. **Backup result≠0** — LastTaskResult 2147946720 (0x800710E0 — "operator or administrator refused"?) lúc 20:00; NextRun 2AM; chưa rõ backup có chạy đêm 10-11/11 không → DB mới nhất 09/11.
4. **Health DEGRADED do ollama DISABLED** — không phải sự cố (owner gỡ 02/11) nhưng component status nên được whitelist DISABLED (đã có 1 test fail cũ liên quan) — đề xuất nhỏ.
5. **knowledge_units gần trống** — reasoning V9 chỉ thấy 148 units (kho riêng V9); kho thật 10.874 ở semantic+chroma không nối vào → mọi câu hỏi thật sẽ "không đủ bằng chứng". Đây là gap quan trọng nhất cho Phase 2.
6. **Memory review tắc** — session mới nhất 07/11, findings có nhưng changes_applied=0; vòng tự cải thiện chưa khép.
7. **Quarantine tăng +56 trong ~4h** (6.175→6.231) — pace ~340/ngày nếu không chặn write-path dup.

## 4. Rủi ro nếu triển khai Cognitive Core NGAY (không qua COG-0)
- Trust engine tag memory từ learning ingest → tag trên rác lặp → 1.494×rác được "trust đúng nguồn" nhưng vẫn rác → benchmark false-reject loạn.
- Working memory recovery đọc brain.db → nạp dup vào session context → chất lượng suy luận giảm.
- Benchmark đo trên nền dual daemon → số liệu 2 lần thật/không ổn định → không tái lập được.
- Backup chết + migration ADD-only → rủi ro mất dữ liệu không có lưới an toàn mới nhất.

## 5. Khuyến nghị cổng chạy Phase 1
Phase 1 (Cognitive Foundation) CHỈ khởi động khi COG-0 đạt đủ 5 điều kiện mục 2. Đề xuất trình owner duyệt Sprint COG-0 ngay (R2, không đụng cognitive, rollback đơn giản).

## 6. Tuyên bố NOT VERIFIED (trung thực)
- Restore drill (khôi phục DB từ backup lên DB tạm) — NOT VERIFIED.
- Benchmark V1 — NOT BUILT.
- Speaker verification (voiceprint) — NOT BUILT (cần quyết định owner về thu thập mẫu giọng).
- E2E edge qua Pi5 — BLOCKED (Pi5 offline vật lý từ 10/11 13:31).
- Full regression ngày 11/11 — đang chạy lúc audit; kết quả sẽ bổ sung vào TASK A report.

---
*Audit độc lập lần 1 — sao chép evidence từ tool output thật; không mục nào đánh "đạt" thiếu bằng chứng.*
