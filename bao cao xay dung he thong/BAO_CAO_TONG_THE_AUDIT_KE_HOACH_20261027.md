# BÁO CÁO TỔNG THỂ HỆ THỐNG + AUDIT + KẾ HOẠCH NÂNG CẤP

**Thời điểm:** 27/10/2026 ~10:00 (dữ liệu probe thật, không dùng dữ liệu cũ)
**Người lập:** Trợ lý QUAN AI BRAIN | **Chủ sở hữu:** quanpt1

---

## PHẦN 1 — TRẠNG THÁI HỆ THỐNG HIỆN TẠI (probe 27/10 10:00)

### 1.1 Hạ tầng chạy 24/7

| Thành phần | Trạng thái probe | Ghi chú |
|---|---|---|
| Dashboard 8765 | 🟢 ONLINE (`success: true`) | LLM cloud GLM-5.3-Flash |
| Core 8766 | 🟢 ONLINE | Executive API |
| **Pi 5 edge** | 🟢 **READY, heartbeat 0.74s, RTT 12.4ms** | paired, kiosk; systemd enabled + Restart=always/3s (đã verify 27/10 sáng) |
| Ollama | 🟢 ONLINE — bge-m3, qwen2.5:7b, qwen2.5:0.5b | VỪA được đưa vào KHOI_DONG_24_7.bat (Sprint 6) |
| NetChat responder | 🟢 chạy (venv + heartbeat) | bot "Trợ lý Tony Pham" 2 chiều |
| Watchdog | 🟢 chạy | auto-restart dual servers |
| Learning daemon | 🟢 chạy | tự học 5 phút/vòng |
| Task backup 2AM | 🟢 Ready → 28/10 02:00 | đã chạy thử OK (`brain_20261027_024356.db`) |
| Task báo cáo sáng 8AM | 🟢 Ready → 28/10 08:00 | đã gửi thử E2E lên kênh |

### 1.2 Dữ liệu & trí nhớ

| Kho | Số liệu | Sức khỏe |
|---|---|---|
| Semantic memory (đã duyệt) | 1.841 tri thức | ổn, không đụng từ Sprint 4 |
| Candidate cách ly | 678 (sạch 0 trùng) + 108.501 archived | đã dedup Sprint 4, backup giữ đủ |
| Approval cards | 4 APPROVED / 0 PENDING / 1 CANCELLED | chu kỳ duyệt vận hành chuẩn consume-once |
| Info-gap tasks chờ | 0 | không có việc treo |
| Backups | 3 file (mới nhất 09:03 hôm nay) | đủ, mới nhất <24h |

### 1.3 Git — chuỗi sprint đã duyệt

```
06b9f06 Sprint 6-GOP (4 hướng: RAG + 24/7 + báo cáo sáng + TTNS)  ← HEAD
7d72f02 Sprint 4 (LLM gap + reminder + dedup 108k)
39770d9 Sprint 3 (Information Gap Engine)
fe0f3fe Avatar sync PC↔Pi5
54a670f External lookup (Gemini + RSS)
f92b32a Pi5 truth probe fix | 634a7c1 ok-confirm | 938d5ba 24/7 stack
```

Working tree sạch. **Full regression: 767 passed / 1 skipped / 0 fail.**

### 1.4 Năng lực trợ lý đã có (đổi mới tính từ 25→27/10)

1. **Nhận biết thiếu thông tin** (Sprint 3): 9 nhóm gap A-I, fail-closed, hỏi đúng người đúng câu, im lặng ≠ đồng ý
2. **LLM gap detection** (Sprint 4a): trích gap từ tiếng Việt tự do, timeout 8s không chậm chat
3. **Auto-reminder** (Sprint 4b): nhắc việc cap 5/12h
4. **Tra cứu ngoài** (54a670f): tin tức tự truy xuất + synthesis, fail-closed
5. **Avatar biểu cảm 4 pha** (fe0f3fe): THINKING → RESEARCHING → SPEAKING+transcript → IDLE, E2E trên Pi thật
6. **Document RAG** (Sprint 6): hỏi sổ tay nội bộ có citation `[tài liệu §mục | version]`, benchmark 10/10
7. **TTNS/lịch họp** (Sprint 6): E2E thật trả lịch họp của anh
8. **Báo cáo sáng tự động** (Sprint 6): 8h hằng ngày qua NetChat
9. **Duyệt có kiểm soát**: card consume-once, 4 sprint duyệt — 4 commit, 0 lần tự ý vượt quyền

---

## PHẦN 2 — AUDIT: ĐIỂM MẠNH / ĐIỂM YẾU / RỦI RO

### 2.1 Điểm mạnh (đo được)

- **Kỷ luật an toàn:** 0 vi phạm R4/R5; mọi thay đổi qua card + duyệt; fail-closed xuyên suốt (gap check, external lookup, RAG, TTNS, báo cáo sáng)
- **Trung thực có cơ chế:** honesty rule chèn vào test (probe lỗi → "chưa xác minh được"); benchmark phạt câu trả lời bịa (no-answer 2 câu)
- **Hồi quy luôn sạch:** 767 test, mọi sprint tăng test ròng, không có fail mang lại
- **Vận hành 24/7 thật:** Pi 5 tự hồi phục đã verify; PC stack đầy đủ daemon + watchdog + task scheduler

### 2.2 Điểm yếu (trung thực, đã đối chứng)

