"""Email attachment toolkit — CHERRY đọc mail + file đính kèm khi owner yêu cầu.

(26/11/2026, owner: "xây dựng cherry đọc được mail và nội dung file đính kèm
mail khi được yêu cầu. nếu yêu cầu lưu file đính kèm theo mail đó để sau lấy
làm cơ sở dữ liệu tra cứu thì thực hiện và update").

Kiến trúc (đã probe thật 26/11):
- Danh sách mail: tools/mail_reader.py (SOAP SearchRequest, READONLY) —
  has_attachment flag có sẵn ở <a> element.
- Nội dung file đính kèm: Zimbra REST `GET /service/content/get?id={mid}&part={part}`
  với header Cookie ZM_AUTH_TOKEN + User-Agent Mozilla (WAF chặn UA lạ —
  probe thật: thiếu UA → 3860 bytes HTML "Unauthorized Request Blocked").
- Đọc nội dung theo loại:
  * xlsx → zipfile + sharedStrings.xml/sheet XML (không cần openpyxl)
  * docx → zipfile + word/document.xml
  * pdf  → pypdf (có sẵn trong venv)
  * txt/csv → decode utf-8
- Lưu attachment khi owner yêu cầu: data/email_attachments/{mid}_{part}_{filename}
  + đăng ký vào bảng attachments trong data/email_intake.db (tra cứu sau).

An toàn: CHỈ ĐỌC hộp thư (không mark-read/xóa/gửi). Lưu file là R2 mức thấp
(ghi dữ liệu nội bộ workspace — không phải R4/R5). Fail-honest: mọi lỗi
trả message rõ ràng, không bịa.
"""
from __future__ import annotations

import io
import json
import re
import sqlite3
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

_BRAIN_ROOT = Path(__file__).resolve().parents[2]
# __file__ = src/quan_ai_brain/office/email_attachments.py → parents[2] = src/
# Workspace thật là cha của src/ (E:/BRAIN) — nơi data/ brain.db đang sống.
BRAIN_ROOT = _BRAIN_ROOT.parent
_TOOLS_DIR = BRAIN_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from tools import mail_reader as _mr  # noqa: E402

REST_URL = "https://vmail.viettel.vn/service/content/get"
ATTACH_DIR = BRAIN_ROOT / "data" / "email_attachments"
INTAKE_DB = BRAIN_ROOT / "data" / "email_intake.db"

_MAX_EXTRACT_CHARS = 3000  # đủ cho DM NetChat (tin <900 ký tự → cắt khi format)


class AttachmentError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# LOW-LEVEL: tải file nhị phân từ Zimbra REST
# ---------------------------------------------------------------------------

