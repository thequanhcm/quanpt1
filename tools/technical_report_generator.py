"""Sinh báo cáo kỹ thuật chi tiết tự động sau MỖI tác vụ (owner directive 02/11/2026).

Owner: "sẽ tạo tự động sau mỗi tác vụ, đều làm báo cáo kỹ thuật chi tiết, có
định hướng, có đề xuất, phân tích, đánh giá... và lưu tự động có gắn ngày giờ
ở đuôi file, lưu vào bao cao xay dung he thong/11.2026/tiến độ phát triển".

Chuẩn bố cục (định dạng thống nhất cho mọi báo cáo):
1. TÓM TẮT ĐIỀU HÀNH  2. PHÂN TÍCH  3. ĐÁNH GIÁ  4. ĐỊNH HƯỚNG  5. ĐỀ XUẤT
6. BẰNG CHỨNG & MINH CHỨNG SỐ  7. RỦI RO & TRUNG THỰC  8. VIỆC CHỜ OWNER

Fail-honest: thiếu mục nào ghi rõ "(không có)", không bịa số liệu.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Múi giờ Việt Nam (UTC+7) — owner ở VN
VN_TZ = timezone(timedelta(hours=7))

# Thư mục gốc báo cáo (owner chỉ định 02/11/2026)
REPORT_ROOT = Path(r"E:\BRAIN\bao cao xay dung he thong")
DEFAULT_SUBDIR = REPORT_ROOT / "11.2026" / "tiến độ phát triển"


def month_subdir(now: datetime | None = None) -> Path:
    """Thư mục theo THÁNG hiện tại (giờ VN) — tháng sau tự sang 12.2026, 01.2027..."""
    n = now or _vn_now()
    return REPORT_ROOT / f"{n.month:02d}.{n.year}" / "tiến độ phát triển"


def _vn_now() -> datetime:
    return datetime.now(VN_TZ)


def _slug(text: str) -> str:
    """Tên file ASCII an toàn: bỏ dấu tiếng Việt (NFD), thay khoảng trắng bằng _."""
    import unicodedata

    s = unicodedata.normalize("NFD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s.strip("_")[:60] or "bao_cao"


class TechnicalReportGenerator:
    """Sinh + lưu báo cáo kỹ thuật chuẩn hóa, tên file gắn ngày giờ (VN)."""

    def __init__(self, base_dir: Path | None = None) -> None:
        # mặc định: thư mục tháng HIỆN TẠI (sinh động theo lịch, giờ VN)
        self.base_dir = Path(base_dir) if base_dir else month_subdir()

    def generate(
        self,
        task_name: str,
        *,
        summary: str,
        analysis: list[str] | None = None,
        evaluation: list[str] | None = None,
        direction: list[str] | None = None,
        proposals: list[str] | None = None,
        evidence: list[str] | None = None,
        risks: list[str] | None = None,
        pending_owner: list[str] | None = None,
        artifacts: list[str] | None = None,
        extra_sections: dict[str, list[str]] | None = None,
        save: bool = True,
    ) -> dict[str, Any]:
        """Sinh báo cáo chuẩn 8 mục. Trả {path, filename, sections} — fail-honest."""
        now = _vn_now()
        stamp = now.strftime("%Y%m%d_%H%M%S")
        safe_name = _slug(task_name)
        filename = f"BAO_CAO_{safe_name}_{stamp}.md"
        target_dir = self.base_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        def _sec(items: list[str] | None, empty_note: str) -> str:
            if not items:
                return f"- (không có — {empty_note})\n"
            return "".join(f"- {it}\n" for it in items)

        lines: list[str] = [
            f"# BÁO CÁO KỸ THUẬT — {task_name}",
            "",
            f"> Sinh tự động {now.strftime('%d/%m/%Y %H:%M:%S')} (giờ VN) theo chỉ thị owner 02/11/2026:",
            "> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.",
            "",
            "## 1. TÓM TẮT ĐIỀU HÀNH",
            summary.strip(),
            "",
            "## 2. PHÂN TÍCH",
            _sec(analysis, "chưa có phân tích bổ sung cho tác vụ này"),
            "## 3. ĐÁNH GIÁ",
            _sec(evaluation, "chưa đánh giá được — cần bổ sung"),
            "## 4. ĐỊNH HƯỚNG",
            _sec(direction, "chưa xác định hướng tiếp theo"),
            "## 5. ĐỀ XUẤT",
            _sec(proposals, "không có đề xuất mới"),
            "## 6. BẰNG CHỨNG & MINH CHỨNG SỐ",
            _sec(evidence, "chưa thu thập bằng chứng"),
            "## 7. RỦI RO & TRUNG THỰC",
            _sec(risks, "không ghi nhận rủi ro mới"),
            "## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH",
            _sec(pending_owner, "không có việc nào chờ owner"),
        ]
        if artifacts:
            lines += ["## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN",
                      "".join(f"- `{a}`\n" for a in artifacts)]
        if extra_sections:
            for title, items in extra_sections.items():
                lines += [f"## {title}", _sec(items, "trống")]

        content = "\n".join(lines).rstrip() + "\n"
        path = target_dir / filename
        if save:
            path.write_text(content, encoding="utf-8")
        return {
            "path": str(path), "filename": filename,
            "saved": save, "timestamp": now.isoformat(),
            "sections": 8 + (1 if artifacts else 0) + len(extra_sections or {}),
        }


def generate_report(task_name: str, **kwargs: Any) -> dict[str, Any]:
    """Hàm tiện ích 1 dòng — dùng ở cuối mỗi tác vụ."""
    return TechnicalReportGenerator().generate(task_name, **kwargs)


if __name__ == "__main__":
    # CLI nhanh: python tools/technical_report_generator.py --demo
    demo = generate_report(
        "demo_hoat_dong_cong_cu",
        summary="Đây là báo cáo demo để anh xem định dạng chuẩn.",
        analysis=["Mục phân tích demo."],
        evaluation=["Mục đánh giá demo."],
        direction=["Mục định hướng demo."],
        proposals=["Mục đề xuất demo."],
        evidence=["Không có số liệu thật — đây là demo."],
        risks=["Không có rủi ro — demo."],
        pending_owner=["Anh xem định dạng và góp ý."],
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
