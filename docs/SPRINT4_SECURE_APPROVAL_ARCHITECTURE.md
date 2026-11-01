# SPRINT 4 — SECURE OWNER AUTHENTICATION, APPROVAL VERIFICATION & EXECUTION ARCHITECTURE REVIEW

> **Dự án:** QUAN AI BRAIN — Digital Executive Assistant  
> **Tác giả:** AI Software Architect & Senior Python Engineer  
> **Trạng thái:** Kiến trúc thẩm định an toàn (Architecture Review & Verifier Implementation)  
> **Cam kết ranh giới:** Không kích hoạt Production Executor, không cài Windows Service, không chạy Daemon ngầm 24/7 trong Sprint này.

---

## 1. Bối cảnh và Tầm nhìn Kiến trúc (Executive Overview)

Trong Sprint 3B, QUAN AI BRAIN đã thiết lập thành công nguyên tắc bất biến: **Owner Consent First**. Mọi hành vi gọi công cụ (kể cả đọc tệp hay truy vấn bộ nhớ R0) mặc định đều bị chặn (`pending_owner_approval`) trừ khi có sự phê duyệt hợp lệ của chủ nhân hoặc thuộc phạm vi ủy quyền tự quyết (`DelegationGrant`).

Tuy nhiên, kiểm toán an toàn Sprint 3B chỉ ra các lỗ hổng mang tính nền tảng:
1. **Định danh chủ nhân chưa có bằng chứng mật mã:** Hệ thống chấp nhận chuỗi định danh tĩnh (`owner:quanpt1`) hoặc phản hồi Yes/No từ terminal mà chưa xác minh người gửi có thực sự sở hữu khóa bí mật của chủ nhân hay không.
2. **Trạng thái quyền hạn chưa bền vững (In-memory State):** `ApprovalGate`, `DelegationRegistry` và trạng thái `SystemState.STOP` / `FREEZE` hiện lưu trữ trong RAM; nếu tiến trình khởi động lại, trạng thái bảo vệ bị tái lập về ban đầu.
3. **Thiếu cơ chế xác thực kênh ngoài (Out-of-Band - OOB):** Các thao tác nhạy cảm chưa có lớp phòng vệ thứ hai độc lập với terminal máy chủ.

Theo yêu cầu trực tiếp của chủ nhân: **"cần xác thực bằng mã bảo mật riêng của anh hoặc OTP qua SMS điện thoại"**, tài liệu này chuẩn hóa toàn bộ kiến trúc xác thực đa nhân tố, thẩm định phê duyệt bằng chữ ký mật mã, và đánh giá kiến trúc cho Production Executor / Daemon trong các sprint tiếp theo.

---

## 2. Mô hình đe dọa (Threat Model)

Hệ thống được thiết kế để phòng vệ trước các kịch bản đe dọa sau:

| Mã nguy cơ | Tên nguy cơ | Kịch bản tấn công | Cơ chế phòng vệ Sprint 4 |
| :--- | :--- | :--- | :--- |
| **T-01** | **Identity Spoofing** (Mạo danh chủ nhân) | Mã độc hoặc script giả lập chuỗi định danh `"owner:quanpt1"` gửi vào sandbox. | Bắt buộc có **Chữ ký mật mã HMAC-SHA256** dựa trên Mã bảo mật riêng hoặc **SMS OTP** gửi trực tiếp tới điện thoại chủ nhân. |
| **T-02** | **Parameter Tampering** (Sửa tham số sau duyệt) | Kẻ tấn công xin duyệt lệnh `file_read README.md`, nhưng khi chạy tráo tham số thành `file_read .env`. | **Action Fingerprint (SHA-256):** Băm toàn bộ tham số, scope, tool ID. Mọi thay đổi 1 bit đều làm sai lệch fingerprint và hủy bỏ phê duyệt ngay lập tức. |
| **T-03** | **Replay Attack** (Tấn công phát lại) | Kẻ tấn công bắt gói tin approval hợp lệ từ quá khứ và gửi lại nhiều lần để thực thi lặp. | **Single-Use Consumption & Nonce:** Mỗi token approval có một `nonce` ngẫu nhiên và chỉ được tiêu thụ 1 lần duy nhất (`consumed=True`). Token đã tiêu thụ bị khóa vĩnh viễn. |
| **T-04** | **Stale Authorization** (Phê duyệt quá hạn) | Lệnh được duyệt từ hôm trước nhưng bị hoãn và chạy vào thời điểm không còn phù hợp. | **Time-to-Live (TTL):** Mỗi phê duyệt có trường `expires_at` (mặc định tối đa 5 phút cho phê duyệt tương tác, 180s cho SMS OTP). Hết hạn sẽ tự động chuyển sang `EXPIRED`. |
| **T-05** | **Rogue LLM Elevation** (AI tự cấp quyền) | Mô hình LLM tự sinh câu trả lời tự nhận là chủ nhân hoặc tự hạ mức rủi ro từ R4 xuống R1. | **Independent Governance Gate:** Verifier và PolicyEngine chạy bằng mã Python tất định độc lập, nằm ngoài context của LLM; LLM không có quyền truy cập hàm ký hoặc cấp token. |
| **T-06** | **Brute-Force OTP** (Vét cạn mã OTP) | Kẻ tấn công cố thử 1,000,000 mã 6 chữ số để vượt qua xác thực SMS. | **Attempt Limiter & Rate Limiter:** Giới hạn tối đa 3 lần thử sai; quá 3 lần token OTP lập tức bị hủy bỏ (`REVOKED`). Khoảng cách giữa 2 lần xin cấp OTP tối thiểu 60 giây. |
| **T-07** | **Process Restart Bypass** (Vượt rào bằng khởi động lại) | Cố tình làm crash tiến trình để xóa trạng thái STOP/FREEZE hoặc xóa danh sách token đã bị thu hồi. | **Persistent State:** Lưu trữ Blocklist token và System State xuống cơ sở dữ liệu bền vững (SQLite WAL mode). |

