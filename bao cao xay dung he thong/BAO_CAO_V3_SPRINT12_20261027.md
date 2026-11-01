# BÁO CÁO V3 SPRINT 12 — WEB & INTERNAL APPLICATION WORKFLOWS (READ-ONLY)

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT12 (PENDING_APPROVAL → APPROVED → consumed; duyệt bởi quanpt1 qua desktop chat "duyệt Sprint 12 (Web & Internal Application Workflows")
**Rủi ro khai báo:** R1 đọc-only tuyệt đối — không form, không login, không POST/PUT/DELETE ngoài, không tải file, không JS.

## 1. Phạm vi đã duyệt và thực hiện
- (a) **`integration/web_connector.py`**: `WebConnector` Protocol; `HttpWebConnector` (GET-only, timeout 10s, max 256KB, content-type allowlist, **SSRF-guard**: chỉ http/https, chặn loopback/private/link-local/reserved/metadata, DNS-resolve trước khi chặn); **robots.txt tôn trọng** (không đọc được robots → từ chối); `DuckDuckGoSearcher` (giữ làm fallback) + **`BingRssSearcher`** (primary — RSS XML chuẩn); `RssConnector` (RSS + Atom).
- (b) **API localhost-only fail-honest:** GET `/api/web/search?q=&max_results=` · GET `/api/web/page?url=` · GET `/api/web/rss?url=&max_items=` — lỗi → `{success:false, error}` trung thực, không fake.
- (c) **UI Workbench:** khu "🌐 Web & Intranet READ-ONLY" — ô tìm kiếm + kết quả kèm URL nguồn.
- (d) **Tích hợp đề xuất email (Sprint 10):** proposal thêm `research_links` (tối đa 3 nguồn, `verified:false`) khi bối cảnh có tín hiệu nghiên cứu — fail-closed: lỗi web → proposal như cũ.

## 2. Ma trận năng lực
| Năng lực | Trạng thái |
|---|---|
| Đọc trang web công khai (GET, robots) | Đã có và hoạt động (smoke: example.com 200) |
| Tìm kiếm web kèm nguồn | Đã có và hoạt động (Bing RSS, smoke 3 kết quả) |
| Đọc RSS/Atom nội bộ | Đã có và hoạt động (smoke VNE 10 items) |
| Chặn SSRF/loopback/metadata | Đã có và hoạt động (test + smoke API) |
| Form/login/ghi ngoài | **Không có — đúng thiết kế R1** |

## 3. Kiểm chứng
- **Test Sprint 12: 28/28 pass** — 8 URL SSRF bị chặn, 4 scheme lạ bị chặn, DNS fail trung thực, RSS parse qua mock urlopen, proposal research_links fail-closed.
- **Full regression: 893 passed / 0 fail / 1 skipped** (857 → +36 — bao gồm cả test Bing mới).
- **Smoke thật live** (server venv PID 19792): SSRF qua API → `success:false` "Chặn địa chỉ nội bộ/metadata (127.0.0.1)"; search "Viettel Solutions tuyển dụng" → 3 kết quả có nguồn; page example.com → title "Example Domain" 200; RSS VNE → 10 items; UI serve `wb-web-result`.

## 4. Lỗi thật bắt được trong smoke (đã sửa + re-test)
1. **`NameError: parsed_query`** trong do_GET — route mới truyền sai biến (`parsed_query` thay vì `parsed.query`) → RemoteDisconnected; test mock không bắt được vì gọi handler trực tiếp. **Bài học: smoke live là bắt buộc.**
2. **DuckDuckGo HTML trả trang anomaly (chặn bot)** → 0 kết quả. Thay bằng **Bing RSS** (XML chuẩn, GET, ổn định) làm primary; DDG giữ làm fallback.
3. **Watchdog đạt cap 5 restart/giờ** sau các lần kill smoke → khởi động tay đúng cấu hình watchdog (venv python + start_dual_servers.py). Ghi nhận: cap là cơ chế bảo vệ đúng — cần gap giữa các smoke kill.

## 5. Giới hạn trung thực
- Tìm kiếm phụ thuộc Bing RSS (không API key) — có thể bị rate-limit; fallback DDG hiện bị anomaly khi không có browser.
- Nội dung web **chưa xác minh** — research_links luôn `verified:false`, không tự tin vào đề xuất.
- Connector ứng dụng nội bộ (M-Suite) chưa có — Vmail vẫn BLOCKED; đây là nền tảng connector pattern cho sau này.

## 6. Next (đề xuất, chờ phê duyệt)
- Sprint 13 (Continuous Improvement — roadmap cuối §XIV): chất lượng đề xuất + tự đánh giá + dashboard năng lực. Cần card riêng.
- Connector nội bộ M-Suite khi owner đổi pass SSO.
