# V10 — MEMORY CHANGE AUDIT
**Ngày:** 28/10/2026 · Kiểm toán mọi thay đổi tri thức phát sinh trong V10 (trên brain.db thật)

## 1. Nguyên tắc ghi thay đổi
- Mọi ghi tri thức đi qua `review_changes` (change_id `chg_*`) với: `before_json`, `after_json`, `reason`, `owner_response_json`, `confirm_state`, `result`, `undo_json`
- Hai chặng bắt buộc: respond (tạo change PENDING) → preview → **confirm lần 2** → APPLIED
- Undo giữ lịch sử: supersede ngược tạo KU mới `review_status=RESTORED_BY_UNDO` (không sửa/KHÔNG xoá row cũ)

## 2. Nhật ký thay đổi đã diễn ra (live smoke 28/10)
| change_id | session | target | kind | before → after | confirm_state | undo |
|---|---|---|---|---|---|---|
| `chg_17f7a8a22571` | `rev_e2991750498b` | `k_45d6541a0245` (v1, "Anh Quân — Quanpt1, chủ sở hữu của em.") | CLARIFY | v1 EXTRACTED → supersede v2 `k_6fb0b4832e89` | **UNDONE** (đã hoàn tác) | ✅ restored_as v3 `k_e2636cae13cc` |

Chuỗi phiên bản của target:
- v1 `k_45d6541a0245` — SUPERSEDED (giữ nguyên row, lịch sử trước)
- v2 `k_6fb0b4832e89` — SUPERSEDED (trạng thái sau thay đổi, đã bị undo)
- v3 `k_e2636cae13cc` — **EXTRACTED** (nội dung gốc được khôi phục, `derived_from=[v2]`, `review_status=RESTORED_BY_UNDO`)

## 3. Phạm vi ảnh hưởng
- Chỉ 1 KU trong phạm vi mẫu 20 bị chạm tới; và đã hoàn tác về nội dung gốc
- Episodes (1.659), memories, relations không bị sửa/xoá
- `PRAGMA integrity_check` = ok (trước + sau)
- Không có thay đổi âm thầm ngoài phạm vi (Test 6 + Test 11 PASS)

## 4. Khả năng hoàn tác
- `undo_json` lưu mode (`supersede_back` / `restore_status` / `restore_scope`) + đối tượng — mọi APPLIED change đều có đường hoàn tác
- Undo tạo bản ghi mới thay vì xoá — an toàn khi có thay đổi hợp lệ phát sinh sau này (PHẦN VII)

## 5. Khuyến nghị
- Dấu vết smoke (2 session COMPLETED + chuỗi supersede v1→v3) có thể giữ nguyên làm bằng chứng kiểm thử, hoặc làm sạch bằng: restore `backups/brain_pre_v10_live_20261028.db` + drop 5 bảng V10 — **chờ Quanpt1 quyết**, mặc định GIỮ NGUYÊN.
