"""V8 — Vietnamese Conversation Engine: phân loại, chuẩn hóa, guidance.

Thiết kế theo MASTER PROMPT V8 §III-§V, nguyên tắc:
- KHÔNG hậu chỉnh sửa nội dung LLM tự viết — chỉ INJECT guidance vào context.
- KHÔNG tự sửa tên riêng / mã kỹ thuật (literal preservation).
- Fail-honest: guidance luôn nhắc nói "chưa đủ dữ liệu" khi thiếu căn cứ.
- stdlib-only, backward-compat (mọi hàm nhận str trả str/enum, không raise ra ngoài).
"""
from __future__ import annotations

import re
from enum import Enum

# ─────────────────────────── Phân loại yêu cầu (§3.2) ───────────────────────────


class RequestKind(str, Enum):
    QUESTION_SHORT = "question_short"        # câu hỏi đơn giản → trả lời ngắn
    WORK_CHAT = "work_chat"                  # trao đổi công việc → kết luận + bước tiếp
    TECH_ANALYSIS = "tech_analysis"          # phân tích kỹ thuật → chi tiết có căn cứ
    DOC_REQUEST = "doc_request"              # tạo prompt/tài liệu → đầy đủ có cấu trúc
    VOICE_CHAT = "voice_chat"                # hội thoại thoại → câu ngắn dễ nghe
    URGENT = "urgent"                        # khẩn cấp → quan trọng lên trước
    CONTEXT_DEPENDENT = "context_dependent"  # câu ngắn phụ thuộc ngữ cảnh → dùng history
    OTHER = "other"                          # không phân loại được


_URGENT_RE = re.compile(
    r"(khẩn cấp|gấp lắm|ngay bây giờ|cháy|lỗi nghiêm trọng|hệ thống sập|danger|urgent)",
    re.IGNORECASE,
)

_TECH_RE = re.compile(
    r"(phân tích|so sánh|kiến trúc|kiểm toán|audit|thiết kế|đánh giá|rủi ro|"
    r"phương án|trade-?off|hiệu năng|bottleneck|kĩ thuật|kỹ thuật)",
    re.IGNORECASE,
)

_DOC_RE = re.compile(
    r"(viết|soạn|tạo|lập)\s+(prompt|tài liệu|báo cáo|bản ghi|mail|email|văn bản|kịch bản|tóm tắt dài)",
    re.IGNORECASE,
)

_CTX_DEP_RE = re.compile(
    r"^\s*(làm tiếp|làm lại|sửa phần|sửa lại|kiểm tra lại|giúp anh (kiểm tra|sửa|làm)|"
    r"còn phương án nào|triển khai theo|cái này|bản trước|cách thứ (nhất|hai|ba|2|3)|"
    r"phần đó|vấn đề đó|như vậy|tiếp đi|tiếp tục|dừng lại|bắt đầu học)\b.*$",
    re.IGNORECASE,
)

