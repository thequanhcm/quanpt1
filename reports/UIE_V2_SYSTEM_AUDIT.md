# UIE_V2_SYSTEM_AUDIT.md

**PHASE 0 — Kiểm toán toàn hệ thống UIE V2.0 theo §III | 02/11/2026 17:54 (dữ liệu tươi, không dùng báo cáo cũ)**
Phương pháp: SQL trực tiếp, socket probe, PowerShell CIM, filesystem — mỗi ô trạng thái đều có lệnh kiểm tra đi kèm.

---

## A. SECURITY

| Thành phần | Mã nguồn | Đang chạy | API | Database | Test | Bằng chứng | Phụ thuộc | Trùng chức năng |
|---|---|---|---|---|---|---|---|---|
| SEC-S1 watcher/actions | ✅ security/watcher.py, actions.py | ✅ (watchdog cycle) | — | security_contracts.db=3 | ✅ 26/26 (tái chạy 17:5x) | contract REVOKED đúng | watchdog, netchat | — |
| SENTINEL S3 identity/threat/containment | ✅ 3 module | ✅ (SEC cycle apply_violation) | DM `sentinel` | sentinel_agents.db=0, threat_levels.db=1 | ✅ 38/38 | hồ sơ SUSPICIOUS thật 15:xx | EvidenceStore | — |
| Watchdog | ✅ tools/watchdog.py | ✅ 2 PID (parent-child) | — | — | ✅ qua regression | ⚠️ child chạy Python311 thay vì .venv — **cần fix duyệt** | PowerShell CIM | — |
| Whitelist | ✅ actions.py PROTECTED_WHITELIST | ✅ | — | — | ✅ trong test S1 | refuse SYSTEM+TONY | — | — |
| Kill Responder | ✅ actions.py Stop-Process | ✅ (R-gated) | DM `giữ/thả/hạ` | — | ✅ S1 | whitelist refuse trước khi kill | CIM | — |
| Process/Network Monitoring | ✅ watcher.py cmdline bulk + IP scan | ✅ | — | — | ✅ S1+S3 | bắt 2/2 vi phạm thật | CIM | — |
| DM Interface | ✅ netchat_security_center.py | ✅ bot_tony | ✅ 2-bước hash | — | ✅ live nhiều lần | post id thật | skill bot-netchat | ⚠️ bot suspended 429 17:4x (tự hồi) |

## B. INTELLIGENCE

| Thành phần | Mã nguồn | Đang chạy | API | Database | Bằng chứng |
|---|---|---|---|---|---|
| Cognitive Core (web/server.py 6019d) | ✅ | ✅ 8765+8766 | ✅ /api/chat... | — | LLMRouter GLM→qwen→mock |
| Memory | ✅ memory/ (40 module) | ✅ | ✅ qua server | brain.db: episodes 2.898, memories 2.355 | marker test PASS phiên 16:4x |
| RAG/Retrieval | ✅ cognition/retrieval.py | ✅ (keyword) | — | semantic_memory 5.051 | 199/200 chat dùng memory |
| Vector/Embedding BGE-M3 | ✅ embedding.py | ❌ **OFFLINE** (Ollama gỡ) | — | — | mỗi query timeout 6s — **cần circuit breaker (duyệt)** |
| Knowledge Base | ✅ knowledge/ | ✅ | — | knowledge_units=150 (0 thiếu nguồn) | audit 16:3x |
| Learning Engine | ✅ learning/ (12 module) + continuous_learning_daemon | ✅ (daemon duyệt 35% semantic — cần nhãn) | — | candidate 7.852 | pipeline promoted/quarantined |

## C. UNIVERSAL AGENT

