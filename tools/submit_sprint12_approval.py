"""Lập card TASK-V3-SPRINT12 — Web & Internal Application Workflows (read-only connectors).

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("duyệt Sprint 12 (Web & Internal Application
Workflows"). Theo roadmap §XIV master prompt Sprint 9: Sprint 12 = Web & Internal
Application Workflows. Read-only tuyệt đối (R1); không form/login/POST ngoài.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT12"
TITLE = "Sprint 12 — Web & Internal Application Workflows (read-only connectors)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT12

## 1. Mục tiêu
Nhân sự số đọc được thông tin từ web/intranet phục vụ nghiên cứu và đề xuất:
tìm kiếm web + đọc trang (READ-ONLY, R1), lấy tin RSS nội bộ, và đề xuất xử lý
có kèm nguồn trích dẫn. KHÔNG form, KHÔNG login, KHÔNG POST/PUT/DELETE ngoài,
KHÔNG tải file, KHÔNG chạy JS — connector thất bại → trả lỗi trung thực.

## 2. Phạm vi
- (a) integration/web_connector.py: WebConnector Protocol + HttpWebConnector
  (urllib chuẩn thư viện, timeout 10s, max 256KB, chỉ GET, SSRF-guard: chỉ
  http/https, chặn loopback/link-local/metadata IP) + RssConnector (feed RSS
  XML stdlib) + robots.txt tôn trọng + content_type allowlist text/html, text/plain,
  application/json, rss/atom.
- (b) API localhost-only: GET /api/web/search?q=&max_results= (DuckDuckGo HTML lite
  scrape đọc-only, kèm nguồn), GET /api/web/page?url= (đọc trang + trích text +
  robots check), GET /api/web/rss?url= (đọc feed). Fail-closed: lỗi → {success:false,
  error} không chết, không fake dữ liệu.
- (c) UI Workbench: khu "🌐 Web & Intranet (read-only)" — search + xem kết quả kèm
  nguồn, đọc trang hiển thị trích dẫn, nút chuyển kết quả thành ghi chú research
  (tạo memory CANDIDATE quarantine — không tự tin vào semantic).
- (d) Đề xuất email (Sprint 10) dùng web search khi bối cảnh cần nghiên cứu:
  PATCH email_intelligence — thêm 'research_links' (tối đa 3 link nguồn, tiêu đề +
  URL) vào proposal khi query khớp từ khoá nghiên cứu (tìm kiếm/tham khảo/nghiên cứu).
  Fail-closed: lỗi web → bỏ qua, không phá proposal.

## 3. Tác động & rủi ro
- File mới: integration/web_connector.py; PATCH server.py (3 endpoint GET);
  executive.html/js (khu web); email_intelligence.py (+research_links).
- Rủi ro: GET-only + SSRF-guard + robots + content-type allowlist + timeout + max
  size; không lưu cookie, không JS, không upload; dữ liệu ngoài KHÔNG tự tin —
  ghi chú research vào memory CANDIDATE (quarantine, chờ duyệt như Sprint 11).
- Không đụng Vmail/R4/R5; không sửa policy engine.

## 4. Tiêu chí nghiệm thu
- GET-only: mọi method khác bị chặn tại connector (ValueError).
- SSRF-guard: URL loopback/private/metadata bị từ chối với lỗi trung thực.
- robots.txt disallow → từ chối đọc trang, không lén đọc.
- Lỗi mạng/timeout → {success:false} trung thực, không fake.
- Search trả kết quả kèm URL nguồn; RSS đọc feed mẫu (mock test + smoke feed thật).
- Proposal email có research_links khi bối cảnh nghiên cứu; không có thì như cũ.
- Regression sạch; smoke thật qua watchdog respawn.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
