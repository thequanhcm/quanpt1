"""speech_utils — Bộ công cụ xử lý chữ quanh giọng nói cho CHERRY.

Nguồn gốc: port từ vivi-agent (app/voice.py, app/lead_in.py — ADR-0054/0058/0071/0073)
vào QUAN AI BRAIN ngày 18/11/2026. Đây là **nâng cao năng lực**, KHÔNG thay tính năng
hiện có: normalize_text_for_vietnamese_tts trong quan_ai_brain.voice.tts_config vẫn
chạy như cũ; các hàm ở đây bổ sung các bước vivi-agent làm tốt mà Cherry chưa có:

1. punctuate()          — thêm dấu câu cho chữ STT bằng LLM, KHÔNG đổi từ (AD-05 vivi).
2. match_wake()         — dò từ đánh thức "Cherry ơi / Hey Cherry" ở đầu câu STT,
                          chấp nhận cách STT ghi sai ("che ri", "cherri", "cha ri"...).
3. clean_for_speech()   — bỏ markdown/link/ảnh/trích dẫn trước khi đọc TTS, cắt ở ranh
                          giới câu khi quá dài.
4. SentenceSplitter     — cắt chữ streaming thành câu để đọc TTS ngay khi chữ còn đang
                          sinh (streaming TTS), không cắt "22,5" hay "3.5".
5. strip_lead_in()      — lọc câu dẫn thừa đầu câu trả lời ("Mình cần tra cứu...")
                          trước khi đọc TTS.

Quy tắc fail-honest: mọi hàm đều fail-open — lỗi thì trả nguyên văn đầu vào,
không bao giờ làm chết pipeline TTS/STT của Cherry. Chỉ stdlib, không phụ thuộc mới.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1. Thêm dấu câu cho chữ STT (port app/voice.py — vivi)
# ---------------------------------------------------------------------------

def _stt_words(text: str) -> list[str]:
    """Chuỗi từ để so hai bản chữ: bỏ dấu câu, bỏ hoa thường, giữ dấu thanh."""
    s = unicodedata.normalize("NFC", text).lower()
    return re.findall(r"[^\W_]+", s)


def words_equal(a: str, b: str) -> bool:
    """So sánh 2 văn bản chỉ theo từ (bỏ dấu câu + hoa thường) — dùng để xác nhận
    LLM chỉ thêm dấu câu chứ KHÔNG đổi chữ (AD-05 vivi: câu người dùng không bao giờ
    bị LLM viết lại)."""
    return _stt_words(a) == _stt_words(b)


# ---------------------------------------------------------------------------
# 2. Wake word "Cherry ơi / Hey Cherry" (port app/voice.py, đổi tên Vivi → Cherry)
# ---------------------------------------------------------------------------

# Từ mở đầu trước tên ("Cherry ơi", "ê Cherry ơi", "alo Cherry ơi", "này Cherry ơi")
_WAKE_LEAD = {"hey", "hei", "hai", "hay", "e", "alo", "nay", "ê"}
# STT hay ghi "Cherry" thành 2 âm rời: "che ri", "cha ri", "cher ri"...
_WAKE_NAME = {"che", "cha", "cher", "tshe"}
_WAKE_ONE = {
    "cherry", "cherri", "cherrie", "cherie", "chery", "che ri", "cherri", "tscheri",
    "cheri", "cheri", "cherry",
}
# "Hey Cherry" đủ để đánh thức, không cần "ơi" (ADR-0061 vivi). STT tiếng Việt
# ghi "hey" thành "hai/hay/hây" (ADR-0074 vivi).
_WAKE_HEY = {"hey", "hei", "hai", "hay"}


def _fold(tok: str) -> str:
    """Bỏ dấu tiếng Việt + chuẩn hóa (đ → d) để so sánh bất chấp cách STT ghi."""
    s = unicodedata.normalize("NFD", tok.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def match_wake(text: str) -> tuple[bool, str]:
    """Dò "Cherry ơi" hoặc "Hey Cherry" ở ĐẦU chữ STT. Trả (có đánh thức, phần lệnh
    phía sau). Phần lệnh cắt thẳng từ chữ gốc của STT, giữ nguyên "50%", "22,5", dấu
    câu: chỉ bỏ dấu phân cách ngay sau "Cherry ơi". Chỉ khớp ở ĐẦU câu, để câu nói
    chuyện có nhắc tên Cherry giữa chừng không bật nhầm. Bỏ dấu khi so, chấp nhận
    "cherry", "che ri", "cherri", "cherrie" và từ mở đầu "hey/ê/alo/này". Riêng
    "hey/hei" + tên Cherry thì không cần "ơi" (ADR-0061)."""
    if not text:
        return False, ""
    s = unicodedata.normalize("NFC", text)
    spans = list(re.finditer(r"[^\W_]+", s))
    f = [_fold(m.group()) for m in spans]
    i = 1 if f and f[0] in _WAKE_LEAD else 0
    end = 0
    if len(f) >= i + 2 and f[i] in _WAKE_ONE and f[i + 1] == "oi":
        end = i + 2
    elif len(f) >= i + 3 and f[i] in _WAKE_NAME and f[i + 1] in ("ri", "ry", "rie", "ry") and f[i + 2] == "oi":
        end = i + 3
    elif i and f[0] in _WAKE_HEY and len(f) >= 2 and f[1] in _WAKE_ONE:
        end = 2
    elif i and f[0] in _WAKE_HEY and len(f) >= 3 and f[1] in _WAKE_NAME and f[2] in ("ri", "ry", "rie"):
        end = 3
    else:
        return False, ""
    return True, s[spans[end - 1].end():].lstrip(" ,.!?:;…-–")


# ---------------------------------------------------------------------------
# 3. Làm sạch chữ trước khi đọc TTS (port app/voice.py clean_for_speech)
# ---------------------------------------------------------------------------

_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_CITE = re.compile(r"\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]")
_URL = re.compile(r"https?://\S+")
_SRC_LINE = re.compile(r"^\s*(?:nguồn|trích dẫn|tham khảo)\s*[:：].*$", re.IGNORECASE | re.MULTILINE)


def clean_for_speech(text: str, max_chars: int = 1500) -> str:
    """Bỏ markdown, link, ảnh, dấu trích dẫn và dòng "Nguồn:" để giọng đọc không đọc
    ra ký hiệu. Cắt ở ranh giới câu khi quá `max_chars`. Fail-open: lỗi → trả rỗng."""
    try:
        s = _IMG.sub("", text)
        s = _LINK.sub(r"\1", s)
        s = _SRC_LINE.sub("", s)
        s = _CITE.sub("", s)
        s = _URL.sub("", s)
        s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.MULTILINE)           # tiêu đề
        s = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", s, flags=re.MULTILINE)    # đầu dòng danh sách
        s = re.sub(r"[*_`~>|]+", "", s)
        s = re.sub(r"\n+", "\n", s)
        s = re.sub(r"[ \t]+", " ", s).strip()
        if len(s) > max_chars:
            cut = s[:max_chars]
            k = max(cut.rfind(". "), cut.rfind("\n"), cut.rfind("? "), cut.rfind("! "))
            s = (cut[:k + 1] if k > max_chars // 2 else cut).strip()
        return s
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 4. Cắt câu streaming (port app/voice.py SentenceSplitter)
# ---------------------------------------------------------------------------

_BOUNDARY = re.compile(r"(?<=[.!?…])\s+|\n+")
_SOFT = re.compile(r"[,;:](?=\s)")


class SentenceSplitter:
    """Cắt chữ đang ra từng mảnh thành câu để đọc ngay (streaming TTS). Chỉ cắt khi
    dấu kết câu theo sau bởi khoảng trắng (không cắt "22,5" hay "3.5"). Câu quá ngắn
    ("1.") gộp vào câu sau. Câu dài không có dấu chấm thì cắt ở dấu phẩy sau
    `soft_chars` ký tự, để giọng không phải chờ quá lâu (ADR-0058 vivi — G5.5)."""

    def __init__(self, soft_chars: int = 140):
        self._buf = ""
        self._carry = ""
        self._soft = soft_chars

    def _emit(self, sent: str, out: list[str]) -> None:
        sent = (self._carry + sent).strip()
        if len(sent) < 4:                              # "1." hay "-": chờ ghép câu sau
            self._carry = sent + " " if sent else self._carry
            return
        self._carry = ""
        out.append(sent)

    def feed(self, text: str) -> list[str]:
        """Nhận thêm 1 mảnh chữ, trả danh sách câu hoàn chỉnh sẵn sàng đọc."""
        out: list[str] = []
        try:
            self._buf += text
            parts = _BOUNDARY.split(self._buf)
            self._buf = parts.pop() if parts else ""
            for p in parts:
                if p.strip():
                    self._emit(p.strip(), out)
            # Câu dài không có dấu kết câu: cắt ở dấu phẩy ĐẦU TIÊN sau soft_chars
            # (KHÔNG cắt "22,5"/"3.5": dấu phẩy/chấm trong số không có khoảng trắng
            # theo sau nên _SOFT không khớp — an toàn tự nhiên)
            if len(self._buf) > self._soft:
                m = _SOFT.search(self._buf, self._soft)
                if m:
                    self._emit(self._buf[:m.end()].strip(), out)
                    self._buf = self._buf[m.end():].lstrip()
        except Exception:
            # fail-open: đẩy hết buffer thành 1 câu duy nhất
            if self._buf.strip():
                out.append(self._buf.strip())
                self._buf = ""
        return out

    def flush(self) -> str:
        """Kết thúc lượt: trả phần chữ còn chưa thành câu (nếu có)."""
        rest = (self._carry + self._buf).strip()
        self._buf = ""
        self._carry = ""
        return rest


# ---------------------------------------------------------------------------
# 5. Lọc câu dẫn đầu câu trả lời (port app/lead_in.py — ADR-0071 vivi)
# ---------------------------------------------------------------------------

_MAX_LEN = 90                       # câu dẫn thật ngắn; câu dài là nội dung trả lời
_LEAD = re.compile(
    r"^(de )?(minh|toi|em) (se |can |xin |dang |hay |phai )*(tra cuu|tra|tim kiem|tim)\b(?! (thay|duoc|ra|ve)\b)"
)
# Câu dẫn chỉ là câu NGẮN giới thiệu việc tra: nếu theo sau là danh từ chỉ đối tượng
# cụ thể kèm nội dung ("thông tin này", "thông tin từ...") thì là câu trả lời thật.
# "tra cứu thông tin." (kết thúc luôn) vẫn là câu dẫn → chỉ loại khi có từ tiếp nối.
_LEAD_TOO_MUCH = re.compile(
    r"^(de )?(minh|toi|em) (se |can |xin |dang |hay |phai )*"
    r"(tra cuu|tra|tim kiem|tim) (thong tin|noi dung|du lieu|chi tiet) .+"
)
_WAIT = re.compile(r"^(ban )?(cho|doi|cho doi) (minh|toi) (mot )?(chut|lat|xiu)\b")
# Câu hỏi tiếng Anh vẫn được trả lời bằng tiếng Việt nhưng LLM đôi khi mở đầu bằng câu dẫn tiếng Anh.
_EN = re.compile(r"^(i'll|i will|i'm going to|i am going to|let me|allow me to|one moment while i) (go and )?(look|check|search|find)\b")
_END = re.compile(r"[.!?…:](\s|$)")
_VF = re.compile(r"\bvf\s?\d+\b")   # (giữ tên hàm vivi: tên dòng xe không phải số liệu)


def is_lead_in(sentence: str) -> bool:
    """Câu đầu của câu trả lời là câu dẫn khi: ngắn (≤90 ký tự), không có chữ số
    (số liệu là nội dung thật), và bắt đầu bằng "mình/tôi/em + (sẽ/cần/xin/đang/hãy/
    phải) + tra cứu/tra/tìm (kiếm)" hoặc "bạn chờ mình một chút", hoặc câu dẫn
    tiếng Anh ("I'll look that up…", "Let me check…")."""
    p = _fold(sentence)
    if not p or len(p) > _MAX_LEN or any(ch.isdigit() for ch in p):
        return False
    if _LEAD_TOO_MUCH.match(p):
        return False
    return bool(_LEAD.match(p) or _WAIT.match(p) or _EN.match(p))


def split_first_sentence(text: str) -> tuple[str, str]:
    m = _END.search(text)
    return (text[:m.end()], text[m.end():]) if m else (text, "")


def strip_lead_in(text: str) -> str:
    """Bỏ tối đa hai câu dẫn đầu. Nếu bỏ hết thì giữ nguyên bản gốc (không để câu
    trả lời rỗng) — ADR-0071 vivi: lỗi nhẹ nhưng đọc lên bằng giọng thì thừa."""
    try:
        rest = text.lstrip()
        for _ in range(2):
            first, tail = split_first_sentence(rest)
            if first and is_lead_in(first) and tail.strip():
                rest = tail.lstrip()
            else:
                break
        return rest if rest.strip() else text
    except Exception:
        return text


__all__ = [
    "words_equal",
    "match_wake",
    "clean_for_speech",
    "SentenceSplitter",
    "is_lead_in",
    "strip_lead_in",
    "split_first_sentence",
]
