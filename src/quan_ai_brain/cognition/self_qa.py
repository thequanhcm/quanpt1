"""Self-Q&A — trả lời câu hỏi về BẢN THÂN CHERRY từ dữ liệu sống (M5, G-12 + M4-C).
(Rename 07/11: pattern nhận cả tên CHERRY; giữ tony quá độ.)

Nguyên tắc:
- Khi anh hỏi "em là ai / em làm được gì / em đang ở đâu / sức khỏe em /
  em học được gì / em không làm được gì" → trả lời từ SelfModelEngine +
  monitoring + DB THẬT lúc gọi, KHÔNG để LLM phỏng đoán (chống ảo giác).
- Không khớp câu hỏi self → trả None để caller đi đường intent/GLM bình thường.
- Fail-honest: đọc dữ liệu lỗi → trả lời trung thực "chưa đọc được", không bịa.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# (category, pattern) — anchor vào em/bạn/cherry/tony + chủ đề, KHÔNG khớp "tôi ...".
_SELF_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("identity", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,40}(là ai|tên gì|là gì|giới thiệu|nhận diện)"
        r"|\b(giới thiệu|nhận diện)[^.?!\n]{0,20}\b(em|tony)\b", re.IGNORECASE)),
    ("limits", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,40}"
        r"(không (làm )?được gì|hạn chế|giới hạn|khó khăn)", re.IGNORECASE)),
    ("capabilities", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,50}"
        r"(làm được( những)? gì|có (những )?(năng lực|kỹ năng|công cụ)|năng lực gì"
        r"|kỹ năng gì|công cụ gì|biết làm gì)", re.IGNORECASE)),
    ("location", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,40}(đang (chạy|ở)|ở đâu|chạy ở đâu|nơi nào)",
        re.IGNORECASE)),
    ("health", re.compile(
        r"(sức khỏe|sức khoẻ|tình trạng hệ thống|hệ thống (có )?khỏe|"
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,30}(khỏe không|ổn không|có vấn đề))",
        re.IGNORECASE)),
    ("learning", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,40}"
        r"(học được( gì| những gì)|đã học gì|tự học|tiến bộ|đang học)",
        re.IGNORECASE)),
    ("limits", re.compile(
        r"\b(em|bạn|cherry|tony)\b[^.?!\n]{0,40}"
        r"(không (làm )?được gì|hạn chế|giới hạn|khó khăn)", re.IGNORECASE)),
]


class SelfQA:
    """Trả lời câu hỏi self từ dữ liệu sống (không LLM)."""

    def __init__(self, workspace: str | Path = ".") -> None:
        self.workspace = Path(workspace)
        self._engine: Any = None

    def _engine_lazy(self) -> Any:
        if self._engine is None:
            from quan_ai_brain.cognition.self_model_engine import SelfModelEngine
            self._engine = SelfModelEngine(str(self.workspace))
        return self._engine

    # ---------- detection ----------
    def classify(self, text: str) -> str | None:
        """Trả category nếu là câu hỏi về bản thân; None nếu không phải."""
        t = str(text or "").strip()
        if not t or len(t) > 300:
            return None
        for cat, pat in _SELF_PATTERNS:
            if pat.search(t):
                return cat
        return None

    # ---------- data helpers ----------
    def _live_model(self) -> dict[str, Any]:
        return self._engine_lazy().generate_self_model().to_dict()

    def _learning_state(self) -> dict[str, Any]:
        return self._engine_lazy().get_learning_checkpoint_state(self.workspace)

    def _candidate_counts(self) -> dict[str, int]:
        import sqlite3
        out = {"approved": 0, "quarantined": 0}
        db = self.workspace / "data" / "brain.db"
        if not db.exists():
            return out
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT status, COUNT(*) FROM candidate_knowledge GROUP BY status"
            ).fetchall()
            d = dict(rows)
            out["approved"] = int(d.get("approved", 0))
            out["quarantined"] = int(d.get("quarantined", 0))
        finally:
            con.close()
        return out

    def _health_snapshot(self) -> dict[str, Any]:
        from quan_ai_brain.monitoring import get_global_aggregator
        return get_global_aggregator().snapshot()

    # ---------- answers ----------
    def answer(self, text: str) -> str | None:
        """Câu trả lời self grounded; None nếu không phải câu hỏi self."""
        cat = self.classify(text)
        if cat is None:
            return None
        try:
            return getattr(self, f"_answer_{cat}")()
        except Exception as exc:
            return (f"Em chưa đọc được dữ liệu tự nhận thức lúc này "
                    f"(lỗi: {type(exc).__name__}). Anh hỏi lại giúp em nhé.")

    def _answer_identity(self) -> str:
        m = self._live_model()
        i, d = m["identity"], m["deployment"]
        return (f"Em là {i['assistant_name']}, trợ lý điều hành số của anh "
                f"{i['owner']}. Em chạy trên PC {d['core_location'].split('(')[0].strip()} "
                f"và {d['edge_location'].split('(')[0].strip()}. "
                f"Em có {(m.get('verified_capabilities') or []).__len__()} năng lực "
                f"đã kiểm chứng — anh hỏi \"em làm được gì\" để nghe chi tiết nhé.")

    def _answer_capabilities(self) -> str:
        m = self._live_model()
        verified = m.get("verified_capabilities") or []
        unverified = m.get("unverified_capabilities") or []
        names = "; ".join(str(x) for x in verified[:5])
        extra = f" …còn {len(verified) - 5} nữa" if len(verified) > 5 else ""
        return (f"Em có {len(verified)} năng lực đã kiểm chứng: {names}{extra}. "
                f"Còn {len(unverified)} năng lực chưa kiểm chứng/chờ phê duyệt. "
                f"Mọi năng lực em báo đều có bằng chứng kiểm thử, không phóng đại ạ.")

    def _answer_location(self) -> str:
        m = self._live_model()
        d = m["deployment"]
        return (f"Em đang chạy tại: {d['core_location']} — và hình thể "
                f"{d['edge_location']}. Kiến trúc: {d['architecture']}.")

    def _answer_health(self) -> str:
        snap = self._health_snapshot()
        overall = str(snap.get("overall_status", "UNKNOWN"))
        pc = (snap.get("pc") or {}).get("status", "UNKNOWN")
        pi5 = (snap.get("pi5") or {}).get("status", "UNKNOWN")
        warn = [
            f"{cid.split(':')[-1]} ({info.get('severity')})"
            for comp in (snap.get("pc"), snap.get("pi5"))
            for cid, info in ((comp or {}).get("checks") or {}).items()
            if info.get("severity") not in ("NORMAL", None)
        ]
        tail = f" Đang cảnh báo: {', '.join(warn[:3])}." if warn else " Không có cảnh báo nào."
        vn = {"NORMAL": "bình thường", "WARNING": "có cảnh báo",
              "CRITICAL": "nghiêm trọng", "UNKNOWN": "chưa đo được",
              "MAINTENANCE": "đang bảo trì"}
        return (f"Sức khỏe tổng thể: {vn.get(overall, overall)}. "
                f"PC: {vn.get(pc, pc)}, Pi5: {vn.get(pi5, pi5)}.{tail}")

    def _answer_learning(self) -> str:
        clo = self._learning_state()
        cd = self._candidate_counts()
        import json as _json
        skills_total, skills_ready = 0, 0
        reg = self.workspace / "data" / "skill_registry.json"
        if reg.exists():
            try:
                skills = _json.loads(reg.read_text(encoding="utf-8")).get("skills", [])
                skills_total = len(skills)
                skills_ready = sum(1 for s in skills if s.get("status") == "AVAILABLE")
            except (json.JSONDecodeError if False else OSError, ValueError, KeyError):
                pass
        last = clo.get("clo_last_session")
        clo_txt = "chưa có vòng tự chủ học nào"
        if last:
            clo_txt = (f"vòng #{last['cycle']} trạng thái {last['status']} "
                       f"từ {str(last['started_at'])[:16]}")
        return (f"Tự chủ học: {clo.get('clo_sessions', 0)} phiên CLO, {clo_txt}. "
                f"Tri thức: {cd['approved']} mục anh đã duyệt, {cd['quarantined']} mục "
                f"chờ anh duyệt (Q-4). Kỹ năng: {skills_total} đăng ký, "
                f"{skills_ready} sẵn sàng.")

    def _answer_limits(self) -> str:
        m = self._live_model()
        lims = m.get("known_limitations") or []
        if not lims:
            return ("Em không ghi nhận giới hạn mới nào trong self model. "
                    "Mọi giới hạn em báo đều dựa trên dữ liệu thật ạ.")
        lines = "; ".join(str(x) for x in lims[:3])
        return (f"Giới hạn em đang ghi nhận (từ self model): {lines}. "
                f"Chi tiết đầy đủ trong dashboard /health khu M4 ạ.")
