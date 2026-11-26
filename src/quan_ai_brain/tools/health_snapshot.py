"""Health snapshot — bằng chứng sống cho tư duy phản biện của CHERRY.

(26/11/2026, Sprint CHERRY-CÓ-TƯ-DUY) Owner: "cherry chưa có quan điểm, suy
nghĩ. hãy xây dựng để cherry có tư duy".

Vấn đề thật (ảnh image_92b084): owner hỏi "em tư vấn thấy hệ thống của em có
thiếu sót gì?" → CHERRY không trả lời được vì (1) system prompt toàn luật cấm
→ model không được có ý kiến; (2) không có DỮ LIỆU SỐNG nào được nạp cho câu
hỏi đánh giá → GLM hoặc bịa hoặc né.

Module này cung cấp:
1. collect_health_snapshot()  — probe THẬT read-only, không bao giờ raise
   (fail-open): components (grounding), Pi5, ổ đĩa E:, heartbeat responder,
   lỗi gần nhất trong logs, hàng chờ tự học chờ duyệt.
2. render_health_snapshot_block() — block "[SNAPSHOT SỨC KHỎE HỆ THỐNG...]"
   để chèn vào system_instructions, hướng dẫn model ĐƯA QUAN ĐIỂM có căn cứ.
3. looks_like_analysis_query() — detector câu hỏi phân tích/đánh giá
   ("thiếu sót gì", "tư vấn", "đánh giá", "cải thiện"...). Ngưỡng thận trọng:
   chỉ khớp câu HỎI về hệ thống, không ăn lệnh hành động.

An toàn: 100% chỉ-đọc, không chạy subprocess lạ, không raise; timeout thấp
(<= 2s mỗi probe). Không đụng R4/R5, không đổi trạng thái gì.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "collect_health_snapshot",
    "render_health_snapshot_block",
    "looks_like_analysis_query",
]

_WORKSPACE = Path(__file__).resolve().parents[3]

_ANALYSIS_RE = re.compile(
    r"(thiếu\s*sót|thieu sot|tư vấn|tu van|đánh giá|danh gia|nhận xét|nhan xet|"
    r"ý kiến|y kien|quan điểm|quan diem|suy nghĩ|suy nghi|cải thiện|cai thien|"
    r"nâng câ?p|nang cap|hạn chế|han che|vấn đề|van de|rủi ro|rui ro|"
    r"làm\s*(gì|gi)\s*(được|duoc)?\s*(tốt|tot|khác|khac|hơn|nữa|nua)|"
    r"(hệ thống|he thong|bot|cherry|em)\s*(có|co)\s*(gì|gi|vấn đề|van de|ổn|on|ok|ổn định|on dinh)\b|"
    r"(sao|tại sao|tai sao)[^?]*\?)",
    re.IGNORECASE,
)

# Câu hỏi HỌC HỎI tri thức chung (không phải đánh giá hệ thống) — loại trừ để
# detector không kích hoạt oan cho câu "AI là gì", "Việt Nam có bao nhiêu dân".
_NOT_SYSTEM_RE = re.compile(
    r"(thế giới|the gioi|việt nam|viet nam|bầu trời|bau troi|mon\s*ăn|mon an|"
    r"thời tiết|thoi tiet|học bài|hoc bai|giúp tôi làm|giup toi lam)",
    re.IGNORECASE,
)


def looks_like_analysis_query(query: str) -> bool:
    """True nếu câu hỏi muốn CHERRY PHÂN TÍCH/ĐÁNH GIÁ hệ thống.

    Thận trọng: phải có từ khóa phân tích VÀ nhắc đến hệ thống/em/bot/anh
    (hoặc là câu hỏi mở về hệ thống), trừ câu hỏi tri thức chung.
    """
    q = str(query or "")
    if not q.strip():
        return False
    if _NOT_SYSTEM_RE.search(q):
        return False
    if not _ANALYSIS_RE.search(q):
        return False
    # Phải nói về hệ thống/em/bot/công việc của em (chỉ định đối tượng đánh giá)
    return bool(re.search(
        r"(hệ thống|he thong|em|bot|cherry|bản thân|ban than|hệ\w*|công việc|cong viec|"
        r"trợ lý|tro ly|assistant|hiệu năng|hieu nang|code|kiến trúc|kien truc|bộ não|bo nao)",
        q,
        re.IGNORECASE,
    ))


def _probe_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _disk_usage_e() -> dict[str, Any]:
    try:
        import shutil
        total, used, free = shutil.disk_usage("E:/")
        return {
            "free_gb": round(free / 1024**3, 1),
            "total_gb": round(total / 1024**3, 1),
            "used_pct": round(used / total * 100, 1),
        }
    except Exception:
        return {}


def _responder_heartbeat_age_s() -> float | None:
    try:
        p = _WORKSPACE / "logs" / "netchat_responder_heartbeat.log"
        return max(0.0, time.time() - p.stat().st_mtime)
    except Exception:
        return None


def _recent_log_errors(max_lines: int = 400, max_items: int = 5) -> list[str]:
    """Quét log gần nhất tìm lỗi thật (chỉ đọc, không đụng file khác)."""
    logs = [
        _WORKSPACE / "logs" / "netchat_auto_responder_stdout.log",
        _WORKSPACE / "logs" / "dual_servers_watchdog.log",
    ]
    found: list[str] = []
    pat = re.compile(
        r"(error|exception|traceback|failed|lỗi|crash|⚠️|❌)", re.IGNORECASE)
    for log in logs:
        try:
            if not log.exists():
                continue
            with log.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-max_lines:]
            for line in reversed(lines):  # mới nhất trước
                s = line.strip()
                if s and pat.search(s) and not s.startswith("#"):
                    # rút gọn, bỏ đường dẫn dài
                    s = re.sub(r"File \"[^\"]+\", line \d+", "…", s)
                    found.append(s[:160])
                    if len(found) >= max_items:
                        return found
        except Exception:
            continue
    return found


def _self_improve_pending() -> int:
    try:
        p = _WORKSPACE / "data" / "self_improve" / "proposals.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return sum(1 for x in data
                       if isinstance(x, dict)
                       and str(x.get("status", "")).upper() == "PENDING_REVIEW")
        if isinstance(data, dict):
            items = data.get("proposals") or data.get("items") or []
            if isinstance(items, list):
                return sum(1 for x in items
                           if isinstance(x, dict)
                           and str(x.get("status", "")).upper() == "PENDING_REVIEW")
        return 0
    except Exception:
        return 0


def _pi5_state() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:8765/api/executive/edge/status",
                timeout=2.0) as r:
            edge = (json.loads(r.read().decode("utf-8", errors="replace"))
                    .get("edge") or {})
        state = str(edge.get("state", "UNKNOWN"))
        return {
            "connected": state in ("READY", "CONNECTED", "SYNCING", "RECOVERING"),
            "state": state,
            "heartbeat_age_s": edge.get("seconds_since_heartbeat"),
        }
    except Exception:
        return {"connected": False, "state": "UNAVAILABLE",
                "heartbeat_age_s": None}


def collect_health_snapshot(current_model: str | None = None) -> dict[str, Any]:
    """Probe thật toàn hệ thống, trả dict fact — KHÔNG bao giờ raise."""
    snap: dict[str, Any] = {"generated_at_utc":
                            datetime.now(timezone.utc).isoformat()}
    try:
        # Components — tái dùng logic probe TCP của grounding (nhẹ, <=1s)
        try:
            from quan_ai_brain.cognition.grounding_facts import (
                collect_grounding_facts as _cgf,
            )
            gf = _cgf(current_model=current_model)
            snap["components"] = gf.get("components", {})
            snap["llm"] = gf.get("llm", {})
            snap["pi5"] = gf.get("pi5_edge", {})
        except Exception:
            snap["components"] = {}
            snap["pi5"] = {"connected": False, "state": "UNKNOWN"}

        snap["disk_e"] = _disk_usage_e()
        hb = _responder_heartbeat_age_s()
        snap["responder_heartbeat_age_s"] = (round(hb) if hb is not None
                                             else None)
        snap["recent_errors"] = _recent_log_errors()
        snap["self_improve_pending"] = _self_improve_pending()
    except Exception as e:  # fail-open tuyệt đối
        snap["error"] = f"{type(e).__name__}: {e}"
    return snap


def render_health_snapshot_block(snap: dict[str, Any]) -> str:
    """Render block tiếng Việt hướng dẫn model ĐƯA QUAN ĐIỂM (không né)."""
    comp = snap.get("components", {})
    pi5 = snap.get("pi5", {})
    disk = snap.get("disk_e", {})
    hb = snap.get("responder_heartbeat_age_s")
    errs = snap.get("recent_errors", []) or []
    pend = snap.get("self_improve_pending", 0)

    online = [k for k, v in comp.items() if v == "ONLINE"]
    offline = [k for k, v in comp.items() if v == "OFFLINE"]

    lines: list[str] = [
        "[SNAPSHOT SỨC KHỎE HỆ THỐNG — đo bằng probe thật lúc "
        f"{snap.get('generated_at_utc', '?')}. Đây là BẰNG CHỨNG cho em tự "
        "phân tích, KHÔNG phải lệnh hành động:]",
        f"1. Components ONLINE: {', '.join(online) if online else 'không rõ'}"
        + (f" | OFFLINE: {', '.join(offline)}" if offline else ""),
    ]
    if pi5:
        if pi5.get("connected"):
            hb_pi5 = pi5.get("heartbeat_age_s")
            lines.append(
                f"2. Pi 5 (hình thể): ONLINE — heartbeat {hb_pi5:.0f}s trước."
                if isinstance(hb_pi5, (int, float))
                else "2. Pi 5 (hình thể): ONLINE (heartbeat không rõ tuổi).")
        else:
            lines.append(
                f"2. Pi 5 (hình thể): {pi5.get('state', 'KHÔNG RÕ')} — mất/"
                "chưa xác minh kết nối. Đây là điểm yếu thật nếu owner đang "
                "cần điều khiển loa/màn hình.")
    if disk:
        lines.append(
            f"3. Ổ E: (workspace) còn {disk.get('free_gb', '?')}GB / "
            f"{disk.get('total_gb', '?')}GB (dùng {disk.get('used_pct', '?')}%).")
    if hb is not None:
        stale = " — CHÚ Ý: responder chat có thể đang treo/chậm" if hb > 300 else ""
        lines.append(f"4. Responder chat (tim đập): {hb:.0f}s trước.{stale}")
    else:
        lines.append("4. Responder chat (tim đập): KHÔNG THẤY — điểm nghi "
                     "trọng: bot có thể chết im lặng.")
    if errs:
        lines.append("5. Lỗi gần nhất trong logs (tối đa 5, mới nhất trước):")
        lines += [f"   - {e}" for e in errs]
    else:
        lines.append("5. Lỗi gần nhất trong logs: không thấy lỗi nổi bật.")
    lines.append(
        f"6. Hàng chờ tự học chờ anh duyệt: {pend} đề xuất."
        + (" — owner chưa duyệt nên kiến thức mới chưa vào được." if pend
           else ""))
    lines += [
        "7. [YÊU CẦU TƯ DUY — BẮT BUỘC] Khi anh hỏi phân tích/đánh giá/tư vấn "
        "về hệ thống: em PHẢI đưa QUAN ĐIỂM CÓ CĂN CỨ từ snapshot ở trên: "
        "(a) nêu 1-3 điểm yếu/điểm cần cải thiện THẬT (dựa vào dữ liệu, "
        "không bịa), (b) nói rõ vì sao, (c) đề xuất hướng xử lý cụ thể, "
        "(d) nêu 1-2 điểm đang TỐT để anh thấy rõ cả hai mặt.",
        "8. KHÔNG né bằng câu kiểu 'em chưa đủ dữ kiện', 'hệ thống đang ổn "
        "định không có gì đáng nói' — snapshot trên CHÍNH LÀ dữ kiện. Không "
        "đủ dữ kiện phần nào thì nói rõ thiếu gì và đề xuất cách đo thêm.",
        "9. Giữ đúng luật xưng 'em' gọi 'anh', tiếng Việt tự nhiên, ngắn gọn "
        "(5-8 gạch đầu dòng), không liệt kê metadata nguồn.",
    ]
    return "\n".join(lines)
