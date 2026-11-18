# -*- coding: utf-8 -*-
"""SELF-CHECK LITE (TASK-MEMORY-TRUTH-M6, P1) — kiểm căn cứ sau khi trả lời.

Nguồn cảm hứng: selfcheck.py của vivi-agent (trợ lý ảo xe VinFast) — sau khi
viết câu trả lời DỰA TRÊN TÀI LIỆU, một lượt LLM chấm liệt kê ý KHÔNG CÓ
căn cứ; sửa tối đa 1 lần và CHỈ ĐƯỢC XÓA/RÚT GỌN (cấm thêm ý mới); vẫn sai
thì trả lời từ chối trung thực.

Cherry-adapted (khác Vivi):
- Chỉ kích hoạt khi câu trả lời có EVIDENCE block (memory_recall / semantic /
  ttns / external). Câu greeting/điều khiển đơn giản KHÔNG qua bước chấm
  (không đắt thêm thời gian).
- Fail-open: LLM lỗi/quá giờ → trả nguyên câu gốc, ghi warning. Không bao giờ
  làm hỏng đường chat chính.
- Không thực thi gì — chỉ chấm văn bản; không ghi DB; không side effect.
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from quan_ai_brain.llm.models import LLMRequest

# Câu trả lời từ chối trung thực khi vẫn còn ý không căn cứ sau khi sửa.
REFUSAL_TEXT = (
    "Dạ, em không có thông tin chính xác về việc này trong ghi nhớ của mình, "
    "anh ạ. Em không muốn trả lời sai — anh hỏi em nội dung khác nhé."
)

# Dấu hiệu câu hỏi xã giao / điều khiển — KHÔNG có evidence nào phục vụ, skip.
_BYPASS_PATTERNS = re.compile(
    r"^\s*(chào|xin chào|hello|hi\b|hey\b|cảm ơn|ok\b|oke|ừ\b|bye|tạm biệt"
    r"|mở|đóng|bật|tắt|phát (nhạc|bài)|dừng|pause|resume|restart|khởi động"
    r"|chụp ảnh|chuyển (trang|đổi))\b",
    re.IGNORECASE,
)

_TIMEOUT_SECONDS = 8.0


class _GenerateFn(Protocol):
    """Callable chấm điểm: (request: LLMRequest) -> object có .text."""

    def __call__(self, request: LLMRequest) -> Any: ...


def _grader_prompt(query: str, answer: str, evidence: str) -> str:
    return (
        "Bạn là bộ kiểm chứng căn cứ (fact-checker). Dưới đây là CÂU HỎI, "
        "CÂU TRẢ LỜI của trợ lý, và BẰNG CHỨNG (ghi nhớ/tài liệu) được cấp cho trợ lý.\n\n"
        f"[CÂU HỎI]\n{query}\n\n"
        f"[CÂU TRẢ LỜI]\n{answer}\n\n"
        f"[BẰNG CHỨNG]\n{evidence[:6000]}\n\n"
        "Nhiệm vụ: liệt kê các Ý CHÍNH của câu trả lời mà BẰNG CHỨNG không "
        "chứa hoặc không hỗ trợ (ý bịa/không căn cứ). Nếu mọi ý đều có căn cứ "
        "trong bằng chứng, trả mảng rỗng.\n"
        "Chỉ trả JSON đúng schema, không thêm chữ gì khác:\n"
        '{"du_can_cu": true|false, "y_khong_co_can_cu": ["ý 1", "ý 2"]}\n'
    )


def parse_verdict(text: str) -> dict[str, Any] | None:
    """Parse JSON verdict từ LLM; trả None nếu không parse được (fail-open)."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or "du_can_cu" not in data:
        return None
    claims = data.get("y_khong_co_can_cu")
    if not isinstance(claims, list):
        claims = []
    claims = [str(c).strip() for c in claims if str(c).strip()]
    return {"du_can_cu": bool(data["du_can_cu"]), "y_khong_co_can_cu": claims}


