# -*- coding: utf-8 -*-
"""Office email sync runner — chạy 1 lần sync+analyze rồi in ra tóm tắt A/B.

TASK-OFFICE-S1 (23/11): handle_email_today gọi script này trong subprocess
(timeout 110s — SOAP có thể chậm). In stdout = tin nhắn DM; lỗi → exit != 0.

R2 READONLY: chỉ đọc mail (SOAP), dedupe + lưu intake, phân tích. Không gửi/xóa.
PYTHONPATH phải chứa src/ + tools/ (do caller set).
"""
from __future__ import annotations

import sys
from pathlib import Path

BRAIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN_ROOT / "src"))
sys.path.insert(0, str(BRAIN_ROOT / "tools"))

from quan_ai_brain.integration.email_intake import EmailIntakeStore  # noqa: E402
from quan_ai_brain.office.email_connector import (  # noqa: E402
    SOAPMailConnector,
    format_summary_ab,
    sync_and_analyze,
)

DB_PATH = BRAIN_ROOT / "data" / "email_intake.db"


def main() -> int:
    connector = SOAPMailConnector()
    status = connector.status()
    if status.value == "NOT_CONFIGURED":
        print("⚠️ Chưa có thông tin đăng nhập mail (vmail_username/vmail_password trong "
              "secrets.local.json) — anh cấu hình giúp em 1 lần.")
        return 2
    store = EmailIntakeStore(DB_PATH)
    # limit 15: đủ cho hôm nay, không quá tải SOAP
    result, analyses = sync_and_analyze(connector, store, limit=15)
    print(format_summary_ab(result, analyses, top_n=5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
