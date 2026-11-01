"""QUAN AI BRAIN — V3 Sprint 4 (a): LLM-assisted Gap Detection.

Trích khoảng trống thông tin từ yêu cầu tiếng Việt TỰ DO bằng GLM-5.3-Flash,
output JSON có schema. FAIL-CLOSED tuyệt đối:
- LLM lỗi / timeout / JSON sai / trường thiếu → trả None, caller về heuristic
  Sprint 3. KHÔNG BAO GIỜ tự đoán khi không chắc (unknown → để heuristic).
- Timeout 8s không làm chậm chat.
- Key đọc env → HKCU fallback (như external_lookup), KHÔNG log giá trị.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

_LLM_TIMEOUT_S = 8.0

_PROMPT = """Bạn là bộ phân tích yêu cầu của trợ lý số. Đọc yêu cầu tiếng Việt của chủ nhân và trích xuất JSON CHÍNH XÁC schema sau — KHÔNG thêm trường, KHÔNG thêm chữ:

{{
  "goal": "mục tiêu công việc rút gọn 1 câu, hoặc '' nếu không rõ",
  "expected_outcome": "kết quả cuối cùng mong muốn, hoặc '' nếu không rõ",
  "required_inputs": [{{"key": "ten_ngan_quoc_lieu", "note": "vì sao cần"}}],
  "conflicts": ["mô tả mâu thuẫn nếu yêu cầu có dấu hiệu mâu thuẫn"],
  "owner_decisions_required": ["câu hỏi quyết định nếu có nhiều phương án cần chủ nhân chọn"],
  "acceptance_criteria": ["tiêu chí nghiệm thu nếu đề cập"],
  "constraints": ["ràng buộc thời hạn/phạm vi/định dạng nếu đề cập"]
}}

QUY TẮC:
- Chỉ liệt kê cái CÓ TRONG văn bản. Không suy diễn thêm.
- Không rõ → để mảng rỗng hoặc "".
- Trả về CHỈ JSON, không markdown."""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _read_key() -> str | None:
    """GEMINI_API_KEY env → HKCU fallback. Không in/log giá trị."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment"
        ) as k:
            val, _ = winreg.QueryValueEx(k, "GEMINI_API_KEY")
            return val if val else None
    except Exception:
        return None


def _read_model() -> str:
    m = os.environ.get("GEMINI_MODEL")
    if m:
        return m
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment"
        ) as k:
            val, _ = winreg.QueryValueEx(k, "GEMINI_MODEL")
            if val:
                return val
    except Exception:
        pass
    return "gemini-3-flash-preview"


def extract_gaps_with_llm(request_text: str) -> dict[str, Any] | None:
    """Gọi LLM trích gap từ văn bản tự do. Trả dict hợp lệ hoặc None (fail-closed).

    Guarantees:
    - None khi: text rỗng / không có key / HTTP lỗi / timeout / JSON không parse
      / thiếu trường bắt buộc / kiểu dữ liệu sai.
    - Không bao giờ raise ra ngoài.
    """
    if not request_text or not request_text.strip():
        return None
    text = request_text[:3000]  # giới hạn đầu vào
    key = _read_key()
    if not key:
        return None
    model = _read_model()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": _PROMPT.format() + "\n\nYÊU CẦU: " + text}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800},
    }).encode()
    try:
        req = subprocess.run(
            [
                "curl", "-s", "--max-time", str(int(_LLM_TIMEOUT_S)),
                "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-H", f"x-goog-api-key: {key}",
                "-d", "@-",
            ],
            input=body, capture_output=True, timeout=_LLM_TIMEOUT_S + 4,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if req.returncode != 0 or not req.stdout:
        return None
    try:
        resp = json.loads(req.stdout)
        raw = resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    # Schema check nghiêm: thiếu/kieu sai → None (không tự sửa)
    if not isinstance(data, dict):
        return None
    if "goal" not in data or not isinstance(data["goal"], str):
        return None
    for list_field in (
        "required_inputs", "conflicts", "owner_decisions_required",
        "acceptance_criteria", "constraints",
    ):
        if list_field in data and not isinstance(data[list_field], list):
            return None
    if "required_inputs" in data:
        for item in data["required_inputs"]:
            if not isinstance(item, dict) or "key" not in item:
                return None
    return data
