# TONY RISK REGISTER — Sổ rủi ro (PHẦN XV)
**Cập nhật:** 01/11/2026 16:45 · 17 nhóm rủi ro master prompt + rủi ro phát hiện thêm

| Risk ID | Mô tả | Xác suất | Tác động | Mức | Bằng chứng | Giảm thiểu | Trạng thái |
|---|---|---|---|---|---|---|---|
| R01 | HMAC chưa verify (giả mạo hình thể) | — | — | — | — | M6-B1 fail-closed | ✅ **ĐÓNG 15:50** (6/6 tests, 0 fault 120s) |
| R02 | Edge-TTS 403 → TONY không nói được | Cao | TB | P0 | G-33 flaky | Q-3 Piper (đã duyệt, hàng đợi) | 🟡 CHỜ LÀM |
| R03 | 3.088 candidates kẹt quarantine | Chắc | TB | P0 | DB live | Q-4 verifier (đã duyệt, sau Q-3) | 🟡 CHỜ LÀM |
| R04 | Không mic/loa Pi5 → voice chết | Chắc | TB | P1 | alsa_cards=0 | AUDIO: gắn USB (cần duyệt) | 🟡 CHỜ DUYỆT |
| R05 | reflection.py mất hypothesis | Cao | TB | P1 | M2 root-cause | Fix M2 (cần duyệt) | 🟡 CHỜ DUYỆT |
| **R-new01** | **Watchdog MISSING — tự hồi phục vĩnh viễn tắt** | Cao | Cao | **P1** | 0 process 16:33 | Bật lại qua KHOI_DONG phần [4/5] | 🔴 MỚI — CẦN DUYỆT |
| **R-new02** | **Backup 2AM dừng từ 28/10 — mất mốc phục hồi DB** | Cao | Cao | **P1** | brain_*.db mới nhất 28/10 | Kiểm tra + bật lại task; mirror F tạm bù 24h | 🔴 MỚI — CẦN DUYỆT |
| R06 | CriticalThinker orphan → suy luận mỏng | TB | Thấp | P2 | M2 audit | Tích hợp P2 | TODO |
| R07 | Không git → không track changes | Cao | Thấp | MED | chưa init | Q-1 (chờ duyệt) | CHỜ DUYỆT |
| R08 | NetChat rate-limit suspend | TB | TB | MED | sự cố 01:07 | backoff 90s + suspended-aware ✅ | GIẢM ĐÃ XÁC MINH |
| R09 | DB hỏng khi mirror/copy thô | Thấp | Cao | MED | — | sqlite backup API + integrity ✅ | ✅ GIẢM (mirror mới) |
| R10 | Server.py 272KB khó bảo trì | Chắc | Thấp | P3 | inventory | Tách blueprint P3 | TODO |
| R11 | Credential lộ | Thấp | Nghiêm trọng | MED | — | [REDACTED] policy + HMAC key file 600 | KIỂM SOÁT |
| R12 | Task treo không ai phát hiện | TB | TB | MED | CLO-stall alert ✅ | edge-trigger + reminder | KIỂM SOÁT |
| R13 | Dữ liệu cũ dùng như hiện tại | TB | TB | MED | audit 12:30 cũ | Nguyên tắc evidence-live (đã áp) | KIỂM SOÁT |

## STOP/FREEZE & phục hồi an toàn

- NÚT STOP: ✅ có, đã dùng (01/11) — chỉ thoát UI + flag 15'.
- FREEZE learning: approval gate — ✅.
- Khôi phục toàn hệ thống: **mới** — mirror F:\BRAIN hằng ngày + .venv chạy được → RTO ≈ copy ngược (phút). ✅ R09→đã giảm.

**Điều kiện chấp nhận rủi ro hiện tại:** Mirror F bù backup 24h (R-new02 tạm chấp nhận CHỜ DUYỆT bật lại backup 2AM); watchdog tắt tạm chấp nhận DO services ổn định + KHOI_DONG chuẩn — không chấp nhận kéo dài quá 48h.
