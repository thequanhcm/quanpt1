# TONY CAPABILITY SCORECARD — Ma trận năng lực tổng thể (PHẦN 17.2)
**Cập nhật:** 01/11/2026 16:45 · Mọi ô đều có bằng chứng; NOT_VERIFIED khi chưa đo

| Năng lực | Trạng thái thực tế | Cấp 1 | Cấp 2 | Cấp 3 | Bằng chứng | Khoảng trống |
|---|---|---|---|---|---|---|
| **Cognitive Kernel** | 1 lõi điều phối + 4 engine ORPHAN; runtime sống | ✅ | ✅ | ⚠️ | server.py + cognitive_loop :1669-1690; 3.002 tests | Tích hợp 4 engine (P2) |
| **Deep Memory** | 19 bảng live; 4.579 candidates; review chạy thật | ✅ | ✅ | ⚠️ | brain.db 16:33; review_findings 76 | M2 bug + vòng phản hồi owner |
| **Reasoning** | Cấp 2 kỹ thuật; phản biện còn module rời | ✅ | ✅ | ❌ | root-cause hôm nay; CriticalThinker ORPHAN | Tích hợp + Test A |
| **Self Model** | 10/10 loại câu trả lời đúng, khớp runtime | ✅ | ✅ | ⚠️ | /api/self/*; 13/13 M4 | 2 điểm mù nhỏ (backup, rác) |
| **Learning** | Chu trình đầy đủ + checkpoint; KHÔNG tự promote | ✅ | ✅ | ⚠️ | 4.579 candidates; archive 110.962 | Q-4 mở quarantine; tool-factory |
| **Tool/Skill Factory** | 126 tools; chưa tự sinh tool mới hoàn chỉnh | ✅ | ✅ | ❌ | tools/; capability gap detect | Auto-factory (P2) |
| **Health Intelligence** | Đo-cảnh báo-đề xuất-theo dõi + owner-ACK | ✅ | ✅ | ⚠️ | 187 alert records; ACK live | Predictive (P2); watchdog |
| **Pi5 Conversation** | Văn bản Cấp 2; voice chờ phần cứng | ✅ | ⚠️(văn bản ✅) | ❌ | DM cả ngày; voice NOT_VERIFIED | AUDIO + Q-3 |
| **Multi-Embodiment** | PC+Pi5 HMAC E2E 0-fault; NetChat embodiment | ✅ | ✅ | ⚠️ | 120s giám sát; camera thật | Fail-over test có chủ đích |
| **Governance** | 0 vi phạm; gate fail-closed mọi đường | ✅ | ✅ | ✅ | M6-B1 + approval workflow | — |
| **Task Management** | Full lifecycle có bằng chứng | ✅ | ✅ | ⚠️ | task_registry; M6-B1 walkthrough | Auto-retry (P2) |
| **Reporting** | 305+ reports + cron 8h + HANDOFF auto | ✅ | ✅ | ⚠️ | validate exit 0 16:31 | KPI dashboard (P2) |

**Tổng kết:** 0/12 dưới Cấp 1 · 2/12 đạt Cấp 3 (Governance; ready-operations) · 9/12 Cấp 2 · 1/12 phân tách văn-bản-voice.
**KHÔNG dùng trung bình che giấu:** 2 điểm yếu nhất ghi rõ = Pi5 voice (phần cứng) + CriticalThinker integration.
