# -*- coding: utf-8 -*-
"""Mail reader cho QUAN AI BRAIN — đọc mail Viettel (vmail.viettel.vn) qua Zimbra SOAP.

(23/11/2026, owner: "cho cherry đọc mail của anh trên vmail.viettel.vn")

Kiến trúc (đã kiểm chứng 23/11 trên máy QUANPT):
- vmail.viettel.vn = Zimbra web client (CloudFront). IMAP tại mail.viettel.com.vn:993
  có mở port nhưng TỪ CHỐI LOGIN cho account này (LOGIN + AUTH PLAIN đều NO) dù
  mật khẩu ĐÚNG (SOAP AuthRequest nhận authToken thành công).
- → Đọc qua Zimbra SOAP SearchRequest/GetMsgRequest trên https://vmail.viettel.vn/service/soap/
  — cùng đường owner dùng trên web, mật khẩu không rời máy.

Credentials: loader tập trung (E:/BRAIN/user, pass, token/loader.py),
key `vmail_username` (vd quanpt1@viettel.com.vn) + `vmail_password`.
KHÔNG BAO GIỜ in/log giá trị secret. Owner cấp qua NetChat 23/11 — đã lưu.

Fail-honest: mọi lỗi trả {"error": ...} — không raise ra ngoài router.
READONLY: chỉ Search/GetMsg — không đánh dấu đã đọc, không xóa, không gửi.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# ---- Secrets loader tập trung (không in giá trị) ----
_SECRET_DIR = Path("E:/BRAIN/user, pass, token")
if str(_SECRET_DIR) not in sys.path:
    sys.path.insert(0, str(_SECRET_DIR))
import loader as _loader  # noqa: E402

_loader.reload()  # luôn đọc file mới — secrets có thể vừa được owner thêm

SOAP_URL = "https://vmail.viettel.vn/service/soap/"
MAIL_NS = "urn:zimbraMail"
ACC_NS = "urn:zimbraAccount"

_MAX_BODY_CHARS = 2000  # cắt body cho DM NetChat (tin dài gây khó đọc)


class _MailError(RuntimeError):
    pass


def _creds() -> tuple[str, str]:
    user = _loader.get_secret("vmail_username") or ""
    pwd = _loader.get_secret("vmail_password") or ""
    if not user or not pwd:
        raise _MailError(
            "Chưa có thông tin đăng nhập mail — cần key vmail_username + vmail_password "
            "trong secrets.local.json (owner cấu hình 1 lần)."
        )
    if "@" not in user:
        user = f"{user}@viettel.com.vn"
    return user, pwd


def _soap(body_xml: str, token: str | None = None) -> str:
    """POST 1 SOAP envelope, trả text. Lỗi HTTP/soap fault → _MailError."""
    header = (
        f'<soap:Header><context xmlns="urn:zimbra">'
        f"<authToken>{token}</authToken></context></soap:Header>"
        if token
        else "<soap:Header/>"
    )
    envelope = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f"{header}<soap:Body>{body_xml}</soap:Body></soap:Envelope>"
    )
    req = urllib.request.Request(
        SOAP_URL,
        data=envelope.encode("utf-8"),
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        m = re.search(r"<soapenv:Text[^>]*>([^<]+)<", body) or re.search(
            r"&lt;Code&gt;([^&]*)&lt;", body
        )
        reason = m.group(1) if m else f"HTTP {e.code}"
        raise _MailError(f"SOAP lỗi: {reason[:200]}") from None
    except Exception as e:
        raise _MailError(f"Không kết nối được vmail.viettel.vn: {e}") from None


def _auth() -> str:
    """Login SOAP → authToken."""
    user, pwd = _creds()
    out = _soap(
        f'<AuthRequest xmlns="{ACC_NS}">'
        f"<account>{user}</account><password>{pwd}</password>"
        f"</AuthRequest>"
    )
    m = re.search(r"<authToken>([^<]+)</authToken>", out)
    if not m:
        raise _MailError("Đăng nhập mail thất bại (không nhận được authToken).")
    return m.group(1)


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _fmt_date(ms: str | int | None) -> str:
    try:
        dt = _dt.datetime.fromtimestamp(int(ms) / 1000)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ms or "")


def _search(token: str, query: str, limit: int) -> list[dict[str, Any]]:
    """SearchRequest types=message → list summary (id, date, from, subject, fragment)."""
    body = (
        f'<SearchRequest xmlns="{MAIL_NS}" types="message" limit="{int(limit)}" '
        f'fullConversation="0" sortBy="dateDesc"><query>{query}</query></SearchRequest>'
    )
    out = _soap(body, token)
    root = ET.fromstring(out)
    items: list[dict[str, Any]] = []
    for m_el in root.iter(f"{{{MAIL_NS}}}m"):
        fr = m_el.find(f"{{{MAIL_NS}}}fr")
        su = m_el.find(f"{{{MAIL_NS}}}su")
        e_els = [e for e in m_el.findall(f"{{{MAIL_NS}}}e") if e.get("t") == "f"] or m_el.findall(f"{{{MAIL_NS}}}e")
        emails = [e.get("a") or "" for e in e_els]
        names = [e.get("p") or "" for e in e_els]
        # (24/11 S3-v5, owner: "mail chỉ gửi đến anh") lấy TO/CC đầy đủ để lọc:
        _to = sorted({e.get("a") or "" for e in m_el.findall(f"{{{MAIL_NS}}}e") if e.get("t") == "t"} - {""})
        _cc = sorted({e.get("a") or "" for e in m_el.findall(f"{{{MAIL_NS}}}e") if e.get("t") == "c"} - {""})
        mid = m_el.get("id") or ""
        # id có thể dạng "123" hoặc "123-456" (conversation item) — lấy phần trước '-'
        short_id = mid.split("-")[0]
        items.append(
            {
                "id": short_id,
                "uid": short_id,
                "date": _fmt_date(m_el.get("d")),
                "subject": _clean(su.text if su is not None else None) or "(không tiêu đề)",
                "from_addr": emails[0] if emails else "",
                "from_name": names[0] or (emails[0] if emails else ""),
                "fragment": _clean(fr.text if fr is not None else None),
                "has_attachment": m_el.find(f"{{{MAIL_NS}}}a") is not None,
                "read": m_el.get("f", "").find("u") == -1,  # flag u = unread
                "to_addrs": _to,
                "cc_addrs": _cc,
            }
        )
    return items


def _get_body(token: str, mid: str) -> str:
    """GetMsgRequest → nội dung text thuần của mail (bỏ tag HTML, giới hạn _MAX_BODY_CHARS)."""
    out = _soap(
        f'<GetMsgRequest xmlns="{MAIL_NS}">'
        f'<m id="{mid}"><header n="subject"/><header n="from"/></m>'
        f"</GetMsgRequest>",
        token,
    )
    root = ET.fromstring(out)
    texts: list[str] = []
    for part in root.iter(f"{{{MAIL_NS}}}content"):
        raw = part.text or ""
        if "<" in raw and ">" in raw:  # HTML → bỏ tag
            raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
            raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = raw.replace("&nbsp;", " ")
        texts.append(raw)
    body = _clean(" ".join(texts))
    return body[:_MAX_BODY_CHARS]


def _list_emails(query: str, limit: int = 10, with_body: bool = True) -> dict[str, Any]:
    """Chung: search theo query Zimbra. Trả dict kết quả (fail-honest)."""
    try:
        token = _auth()
        items = _search(token, query, max(1, min(limit, 20)))
        for it in items:
            if with_body and it["id"]:
                try:
                    it["body_preview"] = _get_body(token, it["id"])
                except Exception:
                    it["body_preview"] = it.get("fragment", "")
            else:
                it["body_preview"] = it.get("fragment", "")
        return {"host": "vmail.viettel.vn", "folder": "query=" + query,
                "count": len(items), "emails": items}
    except _MailError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def read_latest(n: int = 1) -> dict[str, Any]:
    """Mail gần nhất (mặc định 1) trong INBOX — lệnh 'đọc mail gần nhất'."""
    return _list_emails("in:inbox", limit=max(1, min(n, 10)))


def read_today() -> dict[str, Any]:
    """Mail nhận trong ngày hôm nay."""
    d = _dt.date.today().strftime("%m/%d/%Y")
    return _list_emails(f"in:inbox after:{d}", limit=15)


def read_since(date_ddmm: str, limit: int = 20) -> dict[str, Any]:
    """Mail từ ngày DD/MM (năm nay) đến giờ — lệnh 'check mail từ ngày 22/11'.

    Zimbra query after:MM/DD/YYYY (format US). Fail-honest giữ nguyên.
    (24/11 fix E2E) Zimbra 'after:' KHÔNG tính chính ngày đó (strict greater) →
    nếu DD/MM == hôm nay dùng 'date:' để không bỏ sót mail hôm nay.
    """
    try:
        dd, mm = date_ddmm.split("/")[:2]
        d = f"{int(mm):02d}/{int(dd):02d}/{_dt.date.today().year}"
    except Exception:
        return {"error": f"định dạng ngày sai: {date_ddmm!r} (cần DD/MM)"}
    today = _dt.date.today().strftime("%m/%d/%Y")
    if d == today:
        return _list_emails(f"in:inbox date:{d}", limit=max(1, min(limit, 20)))
    return _list_emails(f"in:inbox after:{d}", limit=max(1, min(limit, 20)))


def _get_msg_addrs(token: str, mid: str) -> tuple[set[str], set[str]]:
    """GetMsgRequest header to/cc → (to_set, cc_set). Lỗi → ({}, {}) (fail-honest)."""
    try:
        out = _soap(
            f'<GetMsgRequest xmlns="{MAIL_NS}">'
            f'<m id="{mid}"><header n="to"/><header n="cc"/></m>'
            f"</GetMsgRequest>",
            token,
        )
        root = ET.fromstring(out)
        to: set[str] = set()
        cc: set[str] = set()
        for e in root.iter(f"{{{MAIL_NS}}}e"):
            a = (e.get("a") or "").lower()
            if not a:
                continue
            t = e.get("t")
            if t == "t":
                to.add(a)
            elif t == "c":
                cc.add(a)
        # header fallback (nếu SOAP không trả e):
        if not to:
            for h in root.iter(f"{{{MAIL_NS}}}header"):
                if h.get("n") == "to" and h.text:
                    to |= {x.strip().lower() for x in re.findall(r"[\w.+-]+@[\w.-]+", h.text)}
                if h.get("n") == "cc" and h.text:
                    cc |= {x.strip().lower() for x in re.findall(r"[\w.+-]+@[\w.-]+", h.text)}
        return to, cc
    except Exception:
        return set(), set()


def read_since_direct_only(date_ddmm: str, limit: int = 20) -> dict[str, Any]:
    """(24/11 S3-v5, owner: 'lọc đúng, chỉ gửi đến cá nhân anh') — CHỈ mail gửi
    TRỰC TIẾP đến owner (TO chứa owner; loại mail gửi danh sách/aliasgroup/broadcast).

    2 bước: query 'to:<owner>' (Zimbra) → lọc client-side 'to_addrs' CHỈ gồm
    owner (± cc_addrs rỗng). Mail nhóm (pdl viettel, bo td kv1, all-hands…)
    bị loại — đúng nghĩa 'chỉ gửi đến cá nhân anh'.
    """
    try:
        user, _ = _creds()
    except _MailError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    try:
        dd, mm = date_ddmm.split("/")[:2]
        d = f"{int(mm):02d}/{int(dd):02d}/{_dt.date.today().year}"
    except Exception:
        return {"error": f"định dạng ngày sai: {date_ddmm!r} (cần DD/MM)"}
    res = _list_emails(f"in:inbox to:{user} after:{d}", limit=max(1, min(limit, 20)))
    if "error" in res:
        return res
    # SearchRequest summary KHÔNG trả e t="t" đầy đủ → GetMsg từng mail lấy
    # to/cc thật (chính xác tuyệt đối, vẫn READONLY).
    try:
        token = _auth()
    except _MailError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    emails = []
    for m in res.get("emails", []):
        to, cc = _get_msg_addrs(token, m["id"])
        m["to_addrs"] = sorted(to)
        m["cc_addrs"] = sorted(cc)
        # 'chỉ gửi đến anh' = TO chỉ có owner và KHÔNG có CC khác.
        # TO rỗng (không đọc được header) → fail-honest: loại (không đoán).
        if to and to <= {user} and not (cc - {user}):
            emails.append(m)
    return {"host": res.get("host", ""), "folder": f"query=in:inbox to:{user} (chỉ cá nhân) after:{d}",
            "count": len(emails), "emails": emails}


def read_unread(limit: int = 10) -> dict[str, Any]:
    """Mail CHƯA ĐỌC mới nhất."""
    return _list_emails("in:inbox is:unread", limit=limit)


def search_from_sender(sender: str, limit: int = 10) -> dict[str, Any]:
    """Tìm mail theo người gửi (lệnh 'kiểm tra mail từ người gửi dha1')."""
    if not sender or len(sender) < 2:
        return {"error": "Từ khóa người gửi quá ngắn."}
    return _list_emails(f"in:inbox from:{sender}", limit=limit)


def search_keyword(keyword: str, limit: int = 10) -> dict[str, Any]:
    """Tìm mail theo từ khóa trong tiêu đề/nội dung."""
    if not keyword or len(keyword) < 2:
        return {"error": "Từ khóa quá ngắn."}
    return _list_emails(f"in:inbox {keyword}", limit=limit)


def format_for_dm(result: dict[str, Any], max_emails: int = 5) -> str:
    """Format kết quả thành tin nhắn DM gọn tiếng Việt (không lộ mật khẩu)."""
    if "error" in result:
        return f"⚠️ {result['error']}"
    emails = result.get("emails") or []
    if not emails:
        return "📭 Không có email nào khớp trong hộp thư."
    label = result.get("folder", "INBOX")
    lines = [f"📬 {len(emails)} email ({label}):"]
    for i, m in enumerate(emails[:max_emails], 1):
        att = " 📎" if m.get("has_attachment") else ""
        unread = " 🔵chưa đọc" if not m.get("read", True) else ""
        lines.append(
            f"\n{i}. {m['subject']}{att}{unread}\n"
            f"   👤 {m['from_name']} <{m['from_addr']}>\n"
            f"   🕐 {m['date']}"
        )
        preview = (m.get("body_preview") or "").strip()
        if preview:
            lines.append(f"   💬 {preview[:300]}{'…' if len(preview) > 300 else ''}")
    return "\n".join(lines)


if __name__ == "__main__":
    # CLI nhanh: python mail_reader.py latest|today|unread|from:xxx|kw:xxx
    arg = sys.argv[1] if len(sys.argv) > 1 else "latest"
    if arg == "latest":
        res = read_latest(3)
    elif arg == "today":
        res = read_today()
    elif arg == "unread":
        res = read_unread(5)
    elif arg.startswith("from:"):
        res = search_from_sender(arg[5:])
    elif arg.startswith("kw:"):
        res = search_keyword(arg[3:])
    else:
        res = read_latest(1)
    print(format_for_dm(res, max_emails=5))
