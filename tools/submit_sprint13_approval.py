"""Lập card TASK-V3-SPRINT13 — Continuous Improvement (self-assessment & capability matrix).

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("duyệt Sprint 13").
Theo roadmap §XIV master prompt Sprint 9: Sprint 13 = Continuous Improvement (sprint
cuối của lộ trình đề xuất). KHÔNG trùng cognitive_loop.reflect — lớp tổng hợp + UI.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT13"
TITLE = "Sprint 13 — Continuous Improvement (capability matrix & improvement report)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT13

## 1. Mục tiêu
Nhân sự số tự đánh giá năng lực bằng DỮ LIỆU THẬT (số test, số lesson, số đề xuất,
tỷ lệ từ chối, uptime) — không tự khen: mỗi mục năng lực kèm bằng chứng truy vết
được. Xuất báo cáo cải tiến + ma trận 5 mức (master prompt §2.3) vào Workbench.

## 2. Phạm vi
- (a) cognition/improvement_report.py: build_improvement_report() tổng hợp từ DB
  hiện có — tasks (COMPLETED/FAILED/CANCELLED), approvals (duyệt/từ chối/tỷ lệ),
  lessons (candidates/confirmed), proposals (đã tạo/đã link task), tests (đọc số
  từ báo cáo Sprint gần nhất nếu có, không tự chạy pytest), gaps (số info gap mở).
  Mỗi mục kèm evidence (nguồn DB + số liệu + thời điểm). KHÔNG tự đánh giá "giỏi/xấu"
  — chỉ số liệu + trạng thái 5 mức.
- (b) API: GET /api/improvement/report (localhost-only, fail-honest từng khối như
  workbench overview).
- (c) UI Workbench: khu "📈 Continuous Improvement" — ma trận năng lực 5 mức +
  số liệu chính + nút xuất báo cáo .md vào 'bao cao xay dung he thong/' (R2 ghi
  trong workspace, an toàn).
- (d) Không tự sửa code, không tự chạy pytest trong luồng này (trung thực: báo cáo
  test lấy từ file báo cáo gần nhất; nếu không có → CHƯA XÁC MINH).

## 3. Tác động & rủi ro
- File mới: cognition/improvement_report.py; PATCH server.py (1 GET); executive.js/html.
- Rủi ro thấp: chỉ ĐỌC các DB hiện có + GHI 1 file báo cáo .md khi anh bấm.
- Không trùng: cognitive_loop.reflect (phản chiếu 1 task) — cái này là tổng hợp
  hệ thống; workbench overview (tổng quan realtime) — cái này là đánh giá năng lực.

## 4. Tiêu chí nghiệm thu
- Mỗi mục ma trận kèm evidence truy vết được (DB + số liệu).
- DB lỗi → mục đó CHƯA XÁC MINH (không chết, không 0 giả).
- Xuất báo cáo .md thành công vào thư mục báo cáo; nội dung khớp API.
- Regression sạch; smoke thật qua server live.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