---

## 3. Kiến trúc xác thực danh tính chủ nhân 2 kênh (Dual-Channel Authentication)

Hệ thống hỗ trợ 3 chế độ xác thực theo chỉ thị của chủ nhân:

```
                                      [ Yêu cầu gọi công cụ ]
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ PolicyEngine (R0-R5)  │
                                     └───────────┬───────────┘
                                                 │
                              ┌──────────────────┴──────────────────┐
                              │ R5: Chặn cứng (BLOCKED)             │
                              │ R0-R2: Cần Consent / Delegation     │
                              │ R4: Bắt buộc Phê duyệt xác thực cao │
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Verification Gateway  │
                                     └───────────┬───────────┘
                                                 │
            ┌────────────────────────────────────┼────────────────────────────────────┐
            ▼                                    ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐          ┌─────────────────────────┐
│ Kênh 1: MÃ BẢO MẬT RIÊNG│          │ Kênh 2: SMS OTP         │          │ Chế độ DUAL-FACTOR      │
│ (Owner Private Passcode)│          │ (Out-of-Band Mobile)    │          │ (Mã riêng + SMS OTP)    │
│                         │          │                         │          │                         │
│ • HMAC-SHA256 Signature │          │ • 6 chữ số ngẫu nhiên   │          │ • Bắt buộc cho R4       │
│ • Canonical Envelope    │          │ • TTL 180 giây          │          │ • Thao tác nhạy cảm cao │
│ • Salted Hash verify    │          │ • Max 3 lần thử         │          │ • Cả 2 kênh cùng đạt    │
└───────────┬─────────────┘          └───────────┬─────────────┘          └───────────┬─────────────┘
            │                                    │                                    │
            └────────────────────────────────────┼────────────────────────────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │ AuthenticatedApprovalVerifier│
                                  │ • Kiểm tra Signature / OTP  │
                                  │ • So khớp Fingerprint       │
                                  │ • Kiểm tra Expiry & Nonce   │
                                  │ • Kiểm tra Anti-replay      │
                                  └──────────────┬──────────────┘
                                                 │
                                       [ Phê duyệt hợp lệ ]
                                                 │
                                                 ▼
                                      ┌─────────────────────┐
                                      │ SafeToolSandbox     │
                                      │ (R0-R2 thực thi)    │
                                      └─────────────────────┘
```

### Kênh 1: Xác thực bằng Mã bảo mật riêng (Owner Private Secret Code)
- **Cơ chế:** Chủ nhân sở hữu một mã bí mật riêng (Owner Passcode / Secret Key).
- **Nguyên tắc không lưu Plaintext:** Mã bí mật tuyệt đối không được ghi vào mã nguồn, file cấu hình `.json` hay cơ sở dữ liệu.
- **Xác minh qua HMAC-SHA256:**
  - Payload chuẩn hóa: `canonical_string = f"{approval_id}|{tool_id}|{action}|{fingerprint}|{nonce}|{expires_at}"`
  - Chữ ký: `signature = hmac.new(secret_bytes, canonical_string.encode('utf-8'), hashlib.sha256).hexdigest()`
  - So khớp an toàn: Sử dụng `hmac.compare_digest(provided_signature, expected_signature)` để triệt tiêu lỗ hổng tấn công phân tích thời gian (timing attack).

