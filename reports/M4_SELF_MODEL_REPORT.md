# TONY COGNITIVE EVOLUTION — M4: SELF MODEL & AUTONOMOUS LEARNING (Phần 1)

**Người thực hiện:** TONY (netMind Desktop) · **Ngày:** 01/11/2026 · **Phê duyệt:** "BẮT ĐẦU M4" (anh Quân, 01/11)
**Workspace:** `D:\AI\AI Quanpt1 2026\BRAIN` · **Execution mode:** AUDIT-FIRST / READ-ONLY / OWNER-GOVERNED
**Phạm vi:** M2 (Cognitive Core) và M3 (Deep Memory) vẫn PENDING_DESIGN_APPROVAL — không cài. M4 phần này KHÔNG đụng promotion R4 (Q-4 chờ duyệt), không giả lập approval.

---

## 1. Audit-first — dữ liệu thật trước khi viết code

| Hạng mục | Giá trị đo thật 01/11 | Ghi chú |
|---|---|---|
| candidate_knowledge | **1.491 approved + 2.933 quarantined** (tổng 4.424; lúc verify sau là 2.943/4.434) | **Sai lệch với M0**: không phải "4.284 kẹt" |
| Nguồn gốc approved | `decision_note` = "owner-approved bulk 31/10/2026: nội dung thật, unique, đã backup brain_pre_approval.db" (27/10–30/10: 907+216+229+47) | Do ANH duyệt hàng loạt phiên trước, KHÔNG phải tự promote |
| **Backup brain_pre_approval.db** | **KHÔNG TỒN TẠI** trong data/ | ⚠️ Ghi nhận trung thực: note nói có backup nhưng không thấy file — có thể backup ở nơi khác hoặc đã xoá; cần anh xác nhận |
| CLO (tự chủ học) | 7 sessions; vòng cuối #7 RUNNING từ 27/10 16:10 (không tiến triển 5 ngày) | self-care sẽ cảnh báo khi kẹt |
| Skill registry | 6 skills: 1 AVAILABLE, 5 TESTED | Đã wire /api/skills từ V6 |
| Engine nhận thức | 4/5 ORPHAN (M2 thiết kế xong chưa cài) | Không thay đổi trong M4 phần này |
| Quarantined mới nhất | 198 rows ngày 01/11 (kể cả các fact M0/M1 vừa tạo) | Pipeline học từ workflow vẫn sống, chỉ chờ duyệt |

**Kết luận:** nút thắt learning là **Q-4 approval_verifier** (chờ anh duyệt thiết kế R4), không phải thiếu dữ liệu.

---

## 2. Đã xây + kiểm chứng E2E

### 2.1 Self Model sống — 3 API đọc-only (server 8766)

| API | Nội dung | Bằng chứng E2E |
|---|---|---|
| `GET /api/self/model` | Identity + deployment + inventory quét thật lúc gọi + capability registry + limitations | success, confidence 92.3%, edge = `Raspberry Pi 5 quanpt1@100.100.83.59 (EDGE-PI5-DESK-01, Tailscale)` |
| `GET /api/self/state` | 13 câu tự nhận thức, mỗi câu kèm `verification_status` + `evidence_ref`; fail-honest | q1 VERIFIED_LIVE; q2 online: core_server+ollama+pi5 đều HEALTHY; q3 offline: rỗng; q7=1.842 / q8=2.943; q9=0; **q13_learning_autonomy VERIFIED_LIVE** |
| `GET /api/self/learning` | CLO checkpoints + candidates theo trạng thái + skills | clo_sessions=7, clo_enabled=true, vòng #7 RUNNING; approved 1.491 / quarantined 2.943; skills 6 (1 AVAIL, 5 TESTED) |

Sửa trung thực kèm theo: `deployment.edge_location` và `system_inventory._scan_pi5_device` còn ghi IP LAN cũ `192.168.1.21` → cập nhật `100.100.83.59` (Tailscale) — Pi5 giờ probe HEALTHY thật (trước đây luôn FAILED ảo).

### 2.2 Self-Care thực — nối SelfCareEngine vào HealthMonitor

