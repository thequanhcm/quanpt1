# -*- coding: utf-8 -*-
"""ThreadAnalyzer — CHERRY VMAIL INTELLIGENCE V1.0 — Sprint 2 (card TASK-VMAIL-S2).

Owner duyệt (23/11 chat): Roadmap mục 6 "Sprint 2 VMAIL Thread Analyzer — Sprint 1
VmailConnector đã LIVE; kế tiếp: Thread Analyzer → Shared Memory → ...".

Lớp mỏng TRÊN VmailConnector (Sprint 1) — KHÔNG cognitive core thứ 2, KHÔNG LLM
(deterministic; GLM tổng hợp tự nhiên thuộc sprint sau). Nguồn dữ liệu duy nhất:
VmailConnector (SOAP READONLY R2).

Đáp ứng master prompt VMAIL §5.3 (Email Thread Understanding — 10 mục):
  1. Nội dung ban đầu        2. Các lần phản hồi      3. Người tham gia
  4. Các yêu cầu             5. Các câu hỏi           6. Các cam kết
  7. Các quyết định          8. Các nội dung thay đổi  9. Các vấn đề còn tồn tại
 10. Trạng thái hiện tại
§5.3+: email mới nhất KHÔNG mặc định đúng; mâu thuẫn → trình bày CẢ HAI + nguồn.
§5.4 (Email Summary — 8 mục, bắt buộc dẫn nguồn mail cụ thể):
  Tổng quan | Nội dung chính | Các bên liên quan | Yêu cầu | Deadline |
  Quyết định | Vấn đề chưa giải quyết | Đề xuất hành động.

Tiêu chí nghiệm thu (docs/DE_XUAT_CAI_TIEN_NANG_CAP_20261123.md P1-3):
- Thread test gồm "[Hủy cuộc họp]" ghép ĐÚNG gốc.
- DM "tóm tắt luồng email X" trả đủ 10 mục.

R2 bất biến: CHỈ ĐỌC — không gửi/mark_read/delete. Fail-honest: connector lỗi →
StructuredResult(status="error"), không fake thread.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any

# ---- Nhãn thay đổi nhận diện từ subject (mâu thuẫn tiềm năng với bản gốc) ----
_CHANGE_TAGS: tuple[tuple[str, str], ...] = (
    ("hủy cuộc họp", "HỦY_CUỘC_HỌP"),
    ("huy cuoc hop", "HỦY_CUỘC_HỌP"),
    ("hủy họp", "HỦY_CUỘC_HỌP"),
    ("huy hop", "HỦY_CUỘC_HỌP"),
    ("hoãn", "HOÃN"),
    ("hoan lich", "HOÃN"),
    ("dời lịch", "DỜI_LỊCH"),
    ("doi lich", "DỜI_LỊCH"),
    ("đổi lịch", "DỜI_LỊCH"),
    ("cancel", "CANCEL"),
    ("postpone", "POSTPONE"),
)

# Reply/forward prefix cần strip khi normalise subject (KHÔNG strip action-tag —
# tag là TÍN HIỆU NỘI DUNG, chỉ tách khỏi key để ghép đúng gốc).
_REPLY_PREFIX = re.compile(r"^\s*((re|fw|fwd|trl|vr|aw)\s*(\[\d+\])?\s*[:：]\s*)+", re.I)

# Từ khóa nghiệp vụ (deterministic — kế thừa tinh thần _KW_* của Sprint 1a)
_KW_REQUEST = ("đề nghị", "de nghi", "yêu cầu", "yeu cau", "vui lòng", "vui long",
               "cần anh", "can anh", "cần chị", "can chi", "xử lý", "xu ly",
               "gửi lại", "gui lai", "hoàn thành", "hoan thanh", "điền", "dien",
               "đăng ký", "dang ky", "thực hiện", "thuc hien", "provide", "please")
_KW_COMMIT = ("cam kết", "cam ket", "tôi sẽ", "toi se", "em sẽ", "em se", "anh sẽ",
              "anh se", "chúng tôi sẽ", "chung toi se", "đồng ý thực hiện",
              "dong y thuc hien", "sẽ hoàn thành", "se hoan thanh", "will ")
_KW_DECISION = ("quyết định", "quyet dinh", "chốt", "chot", "thống nhất", "thong nhat",
                "phê duyệt", "phe duyet", "đã duyệt", "da duyet", "đồng ý", "dong y",
                "approved", "confirmed", "chấp thuận", "chap thuan")
_KW_CHANGE = ("hủy", "huy", "hoãn", "hoan", "dời", "doi", "đổi", "thay đổi",
              "thay doi", "cập nhật", "cap nhat", "sửa", "sua", "bổ sung", "bo sung")
_KW_DEADLINE = ("trước ", "truoc ", "hạn", "han ", "deadline", "vào ngày", "vao ngay",
                "trước ngày", "truoc ngay", "trước ", "ngày", "gio", "giờ")

_MEETING_KW = ("họp", "hop ", "cuộc họp", "cuoc hop", "meeting", "lịch", "lich ")


def normalize_subject(subject: str) -> tuple[str, list[str]]:
    """Subject → (group_key, change_tags).

    - Strip reply/forward prefix (RE:/FW:/...) — KHÔNG mất nội dung.
    - Tách action-tag (Hủy cuộc họp/hoãn/dời lịch...) khỏi key ĐỂ GHÉP ĐÚNG GỰC
      nhưng TRẢ LẠI tag dưới dạng tín hiệu thay đổi (§5.3 mục 8 + mâu thuẫn).
    - Lowercase + bỏ dấu cách thừa → key so khớp ổn định.
    """
    s = (subject or "").strip()
    tags: list[str] = []
    low = s.lower()
    # Nhận tag thay đổi từ subject gốc (trước khi strip — tag có thể nằm trong RE:)
    for kw, tag in _CHANGE_TAGS:
        if kw in low and tag not in tags:
            tags.append(tag)
    # Strip reply prefix
    s2 = _REPLY_PREFIX.sub("", s).strip()
    low2 = s2.lower()
    # Strip action-tag khỏi KEY (chỉ cho key; tag đã ghi ở trên)
    for kw, _tag in _CHANGE_TAGS:
        low2 = low2.replace(kw, " ")
        low2 = low2.replace(kw.replace(" ", ""), " ")  # biến thể không dấu cách
    low2 = re.sub(r"\[[^\]]*\]", " ", low2)   # bỏ bracket tag còn lại trong key
    low2 = re.sub(r"\s+", " ", low2).strip(" -–—:;")
    return (low2 or low or "(không tiêu đề)"), tags


def _parse_date(s: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        return None


@dataclass
class ThreadMessage:
    """1 email trong luồng (metadata + body text thuần)."""

    id: str
    date: str                      # "YYYY-MM-DD HH:MM"
    from_name: str
    from_addr: str
    subject: str
    fragment: str
    body: str = ""                 # body text (đã bỏ HTML — từ get_message)
    has_attachment: bool = False
    _dt: _dt.datetime | None = field(default=None, repr=False)

    def sort_key(self) -> tuple:
        return (self._dt or _dt.datetime.max, self.id)


@dataclass
class ThreadAnalysis:
    """Kết quả phân tích 1 luồng — 10 mục §5.3 + nguồn từng mục."""

    key: str
    subject_display: str
    messages: list[ThreadMessage]
    participants: list[str]        # (3) "Tên <email>"
    initial: ThreadMessage | None  # (1) nội dung ban đầu
    replies: list[ThreadMessage]   # (2) các lần phản hồi
    requests: list[str]            # (4) kèm nguồn "(mail #id ngày)"
    questions: list[str]           # (5)
    commitments: list[str]         # (6)
    decisions: list[str]           # (7)
    changes: list[str]             # (8) thay đổi + nguồn
    unresolved: list[str]          # (9) câu hỏi/yêu cầu mới nhất chưa có hồi âm
    status: str                    # (10) trạng thái hiện tại + đang chờ ai
    contradictions: list[str]      # §5.3: mâu thuẫn → CẢ HAI nội dung + nguồn
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "subject": self.subject_display,
            "message_count": len(self.messages),
            "message_ids": [m.id for m in self.messages],
            "participants": self.participants,
            "requests": self.requests,
            "questions": self.questions,
            "commitments": self.commitments,
            "decisions": self.decisions,
            "changes": self.changes,
            "unresolved": self.unresolved,
            "status": self.status,
            "contradictions": self.contradictions,
            "confidence": self.confidence,
        }


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 8]


def _src(m: ThreadMessage) -> str:
    return f"(mail #{m.id} {m.date})"


def build_threads(messages: list[dict[str, Any]]) -> dict[str, list[ThreadMessage]]:
    """Gom messages (dict từ VmailConnector.list_messages/_search) thành luồng
    theo subject-normalize. Trả dict key → messages SORTED cũ→mới."""
    threads: dict[str, list[ThreadMessage]] = {}
    for d in messages:
        subj = d.get("subject", "") or "(không tiêu đề)"
        key, _tags = normalize_subject(subj)
        tm = ThreadMessage(
            id=str(d.get("id", "")),
            date=d.get("date", "") or "",
            from_name=d.get("from_name", "") or d.get("from_addr", ""),
            from_addr=d.get("from_addr", ""),
            subject=subj,
            fragment=d.get("fragment", "") or "",
            body=d.get("body_preview", "") or d.get("body", "") or "",
            has_attachment=bool(d.get("has_attachment")),
            _dt=_parse_date(d.get("date", "") or ""),
        )
        threads.setdefault(key, []).append(tm)
    for k in threads:
        threads[k].sort(key=ThreadMessage.sort_key)
    return threads


def _extract_items(msgs: list[ThreadMessage]) -> dict[str, list[str]]:
    """Quét câu trong (body || fragment) → yêu cầu/câu hỏi/cam kết/quyết định/thay đổi.
    Mỗi item dẫn nguồn _src(m) (§5.4 bắt buộc dẫn nguồn)."""
    req: list[str] = []
    q: list[str] = []
    com: list[str] = []
    dec: list[str] = []
    chg: list[str] = []
    for m in msgs:
        text = (m.body or m.fragment or "").strip()
        for sent in _split_sentences(text):
            low = sent.lower()
            if any(k in low for k in _KW_DECISION):
                dec.append(f"“{sent[:180]}” {_src(m)}")
            if any(k in low for k in _KW_REQUEST):
                req.append(f"“{sent[:180]}” {_src(m)}")
            if "?" in sent or any(k in low for k in ("bao giờ", "bao gio", "khi nào", "khi nao", "ai ", "gì ", "gi ")) :
                q.append(f"“{sent[:180]}” {_src(m)}")
            if any(k in low for k in _KW_COMMIT):
                com.append(f"“{sent[:180]}” {_src(m)}")
            if any(k in low for k in _KW_CHANGE):
                chg.append(f"“{sent[:180]}” {_src(m)}")
    # Dedupe giữ thứ tự
    def dedupe(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for x in xs:
            k = x[:120]
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out
    return {"requests": dedupe(req), "questions": dedupe(q), "commitments": dedupe(com),
            "decisions": dedupe(dec), "changes": dedupe(chg)}


def _detect_contradictions(msgs: list[ThreadMessage], changes: list[str]) -> list[str]:
    """§5.3: mâu thuẫn → trình bày CẢ HAI nội dung + nguồn.

    Kịch bản chính (tiêu chí nghiệm thu P1-3): mail gốc mời/thông báo cuộc họp,
    mail sau mang tag HỦY/HOÃN/DỜI → hai nội dung đối lập, KHÔNG kết luận mail
    nào 'đúng' — chỉ trình bày + nguồn, owner tự đánh giá."""
    out: list[str] = []
    if not msgs:
        return out
    first = msgs[0]
    first_low = ((first.body or "") + " " + first.fragment + " " + first.subject).lower()
    original_is_meeting = any(k in first_low for k in _MEETING_KW)
    for m in msgs[1:]:
        subj_low = m.subject.lower()
        body_low = ((m.body or "") + " " + m.fragment).lower()
        if ("HỦY_CUỘC_HỌP" or "") and (("hủy cuộc họp" in subj_low) or ("huy cuoc hop" in subj_low)):
            if original_is_meeting:
                out.append(
                    f"MAU THUẪN LỊCH HỌP — BẢN GỐC: “{first.subject}” ({first.from_name}, "
                    f"{first.date}, mail #{first.id}) THÔNG BÁO/MỜI cuộc họp ⇄ "
                    f"BẢN SAU: “{m.subject}” ({m.from_name}, {m.date}, mail #{m.id}) "
                    f"HỦY cuộc họp. Em trình bày CẢ HAI, không tự kết luận bên nào đúng."
                )
            else:
                out.append(
                    f"THAY ĐỔI — “{m.subject}” ({m.from_name}, {m.date}, mail #{m.id}) "
                    f"mang tín hiệu hủy so với luồng “{first.subject}” (mail #{first.id})."
                )
        elif any(t in subj_low for t in ("hoãn", "hoan lich", "dời lịch", "doi lich", "đổi lịch")):
            out.append(
                f"THAY ĐỔI LỊCH — “{m.subject}” ({m.from_name}, {m.date}, mail #{m.id}) "
                f"so với bản gốc “{first.subject}” (mail #{first.id})."
            )
    return out


def analyze_thread(msgs: list[ThreadMessage]) -> ThreadAnalysis:
    """Phân tích 1 luồng (đã sort cũ→mới) → 10 mục §5.3.

    Không suy diễn: chỉ trích xuất câu có từ khóa tường minh; thiếu dữ liệu →
    mục để rỗng + status ghi rõ 'chưa đủ dữ liệu'."""
    if not msgs:
        raise ValueError("analyze_thread: messages rỗng")
    first, last = msgs[0], msgs[-1]
    items = _extract_items(msgs)

    # (3) người tham gia — từ from_name/addr, giữ thứ tự xuất hiện
    parts: list[str] = []
    seen: set[str] = set()
    for m in msgs:
        label = f"{m.from_name} <{m.from_addr}>" if m.from_addr else m.from_name
        k = label.lower()
        if k not in seen:
            seen.add(k)
            parts.append(label)

    # (9) vấn đề còn tồn tại: câu hỏi/yêu cầu ở mail MỚI NHẤT (chưa có mail nào
    # sau nó để trả lời) + mail KHÁC chưa được hồi âm khi chủ luồng là owner.
    unresolved: list[str] = []
    last_questions = [q for q in items["questions"] if f"#{last.id}" in q]
    last_requests = [r for r in items["requests"] if f"#{last.id}" in r]
    unresolved.extend(last_questions[-2:])
    unresolved.extend(last_requests[-2:])
    if not unresolved and (items["questions"] or items["requests"]):
        unresolved.append(
            f"Câu hỏi/yêu cầu trong luồng chưa thấy hồi âm sau đó "
            f"(mail gần nhất #{last.id} {last.date})."
        )

    # (10) trạng thái hiện tại + đang chờ ai
    owner_marker = ("quanpt1", "quân", "quan")
    last_from_owner = any(k in (last.from_addr or "").lower() for k in owner_marker) or \
        any(k in (last.from_name or "").lower() for k in owner_marker)
    if last_from_owner:
        waiting = "đang chờ BÊN NHẬN phản hồi"
    else:
        waiting = "đang chờ ANH (owner) xem/xử lý"
    status = (
        f"Mail mới nhất: “{last.subject}” từ {last.from_name} lúc {last.date} "
        f"(mail #{last.id}) — {waiting}. "
        f"Luồng gồm {len(msgs)} mail từ {first.date} → {last.date}. "
        f"Lưu ý §5.3: mail mới nhất KHÔNG mặc định đúng"
        + (f"; có {len(items['changes'])} tín hiệu thay đổi trong luồng." if items["changes"] else ".")
    )

    # Confidence: tỉ lệ mục có dữ liệu
    filled = sum(1 for v in (items["requests"], items["questions"], items["commitments"],
                             items["decisions"], items["changes"]) if v)
    confidence = round(0.4 + 0.12 * filled, 2)

    return ThreadAnalysis(
        key=normalize_subject(first.subject)[0],
        subject_display=first.subject,
        messages=msgs,
        participants=parts,
        initial=first,
        replies=msgs[1:],
        requests=items["requests"],
        questions=items["questions"],
        commitments=items["commitments"],
        decisions=items["decisions"],
        changes=items["changes"],
        unresolved=unresolved,
        status=status,
        contradictions=_detect_contradictions(msgs, items["changes"]),
        confidence=confidence,
    )


def format_thread_summary(a: ThreadAnalysis) -> str:
    """8 mục §5.4 — mỗi mục dẫn nguồn mail. Dùng cho DM 'tóm tắt luồng email X'."""
    L: list[str] = []
    L.append(f"🧵 TÓM TẮT LUỒNG: “{a.subject_display}” ({len(a.messages)} mail)")
    # 1. Tổng quan
    L.append("\n1️⃣ TỔNG QUAN")
    init = a.initial
    L.append(f"   • Bắt đầu {init.date} bởi {init.from_name} (mail #{init.id}): "
             f"{(init.body or init.fragment or '')[:220]}{'…' if len(init.body or init.fragment or '') > 220 else ''}")
    # 2. Nội dung chính (diễn biến)
    L.append("\n2️⃣ DIỄN BIẾN (các lần phản hồi)")
    if a.replies:
        for m in a.replies[:6]:
            frag = (m.body or m.fragment or "")[:160]
            L.append(f"   • {m.date} {m.from_name} (mail #{m.id}): {frag}{'…' if frag else ''}")
    else:
        L.append("   • Chưa có phản hồi nào trong luồng.")
    # 3. Các bên liên quan
    L.append("\n3️⃣ CÁC BÊN LIÊN QUAN")
    L.append("   • " + "; ".join(a.participants[:8]))
    # 4. Yêu cầu
    L.append("\n4️⃣ YÊU CẦU")
    L += [f"   • {x}" for x in (a.requests[:5] or ["(không phát hiện yêu cầu tường minh)"])]
    # 5. Deadline (explicit — từ câu chứa từ khóa hạn + số ngày/giờ)
    L.append("\n5️⃣ DEADLINE (chỉ ghi khi email nêu rõ)")
    dl = [x for x in a.requests + a.commitments if any(k in x.lower() for k in _KW_DEADLINE)]
    L += [f"   • {x}" for x in (dl[:4] or ["(không có deadline tường minh trong luồng)"])]
    # 6. Quyết định
    L.append("\n6️⃣ QUYẾT ĐỊNH")
    L += [f"   • {x}" for x in (a.decisions[:5] or ["(chưa phát hiện quyết định tường minh)"])]
    # 7. Vấn đề chưa giải quyết + mâu thuẫn
    L.append("\n7️⃣ VẤN ĐỀ CHƯA GIẢI QUYẾT")
    if a.contradictions:
        L += [f"   ⚠️ {x}" for x in a.contradictions]
    L += [f"   • {x}" for x in (a.unresolved[:4] or ["(không còn câu hỏi/yêu cầu treo)"])]
    # 8. Đề xuất hành động (dựa trên bằng chứng, không suy diễn vượt)
    L.append("\n8️⃣ ĐỀ XUẤT HÀNH ĐỘNG")
    if a.unresolved:
        L.append("   • Anh xem các câu hỏi/yêu cầu mục 7 — hồi âm mail gần nhất nếu cần.")
    if a.contradictions:
        L.append("   • Có mâu thuẫn lịch/nội dung: anh xác nhận phiên bản đúng trước khi hành động.")
    if not a.unresolved and not a.contradictions:
        L.append("   • Luồng ổn định — không có việc treo phát hiện được.")
    L.append(f"\n⏱ Trạng thái: {a.status}")
    L.append(f"🎯 Confidence trích xuất: {a.confidence:.0%} (deterministic, không LLM)")
    return "\n".join(L)


def format_10_items(a: ThreadAnalysis) -> str:
    """Bảng 10 mục §5.3 đầy đủ (tiêu chí nghiệm thu P1-3: DM trả ĐỦ 10 mục)."""
    L = [f"🧵 LUỒNG “{a.subject_display}” — 10 MỤC §5.3 ({len(a.messages)} mail)"]
    items: list[tuple[str, list[str] | str]] = [
        ("1. Nội dung ban đầu", [f"“{a.initial.subject}” — {a.initial.from_name}, {a.initial.date}, mail #{a.initial.id}"]),
        ("2. Các lần phản hồi", [f"{m.date} {m.from_name} (mail #{m.id})" for m in a.replies] or ["(không có)"]),
        ("3. Người tham gia", a.participants),
        ("4. Các yêu cầu", a.requests or ["(không phát hiện)"]),
        ("5. Các câu hỏi", a.questions or ["(không phát hiện)"]),
        ("6. Các cam kết", a.commitments or ["(không phát hiện)"]),
        ("7. Các quyết định", a.decisions or ["(không phát hiện)"]),
        ("8. Các nội dung thay đổi", a.changes or ["(không phát hiện)"]),
        ("9. Vấn đề còn tồn tại", (a.contradictions + a.unresolved) or ["(không có)"]),
        ("10. Trạng thái hiện tại", [a.status]),
    ]
    for name, vals in items:
        L.append(f"\n{name}:")
        if isinstance(vals, str):
            vals = [vals]
        for v in vals[:6]:
            L.append(f"   • {v}")
    return "\n".join(L)
