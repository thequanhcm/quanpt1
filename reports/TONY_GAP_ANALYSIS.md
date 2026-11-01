# TONY GAP ANALYSIS — Khoảng trống cần lấp (PHẦN XVIII)
**Cập nhật:** 01/11/2026 16:45 · Ưu tiên theo rủi ro + giá trị; KHÔNG xây lại thứ đang tốt

| # | Khoảng trống | Hiện trạng (bằng chứng 16:33) | Mục tiêu | Giá trị | Chi phí | Dependency | P |
|---|---|---|---|---|---|---|---|
| 1 | **Watchdog bật lại** | 0 process | Tự hồi phục vĩnh viễn cap 5/h | Chống downtime im lặng | 15' | Duyệt (restart service) | **P0→P1** |
| 2 | **Backup 2AM bật lại** | brain_*.db dừng 28/10 | brain DB mốc phục hồi hằng ngày | RPO ≤24h | 30' | Duyệt (schtasks) | **P0→P1** |
| 3 | **Piper TTS (Q-3)** | Edge-TTS 403 flaky | TTS local ổn định | Voice sống | 4h | ✅ ĐÃ DUYỆT | **P0** |
| 4 | **Approval verifier (Q-4)** | 3.088 quarantined | Mở khoá học tập có kiểm chứng | Learning Cấp 3 | 6h | ✅ ĐÃ DUYỆT (sau Q-3) | **P0** |
| 5 | **Fix reflection M2** | hypothesis mất | FACT/INFERENCE/HYPOTHESIS đầy đủ | Data integrity | 1h | Duyệt | P1 |
| 6 | **USB audio (AUDIO)** | alsa_cards=0 | Voice Pi5 thật | Conversation Cấp 2 voice | 1h + mua thiết bị | Duyệt | P1 |
| 7 | Review-owner loop | owner_questions=0 | Câu hỏi SÀNG LỌC vào Morning Report | Đóng vòng trí nhớ | 2h | — | P1 |
| 8 | Fail-over test có chủ đích | chỉ gián tiếp | Bài test mất-Pi5 theo kịch bản | Embodiment Cấp 3 | 2h | — | P2 |
| 9 | CriticalThinker integration | ORPHAN | REASON bước 10/10 | Reasoning Cấp 3 | 8h | #5 | P2 |
| 10 | Self-model 2 điểm mù | backup/rác không biết | Self-model đọc ops-state | Self Cấp 3 | 2h | #1#2 | P2 |
| 11 | Auto tool-factory | chưa tự sinh tool | CLO sinh tool có test | Tool Cấp 3 | 12h | Q-4 | P2 |
| 12 | KPI dashboard | baseline giấy | Collector + dashboard | Đo lường liên tục | 6h | morning_report | P2 |
| 13 | Tách server.py 272KB | monolith | Blueprint theo domain | Bảo trì | 16h | — | P3 |
| 14 | Logs rotation | 124 MB | Xoay 30 ngày | Đĩa sạch | 1h | — | P3 |
| 15 | Dọn .venv_broken_backup | 1,1 GB rác | Xóa sau duyệt | Đĩa sạch | 5' | Duyệt (NHÓM B) | P3 |
| 16 | Test A email-progress | NOT_VERIFIED | Bài thật qua Outlook skill | Nhân sự Cấp 3 | 4h | Anh giao bài | P2 |

**Nguyên tắc:** không đề xuất xây lại health/governance/memory (đang tốt); ưu tiên #1#2 (rủi ro vận hành mới) rồi #3#4 (đã duyệt).