_VOICE_HINT_RE = re.compile(
    r"(nói ngắn|đọc giúp|nói giúp|nghe không rõ|anh đang nói|nói chuyện)",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(r"\?|^\s*(cái gì|gì|ai|đâu|khi nào|bao nhiêu|sao vì|tại sao|như thế nào|có .* không)\b", re.IGNORECASE)


def classify_request(query: str) -> RequestKind:
    """Phân loại yêu cầu trước khi tạo phản hồi (V8 §3.2). Ưu tiên: urgent > context > voice > doc > tech > question."""
    q = (query or "").strip()
    if not q:
        return RequestKind.OTHER
    if _URGENT_RE.search(q):
        return RequestKind.URGENT
    if _CTX_DEP_RE.match(q):
        return RequestKind.CONTEXT_DEPENDENT
    if _VOICE_HINT_RE.search(q):
        return RequestKind.VOICE_CHAT
    if _DOC_RE.search(q):
        return RequestKind.DOC_REQUEST
    if _TECH_RE.search(q) or len(q) > 160:
        return RequestKind.TECH_ANALYSIS
    if _QUESTION_RE.search(q) and len(q) < 120:
        return RequestKind.QUESTION_SHORT
    if len(q) < 80:
        return RequestKind.WORK_CHAT
    return RequestKind.TECH_ANALYSIS


# ──────────────────────── Chuẩn hóa đầu vào an toàn (§4, P3) ────────────────────────

# Filler mở đầu/kết thúc an toàn — KHÔNG đụng từ trong ngoặc/tên riêng/mã.
_LEADING_FILLER_RE = re.compile(
    r"^\s*(ừ|ừm|ờ|à|ơ|này|nhé nha|đấy ạ|thế)\b[,\s]*",
)
_TRAILING_FILLER_RE = re.compile(r"[,\s]*(nhé nha|nhá|nhỉ|đấy ạ|haustus)\s*$")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_TOKEN_SAFE_RE = re.compile(r"[A-Za-z0-9_\-\.:/%]+")  # mã kỹ thuật: TASK-123, 8766, R5...


def normalize_vietnamese_input(query: str) -> str:
    """Làm sạch filler + khoảng trắng thừa. TUYỆT ĐỐI không sửa token kỹ thuật.

    Lưu ý trung thực: KHÔNG tự thêm dấu cho text không dấu (nguy cơ sai nghĩa
    tên riêng — V8 §6.1 cấm đoán theo suy đoán).
    """
    if not query:
        return query
    s = query.strip()
    prev = None
    while prev != s and s:
        prev = s
        s = _LEADING_FILLER_RE.sub("", s)
        s = _TRAILING_FILLER_RE.sub("", s).strip()
    s = _MULTI_SPACE_RE.sub(" ", s)
    return s


# ──────────────────────── Guidance block (§3.1, §3.3, §V) ────────────────────────

_BANNED_OPENERS = '"Chắc chắn rồi", "Tôi rất sẵn lòng hỗ trợ", "Tất nhiên", "Dạ vâng ạ"'

_GUIDANCE_BY_KIND: dict[RequestKind, str] = {
    RequestKind.QUESTION_SHORT: (
        "- Câu hỏi đơn giản: trả lời TRỰC TIẾP 1-3 câu, không liệt kê, không lặp lại câu hỏi."
    ),
    RequestKind.WORK_CHAT: (
        "- Trao đổi công việc: nêu KẾT LUẬN trước, sau đó bước tiếp theo (nếu có). Tối đa 5 ý."
    ),
    RequestKind.TECH_ANALYSIS: (
        "- Phân tích kỹ thuật: chi tiết có căn cứ, mỗi khẳng định kèm bằng chứng hoặc ghi rõ là suy luận "
        "('Khả năng cao là...', 'Em chưa đủ căn cứ để kết luận...')."
    ),
    RequestKind.DOC_REQUEST: (
        "- Yêu cầu tạo tài liệu/prompt: trình bày đầy đủ, có cấu trúc, giữ nguyên tên module/API/mã lỗi."
    ),
    RequestKind.VOICE_CHAT: (
        "- Phản hồi sẽ được ĐỌC THÀNH TIẾNG: dùng câu NGẮN (≤2 câu mỗi đoạn), không bảng, không markdown, "
        "con số và mã đọc được tự nhiên."
    ),
    RequestKind.URGENT: (
        "- Yêu cầu KHẨN CẤP: thông tin quan trọng nhất lên đầu, ngắn gọn, không nói vòng."
    ),
    RequestKind.CONTEXT_DEPENDENT: (
        "- Câu hỏi PHỤ THUỘC NGỮ CẢNH ('làm tiếp', 'phần đó', 'cách thứ hai'...): xác định đối tượng từ "
        "[RECENT CONVERSATION HISTORY] trước khi trả lời. Nhiều khả năng khác nhau mà không rõ → hỏi lại "
        "MỘT câu làm rõ, KHÔNG tự chọn đối tượng đoán mò."
    ),
    RequestKind.OTHER: (
        "- Trả lời đúng trọng tâm câu hỏi, không lan man sang chủ đề khác."
    ),
}

_BASE_GUIDANCE = (
    "- Xưng 'em', gọi chủ là 'anh' — giữ nhất quán suốt hội thoại, không gọi tên tài khoản lặp lại mỗi câu.\n"
    "- Không mở đầu rập khuôn như " + _BANNED_OPENERS + " — vào thẳng nội dung.\n"
    "- Không lặp lại nguyên văn yêu cầu của anh, không nhắc lại kết luận nhiều lần trong cùng câu trả lời.\n"
    "- Thuật ngữ kỹ thuật giữ nguyên (tên module, API, mã lỗi, tên file); giải thích bằng tiếng Việt khi cần.\n"
    "- Chưa hiểu thì HỎI LẠI; thiếu dữ liệu thì nói rõ phần nào chưa biết; KHÔNG bịa để duy trì cuộc trò chuyện; "
    "không nói 'đã kiểm tra' một nguồn em không truy cập được.\n"
    "- Không hy sinh độ chính xác để đổi câu chữ bóng bẩy."
)


def build_guidance_block(kind: RequestKind, *, is_voice_output: bool = False) -> str:
    """Tạo block [CONVERSATION GUIDANCE] ghép vào system_instructions."""
    lines = [f"[CONVERSATION GUIDANCE — {kind.value}]"]
    lines.append(_GUIDANCE_BY_KIND.get(kind, _GUIDANCE_BY_KIND[RequestKind.OTHER]))
    lines.append(_BASE_GUIDANCE)
    if is_voice_output or kind == RequestKind.VOICE_CHAT:
        lines.append("- (VOICE) Ưu tiên câu ngắn, dễ nghe; tránh đọc bảng/liệt kê dài.")
    return "\n".join(lines)


def should_inject_guidance(query: str) -> bool:
    """Inject khi query có dấu hiệu tiếng Việt (kể cả không dấu) hoặc câu phụ thuộc ngữ cảnh.

    Câu thuần tiếng Anh/mã lệnh không inject — tránh nhiễu.
    """
    if not query or not query.strip():
        return False
    vi_re = re.compile(
        r"[ăâđêôơưàáảãạằắẳẵặèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ"
        r"ĂÂĐÊÔƠƯÀÁẢÃẠẰẮẲẴẶÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤỲÝỶỸỴ]",
    )
    q = query.lower()
    if vi_re.search(q):
        return True
    # tiếng Việt không dấu: từ khóa phổ thông
    no_tone_re = re.compile(
        r"\b(la gi|nghe|kiem tra|lam tiep|sua lai|giup anh|bao cao|he thong|tin|lam on|cho anh|cho em)\b",
    )
    return bool(no_tone_re.search(q))