| Thành phần | Mã nguồn | DB | Test | Ghi chú trung thực |
|---|---|---|---|---|
| UAIIF knowledge/discovery/profile/qpig | ✅ uaiif/ 5 module | knowledge=8, profiles=1 | ✅ 34/34 | QPIG chưa cắm server chat |
| Agent Registry | ✅ federation_nodes.db=2 | ✅ | ✅ 22/22 | Pi5 + PC core |
| Agent Intelligence Scorecard | ✅ agent_knowledge.py | — | ✅ | 60/100 evidence-based |
| Agent Communication | ⚠️ | — | — | chỉ probe kênh đã đăng ký; **MCP/A2A chưa có** |
| Agent Capability Mapping | ✅ qpig capability_list | — | ✅ | kiosk/audio/camera từ federation |

## D. PHYSICAL INTERACTION

| Thành phần | Trạng thái thật |
|---|---|
| Pi5 192.168.1.2 | REACHABLE nhưng **mọi cổng đóng** — H6 CHƯA ĐẠT, chờ owner 1 bước vật lý |
| QPIG | skeleton 6 nhóm tool ✅ code — chưa chạy thật trên thiết bị |
| QEP | **CHƯA CÓ CODE** — chỉ spec docs/MASTER_PROMPT_UAME_V2.md (UIE sẽ làm Phase QEP) |
| Tool Registry | ✅ code — **0 tool đăng ký** (tool chat chạy ngoài registry — lỗ hổng đã ghi) |
| Protocol Adapters | ❌ chưa có (UART/RS485/MCP/A2A/WS) |
| Device Registry | ✅ federation_nodes.db |

## E. SELF-EVOLUTION

| Thành phần | Trạng thái thật |
|---|---|
| CSEF RC + Approval Gateway | ✅ code + 12/12 test — **chưa có RC nào thực tế, chưa đấu vào DM** |
| AuthorityGovernor | ✅ 32/32 — chưa đấu vào luồng hành động thật |
| Development Sandbox | ✅ TONY_DEVELOPMENT/ 12 thư mục |
| Version Control | ✅ git 5 sprint commit+push 02/11 (43738b3) |
| Rollback | ✅ cơ chế trong RC (rollback_plan bắt buộc) — chưa chạy thật lần nào |
| Secret Approval Code (Method B) | ❌ chưa có — owner tự tạo, chưa giao |
| DM /approve /approval_pending | ❌ chưa có — Method A hiện là DM 2 bước hash |

---

## KẾT LUẬN PHASE 0 — khoảng trống ưu tiên (đúng thứ tự §XVI)

1. **QEP chưa có code** — spec có sẵn, UIE Phase kế thực thi GĐ A (UAME-S5).
2. **Tool Registry rỗng** — tool chạy ngoài registry: đấu QPIG + tool chat vào registry (khắc phục lỗ hổng lớn nhất).
3. **Evidence Store 11 trường** — ✅ ĐÃ HOÀN THÀNH ngay sau audit (4/4 test): `record_incident`/`get_incident` bảng `security_incidents` + evidence payload SHA-256 gắn `incident:<id>`.
4. **DM approval commands** (/approval_pending, /approve <ID>) — Method A chuẩn hóa.
5. **Embedding circuit breaker** — 6s/query → 30ms fail-fast.
6. **Watchdog child interpreter lệch** — chờ duyệt.
7. Pi5 2 chiều — chờ owner chạy script (blocker vật lý, không phải code).

**Trạng thái được phân biệt rõ (§XIV): Đã thiết kế / Đã viết mã / Đã tích hợp / Đã chạy / Đã kiểm thử / Đã xác minh:**
- QEP: ĐÃ THIẾT KẾ (chưa viết mã)
- QPIG/UAIIF/AUTHORITY/CSEF: ĐÃ VIẾT MÃ + ĐÃ KIỂM THỬ (chưa tích hợp hết vào server thật)
- SEC-S1/S3, Memory, DM: ĐÃ CHẠY + ĐÃ XÁC MINH (bằng chứng phiên 02/11)
- Chưa có mục nào "ĐÃ TRIỂN KHAI PRODUCTION" mới — mọi thay đổi hôm nay qua commit+push chờ merge PR.
