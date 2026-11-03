"""CAI V3.0 — SELF-STUDY ENGINE V2 (triển khai "chạy thử chu trình tự học").

Xử lý tồn tại tự khai (netChat 07:49 02/11):
- "Động Cơ Tự Học V1 đã viết xong nhưng chưa chạy thử thực địa, DB học tập gần trống"
- Cogitate() hardcoded 3 kịch bản → không học gì mới
- Dupes 44% trong candidate_knowledge (audit UAME)

Chu trình §VI (CAI V3.0 Phase 4+9) + CSEF §3:
    SCAN (lỗ hổng tri thức từ episodes/lessons/test failures)
  → STUDY (researcher injectable: web_search prod, fake test — KHÔNG fake trong prod)
  → SYNTHESIZE (statement + provenance: source_type, source_ref, confidence)
  → DEDUP (so statement đã có trong candidate_knowledge + semantic_memory — chống dupes)
  → QUARANTINE (ghi candidate_knowledge status='quarantined' — KHÔNG tự nạp memory)
  → REPORT (chu kỳ có số liệu thật, từng bước có bằng chứng)

Ranh giới an toàn: kiến thức mới LUÔN quarantined chờ anh Quanpt1 duyệt
(§XI: không tự sửa Memory Production). Engine không tự bật chạy nền — chỉ
chạy chu kỳ khi được gọi (test/demo/owner-approved daemon sau này).
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

UTC = timezone.utc

# Nguồn tri thức: episodes kinds được quét
GAP_EPISODE_KINDS = ("experience_lesson", "task")


def _norm(text: str) -> str:
    """Chuẩn hóa so khớp dedup: lowercase + bỏ dấu + bỏ ký tự thừa."""
    t = unicodedata.normalize("NFD", (text or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


# ───────────────────────── SCAN: lỗ hổng tri thức ─────────────────────────
@dataclass
class KnowledgeGap:
    gap_id: str
    topic: str
    source: str          # "episodes:experience_lesson" / "test_failure:..." / "manual"
    evidence: str        # bằng chứng vì sao đây là gap
    priority: int = 1    # 3 = cao


class KnowledgeGapScanner:
    """Quét dữ liệu thật (episodes + lessons) tìm lỗ hổng tri thức.

    Gap = chủ đề xuất hiện trong kinh nghiệm nhưng chưa có knowledge
    quarantined/approved/promoted tương ứng trong candidate_knowledge.
    """

    def __init__(self, db_path: str | Any) -> None:
        self.db_path = str(db_path)

    def scan(self, *, limit: int = 10) -> list[KnowledgeGap]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        gaps: list[KnowledgeGap] = []
        try:
            # 1) Lessons từ kinh nghiệm chưa được chuyển thành knowledge
            rows = con.execute(
                "SELECT id, summary, created_at_utc FROM episodes "
                "WHERE kind='experience_lesson' ORDER BY created_at_utc DESC LIMIT ?",
                (limit * 4,)).fetchall()
            known_sets = self._known_word_sets(con)
            for r in rows:
                topic = self._topic_from_summary(r["summary"])
                if not topic:
                    continue
                if self._topic_known(topic, known_sets):
                    continue  # đã có knowledge tương đương — không phải gap
                gaps.append(KnowledgeGap(
                    gap_id=f"gap-{r['id'][:12] if r['id'] else 'x'}",
                    topic=topic,
                    source="episodes:experience_lesson",
                    evidence=f"lesson {r['created_at_utc'][:10]}: {r['summary'][:140]}",
                    priority=2))
        finally:
            con.close()
        # dedup gap theo topic + cắt limit
        seen: set[str] = set()
        unique: list[KnowledgeGap] = []
        for g in sorted(gaps, key=lambda x: -x.priority):
            key = _norm(g.topic)
            if key in seen:
                continue
            seen.add(key)
            unique.append(g)
        return unique[:limit]

    def _known_word_sets(self, con: sqlite3.Connection) -> list[set[str]]:
        sets: list[set[str]] = []
        for (stmt,) in con.execute(
                "SELECT statement FROM candidate_knowledge LIMIT 20000"):
            ws = set(_norm(stmt or "").split())
            if ws:
                sets.append(ws)
        return sets

    @staticmethod
    def _topic_known(topic: str, known_sets: list[set[str]]) -> bool:
        """Topic là 'đã biết' nếu word-set của nó nằm trọn trong 1 statement cũ
        (containment > 0.75, cả hai >= 4 từ) — cùng logic với dedup của engine,
        chống gap giả do cắt 60 ký tự lệch biên từ."""
        tw = set(_norm(topic).split())
        if not tw:
            return True
        for other in known_sets:
            if len(other) >= 4 and len(tw) >= 4:
                if len(tw & other) / max(1, len(tw)) > 0.75:
                    return True
            elif tw == other:
                return True
        return False

    @staticmethod
    def _topic_from_summary(summary: str) -> str:
        """Lấy cụm chủ đề ngắn từ câu summary (cắt 60 ký tự tại biên từ)."""
        s = re.sub(r"\s+", " ", (summary or "").strip())
        if len(s) <= 60:
            return s
        cut = s[:60]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        return cut


# ───────────────────────── STUDY → SYNTHESIZE ─────────────────────────
@dataclass
class StudyFinding:
    gap: KnowledgeGap
    statement: str
    source_type: str      # WEB_RESEARCH / EXPERIENCE / DOC / UNRESOLVED
    source_ref: str
    confidence: float     # 0..1 — hết thấp thì khai UNRESOLVED, không bịa
    raw_notes: str = ""


# Researcher callable: (gap) -> list[dict] sources [{"title","snippet","url"}]
Researcher = Callable[[KnowledgeGap], list[dict[str, Any]]]


class StudyCycleEngine:
    """Chu trình tự học đầy đủ — mọi kết quả ghi vào QUARANTINE, không tự nạp."""

    def __init__(self, db_path: str | Any, researcher: Researcher,
                 *, max_gaps_per_cycle: int = 3) -> None:
        self.db_path = str(db_path)
        self.researcher = researcher
        self.max_gaps = max_gaps_per_cycle
        self.scanner = KnowledgeGapScanner(db_path)

    # ------------------------------------------------------------------
    def run_cycle(self, *, gaps: list[KnowledgeGap] | None = None) -> dict[str, Any]:
        started = datetime.now(UTC).isoformat()
        gap_list = gaps if gaps is not None else self.scanner.scan(
            limit=self.max_gaps)
        findings: list[StudyFinding] = []
        quarantined: list[dict[str, Any]] = []
        duplicates: list[str] = []
        unresolved: list[str] = []
        for gap in gap_list[: self.max_gaps]:
            try:
                sources = self.researcher(gap)
            except Exception as exc:
                sources = []
                unresolved.append(f"{gap.topic} (researcher lỗi: {exc})")
            if not sources:
                if gap.topic not in unresolved:
                    unresolved.append(gap.topic)
                findings.append(StudyFinding(
                    gap=gap, statement="", source_type="UNRESOLVED",
                    source_ref="", confidence=0.0))
                continue
            f = self._synthesize(gap, sources)
            findings.append(f)
            if f.source_type == "UNRESOLVED":
                unresolved.append(gap.topic)
                continue
            dup = self._is_duplicate(f.statement)
            if dup:
                duplicates.append(gap.topic)
                continue
            kid = self._quarantine(f)
            quarantined.append({"knowledge_id": kid, "topic": gap.topic,
                                "statement": f.statement,
                                "source_type": f.source_type,
                                "confidence": f.confidence})
        return {
            "cycle_id": f"study-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "started_at": started,
            "finished_at": datetime.now(UTC).isoformat(),
            "gaps_scanned": len(gap_list),
            "findings": len(findings),
            "quarantined": quarantined,
            "duplicates_skipped": duplicates,
            "unresolved": unresolved,
            "boundary": "mọi tri thức mới ở trạng thái QUARANTINED — chờ Quanpt1 duyệt",
        }

    # ------------------------------------------------------------------
    def _synthesize(self, gap: KnowledgeGap, sources: list[dict[str, Any]]) -> StudyFinding:
        """Tổng hợp statement từ nguồn thật — trích dẫn, không bịa.

        Statement chỉ gồm nội dung có trong sources; confidence theo số
        nguồn độc lập. Không đủ → UNRESOLVED."""
        good = [s for s in sources if (s.get("snippet") or s.get("title"))]
        if not good:
            return StudyFinding(gap=gap, statement="", source_type="UNRESOLVED",
                                source_ref="", confidence=0.0)
        title = str(good[0].get("title") or "")[:120]
        snippet = str(good[0].get("snippet") or good[0].get("title") or "")[:280]
        url = str(good[0].get("url") or "internal")
        statement = f"{gap.topic}: {snippet} (nguồn: {title or url})"
        confidence = min(0.9, 0.4 + 0.15 * len(good))
        return StudyFinding(gap=gap, statement=statement,
                            source_type="WEB_RESEARCH",
                            source_ref=json.dumps(
                                {"url": url, "title": title,
                                 "n_sources": len(good)}, ensure_ascii=False),
                            confidence=round(confidence, 2),
                            raw_notes=snippet)

    def _is_duplicate(self, statement: str) -> bool:
        """DEDUP: so word-set (containment) với candidate_knowledge + semantic_memory.

        Xử lý tồn tại 'dupes 44%': knowledge trùng không được ghi thêm.
        Containment > 0.7 (word-set mới nằm sẵn trong statement cũ) → trùng."""
        words = set(_norm(statement).split())
        if len(words) < 3:
            return True
        con = sqlite3.connect(self.db_path)
        try:
            rows: list[str] = [r[0] for r in con.execute(
                "SELECT statement FROM candidate_knowledge LIMIT 20000")]
            try:
                rows += [r[0] for r in con.execute(
                    "SELECT statement FROM semantic_memory LIMIT 20000")]
            except sqlite3.OperationalError:
                pass
        finally:
            con.close()
        for stmt in rows:
            other = set(_norm(stmt or "").split())
            if not other:
                continue
            # Guard chống false-positive: statement cũ quá ngắn (<4 từ) chỉ
            # tính trùng khi GIỐNG HẲT, không dùng containment (vd "tài về"
            # nằm trong mọi câu → dính 1.0 oan).
            if len(other) >= 4 and len(words) >= 4:
                inter = len(words & other)
                if inter / max(1, min(len(words), len(other))) > 0.75:
                    return True
            elif words == other:
                return True
        return False

    def _quarantine(self, f: StudyFinding) -> str:
        """Ghi vào candidate_knowledge status='quarantined' + provenance."""
        import uuid
        kid = f"know_{uuid.uuid4().hex[:12]}"
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "INSERT INTO candidate_knowledge(id, created_at_utc, statement, "
                "source_ref, rationale, status, decision_note) VALUES(?,?,?,?,?,?,?)",
                (kid, datetime.now(UTC).isoformat(), f.statement,
                 json.dumps({"source_type": f.source_type,
                             "source_ref": f.source_ref,
                             "confidence": f.confidence}, ensure_ascii=False),
                 f"self-study cycle cho gap '{f.gap.topic}' ({f.gap.source})",
                 "quarantined", ""))
            con.commit()
        finally:
            con.close()
        return kid


# ───────────────────────── Tích hợp AutonomousMind ─────────────────────────
def build_thought_from_cycle(cycle: dict[str, Any]) -> dict[str, Any]:
    """Suy nghĩ NỘI TÂM THẬT từ kết quả chu trình (thay hardcoded cogitate)."""
    q = cycle.get("quarantined", [])
    dup = cycle.get("duplicates_skipped", [])
    unres = cycle.get("unresolved", [])
    lines = [
        f"Chu trình tự học {cycle.get('cycle_id')}: quét {cycle.get('gaps_scanned')} lỗ hổng.",
    ]
    if q:
        lines.append("Đã tổng hợp và CÁCH LY " + ", ".join(
            f"'{x['topic']}'" for x in q) + " — chờ anh duyệt trước khi vào trí nhớ chính thức.")
    if dup:
        lines.append("Phát hiện trùng lặp, đã bỏ qua: " + ", ".join(dup) + " (chống dupes).")
    if unres:
        lines.append("Chưa giải quyết được (không bịa): " + ", ".join(unres) + ".")
    if not q and not dup and not unres:
        lines.append("Không có lỗ hổng mới cần học trong chu kỳ này.")
    lines.append(f"Ranh giới: {cycle.get('boundary')}")
    return {
        "thought_id": f"study-{cycle.get('cycle_id')}",
        "topic": "Tự học: quét và cách ly tri thức mới",
        "trigger": "SELF_STUDY_CYCLE",
        "inner_monologue": " ".join(lines),
        "actionable_idea": (f"Duyệt {len(q)} kiến thức quarantined" if q else None),
        "sentiment": "ASPIRATIONAL" if q else "CONSTRUCTIVE",
        "created_at_utc": cycle.get("finished_at"),
    }