### Kênh 2: Xác thực qua SMS OTP điện thoại (Out-of-Band Channel)
- **Cơ chế:** Hệ thống sinh mã OTP ngẫu nhiên an toàn bằng `secrets.randbelow(1000000)` (định dạng 6 chữ số: `000000` - `999999`).
- **Gửi tin nhắn kênh ngoài:** Mã được gửi tới số điện thoại di động đã được đăng ký và xác nhận duy nhất của chủ nhân.
- **Ràng buộc an toàn:**
  - **Thời hạn sống (TTL):** Tối đa 180 giây (3 phút).
  - **Giới hạn số lần thử (Max attempts):** Tối đa 3 lần. Sau lần thứ 3 sai, hủy phiên xác thực ngay lập tức.
  - **Gắn chặt với Action Fingerprint:** Mã OTP chỉ có giá trị cho đúng hành động và tham số của phiên yêu cầu đó; không thể dùng OTP của hành động này cho hành động khác.

### Chế độ Xác thực kép (Dual-Factor Verification)
- **Áp dụng:** Bắt buộc cho toàn bộ hành động có mức độ rủi ro **R4** (hành động thay đổi cấu hình hệ thống lớn, can thiệp tài nguyên quan trọng).
- **Yêu cầu:** Người phê duyệt phải cung cấp đồng thời cả **Mã bảo mật riêng hợp lệ** VÀ **Mã SMS OTP hợp lệ** trong cùng một phiên phê duyệt. Thiếu 1 trong 2 yếu tố, quyền bị từ chối ngay.

---

## 4. Quản lý Khóa và Bảo vệ Bí mật (Key Management Lifecycle)

Tuân thủ nghiêm ngặt nguyên tắc của `AGENTS.md`: *"Never open, print, copy, or log secret values"*:

1. **Nạp khóa từ Trust Anchor:**
   - Khóa bí mật hoặc hash salt được cấu hình qua biến môi trường được bảo vệ riêng của OS hoặc qua module Keyring của hệ điều hành.
   - Khi chạy ở môi trường kiểm thử (Testing / CI), Verifier cho phép nạp Mock Trust Anchor được cô lập trong fixture của bài test và tự động tiêu hủy sau khi test kết thúc.
2. **Trạng thái Mặc định khi thiếu Khóa (Default Deny):**
   - Nếu hệ thống chạy mà không phát hiện cấu hình Trust Anchor hợp lệ, Verifier **tuyệt đối không tự động sinh khóa ngầm**, không hạ rào an toàn, mà lập tức chuyển sang trạng thái `DENIED_NO_TRUST_ANCHOR` và từ chối mọi yêu cầu thực thi.
3. **Quy trình thay khóa (Key Rotation):**
   - Hỗ trợ cấu hình `Key ID` (vd: `key_2026_v1`, `key_2026_v2`).
   - Cho phép thời gian chuyển tiếp (grace period) nhận diện cả khóa cũ và khóa mới trong quá trình xoay vòng khóa.
4. **Quy trình ứng phó khi lộ khóa (Compromise Protocol):**
   - Chủ nhân kích hoạt lệnh `REVOKE_ALL_KEYS` hoặc chuyển `SystemState` sang `STOP` / `FREEZE`.
   - Vô hiệu hóa toàn bộ token đang chờ và làm mới định danh tin cậy.

---

## 5. Tính Bền vững của Trạng thái Quyền hạn (Persistent Governance State)

Để khắc phục điểm yếu lưu trữ RAM của Sprint 3B:
1. **Bảng lưu trữ SQLite (`security_approvals`):**
   - `approval_id` (PRIMARY KEY)
   - `action_fingerprint` (TEXT)
   - `verification_method` (TEXT)
   - `status` (TEXT: pending, approved, completed, expired, revoked)
   - `consumed_at_utc` (TEXT, NULL nếu chưa dùng)
   - `expires_at_utc` (TEXT)
   - `attempts_count` (INTEGER)
   - `audit_ref` (TEXT)
2. **Khối chặn Token đã tiêu thụ (Consumed Blocklist):**
   - Được ghi trực tiếp xuống đĩa (WAL mode). Khi tiến trình khởi động lại, Verifier đọc lại danh sách token đã dùng và token bị thu hồi để đảm bảo **không bao giờ có thể replay token cũ sau khi restart**.
3. **Bền vững hóa trạng thái Khẩn cấp:**
   - Trạng thái `SystemState.STOP` và `SystemState.FREEZE` được lưu trong file cờ trạng thái bền vững hoặc bảng cấu hình. Khi khởi động lại, nếu hệ thống đang ở trạng thái `FREEZE`, nó vẫn giữ nguyên trạng thái `FREEZE` cho đến khi có lệnh giải phóng tường minh từ chủ nhân.

---

## 6. Ranh giới Phê duyệt một lần vs. Ủy quyền tự quyết (Delegation Grant)

