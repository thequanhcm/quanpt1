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
    # (24/11/2026, owner: "Check mail từ ngày 22/11 đến bây giờ") --since DD/MM:
    # đọc mail TỪ NGÀY chỉ định (Zimbra after: query) thay vì chỉ mail mới nhất.
    since = None
    range_mode = False
    if "--since" in sys.argv:
        i = sys.argv.index("--since")
        if i + 1 < len(sys.argv):
            since = sys.argv[i + 1]
    # (24/11 S3-v4, owner ảnh image_9035c0: "kiểm tra trong 1 tháng gần đây, anh
    # có mail nào cần phải phản hồi không, tóm tắt các nội dung mail đó")
    # --range DD/MM: TÓM TẮT TOÀN BỘ mail trong khoảng (KHÔNG dedupe 'đã thấy' —
    # mail cũ đã import vẫn được phân tích lại để owner thấy bức tranh khoảng).
    # R2 vẫn CHỈ ĐỌC: không mark-read, không xóa, không gửi.
    if "--range" in sys.argv:
        i = sys.argv.index("--range")
        if i + 1 < len(sys.argv):
            since = sys.argv[i + 1]
            range_mode = True
    connector = SOAPMailConnector()
    status = connector.status()
    if status.value == "NOT_CONFIGURED":
        print("⚠️ Chưa có thông tin đăng nhập mail (vmail_username/vmail_password trong "
              "secrets.local.json) — anh cấu hình giúp em 1 lần.")
        return 2
    store = EmailIntakeStore(DB_PATH)
    if since:
        # lọc thêm client-side theo received_at để chắc chắn đúng khoảng
        from datetime import date as _date, datetime as _dt

        try:
            dd, mm = since.split("/")[:2]
            since_date = _date(_date.today().year, int(mm), int(dd))
        except Exception:
            print(f"⚠️ Định dạng ngày sai: {since!r} (cần DD/MM, ví dụ 22/11).")
            return 2

        try:
            raw = connector.fetch_since(since, limit=20)
        except Exception as exc:
            print(f"⚠️ Đọc mail từ {since} thất bại (fail-honest): {exc}")
            return 1
        if range_mode:
            # S3-v4: phân tích TOÀN BỘ (không skip already_seen) — owner muốn
            # tóm tắt mọi mail trong khoảng, kể cả đã đọc/import trước đó.
            from quan_ai_brain.office.email_connector import (
                ConnectorStatus as _CS, IntakeResult as _IR, analyze_email as _ae)
            result = _IR(connector_status=_CS.CONNECTED, fetched=len(raw), new=len(raw))
            analyses = []
            for msg in raw:
                a = _ae(msg)
                analyses.append(a)
                result.by_category[a.category] = result.by_category.get(a.category, 0) + 1
                if store.already_seen(msg.message_id):
                    result.duplicates += 1
            print(format_summary_ab(result, analyses, top_n=10))
            return 0

        def _parse_recv(s: str):
            try:
                return _dt.fromisoformat((s or "").replace("Z", "+00:00"))
            except Exception:
                return None

        messages = []
        for m in raw:
            dt = _parse_recv(m.received_at_utc)
            if dt is None or dt.date() >= since_date:
                messages.append(m)
        # phân tích theo pipeline chung:
        from quan_ai_brain.office.email_connector import analyze_email
        from quan_ai_brain.integration.email_intake import classify_email
        result, analyses = _intake_save(store, messages)
    else:
        result, analyses = sync_and_analyze(connector, store, limit=15)
    print(format_summary_ab(result, analyses, top_n=5))
    return 0


def _intake_save(store, messages):
    """Lưu + phân tích 1 list EmailMessage có sẵn (không fetch lại SOAP)."""
    from quan_ai_brain.office.email_connector import ConnectorStatus, IntakeResult, analyze_email
    from quan_ai_brain.integration.email_intake import classify_email
    result = IntakeResult(connector_status=ConnectorStatus.CONNECTED, fetched=len(messages))
    analyses = []
    for msg in messages:
        if store.already_seen(msg.message_id):
            result.duplicates += 1
            continue
        if store.save(msg, classify_email(msg)):
            result.new += 1
            a = analyze_email(msg)
            analyses.append(a)
            result.by_category[a.category] = result.by_category.get(a.category, 0) + 1
    return result, analyses


if __name__ == "__main__":
    raise SystemExit(main())
