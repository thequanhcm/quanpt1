# DEOM M1 — TÀI LIỆU 4/4: APPROVAL DESIGN (Thiết kế phê duyệt hoàn chỉnh)

**Ngày:** 01/11/2026 · **Cơ sở:** approval_verifier (Q-4, fail-closed HMAC) + approval_cards (20 APPROVED) + charter · **Thiết kế cho M4**

---

## 1. Nguyên tắc bất di bất dịch

1. **Quyền phê duyệt duy nhất thuộc Quanpt1** — không AI, không agent, không quy trình tự động nào tự phê duyệt (charter verbatim).
2. **Fail-closed**: không có verifier cấu hình / token sai / hết hạn → KHÔNG thực thi, không mô phỏng.
3. **1 token = 1 lần dùng** (nonce) — tái dùng bị từ chối.
4. Mọi phê duyệt có vết: ai, khi nào, phê cái gì, bằng chứng nào — vào `audit.db` + approval_cards.
5. R4 KHÔNG có approval hợp lệ → dừng đúng hành động đó, ghi nhận, giải thích, xin lại (DEOM §2.3).

## 2. Đối tượng Approval Card (mở rộng approval_cards hiện có)

```
approval_id        : UUID
task_id            : task cần duyệt (liên kết registry M2)
action_summary     : mô tả ngắn (dùng cho DM 600 ký tự)
risk_level         : R4 (R5 không bao giờ tạo card)
requested_by       : 'tony' | agent id
scope_json         : quyền tối đa cấp cho lần thực thi này
evidence_bundle    : link bằng chứng (logs, reports, diffs)
expires_at_utc     : mặc định 24h — hết hạn phải xin lại
state              : PENDING → APPROVED / REJECTED / CANCELLED / EXPIRED
consumed_at_utc    : filled khi token dùng (1 lần)
```

## 3. Luồng phê duyệt (kết nối kênh thật đã sống)

```
TONY cần R4 → tạo card PENDING + DM NetChat cho anh (≤600 ký tự, tiếng Việt):
  "🟡 XIN DUYỆT <tóm tắt> — rủi ro: <gì>. Phản hồi: OK <mã> / KHÔNG"
  → Anh trả lời DM "OK <mã>" (hoặc "a duyệt" khi code quy ước đang mở)
  → Responder chốt card APPROVED (HMAC token từ approval_verifier)
  → Supervisor chuyển task WAITING_APPROVAL → APPROVED → IN_PROGRESS (scope_json)
  → Sau chạy: VERIFYING → COMPLETED_VERIFIED + báo kết quả kèm bằng chứng
REJECT/CANCEL: card đóng, task → REJECTED/CANCELLED, transition log lý do.
EXPIRED: >24h không phản hồi → card EXPIRED (watchdog quét), nhắc lại tối đa 1 lần/ngày.
```

## 4. Tách người đề xuất / người phê duyệt (approval separation)

- TONY tạo card = **đề xuất** — không thể tự chuyển PENDING→APPROVED (code chặn: chỉ responder nhận lệnh owner mới ghi APPROVED).
- Task do **owner trực tiếp giao** ("làm luôn") vẫn tạo card và tự APPROVED **bởi lệnh owner đó** (actor=owner trong transition log) — không phải TONY tự duyệt.
- Ghi nhận blanket approval (01/11 "anh phê duyệt toàn bộ, làm luôn"): hợp lệ cho **danh mục việc đã liệt kê cụ thể** trong phiên; việc R4 mới phát sinh ngoài danh mục vẫn phải hỏi.

## 5. Human Override (đã có nền — expose M4)

| Lệnh DM | Hành động | Nền hiện có |
|---|---|---|
| "dừng <task>" | STOP task + card CANCELLED | supervisor STOPPED |
| "tạm dừng" | PAUSE toàn bộ executor | supervisor PAUSED/SAFE_MODE |
| "chạy lại" | RESUME có kiểm | supervisor RECOVERING |
| "khoá tự học" | CLO pause (không xóa dữ liệu) | CLO end_session chuẩn |

## 6. Kiểm thử bắt buộc (M4 — trước khi wire thật)

- [ ] self-approval BLOCKED (TONY tự OK token mình → từ chối, log).
- [ ] agent escalation BLOCKED (agent A xin giúp agent B approve → từ chối).
- [ ] token tái dùng → từ chối; token sai HMAC → 401; hết hạn → EXPIRED.
- [ ] unauthorized send/deploy trong ngữ cảnh task → BLOCKED bởi resolver.
- [ ] owner "dừng" giữa chừng → task PAUSED an toàn, checkpoint giữ nguyên.

---
*TONY — DEOM M1 · Approval Design — tách đề xuất/phê duyệt tuyệt đối, fail-closed, vết đầy đủ.*
