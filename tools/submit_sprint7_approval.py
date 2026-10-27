"""Lập card TASK-V3-SPRINT7 — Chứng minh độ bền + dữ liệu thật.

V3 §5: card ĐI TRƯỚC khi thực hiện. Sprint 7 gồm 4 hạng mục (a-d) từ audit
27/10 10:00: Y1 (reboot thật), Y3 (startup trigger), Y6 (watchdog mở rộng),
Y2 (RAG kho thật), Y7 (dọn tiến trình trùng).
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(r"E:\AI\QUAN AI BRAIN")
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

CARD = """# TASK-V3-SPRINT7 — CHỨNG MINH ĐỘ BỀN + DỮ LIỆU THẬT

**Nguồn:** Audit 27/10 10:00 (BAO_CAO_TONG_THE_AUDIT_KE_HOACH_20261027.md)
**Mức rủi ro:** R2 (không đụng secret, không API ghi ngoài, mọi thay đổi có test + rollback)
**Duyệt bởi:** quanpt1 qua desktop 27/10 ("DUYỆT TASK-V3-SPRINT7")

## Hạng mục

**(a) Reboot-proof thật [Y1+Y3]**
- Sửa 2 task Scheduler (backup 2AM, report 8AM) thêm trigger ONSTART (SYSTEM context, không cần đăng nhập).
- KHOI_DONG_24_7.bat đặt vào Startup folder user (chạy khi anh đăng nhập, không cần quyền admin).
- Checklist verify sau reboot (10 bước) + script `tools/post_reboot_verify.py` tự chạy: servers 8765/8766, Ollama 11434, Pi5 heartbeat, responder heartbeat, 2 task Ready, DB mở được.
- ANH nhấn restart thật → em chạy verify + báo kết quả trung thực (PASS/FAIL từng bước).

**(b) Watchdog mở rộng [Y6]**
- `watchdog.py` thêm auto-restart cho 2 daemon em sở hữu: netchat_auto_responder.py + learning_daemon.py (cap 5 lần/giờ, đúng chuẩn server; heartbeat-freshness làm tín hiệu chết).
- Ollama VẪN chỉ cảnh báo (không restart — policy GAP-R3: không sở hữu thì không đụng).
- Test: mock heartbeat cũ → restart được gọi, cap 5/giờ giữ nguyên.

**(c) RAG kho thật [Y2]**
- `kho_tai_lieu/` nhận tài liệu thật anh thả vào (.txt/.md, guard nhạy cảm giữ nguyên).
- Re-index + chạy lại benchmark bằng BGE-M3 THẬT (Ollama đang ONLINE) + giữ mock-mode cho CI.
- Báo cáo số thật: tỷ lệ pass, câu fail, ngưỡng.

**(d) Dọn tiến trình trùng [Y7]**
- Kill instance thừa (watchdog/dual-servers chạy 2 bản venv + system-python).
- Chuẩn hoá: mỗi daemon đúng 1 instance (khóa file lock nếu cần), KHOI_DONG là nguồn duy nhất.

## Tiêu chí nghiệm thu
- (a) post_reboot_verify.py 10/10 PASS sau 1 lần reboot thật (anh thực hiện).
- (b) +6 test mới pass; watchdog log hiện rõ restart responder/learning khi heartbeat chết.
- (c) benchmark BGE-M3 thật chạy xong, số đo lưu reports/.
- (d) sau dọn: đúng 1 instance/daemon (wmic xác nhận), regression vẫn xanh.
- Full regression: 767 → 773+ passed, 0 fail.
"""

store = ApprovalCardStore(
    WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE)
)
card = store.create_card(
    task_code="TASK-V3-SPRINT7",
    title="Sprint 7 — Chứng minh độ bền + dữ liệu thật (a reboot + b watchdog + c RAG thật + d dọn tiến trình)",
    card_markdown=CARD,
    risk_level=2,
    goal="Chứng minh hệ thống sống sót reboot thật, tự hồi phục đầy đủ, RAG chạy trên kho thật.",
    params={"sprint": 7, "items": ["reboot", "watchdog", "rag-real", "process-cleanup"]},
)
print(f"card_saved: {card.task_code} status={card.status} request_id={card.request_id}")