def _fetch_attachment_bytes(mid: str, part: str, retries: int = 3) -> bytes:
    """REST /service/content/get?id=&part= → BYTES thật (probe 26/11: magic
    %PDF / PK zip đúng). Bắt buộc Cookie ZM_AUTH_TOKEN + UA 'Mozilla/5.0'.
    WAF của vmail chặn KHÔNG ỔN ĐỊNH (probe: cùng request lần OK lần block,
    ~30%) → retry với backoff; UA dài 'Mozilla/5.0 (Windows NT...)' dễ bị
    chặn hơn UA ngắn — dùng UA ngắn."""
    last_err: Exception | None = None
    import time as _time

    for attempt in range(1, retries + 1):
        try:
            token = _mr._auth()
            url = f"{REST_URL}?id={mid}&part={part}"
            req = urllib.request.Request(
                url,
                headers={
                    "Cookie": f"ZM_AUTH_TOKEN={token}",
                    "User-Agent": "Mozilla/5.0",
                    # (probe 26/11) thiếu 'Accept: */*' → WAF block; đủ 3 header
                    # này thì ổn định (WAF rule của vmail dựa trên header set).
                    "Accept": "*/*",
                    "Referer": "https://vmail.viettel.vn/",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            # WAF trang HTML block vẫn HTTP 200 — phát hiện qua magic:
            if data[:5].lstrip() == b"<HTML" or b"Unauthorized Request Blocked" in data[:600]:
                raise AttachmentError(
                    f"WAF chặn tạm thời ({attempt}/{retries})"
                )
            return data
        except AttachmentError as exc:
            last_err = exc
            _time.sleep(1.5 * attempt)  # backoff — WAF block thường thoát sau vài giây
        except Exception as exc:
            last_err = AttachmentError(f"Tải đính kèm {mid}-{part} thất bại: {exc}")
            _time.sleep(1.5 * attempt)
    raise AttachmentError(
        f"Tải đính kèm {mid}-{part} thất bại sau {retries} lần: {last_err}"
    )


def _mp_list(mid: str) -> list[dict[str, str]]:
    """SOAP GetMsg → danh sách part đính kèm [{part, filename, ct, size}]."""
    token = _mr._auth()
    envelope = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Header><context xmlns="urn:zimbra"><authToken>{token}</authToken>'
        "</context></soap:Header>"
        f'<soap:Body><GetMsgRequest xmlns="{_mr.MAIL_NS}"><m id="{mid}"/>'
        "</GetMsgRequest></soap:Body></soap:Envelope>"
    )
    req = urllib.request.Request(
        _mr.SOAP_URL,
        data=envelope.encode("utf-8"),
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    parts: list[dict[str, str]] = []
    for m in re.finditer(r"<mp\b[^>]*>", raw):
        tag = m.group(0)
        cd = re.search(r'cd="([^"]+)"', tag)
        if not cd or cd.group(1) != "attachment":
            continue
        fn = re.search(r'filename="([^"]+)"', tag)
        ct = re.search(r'ct="([^"]+)"', tag)
        part = re.search(r'part="([^"]+)"', tag)
        size = re.search(r'\bs="(\d+)"', tag)
        parts.append({
            "part": part.group(1) if part else "",
            "filename": fn.group(1) if fn else "(không tên)",
            "content_type": ct.group(1) if ct else "",
            "size": size.group(1) if size else "?",
        })
    return parts


# ---------------------------------------------------------------------------
# READ: nội dung theo loại file (không cần openpyxl — zipfile + XML)
# ---------------------------------------------------------------------------

def _read_xlsx(data: bytes) -> str:
    return _read_xlsx_inner(data)


def _extract_attach_meta(mp_tag: str) -> tuple[str, str] | None:
    """Từ 1 dòng <mp .../> XML trong GetMsg → (filename, part) hoặc None.

    CHERRY trước đây chỉ trả metadata từ _list_emails (subject/from/date) —
    không có tên file/part thật từ GetMsg. Hàm này parse 1 tag <mp>:
      - bỏ part=1 (thường là body text, không phải đính kèm)
      - mặc định accept mọi content_type (kể cả text/plain cho .txt)
    """
    if not mp_tag:
        return None
    # Đơn giản hóa: tìm filename & part theo attribute key=value, KHÔNG yêu cầu
    # đúng thứ tự (regex tự do cho phép cd='attachment' ở bất kỳ vị trí nào).
    fn = re.search(r"filename=(?:\"([^\"]+)\"|'([^']+)')", mp_tag)
    part = re.search(r"\bpart=(?:\"([^\"]+)\"|'([^']+)')", mp_tag)
    if not (fn and part):
        return None
    filename = fn.group(1) or fn.group(2)
    p = part.group(1) or part.group(2)
    if p == "1":  # body, không phải attachment
        return None
    return filename, p


def _read_xlsx_inner(data: bytes) -> str:
    zf = zipfile.ZipFile(io.BytesIO(data))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        xml = zf.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
        shared = [
            re.sub(r"<[^>]+>", "", seg)
            for seg in re.findall(r"<si>(.*?)</si>", xml, re.S)
        ]
    # sheet đầu tiên
    sheet_name = next(
        (n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet1\.xml", n)),
        None,
    )
    if not sheet_name:
        return "(xlsx không đọc được sheet1)"
    xml = zf.read(sheet_name).decode("utf-8", errors="replace")
    rows_out: list[str] = []
    row_iter = re.finditer(r"<row\b[^>]*>(.*?)</row>", xml, re.S)
    for row_m in row_iter:
        cells: list[str] = []
        for c_m in re.finditer(r"<c\b[^>]*?(?:/>|>(.*?)</c>)", row_m.group(1), re.S):
            body = c_m.group(1) or ""
            is_shared = "t=\"s\"" in c_m.group(0)
            v = re.search(r"<v>([^<]*)</v>", body)
            if v is None:
                is_ = re.search(r"<is>(.*?)</is>", body, re.S)
                if is_:
                    cells.append(re.sub(r"<[^>]+>", "", is_.group(1))[:40])
                continue
            if is_shared and v.group(1).isdigit():
                idx = int(v.group(1))
                cells.append(shared[idx][:40] if idx < len(shared) else "?")
            else:
                cells.append(v.group(1)[:40])
        if cells:
            rows_out.append(" | ".join(cells))
        if sum(len(r) for r in rows_out) > _MAX_EXTRACT_CHARS:
            break
    return "\n".join(rows_out[:60]) or "(sheet trống)"


def _read_docx(data: bytes) -> str:
    zf = zipfile.ZipFile(io.BytesIO(data))
    if "word/document.xml" not in zf.namelist():
        return "(docx không có document.xml)"
    xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    text = " ".join(re.findall(r"<w:t[^>]*>([^<]+)</w:t>", xml))
    return text[:_MAX_EXTRACT_CHARS]


def _read_pdf(data: bytes) -> str:
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(data))
        chunks = []
        total = 0
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            chunks.append(t)
            total += len(t)
            if total > _MAX_EXTRACT_CHARS:
                break
        return "\n".join(chunks)[:_MAX_EXTRACT_CHARS] or "(PDF không có text layer)"
    except ImportError:
        return "(chưa có pypdf để đọc PDF)"
    except Exception as exc:
        return f"(lỗi đọc PDF: {type(exc).__name__}: {str(exc)[:80]})"


def _read_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1258"):
        try:
            return data.decode(enc)[:_MAX_EXTRACT_CHARS]
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")[:_MAX_EXTRACT_CHARS]


def read_attachment_content(data: bytes, filename: str) -> str:
    """Đọc nội dung file theo đuôi. Fail-honest trả message trong text."""
    low = (filename or "").lower()
    try:
        if low.endswith((".xlsx", ".xlsm")):
            return _read_xlsx(data)
        if low.endswith(".docx"):
            return _read_docx(data)
        if low.endswith(".pdf"):
            return _read_pdf(data)
        if low.endswith((".txt", ".csv", ".md", ".log", ".json", ".xml", ".eml")):
            return _read_text(data)
        if low.endswith(".doc"):
            return "(file .doc cũ — hỗ trợ .docx/.pdf/.xlsx, anh xin gửi lại dạng mới giúp em)"
        return f"(chưa hỗ trợ đọc loại {Path(low).suffix or '(không đuôi)'} — đã tải đủ {len(data)} bytes)"
    except Exception as exc:
        return f"(lỗi đọc {filename}: {type(exc).__name__}: {str(exc)[:80]})"


# ---------------------------------------------------------------------------
# STORE: lưu attachment + đăng ký DB tra cứu (data/email_intake.db)
# ---------------------------------------------------------------------------

def _ensure_table() -> None:
    con = sqlite3.connect(str(INTAKE_DB))
    with con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mail_id TEXT NOT NULL,
                part TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT DEFAULT '',
                size_bytes INTEGER DEFAULT 0,
                saved_path TEXT NOT NULL,
                mail_subject TEXT DEFAULT '',
                mail_sender TEXT DEFAULT '',
                mail_date TEXT DEFAULT '',
                saved_at_utc TEXT NOT NULL
            )
            """
        )
    con.close()


def save_attachment(
    mid: str, part: str, filename: str, *,
    mail_subject: str = "", mail_sender: str = "", mail_date: str = "",
) -> dict[str, Any]:
    """Tải + lưu file vào data/email_attachments/ + đăng ký DB. Idempotent:
    đã có (mail_id, part, filename) → trả bản ghi cũ không tải lại."""
    _ensure_table()
    con = sqlite3.connect(str(INTAKE_DB))
    con.row_factory = sqlite3.Row
    old = con.execute(
        "SELECT * FROM attachments WHERE mail_id=? AND part=? AND filename=?",
        (str(mid), str(part), filename),
    ).fetchone()
    if old:
        con.close()
        return {"already_saved": True, "path": old["saved_path"],
                "size": old["size_bytes"]}

    data = _fetch_attachment_bytes(mid, part)
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)[:120] or "attachment"
    dest = ATTACH_DIR / f"{mid}_{part}_{safe_name}"
    dest.write_bytes(data)

    with con:
        con.execute(
            "INSERT INTO attachments (mail_id, part, filename, content_type, "
            "size_bytes, saved_path, mail_subject, mail_sender, mail_date, "
            "saved_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                str(mid), str(part), filename, "", len(data), str(dest),
                mail_subject, mail_sender, mail_date,
                datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            ),
        )
    con.close()
    return {"already_saved": False, "path": str(dest), "size": len(data)}


def list_saved_attachments(keyword: str = "", limit: int = 10) -> list[dict[str, Any]]:
    """Tra cứu các attachment ĐÃ LƯU (cơ sở dữ liệu). keyword khớp filename/subject."""
    _ensure_table()
    con = sqlite3.connect(str(INTAKE_DB))
    con.row_factory = sqlite3.Row
    if keyword:
        rows = con.execute(
            "SELECT * FROM attachments WHERE filename LIKE ? OR mail_subject LIKE ? "
            "ORDER BY saved_at_utc DESC LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM attachments ORDER BY saved_at_utc DESC LIMIT ?", (limit,)
        ).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# HIGH-LEVEL: API cho command center / responder
# ---------------------------------------------------------------------------

def list_mail_attachments(mid: str) -> list[dict[str, str]]:
    """Danh sách đính kèm 1 mail (chỉ metadata, không tải nội dung)."""
    return _mp_list(str(mid))


def _mail_by_id(mid: str) -> dict[str, Any] | None:
    """Lấy metadata 1 mail theo id qua GetMsg (Search không có cú pháp id:)."""
    try:
        token = _mr._auth()
        envelope = (
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Header><context xmlns="urn:zimbra"><authToken>{token}</authToken>'
            "</context></soap:Header>"
            f'<soap:Body><GetMsgRequest xmlns="{_mr.MAIL_NS}">'
            f'<m id="{mid}"><header n="subject"/><header n="from"/></m>'
            "</GetMsgRequest></soap:Body></soap:Envelope>"
        )
        req = urllib.request.Request(
            _mr.SOAP_URL,
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        subject = re.search(r'<header n="subject">([^<]*)</header>', raw)
        addr = re.search(r'<e a="([^"]+)"', raw)
        d = re.search(r'<m[^>]*\bd="(\d+)"', raw)
        return {
            "id": str(mid),
            "subject": _decode_mime_header(_mr._clean(subject.group(1) if subject else None))
            or "(không tiêu đề)",
            "from_addr": addr.group(1) if addr else "",
            "from_name": addr.group(1) if addr else "",
            "date": _mr._fmt_date(d.group(1)) if d else "",
        }
    except Exception:
        return None


def _decode_mime_header(value: str) -> str:
    """=?utf-8?B?...?= → text thường (header subject GetMsg trả encoded-word)."""
    import email.header

    try:
        parts = email.header.decode_header(value or "")
        out = []
        for data, enc in parts:
            if isinstance(data, bytes):
                out.append(data.decode(enc or "utf-8", errors="replace"))
            else:
                out.append(data)
        return "".join(out)
    except Exception:
        return value or ""


def handle_read_mail_attachment(text: str) -> str:
    """Handler DM: 'đọc file đính kèm mail <id|từ khóa>' → nội dung text.

    Ưu tiên: mail id 5-7 số trong câu → mail đầu tiên khớp từ khóa tiêu đề
    (mail mới nhất có attachment).
    """
    import mail_reader as _mr2

    m_id = re.search(r"\b(\d{4,8})\b", text)
    kw = ""
    m_kw = re.search(
        r"(?:mail|email)\s+(?:về|ve|v/v|v\/v)?\s*(?:báo cáo|bao cao|kiểm đếm|kiem dem)?\s*([\w .\-]{3,40}?)(?:\s*(?:gần nhất|moi nhat|mới nhất)|$)",
        (text or ""), re.I,
    )
    if m_kw and not m_id:
        kw = m_kw.group(1).strip()

    if m_id:
        # Zimbra SearchRequest không có cú pháp id: — dùng ItemId qua GetMsg
        # trực tiếp rồi format lại giống email item (probe 26/11: query id: → 500).
        mail = _mail_by_id(m_id.group(1))
        if mail is None:
            return f"⚠️ Không tìm thấy mail id {m_id.group(1)}."
    else:
        # mail có attachment mới nhất (khớp từ khóa nếu có)
        res = _mr2._list_emails("in:inbox has:attachment", limit=10, with_body=False)
        emails = res.get("emails") or []
        if kw:
            k = kw.lower()
            emails = [e for e in emails if k in (e.get("subject") or "").lower()]
        if not emails:
            return ("📭 Không tìm thấy mail có đính kèm" +
                    (f" khớp '{kw}'" if kw else "") + ".")
        mail = emails[0]

    parts = list_mail_attachments(mail["id"])
    if not parts:
        return f"📭 Mail \"{mail['subject']}\" không có file đính kèm."

    lines = [f"📎 Mail \"{mail['subject']}\" ({mail.get('date','')}) có "
             f"{len(parts)} đính kèm:"]
    for i, p in enumerate(parts, 1):
        lines.append(f"\n{i}. {p['filename']} ({int(p['size'] or 0)//1024} KB)")
        try:
            data = _fetch_attachment_bytes(mail["id"], p["part"])
            content = read_attachment_content(data, p["filename"]).strip()
            preview = content[:700] or "(trống)"
            lines.append(f"   📄 {preview}{'…' if len(content) > 700 else ''}")
        except AttachmentError as exc:
            lines.append(f"   ⚠️ {exc}")
        except Exception as exc:
            lines.append(f"   ⚠️ Lỗi: {type(exc).__name__}: {str(exc)[:80]}")
    return "\n".join(lines)


def handle_save_mail_attachment(text: str) -> str:
    """Handler DM: 'lưu file đính kèm mail <id|từ khóa>' → tải + lưu + đăng ký DB."""
    import mail_reader as _mr2

    m_id = re.search(r"\b(\d{4,8})\b", text)
    kw = ""
    m_kw = re.search(r"(?:mail|email)\s+(?:về|ve|v/v|v\/v)?\s*([\w .\-]{3,40}?)(?:\s*(?:gần nhất|moi nhat|mới nhất)|$)", (text or ""), re.I)
    if m_kw and not m_id:
        kw = m_kw.group(1).strip()

    if m_id:
        # Zimbra Search không có cú pháp id: → GetMsg trực tiếp (như handle_read)
        mail = _mail_by_id(m_id.group(1))
        if mail is None:
            return f"⚠️ Không tìm thấy mail id {m_id.group(1)}."
    else:
        res = _mr2._list_emails("in:inbox has:attachment", limit=10, with_body=False)
        emails = res.get("emails") or []
        if kw:
            k = kw.lower()
            emails = [e for e in emails if k in (e.get("subject") or "").lower()]
        if not emails:
            return ("📭 Không tìm thấy mail có đính kèm" +
                    (f" khớp '{kw}'" if kw else "") + " để lưu.")
        mail = emails[0]

    parts = list_mail_attachments(mail["id"])
    if not parts:
        return f"📭 Mail \"{mail['subject']}\" không có đính kèm để lưu."

    lines = [f"💾 Lưu đính kèm của \"{mail['subject']}\" ({mail.get('date','')}):"]
    saved = 0
    for p in parts:
        try:
            r = save_attachment(
                mail["id"], p["part"], p["filename"],
                mail_subject=mail.get("subject", ""),
                mail_sender=mail.get("from_addr", ""),
                mail_date=mail.get("date", ""),
            )
            note = "đã có sẵn" if r["already_saved"] else "mới lưu"
            lines.append(f"  ✅ {p['filename']} → {r['path']} ({note})")
            saved += 1
        except Exception as exc:
            lines.append(f"  ⚠️ {p['filename']}: {type(exc).__name__}: {str(exc)[:80]}")
    lines.append(f"\n📚 Tổng kho: {len(list_saved_attachments(limit=999))} file "
                 "— tra cứu bằng lệnh 'tìm file đính kèm đã lưu <từ khóa>'.")
    return "\n".join(lines)


def handle_find_saved_attachment(text: str) -> str:
    """Handler DM: 'tìm file đính kèm đã lưu <từ khóa>' → tra DB kho attachment."""
    kw = ""
    m = re.search(r"(?:đã\s*lưu|da\s*luu)\s*(?:là|la)?\s*([\w .\-]{2,40})", (text or ""), re.I)
    if m:
        kw = m.group(1).strip()
    rows = list_saved_attachments(kw, limit=10)
    if not rows:
        return (f"📭 Chưa có file đính kèm nào được lưu" +
                (f" khớp '{kw}'" if kw else "") + ". Anh dùng lệnh "
                "'lưu file đính kèm mail <mã hoặc từ khóa>' trước.")
    lines = [f"📚 {len(rows)} file đính kèm đã lưu" + (f" (khớp '{kw}')" if kw else "") + ":"]
    for r in rows:
        lines.append(
            f"\n• {r['filename']} ({r['size_bytes']//1024} KB)\n"
            f"  📧 \"{r['mail_subject']}\" từ {r['mail_sender']} ({r['mail_date']})\n"
            f"  💾 {r['saved_path']}"
        )
    return "\n".join(lines)
