"""CHERRY Vision Intelligence (CVI) — phân tích ảnh cấp chuyên gia (S2-S4).

(07/11/2026) Theo Master Prompt CVI V1.0 duyệt owner ("duyệt tất cả"):
- S2 Photography Analysis: bố cục, góc máy, ánh sáng, màu (HEX ước lượng), quality 10 tiêu chí
- S3 Art Direction: cảm xúc, ý đồ, storytelling
- S4 Reverse Prompt Engineering: prompt tiếng Anh tái tạo (A/B/C)

NGUYÊN TẮC TRUNG THỰC:
- Mọi kết luận qua GLM-5.3-Flash là PHÂN TÍCH AI, có thể sai chi tiết nhỏ (caller ghi nhãn).
- Model tự phân lớp OBSERVED/INFERRED/UNCERTAIN trong output; không có object-detection
  bounding box thật; không đọc EXIF camera Pi — không bịa thông số máy.
- Fail-honest: trả None khi lỗi, không giả lập thành công.
"""
from __future__ import annotations

import json
from pathlib import Path


def _glm_vision(path: Path, prompt: str, *, timeout: float = 90.0, max_tokens: int = 2000) -> str | None:
    """Gọi GLM-5.3-Flash với ảnh base64 + prompt CVI (tái dùng provider dự án)."""
    try:
        import base64 as _b64
        import sys as _sys
        import urllib.request as _ur
        from pathlib import Path as _P

        _sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
        from quan_ai_brain.llm.netmind_provider import NetMindProvider

        key = NetMindProvider()._get_api_key()
        if not key:
            return None
        data = path.read_bytes()
        if len(data) > 6_000_000:
            try:
                from PIL import Image
                import io as _io
                img = Image.open(_io.BytesIO(data))
                img.thumbnail((1280, 1280))
                buf = _io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                data = buf.getvalue()
            except Exception:
                pass
        payload = {
            "model": "zai-org/GLM-5.3-Flash",
            "messages": [{"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": "data:image/jpeg;base64," + _b64.b64encode(data).decode()}},
                {"type": "text", "text": prompt},
            ]}],
            "max_tokens": max_tokens,
        }
        base_url = NetMindProvider().base_url
        req = _ur.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with _ur.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode())
        text = (d["choices"][0]["message"].get("content") or "").strip()
        if not text:
            payload["max_tokens"] = max_tokens * 2
            req2 = _ur.Request(
                base_url.rstrip("/") + "/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST",
            )
            with _ur.urlopen(req2, timeout=timeout) as resp2:
                d2 = json.loads(resp2.read().decode())
            text = (d2["choices"][0]["message"].get("content") or "").strip()
        return text or None
    except Exception:
        return None


CVI_PRO_PROMPT = (
    "Bạn là chuyên gia thị giác máy tính, nhiếp ảnh gia và giám đốc nghệ thuật. "
    "Phân tích CHUYÊN SÂU ảnh này bằng TIẾNG VIỆT THUẦN, theo đúng khung sau:\n"
    "## 1. BỐI CẢNH & CHỦ THỂ\n\n## 2. BỐ CỤC & GÓC MÁY\n"
    "(góc chụp: ngang tầm/low-angle/high-angle...; cỡ cảnh; bố cục: 1/3, đối xứng, đường dẫn mắt)\n"
    "## 3. ÁNH SÁNG & MÀU SẮC\n"
    "(nguồn sáng tự nhiên/nhân tạo, hướng sáng, cứng/mềm, màu chủ đạo + 3-5 mã HEX ƯỚC LƯỢNG — ghi rõ là ước lượng)\n"
    "## 4. PHONG CÁCH\n"
    "(ảnh chụp thật/3D/vẽ/AI-generated — chỉ nhận định dựa dấu hiệu hình ảnh)\n"
    "## 5. CẢM XÚC & Ý ĐỒ\n\n"
    "## 6. ĐÁNH GIÁ CHẤT LƯỢNG (thang 10 mỗi mục, CÓ LÝ; thiếu dữ liệu ghi N/A): "
    "Bố cục | Ánh sáng | Màu sắc | Độ nét | Phơi sáng | Ấn tượng\n"
    "## 7. CHI TIẾT CHƯA RÕ\n"
    "(liệt kê những gì quá mờ/khó khẳng định — KHÔNG đoán)\n\n"
    "Với MỖI kết luận, thêm nhãn: [QS] quan sát trực tiếp / [SL] suy luận có cơ sở / [CR] chưa rõ. "
    "Tuyệt đối không bịa thông số camera, tiêu cự, nhãn hiệu không nhìn thấy được."
)

REVERSE_PROMPT_TMPL = (
    "Reverse Prompt Engineering cho ảnh này. Trả lời TIẾNG ANH (prompt phải bằng tiếng Anh) "
    "kèm phần giải thích ngắn tiếng Việt:\n\n"
    "**PROMPT A (Faithful Recreation):** tái tạo gần nhất nội dung + bố cục + ánh sáng + phong cách.\n"
    "**PROMPT B (Cinematic Enhancement):** giữ chủ thể, nâng cấp ánh sáng/bố cục/cảm xúc điện ảnh.\n"
    "**PROMPT C (Creative Art Direction):** phiên bản sáng tạo mới giữ tinh thần gốc.\n\n"
    "Mỗi prompt: mô tả rõ chủ thể, bối cảnh, góc máy, bố cục, ánh sáng, màu, phong cách, chất liệu, "
    "tỷ lệ khung; KHÔNG dùng từ chung chung như beautiful/high quality thay cho mô tả cụ thể; "
    "cuối cùng đề xuất 1 negative prompt ngắn (chỉ những gì phù hợp ảnh này)."
)


def analyze_image_pro(path: str | Path) -> str:
    """Phân tích chuyên sâu CVI (S2+S3) — trả text tiếng Việt DM-ready, hoặc thông báo lỗi trung thực."""
    p = Path(path)
    if not p.exists():
        return f"⚠️ Không tìm thấy file ảnh: {p.name}"
    out = _glm_vision(p, CVI_PRO_PROMPT, timeout=90.0, max_tokens=2000)
    if not out:
        return "⚠️ Chưa phân tích chuyên sâu được (LLM không phản hồi) — thử lại sau ạ."
    return ("🔬 *Phân tích chuyên sâu CVI (mô tả AI, có thể sai chi tiết nhỏ):*\n\n" + out)


def reverse_prompt(path: str | Path) -> str:
    """S4: tạo prompt tái tạo A/B/C từ ảnh — trả text DM-ready hoặc thông báo lỗi."""
    p = Path(path)
    if not p.exists():
        return f"⚠️ Không tìm thấy file ảnh: {p.name}"
    out = _glm_vision(p, REVERSE_PROMPT_TMPL, timeout=90.0, max_tokens=2000)
    if not out:
        return "⚠️ Chưa tạo được prompt tái tạo (LLM không phản hồi) — thử lại sau ạ."
    return ("✍️ *Reverse Prompt (do AI suy luận từ ảnh):*\n\n" + out)
