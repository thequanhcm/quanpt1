# BÁO CÁO SPRINT SEC-S1 — TONY NHÂN VIÊN AN NINH (Hợp đồng + Vệ sĩ + Tạm giữ)
**Ngày:** 02/11/2026 · **Card:** TASK-SEC-S1 (APPROVED + consumed, auth `owner_desktop_chat_directive`) · **Rủi ro:** R2

## 1. Phạm vi đã làm (đúng 4 hạng mục card)
| Hạng mục | File | Nội dung |
|---|---|---|
| (a) Hợp đồng nhiệm vụ | `src/quan_ai_brain/security/task_contracts.py` | `TaskContract` (subject/goal/allowed_paths/allowed_domains/cpu+mem cap/expires_at/auto_contain) + `TaskContractStore` SQLite idempotent + `parse_dm_contract()` fail-honest |
| (b) Vệ sĩ giám sát | `src/quan_ai_brain/security/watcher.py` | `SecurityWatcher` quét tasklist/netstat (stdlib, chỉ đọc) + `detect_violations()` 4 loại (UNREGISTERED / OUT_OF_SCOPE_PATH / OUT_OF_SCOPE_DOMAIN / OVER_CONTRACT) + `SecurityEventStore` bằng chứng append-only |
| (c) Hành động tạm giữ | `src/quan_ai_brain/security/actions.py` | Suspend/Resume (NtSuspendProcess/NtResumeProcess ctypes) + Kill (taskkill) · **PROTECTED_WHITELIST cứng** refuse fail-closed (hệ thống Windows + chính TONY/netMind) |
| (d) Lệnh DM | `tools/netchat_security_center.py` + wire `netchat_command_center.py` + `watchdog.py` | `an ninh` / `giữ <pid>` / `thả <pid>` / `hạ <pid>` / `giao nhiệm vụ cho <AI>: ... \| phạm vi: ... \| miền: ... \| hạn: N phút \| tự giữ` · chu kỳ quét gắn vào watchdog main loop (0 chi phí khi chưa có hợp đồng) |

## 2. Bằng chứng kiểm thử (số thật)
- **Test mới: 26/26 PASS** (`tests/test_sec_s1_security.py`, mock 100% + tmp_path).
- **Full regression: 3.348 passed / 0 FAILED / 45 skipped** (5:04) — baseline 3.322 + 26 mới.
- **Live smoke (01:00–15:05, 02/11):**
  - `list_processes` thật: 251 tiến trình; `list_network_connections`: 0 kết nối ngoài.
  - **TỰ BẢO VỆ THẬT**: yêu cầu suspend watchdog thật (PID 12572) → REFUSE đúng whitelist `tools\watchdog.py` ✅.
  - Full chain DM thật qua `route_message`: "an ninh" → trạng thái; "giữ 999999" → từ chối trung thực (PID không tồn tại); "giao nhiệm vụ cho demo-agent..." → hợp đồng thật vào `data/security_contracts.db` (auto_contain=True, hạn 5 phút) → chu kỳ watchdog chạy = 0 vi phạm (đúng — không có tiến trình demo) → revoke dọn dẹp.
  - **E2E tự hồi phục**: kill responder + watchdog cũ (chạy code trước SEC-S1) → spawn watchdog mới → nó **tự phát hiện responder chết và spawn lại** (heartbeat 13s) — responder hiện chạy code mới có lệnh an ninh.

## 3. Mô hình quyền lực (owner chọn "tạm thời nắm quyền kiểm soát, quản trị")
- 🟢 Quan sát + ghi bằng chứng: luôn bật (chỉ đọc, 0 chi phí khi chưa có hợp đồng).
- 🟡 TẠM GIỮ NGAY: khi hợp đồng có `tự giữ` (auto_contain=True) — treo tiến trình giữ dữ liệu, DM báo anh trong cùng chu kỳ.
- 🔴 Hạ gục / thả: chỉ theo lệnh anh (`hạ <pid>` / `thả <pid>`).
- ⛔ Whitelist cứng: Windows system + TONY/netMind — refuse cả khi owner ra lệnh nhầm.

## 4. Trung thực — giới hạn hiện tại
- Giám sát "họ hàng" theo keyword subject trong tên tiến trình/cmdline — agent đổi tên hoàn toàn sẽ không khớp (S2: giám sát theo parent-child tree + hash).
- Hạ gục tiến trình SYSTEM/admin: không có quyền (chỉ báo cáo trung thực).
- AI cloud: chỉ thấy điểm chạm từ máy mình (S2: giám sát lưu lượng domain).
- CPU/mem cap có trong hợp đồng nhưng chưa wired vào detect (S2).

## 5. Bước tiếp theo (đề xuất S2)
- Giám sát resource thật (psutil) + violation OVER_CONTRACT theo cap.
- Parent-child tree tracking (bắt agent tự đẻ tiến trình con).
- Tab "An ninh" trên dashboard 8766.
