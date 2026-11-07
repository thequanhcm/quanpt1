"""Duty Roster Reader — đọc lịch trực FT từ kho_tai_lieu (read-only).

Nguồn: E:\\BRAIN\\kho_tai_lieu\\Lịch trực FT\\LICH_TRUC_TTrPDL_*.xls (BIFF, xlrd).
Cấu trúc sheet "<MM.YYYY>": R3 header (TT|Họ tên|Chức vụ|Điện thoại|1..31|Ghi chú),
R4+ mỗi hàng 1 nhân viên, cột 4+d = ô ngày d+1. Mã ca: N=ngày, Đ=đêm, N+Đ=cả hai,
12hN/12hĐ=nửa ca, N'/Đ'biến thể, Nghỉ phép/Học/Nghỉ dưỡng = không trực, L=trực lễ,
Đ_P/N_P=PĐL, Đ_G/N_G=GVM. Verdict logic đối chiếu ví dụ owner 07/11/2026: MATCH 6+5 tên.

Fail-honest: file/sheet/ngày không có → trả trạng thái rõ ràng, KHÔNG đoán.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
ROSTER_DIR = WORKSPACE / "kho_tai_lieu" / "Lịch trực FT"

# Mã trực thật (có trực) — match từ gốc, không đếm 'Nghỉ' như 'N'
ON_DUTY_RE = re.compile(r"^(N|Đ|L|12hN|12hĐ)([+'\"Mhàadhượngpasieul]*N*|.*\+.*)$")

def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "")).strip()

def _cell(sh, r: int, c: int) -> str:
    try:
        return _norm(str(sh.cell_value(r, c)))
    except Exception:
        return ""

def find_roster_file(month: int, year: int) -> Path | None:
    """Tìm file lịch trực chứa sheet tháng/year (ưu tiên file mới nhất)."""
    if not ROSTER_DIR.exists():
        return None
    candidates = sorted(ROSTER_DIR.glob("*.xls"), key=lambda p: p.stat().st_mtime, reverse=True)
    target = f"{month:02d}.{year}"
    for f in candidates:
        try:
            import xlrd
            book = xlrd.open_workbook(str(f))
            if target in book.sheet_names():
                return f
        except Exception:
            continue
    return None

def _parse_marks(raw: str) -> set[str]:
    """'N+Đ' → {'N','Đ'}; '12hN' → {'N'}; 'N'' → {'N'}; 'Nghỉ phép'/'Học' → set().

    Chuỗi chữ (nghỉ/học/du dưỡng...) KHÔNG phải mã ca — loại trước khi quét ký tự
    để 'Nghỉ phép' không sinh nhầm 'N' (bug bắt được bởi test 07/11).
    """
    s = raw.strip()
    low = s.lower()
    if any(k in low for k in ("nghỉ", "hoc", "học", "du dưỡng", "duong")):
        return set()
    s = s.replace("12h", "").replace("'", "")
    out: set[str] = set()
    for ch in s:
        if ch in ("N", "Đ", "L"):
            out.add(ch)
    return out

def _day_column(sh, day: int) -> int | None:
    """Tìm cột của ngày `day` bằng RÀ SOÁT HEADER HÀNG 4 (A4) — không cộng tĩnh.

    Quy ước 'col = 4 + (day-1)' chỉ đúng khi header liên tục 1..31 từ cột E;
    nếu sheet chèn/ẩn cột hoặc lệch cấu trúc sẽ đọc SAI CỘT → trả nhầm người.
    Owner yêu cầu (07/11): luôn đối chiếu giá trị số ngày ở hàng A4.
    """
    for c in range(4, sh.ncols):
        try:
            if int(float(sh.cell_value(3, c))) == day:
                return c
        except (TypeError, ValueError):
            continue
    return None

def get_duty_for_date(day: int, month: int, year: int) -> dict[str, Any]:
    """Trả {'status','day_shift':[...],'night_shift':[...],'missing':{name:chức_vụ...}} — mỗi tên kèm chức vụ+điện thoại."""
    f = find_roster_file(month, year)
    if not f:
        return {"status": "NO_FILE", "message": f"Không tìm thấy file lịch trực tháng {month:02d}/{year} trong {ROSTER_DIR}"}
    try:
        import xlrd
        book = xlrd.open_workbook(str(f))
        sh = book.sheet_by_name(f"{month:02d}.{year}")
    except Exception as e:
        return {"status": "READ_ERROR", "message": f"Lỗi đọc {f.name}: {e}"}

    if not (1 <= day <= 31):
        return {"status": "BAD_DATE", "message": f"Ngày không hợp lệ: {day}"}

    # Cột ngày d: rà soát header hàng 4 (A4) — dùng hàm dùng chung
    col = _day_column(sh, day)
    if col is None:
        return {"status": "NO_COLUMN", "message": f"Sheet {month:02d}.{year} không có cột ngày {day} ở hàng 4 (A4)"}

    day_shift: list[dict[str, str]] = []
    night_shift: list[dict[str, str]] = []
    unknown: list[dict[str, str]] = []
    for r in range(4, sh.nrows):
        name = _cell(sh, r, 1)
        if not name or name == "Ghi chú:":
            continue
        chuc = _cell(sh, r, 2).replace("\n", " ")
        dt = _cell(sh, r, 3)
        raw = _cell(sh, r, col)
        marks = _parse_marks(raw)
        person = {"name": name, "chuc_vu": chuc or "Chưa rõ", "dien_thoai": dt or "Chưa rõ"}
        if "N" in marks and "Đ" in marks:
            day_shift.append(person); night_shift.append(person)
        elif "N" in marks or "L" in marks:
            day_shift.append(person)
        elif "Đ" in marks:
            night_shift.append(person)
        elif raw and marks == set() and not any(k in raw.lower() for k in ("nghỉ", "học", "du dưỡng")):
            unknown.append({**person, "raw": raw})
    return {
        "status": "OK",
        "file": f.name,
        "sheet": f"{month:02d}.{year}",
        "day": day, "month": month, "year": year,
        "day_shift": day_shift,
        "night_shift": night_shift,
        "unrecognized_marks": unknown,
    }

def find_person_shift(name_query: str, day: int, month: int, year: int) -> dict[str, Any]:
    """Tra 1 cá nhân: trực hay không ngày đó (word-boundary, không dấu).

    Quét TOÀN BỘ nhân viên của sheet (R4..trước Ghi chú), KHÔNG chỉ người trực —
    để phân biệt 'không có trong lịch' vs 'có tên nhưng không trực ngày này'.
    """
    roster = get_duty_for_date(day, month, year)
    if roster.get("status") != "OK":
        return roster
    # Lấy full roster (mọi người + ô ngày thô) bằng 1 lần đọc lại file
    roster_full = _load_sheet_people(roster.get("file"), roster.get("sheet"), day)
    if roster_full.get("status") != "OK":
        return roster_full
    people = roster_full["people"]  # [{name, chuc_vu, dien_thoai, raw}]

    def n(s: str) -> str:
        s = unicodedata.normalize("NFD", s)
        return "".join(c for c in s if not unicodedata.combining(c)).lower()

    def _words(s: str) -> list[str]:
        return [w for w in re.split(r"\s+", s) if w]

    q = n(name_query)
    candidates: list[tuple[int, int, dict[str, str]]] = []
    for p in people:
        pn = n(p["name"])
        words = _words(pn)
        if pn == q:
            rank = 0
        elif q in words:
            rank = 1
        elif any(w.startswith(q) for w in words):
            rank = 2
        elif q in pn:
            rank = 3
        else:
            continue
        candidates.append((rank, len(p["name"]), p))
    if not candidates:
        return {"status": "OK", "found": False,
                "message": (f"Không thấy '{name_query}' trong danh sách lịch trực "
                            f"ngày {day:02d}/{month:02d}/{year}"),
                "date": f"{day:02d}/{month:02d}/{year}"}
    candidates.sort(key=lambda x: (x[0], -x[1]))
    best = candidates[0]

    def _on_duty_flag(p: dict[str, str]) -> bool:
        raw = (p.get("raw") or "").strip()
        if not raw:
            return False
        if any(k in raw.lower() for k in ("nghỉ", "học", "du dưỡng")):
            return False
        return bool(_parse_marks(raw))

    # Ambiguity chuẩn: nhiều NGƯỜI GỐC KHÁC nhau trùng sau bỏ dấu ('quân'/'quản'
    # đều→'quan' NFD) → dù chỉ 1 người trực vẫn hỏi lại (trả nhầm người còn tệ).
    best_rank = candidates[0][0]
    tied_names = {c[2]["name"] for c in candidates if c[0] == best_rank}
    if len(tied_names) > 1:
        return {"status": "AMBIGUOUS",
                "message": (f"Tên '{name_query}' có thể là: " + " / ".join(sorted(tied_names))
                            + ". Anh nói rõ họ tên đầy đủ giúp em ạ."),
                "date": f"{day:02d}/{month:02d}/{year}"}
    best = candidates[0]
    p = best[2]
    raw = (p.get("raw") or "").strip()
    marks = _parse_marks(raw)
    date_str = f"{day:02d}/{month:02d}/{year}"
    if not raw:
        return {"status": "OK", "found": True, "on_duty": False,
                "message": (f"Ngày {date_str}: {p['name']} ({p['chuc_vu']}) KHÔNG trực "
                            f"(không có mã ca trong lịch)"),
                "person": p, "date": date_str}
    if any(k in raw.lower() for k in ("nghỉ", "học", "du dưỡng")):
        return {"status": "OK", "found": True, "on_duty": False,
                "message": (f"Ngày {date_str}: {p['name']} ({p['chuc_vu']}) — ghi chú "
                            f"'{raw}' (không trực)"),
                "person": p, "date": date_str}
    if "N" in marks and "Đ" in marks:
        shift = "cả ca ngày và ca đêm"
    elif "N" in marks or "L" in marks:
        shift = "ca ngày"
    elif "Đ" in marks:
        shift = "ca đêm"
    else:
        return {"status": "OK", "found": True, "on_duty": False,
                "message": (f"Ngày {date_str}: {p['name']} ({p['chuc_vu']}) — mã không rõ "
                            f"'{raw}' (em không đoán)"),
                "person": p, "date": date_str}
    return {"status": "OK", "found": True, "on_duty": True, "shift": shift,
            "person": p, "date": date_str}


def _load_sheet_people(filename: str, sheet: str, day: int) -> dict[str, Any]:
    """Đọc full danh sách nhân viên sheet + ô ngày thô (phục vụ tra cá nhân)."""
    f = ROSTER_DIR / filename
    if not f.exists():
        return {"status": "NO_FILE", "message": f"Không thấy file {filename}"}
    try:
        import xlrd
        book = xlrd.open_workbook(str(f))
        sh = book.sheet_by_name(sheet)
    except Exception as e:
        return {"status": "READ_ERROR", "message": f"Lỗi đọc {filename}: {e}"}
    col = _day_column(sh, day)
    people: list[dict[str, str]] = []
    for r in range(4, sh.nrows):
        name = _cell(sh, r, 1)
        if not name or name.lower().startswith("ghi chú"):
            continue
        people.append({
            "name": name,
            "chuc_vu": _cell(sh, r, 2).replace("\n", " ") or "Chưa rõ",
            "dien_thoai": _cell(sh, r, 3) or "Chưa rõ",
            "raw": _cell(sh, r, col) if col < sh.ncols else "",
        })
    return {"status": "OK", "people": people}

def format_daily_report(res: dict[str, Any]) -> str:
    """Format DM theo mẫu owner: mỗi tên kèm chức vụ + điện thoại."""
    if res.get("status") != "OK":
        return "⚠️ " + res.get("message", "Không đọc được lịch trực")
    lines = [f"📋 Lịch trực ngày {res['day']:02d}/{res['month']:02d}/{res['year']}"]
    for label, key in (("Ca ngày", "day_shift"), ("Ca đêm", "night_shift")):
        if res[key]:
            parts = []
            for p in res[key]:
                parts.append(f"{p['name']} ({p['chuc_vu']} – {p['dien_thoai']})")
            lines.append(f"{label}: " + "\n   ".join(parts))
        else:
            lines.append(f"{label}: (không có ai trực)")
    if res.get("unrecognized_marks"):
        lines.append("⚠️ Có mã không nhận dạng được: " + ", ".join(f"{u['name']}[{u['raw']}]" for u in res["unrecognized_marks"]))
    return "\n".join(lines)
