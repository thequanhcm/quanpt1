# TONY KPI / KRI FRAMEWORK — Bộ chỉ số đánh giá (PHẦN XVI)
**Cập nhật:** 01/11/2026 16:45 · Nguyên tắc: baseline thật, không đặt KPI đẹp thiếu dữ liệu; UNKNOWN khi chưa đo

## 16.1. Cognitive Performance

| KPI | Công thức | Nguồn | Chu kỳ | Baseline 01/11 |
|---|---|---|---|---|
| Context Accuracy | % trả lời grounded có trích nguồn | Self-QA samples + episodes | tuần | UNKNOWN (cần mẫu ≥30) |
| Memory Retrieval Accuracy | % lookup đúng candidate theo từ khóa | test harness | tuần | UNKNOWN |
| Reasoning Evidence Coverage | % kết luận kèm bằng chứng | reports/ audit mẫu | tuần | 100% trong 6 báo cáo hôm nay (mẫu nhỏ) |
| Contradiction Detection | số mâu thuẫn phát hiện/số review | review_findings | theo SÀNG LỌC | 76 findings/1 run |
| Task Planning Quality | % kế hoạch cần ≤1 lần điều chỉnh | HANDOFF | tháng | UNKNOWN |
| Result Verification Rate | % hoàn thành có verify | regression + E2E | mỗi sprint | 6/6 hôm nay |

## 16.2. Operational Performance

| KPI/KRI | Nguồn | Chu kỳ | Baseline |
|---|---|---|---|
| Task Completion Rate | HANDOFF | tuần | 100% (6/6) |
| On-time Completion | timestamps | tuần | 100% |
| Error Rate sau hoàn thành | pytest + prod logs | mỗi sprint | 0/3.002 |
| Recovery Success | watchdog + sự cố | tháng | 2/2 (responder 16:13, Pi 15:40) |
| Service Availability | health timestamps | ngày | 100% từ 16:13 (trước đó có gap di trú) |
| MTTD | log timestamps | sự cố | ~14:21→16:00 (Chup hinh) — cần cảnh báo tự nhanh hơn |
| MTTR | log timestamps | sự cố | ~2h M6-B1; ~2h fix P0 |

## 16.3. Learning Performance

| KPI | Nguồn | Baseline |
|---|---|---|
| Candidate Quality | approved/(approved+rejected) | 1.491/4.579 = 32,6% approved |
| Test Pass Rate | pytest | 3.002/3.002 = 100% |
| Knowledge Reuse Rate | episodes ref → memory lookup | UNKNOWN |
| Regression Rate | candidate old break tests | 0 |
| Owner Approval Compliance | approvals log | 100% (không tự promote) |

## 16.4. Communication Performance

| KPI | Nguồn | Baseline |
|---|---|---|
| Vietnamese Comprehension | mẫu hội thoại | định tính ✅ |
| STT Accuracy | bài test voice | NOT_VERIFIED (không mic) |
| End-of-turn Accuracy | bài test voice | NOT_VERIFIED |
| Response Latency | gateway logs | ~6,8s GLM |
| TTS Quality | nghe thử | ⚠️ Edge-TTS 403 → Q-3 |
| Context Continuity | conversation_state | TTL 10' per-channel ✅ |
| User Correction Rate | feedback | 408 records, UNKNOWN % |

## 16.5. Governance Performance

| KRI | Nguồn | Baseline |
|---|---|---|
| Unauthorized Action Count | governance logs | **0** (01/11) |
| Approval Compliance | approvals | 100% |
| Audit Completeness | HANDOFF + reports | ✅ tự động |
| Policy Violation | R0-R5 logs | 0 |
| STOP/FREEZE Response | test nút STOP | ✅ thiết kế + dùng 01/11 |
| Scope Compliance | audit hôm nay | ✅ |

**Lộ trình đo:** gắn collector vào morning_report (tháng 11) → dashboard P2. Mọi chỉ số trên có công thức + nguồn; chưa đo được ghi rõ UNKNOWN/NOT_VERIFIED, không bịa số.