| Đặc tính | Phê duyệt một lần (`OwnerApproval`) | Ủy quyền tự quyết (`DelegationGrant`) |
| :--- | :--- | :--- |
| **Phạm vi áp dụng** | 1 hành động công cụ cụ thể với tham số chính xác | 1 nhóm tác vụ định kỳ hoặc kế hoạch giới hạn |
| **Cơ chế tiêu thụ** | Tiêu thụ 1 lần (`Single-use`), dùng xong hủy | Giới hạn theo ngân sách số lần gọi (`max_calls`) |
| **Hạn mức rủi ro** | R0, R1, R2, R4 (R4 cần Dual-Factor) | **Tối đa R2**. Tuyệt đối cấm R4 và R5 |
| **Cơ chế xác thực** | Mã bảo mật riêng hoặc SMS OTP | Yêu cầu chữ ký của chủ nhân khi tạo grant |
| **R5 Hard-block** | **Bị chặn cứng** | **Bị chặn cứng** |

---

## 7. Đánh giá Kiến trúc Production Executor và Daemon nền tảng (Review Only)

> **CẢNH BÁO QUAN TRỌNG:** Hạng mục này chỉ phục vụ đánh giá thiết kế kỹ thuật. Không có mã khởi động daemon, không cài đặt Windows Service và không có Production Executor nào được triển khai hay cấp phép trong Sprint 4.

### 7.1. Ranh giới Hộp cát Thực thi Sản xuất (Production Executor Boundaries)
Khi bước vào giai đoạn sản xuất (các sprint tương lai), một Executor phải tuân thủ 7 nguyên tắc:
1. **Pre-execution Gate:** Kiểm tra chữ ký và quyền hạn ngay tại nano-giây trước khi gọi lệnh thực thi (Just-In-Time Authorization), ngăn chặn time-of-check to time-of-use (TOCTOU).
2. **Idempotency (Tính bất biến):** Mọi hành vi ghi phải có mã băm trạng thái và khóa bất biến, đảm bảo nếu mạng ngắt hoặc lỗi giữa chừng, việc chạy lại không gây nhân đôi tác động.
3. **Post-condition Verification:** Sau khi chạy xong, phải có bước kiểm tra bằng chứng (vd: tệp đã được tạo đúng kích thước, hash tệp trùng khớp, dịch vụ phản hồi HTTP 200).
4. **Checkpoint & Rollback:** Tự động tạo bản sao lưu (snapshot) trước khi sửa đổi, có khả năng hoàn tác (rollback) khi có sự cố.
5. **Execution Timeout:** Mọi tiến trình con hoặc kết nối mạng phải có hard timeout (tối đa 30s-120s tùy hành động).

### 7.2. Kiến trúc Daemon / Background Worker
Nếu triển khai daemon trong tương lai:
1. **Không chạy quyền Administrator:** Daemon chỉ được chạy dưới tài khoản dịch vụ có đặc quyền tối thiểu (Least Privilege).
2. **STOP/FREEZE Precedence:** Hàng đợi nhiệm vụ (Task Queue) phải kiểm tra cờ STOP trước khi lấy bất kỳ tác vụ nào ra xử lý. Khi phát hiện cờ STOP, toàn bộ worker phải tạm dừng lập tức.
3. **Heartbeat & Liveness Watchdog:** Daemon phát tín hiệu heartbeat định kỳ vào file log; nếu watchdog phát hiện bất thường, tự động cô lập dịch vụ.
4. **Không tự động khởi động cùng hệ điều hành:** Tránh cài đặt Registry Run key hay Windows Service tự khởi động khi chưa qua nghiệm thu toàn diện của chủ nhân.

---

## 8. Tiêu chí nghiệm thu an toàn (Gate Acceptance Criteria)

Trước khi bất kỳ Production Executor nào được phép xem xét triển khai:
- [x] Lớp `AuthenticatedApprovalVerifier` được triển khai độc lập, có bài test xác minh cho cả Mã bí mật riêng và SMS OTP.
- [x] R5 luôn bị từ chối tuyệt đối, không có bất kỳ ngoại lệ nào.
- [x] Khi thiếu Trust Anchor hoặc khóa bí mật, mặc định từ chối toàn bộ yêu cầu.
- [x] Thử nghiệm tấn công replay, giả mạo tham số, tráo chữ ký, và vét cạn OTP đều bị chặn 100%.
- [x] Báo cáo kiểm thử phản ánh số liệu thực tế, không có số liệu hardcode.
- [x] Không can thiệp bất kỳ tệp tin nào ngoài workspace `E:\AI\QUAN AI BRAIN`.
- [x] Không có bí mật (mật khẩu, khóa riêng, token) nào bị lưu trữ trong mã nguồn hoặc tệp log.

---

*Tài liệu kiến trúc này là cơ sở pháp lý và kỹ thuật định hướng cho toàn bộ các module an toàn của QUAN AI BRAIN từ Sprint 4 trở đi.*
