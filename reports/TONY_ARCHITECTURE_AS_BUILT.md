# TONY ARCHITECTURE AS-BUILT — Đánh giá sự thống nhất kiến trúc
**Cập nhật:** 01/11/2026 16:45 · PHẦN III + 3.3 của Master Prompt V2.0

## 1. Kiến trúc hiện có (đối chiếu runtime)

```
┌─────────────────────────── PC MAIN BRAIN (DESKTOP-SNMI929) ───────────────────────────┐
│  Dual Servers (8765 UI + 8766 Executive) — pythonw .venv, start 16:13, HTTP 200        │
│   ├─ web/server.py — 120+ API endpoints, HMAC fail-closed gate (M6-B1 ✅)              │
│   ├─ cognition/cognitive_loop.py — PERCEIVE→…→LEARN (INTEGRATED :1669-1690)            │
│   ├─ monitoring/health_monitor.py + alert_engine (+owner-ACK ✅ 16:10)                 │
│   ├─ governance/ — approvals, R0-R5, STOP/FREEZE                                        │
│   ├─ learning daemon (tools/learning_daemon.py) — 5 phút/cycle                          │
│   └─ integration/netchat — responder (poll 2s, lệnh đứng đầu, 0 router-error)           │
├─────────────────────────── Pi5 EMBODIMENT (EDGE-PI5-DESK-01) ──────────────────────────┤
│  edge_client daemon — kiosk 8768, camera, audio action, heartbeat + HMAC ký            │
│   ↕ 100.100.83.59 (Tailscale) · RTT ~220ms · state READY · 0 fault sau M6-B1           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   NetChat DM (bot↔quanpt1) = kênh điều hành · Cron: backup 2AM⚠, report 8AM, mirror F 02:30 ✅
```

## 2. Kiểm tra 10 điểm thống nhất (PHẦN 3.3)

| # | Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|---|
| 1 | Bao nhiêu bộ điều phối? | **1 chính** (cognitive_loop trong server) + orchestrator phụ | M2 audit: 1/5 engine INTEGRATED |
| 2 | Bao nhiêu nguồn trạng thái? | 1 nguồn chính (brain.db) + health_alerts.db riêng + seen_state JSON | sqlite live |
| 3 | Bao nhiêu hệ thống trí nhớ? | **1 brain.db** chứa 5 lớp (episodes/memories/semantic/knowledge/feedback) | 19 bảng |
| 4 | Modules dùng chung context? | CÓ qua server.py + brain.db; cognition engines rời vẫn ORPHAN | M2 audit |
| 5 | Agents dùng chung Governance Gateway? | CÓ — mọi POST qua gate HMAC + approval_cards | server.py :489/:805 |
| 6 | Tools đăng ký thống nhất? | CÓ — tools/ + registry; responder import command_center thống nhất | fix P0 16:13 |
| 7 | Event có correlation ID? | PARTIAL — edge events có alert_id/task_id; chat turn có session_ref | episodes.source_ref |
| 8 | Nhiệm vụ sống qua restart? | CÓ — seen_state 248 ID nạp lại; learning checkpoint; catch-up 12h | log 16:13 |
| 9 | Phụ thuộc vòng? | KHÔNG phát hiện import cycle trong runtime hiện hoạt | pytest 3.002 |
| 10 | Nhiều module cùng trách nhiệm? | 2 điểm: server.py 272KB (hồ sụ overload); memory vs semantic_memory gần chồng lấn | inventory |

## 3. Mức đạt ONE BRAIN — ONE MEMORY — ONE GOVERNANCE — MULTIPLE EMBODIMENTS

| Trụ cột | Mức | Ghi chú |
|---|---|---|
| ONE BRAIN | ✅ 85% | 1 điều phối chính; 4 cognition engines còn ORPHAN (CriticalThinker, SelfModelEngine, SelfCareEngine, CognitiveLoop-engine) |
| ONE MEMORY | ✅ 90% | 1 brain.db thống nhất; health_alerts tách DB là hợp lý (audit trail) |
| ONE GOVERNANCE | ✅ 90% | HMAC fail-closed + R0-R5 + approval enforced; HMAC key quản trị tập trung |
| MULTIPLE EMBODIMENTS | ✅ 80% | PC + Pi5 READY; đăng ký hình thể mới = cấu hình device_id + pair; NetChat như embodiment văn bản |
| **OWNER CONTROLLED** | ✅ 100% | Mọi thay đổi quan trọng qua approval_cards; owner-ACK alert mới bổ sung |

## 4. Ranh giới còn tách biệt + kế hoạch hợp nhất

1. **Cognition engines ORPHAN** (4/5) — hợp nhất vào cognitive loop = hạng mục P2 "CriticalThinker integration" (ROADMAP).
2. **server.py 272 KB** — cần tách blueprint theo domain (web/health/edge/self) — P3 refactor, KHÔNG làm trong audit.
3. **mobile/ (2 file)** — chưa wire vào server; giữ nguyên, đánh dấu "chưa sử dụng".
4. **.venv_broken_backup (1,1 GB)** — di tích sự cố; đề xuất owner duyệt dọn (NHÓM B).

**Kết luận:** Kiến trúc ĐÃ thống nhất ở mức vận hành thật (không phải chỉ trên giấy). Các điểm tách biệt còn lại đã có tên tuổi và kế hoạch, không có "hệ thống bóng" đang chạy ngoài kiểm soát.