def _repair_prompt(query: str, answer: str, evidence: str,
                   claims: list[str]) -> str:
    bullet = "\n".join(f"- {c}" for c in claims[:6])
    return (
        "Câu trả lời dưới đây có các ý KHÔNG có căn cứ trong bằng chứng. Hãy "
        "VIẾT LẠI câu trả lời bằng cách CHỈ XÓA hoặc RÚT GỌN các ý đó — CẤM "
        "thêm ý mới, CẤM bịa, CẤM đổi nghĩa phần còn lại. Giữ nguyên văn phong "
        "xưng 'em' gọi 'anh'. Nếu sau khi xóa mà câu trả lời rỗng/ý nghĩa "
        "chỉ còn lại những ý không căn cứ, hãy trả đúng chuỗi: "
        "EM_KHONG_CO_CAN_CU\n\n"
        f"[CÂU HỎI]\n{query}\n\n"
        f"[CÂU TRẢ LỜI GỐC]\n{answer}\n\n"
        f"[Ý KHÔNG CĂN CỨ]\n{bullet}\n\n"
        f"[BẰNG CHỨNG]\n{evidence[:5000]}\n"
    )


def apply_removal_only_repair(answer: str, revised: str) -> str:
    """Guard chống thêm ý mới: revised dài hơn đáng kể hoặc rỗng → từ chối.

    Cả 2 đường sửa (rewrite + marker) đều phải đi qua hàm này để bảo đảm
    bất biến "chỉ xóa/rút gọn, không thêm ý".
    """
    if not revised or not revised.strip():
        return REFUSAL_TEXT
    revised = revised.strip()
    if len(revised) > int(len(answer) * 1.15) + 40:
        return REFUSAL_TEXT
    return revised


def self_check_reply(query: str, answer: str, evidence: str,
                     provider: Any, model: str) -> dict[str, Any]:
    """Chấm + sửa 1 lần. Fail-open mọi bước.

    Returns: {ran, revised_text, verdict, claims, revised, error}
    """
    result: dict[str, Any] = {
        "ran": False, "revised_text": answer, "verdict": None,
        "claims": [], "revised": False, "error": None,
    }
    # Bỏ qua các câu không phải trả lời kiến thức (greeting/điều khiển).
    if _BYPASS_PATTERNS.match(query or ""):
        result["verdict"] = "bypass"
        return result
    if not evidence or not answer:
        result["verdict"] = "no_evidence"
        return result
    result["ran"] = True
    try:
        grader_req = LLMRequest(
            prompt=_grader_prompt(query, answer, evidence),
            system_prompt="Bạn là fact-checker nghiêm ngặt. Chỉ trả JSON.",
            model=model,
            temperature=0.0,
            timeout_seconds=_TIMEOUT_SECONDS,
        )
        resp = provider.generate(grader_req)
        verdict = parse_verdict(resp.text or "")
        if verdict is None:
            result["error"] = "grader_unparseable"
            return result  # fail-open: giữ nguyên câu gốc
        result["verdict"] = verdict
        if verdict["du_can_cu"] and not verdict["y_khong_co_can_cu"]:
            return result  # ổn — giữ nguyên
        claims = verdict["y_khong_co_can_cu"]
        result["claims"] = claims
        repair_req = LLMRequest(
            prompt=_repair_prompt(query, answer, evidence, claims),
            system_prompt="Bạn là biên tập viên chỉ được xóa/rút gọn ý sai.",
            model=model,
            temperature=0.0,
            timeout_seconds=_TIMEOUT_SECONDS,
        )
        resp2 = provider.generate(repair_req)
        revised_raw = (resp2.text or "").strip()
        # Chuẩn marker từ chối (prompt yêu cầu) → refusal trung thực.
        if "EM_KHONG_CO_CAN_CU" in revised_raw:
            revised_raw = ""
        # Bóc quote-fence nếu LLM bọc code fence.
        revised_raw = re.sub(r"^```[a-z]*\n?|```$", "", revised_raw).strip()
        result["revised_text"] = apply_removal_only_repair(answer, revised_raw)
        result["revised"] = result["revised_text"] != answer
        return result
    except Exception as exc:  # fail-open tuyệt đối
        result["error"] = str(exc)[:200]
        result["revised_text"] = answer
        return result