| # | Yếu kém | Bằng chứng | Mức rủi ro |
|---|---|---|---|
| Y1 | **Chưa test reboot thật PC** — toàn bộ stack "24/7" mới chỉ chứng minh khi-running, chưa qua chu kỳ reboot | checklist Sprint 6 mục 2c còn treo | **CAO** — rủi ro mất khả năng tự sống sau mất điện/update Windows |
| Y2 | Benchmark RAG đo trên **kho mẫu 3 tài liệu** + mock embedding — chưa phản ánh kho thật | `sprint6_rag_benchmark.json` | TRUNG BÌNH |
| Y3 | Task Scheduler "Interactive only" — **logon trigger chưa có**: nếu PC reboot mà anh không đăng nhập, task không chạy | `schtasks` Logon Mode: Interactive only | TRUNG BÌNH (liên quan Y1) |
| Y4 | Vmail: chưa tích hợp được — session reset, pass đã lộ trong chat, webmail từng báo "tài khoản bị chặn" | M-Suite đang ở form login | TRUNG BÌNH (nghiệp vụ mail của anh) |
| Y5 | LLM gap detection + LLM faithfulness chưa test E2E với API thật (mock-only theo quy tắc test) | Sprint 4a, Sprint 6 giới hạn | THẤP — chỉ cần 1 lần dùng thật |
| Y6 | Watchdog chỉ giám sát dual servers — responder/learning/Ollama chết thì chỉ cảnh báo GAP-R3, không tự hồi phục | code watchdog.py | TRUNG BÌNH |
| Y7 | 2 instance watchdog + dual servers (venv + system python) chạy song song — rác tiến trình, tài khoản CPU nhẹ nhưng log đè nhau | wmic probe hôm nay | THẤP |
| Y8 | DHCP PC chưa cố định — Pi hard-code IP, PC đổi IP lần nữa sẽ lại mất kết nối (khuyến nghị reservation chưa thực hiện) | Sprint sáng nay fix tay | TRUNG BÌNH (tần suất thấp, hậu quả lớn) |

### 2.3 Đánh giá tổng

Hệ thống ở mức **"Digital Employee vận hành được, an toàn, trung thực"** — 9 năng lực lõi đã hình thành đủ khung (nhận việc → nhận biết thiếu → hỏi → chờ duyệt → tra cứu → trả lời có nguồn → báo cáo tự động). Điểm cần lưu ý nhất **không phải tính năng mới**, mà là **chứng minh độ bền (Y1/Y3)** và **thay thế dữ liệu mẫu bằng dữ liệu thật (Y2/Y4)**.

---

## PHẦN 3 — KẾ HOẠCH NÂNG CẤP TIẾP THEO (đề xuất, chờ duyệt)

### Sprint 7 (đề xuất): "CHỨNG MINH ĐỘ BỀN + DỮ LIỆU THẬT"

| # | Hạng mục | Nội dung | Giải quyết |
|---|---|---|---|
| (a) | **Reboot-proof thật** | Anh nhấn restart PC → em verify sau boot: 5 process + 2 task + Ollama + Pi 5 reconnect; sửa Logon-Mode thành trigger-on-startup (không cần đăng nhập) | Y1, Y3 |
| (b) | **Watchdog mở rộng** | Giám sát responder + learning + Ollama (hiện chỉ dual servers); auto-restart có giới hạn 5 lần/giờ như chuẩn | Y6 |
| (c) | **RAG kho thật** | Anh chỉ định thư mục sổ tay thật → ingest + chạy lại benchmark thật (real BGE-M3, không mock) + câu hỏi thực tế của anh | Y2 |
| (d) | **Dọn tiến trình trùng** | Kill instance thừa (system-python watchdog/servers), chuẩn hoá 1 instance/daemon qua KHOI_DONG | Y7 |

**Kỳ vọng:** +10 test, regression 777+, hệ thống vượt qua 1 chu kỳ reboot thật.

### Sprint 8 (hướng xa hơn — chờ anh xác định ưu tiên)

1. **Bộ kỹ năng văn phòng** (theo yêu cầu "quản lý, xử lý nhiệm vụ văn phòng"): soạn/nháp email có duyệt, quản lý to-do/nhắc việc cá nhân, tổng hợp báo cáo định kỳ
2. **Vmail tích hợp** (sau khi anh đăng nhập lại M-Suite/đổi mật khẩu): đọc hộp thư, tóm tắt mail mới — Y4
3. **Approval Center UI** trên dashboard 8765: xem/phê duyệt card ngay trên web, không cần gõ lệnh
4. **Semantic dedup kho candidate** (678 dòng còn lại — trùng NGHI Ã, khác Sprint 4 chỉ trùng chữ)
5. **Voice 2 chiều Pi 5**: kiosk đã có màn hình — thêm nghe/nói nếu anh dùng

### Việc CHỈ ANH làm được (không có trong sprint)

- ☑ Nhấn **restart PC thật** để test Y1 (10 phút)
- ☑ Đặt **DHCP reservation** cho PC trong router 192.168.1.1 (5 phút) — Y8
- ☑ **Đổi mật khẩu SSO** (đã lộ trong chat) + đăng nhập lại M-Suite — Y4
- ☑ Chỉ định **thư mục tài liệu thật** cho RAG — Y2

---

*Báo cáo lập từ probe thật 27/10 10:00: 2 servers ONLINE, Pi 5 READY hb 0.74s RTT 12ms, Ollama 3 models, 2 task Ready, git HEAD 06b9f06, tree sạch, 767 tests pass, 1841 tri thức đã duyệt.*
