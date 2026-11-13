# Phân tích: ATTT trong kỷ nguyên Agentic AI — định hướng cho CHERRY

Nguồn: `kho_tai_lieu/261113_VTNET_ATTT_Agentic_AI_v4.pdf` (VTNET, 11/2026, 21 slides)
Ngày phân tích: 13/11/2026
Audit hiện trạng: quét 43 file có keyword security + đọc guardrails.py, policy.py,
chat_bridge.py, server.py /api/chat, netchat_auto_responder.py

## 1. Tài liệu nói gì (tóm tắt khung)

| Phần | Nội dung | Áp dụng CHERRY |
|---|---|---|
| Phần 1 — Nhận diện | Agentic AI = AI hành động; prompt injection (dữ liệu thành lệnh); EchoLeak CVE-2025-32711 CVSS 9.3 zero-click; deepfake/mạo danh | CHERRY đọc tin DM + web + tài liệu = bề mặt tấn công giống y hệt EchoLeak |
| Phần 2 — Đánh giá | 3 nhóm rủi ro Con người/Dữ liệu/Hệ thống; thang quyền 3 mức; "lethal trifecta" (dữ liệu riêng tư + nội dung không tin cậy + egress); quyền mặc định thừa (Double Agent Vertex AI) | CHERRY có DM (egress), có knowledge (private data), đọc tin ngoài (untrusted) → phải tách/tăng kiểm soát khi hội đủ |
| Phần 3 — Bảo vệ | Least privilege; sandbox; phased deployment; guardrail human-in-the-loop; hồ sơ kiểm toán; 3 câu hỏi trước khi Enter | 3 lớp AUTO/PROPOSE/NEVER của CHERRY = chính phased deployment + human-in-the-loop |

## 2. Hiện trạng CHERRY — đã khớp khung

- ✅ Output guardrails: `OutputGuardrails.sanitize()` redact credential + script tag
- ✅ Grounding analysis: `analyze_grounding()` chống hallucination
- ✅ Tool description injection check: 5 patterns (chat_bridge.py §III)
- ✅ Integration policy: allowlist + rate limit + R5 hard-block + emergency fail-closed
- ✅ 3 lớp autonomous: AUTO (budget 2/giờ) / PROPOSE (DM 2 bước token) / NEVER
- ✅ Least privilege: localhost-only API, permission whitelist, audit trail
- ✅ Approval card: owner duyệt trước khi làm (đang dùng cho sprint này)

## 3. 4 GAP xác định (cần xây dựng)

| Gap | Tài liệu | Hiện trạng | Rủi ro |
|---|---|---|---|
| GAP-1 Input Injection Shield | Slide 7+8: EchoLeak tấn công ở INPUT | /api/chat + DM responder KHÔNG quét injection ở đầu vào (chỉ chặn tool description + output) | Tin DM/web chứa "bỏ qua hướng dẫn..." → CHERRY làm theo |
| GAP-2 Lethal Trifecta Guard | Slide 13: bộ ba nguy hiểm | Chưa có phát hiện task hội đủ 3 cờ | Task AUTO tự động lấy dữ liệu riêng + đọc tin độc + gửi ra ngoài |
| GAP-3 Untrusted Content Label | Slide 7: "nội dung ngoài = dữ liệu không tin cậy" | Context từ web/knowledge ngoài không được đánh dấu | LLM phân biệt lệnh vs dữ liệu kém |
| GAP-4 Audit nguồn dữ liệu | Slide 11: sự cố đi qua cả 3 nhóm | Audit event thiếu field nguồn dữ liệu | Không truy vết được đường đi khi có sự cố |

## 4. Kế hoạch áp dụng — TASK-AGENTIC-SEC-1 (PENDING_APPROVAL)

- Slice (a): `src/quan_ai_brain/security/input_shield.py` — 12+ pattern EN+VN,
  score 0-100, verdict ALLOW/SANITIZE/BLOCK; wire vào /api/chat + DM responder.
- Slice (b): nhãn `[DỮ LIỆU KHÔNG TIN CẬY — nguồn: X]` bọc context ngoài.
- Slice (c): `security/trifecta_guard.py` — 3 cờ; đủ cả 3 → FORCE PROPOSE.
- Slice (d): audit event thêm `data_source_labels`.
- Nghiệm thu: ≥16 test mock, full regression, live smoke (chat thường + injection mẫu).

## 5. Đã gửi DM owner

post_id `npeyods5ffff8mjjj4cnciax3h` (13/11) — tóm tắt 4 gap + xin duyệt card.