- `HealthMonitor.__init__(self_care=...)` + trong `run_once()`: mỗi cycle chạy 4 health checks TCP thật (Ollama 11434, 8765, 8766, Pi5:8768); chỉ check **không healthy** mới thành alert (value 1=WARNING / 2=CRITICAL, rule `>=1`/`>=2`) qua cùng AlertEngine chống spam 300s.
- **Sửa trung thực (phát hiện từ kiểm kê M2):** `_attempt_auto_recovery` trước đây set `auto_recovered=True` khi recovery chỉ *simulated* → nay action = `PENDING: đề xuất ... (chưa có executor thật — chờ phê duyệt)`, cờ luôn False. Test chặn hồi quy.
- `server.py`: `start_health_monitor()` inject `_get_self_care_engine()` (lazy-init, module-level, dùng chung workspace root).
- **E2E thật:** cycle chạy trong tiến trình server → `self_care_summary: total=4, healthy=4, health_percentage=1.0, auto_recoveries=0`; probe Pi5:8768 qua Tailscale OPEN; 1 alert pi5 bt_speaker (thật) gửi DM thành công. Self-care chỉ cảnh báo khi có sự thật — **không tạo alert giả**.

### 2.3 Dashboard `/health` mở rộng M4

Thêm 2 khu (render fail-honest — lỗi API hiện lý do, không che):
- **M4 — Tự nhận thức**: danh tính, triển khai, module hoạt động, caps verified/unverified, giới hạn, confidence.
- **M4 — Tự học & Tri thức**: CLO sessions/enabled/vòng cuối, candidates approved/quarantined (ghi rõ "quarantine chỉ mở khi anh duyệt Q-4"), skills theo trạng thái.

### 2.4 Sửa flaky lâu năm (phát hiện tình cờ trong regression)

`memory/state_tracker.py::get_state_history` sort SQL `DESC` rồi `return list(reversed(records))` — double-negation: đúng theo thời gian thực CHỈ khi vi giây khác nhau; trùng → thứ tự sqlite ngẫu nhiên → FAIL flaky (lộ ra lần regression này sau restart server). Không có caller production (chỉ test) → sửa gốc an toàn: `ORDER BY transitioned_at ASC, rowid ASC` (ổn định cả khi trùng vi giây), bỏ reverse; sửa luôn annotation `from_state: TaskState | None`. Chạy lại 3 lần liên tiếp PASS.

---

## 3. Tests — bằng chứng số

| Bộ | Kết quả |
|---|---|
| `tests/test_m4_self_introspection.py` (mới) | **16/16 PASS** (3 API trên server thật workspace giả lập; 2 fix trung thực; self-care stub + probe thật) |
| M4 + web + monitoring + capability + self-awareness + self-care | **77/77 PASS** |
| **Regression FULL** | **2.969 passed / 44 skipped / 0 failed (2:36)** — baseline M1 2.953 → +16 |

## 4. Restart server đúng chuẩn

Kill 2 PID dual_servers cũ → spawn `pythonw start_dual_servers.py` với `NETMIND_API_KEY` từ registry User env (len=25, không in giá trị) → 8766+8765 lên (PID 15680+19196) → 3 API M4 verify sống với dữ liệu thật. Responder/watchdog/learning daemon không đụng.

## 5. Ràng buộc tuân thủ

- **Q-4 KHÔNG đụng**: 2.943 candidates vẫn quarantined; API chỉ ĐẾM, không mở.
- Không tự trao quyền phê duyệt; auto-recovery để PENDING chờ thiết kế executor + phê duyệt riêng.
- Fail-honest: mọi metric không đo được → UNKNOWN + lý do; không có cờ "phục hồi thành công" giả.
- Không đụng `daemon/supervisor.py`, không git init (Q-1), không đổi journald (Q-2), không Piper (Q-3), không BT power-save (Q-5).

## 6. Còn lại cho M4 phần 2 (đề xuất, chờ duyệt)

1. **M4-B Learning Health**: cảnh báo CLO kẹt (session RUNNING > 24h không tiến triển) qua AlertEngine — code sẵn đường, chỉ thêm pseudo-check.
2. **M4-C Self-Q&A wired**: khi anh hỏi "em có năng lực gì / em đang ở đâu" qua chat → trả lời từ `/api/self/model` + `/api/self/state` (G-12) thay vì hard-code.
3. **M4-D Ưu tiên duyệt Q-4** (thiết kế R4 verifier) — mở 2.943 candidates được sàng lọc; đây là nút thắt thật của Autonomous Learning.

Người lập: TONY (netMind Desktop) — 01/11/2026
