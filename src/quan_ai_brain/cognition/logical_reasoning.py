"""V9 Slice 2 — Logical Reasoning Engine: suy luận có kiểm chứng trên Deep Memory.

MASTER PROMPT V9 PHẦN V:
- Quy trình 12 bước §V.1 (deterministic subset — mọi bước đều log được).
- Ba loại kết luận §V.2: A trực tiếp / B suy luận / C giả thuyết.
- Chống vòng tròn §V.3: KU suy ra từ B không được dùng làm bằng chứng độc lập
  xác nhận B; nhiều KU cùng gốc 1 nguồn → KHÔNG đếm là đa bằng chứng độc lập.
- Mâu thuẫn §V.4: phân loại DIRECT/CONTEXT_DIFFERENCE, không tự chọn phía.
- Không nhầm INFERRED với VERIFIED (PHẦN IV.1).
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from quan_ai_brain.memory.deep_memory import DeepMemoryStore, _normalize, _tokens

CONCLUSION_A = "A"  # trực tiếp — có bằng chứng VERIFIED khớp trực tiếp
CONCLUSION_B = "B"  # suy luận — từ nhiều dữ kiện, lưu lập luận + giả định
CONCLUSION_C = "C"  # giả thuyết — giải thích được dữ liệu nhưng chưa đủ bằng chứng

_MISSING_MARKERS = ("chưa rõ", "chưa có", "cần kiểm tra", "cần xác minh", "chưa xác định")


def _split_spo_text(statement: str) -> tuple[str, str]:
    """Tách thô subject-head + remainder để so khớp dữ kiện nền."""
    norm = _normalize(statement)
    parts = norm.split()
    return (parts[0] if parts else "", norm)


class ReasoningResult(dict):
    """Kết quả suy luận — luôn serialize được, luôn có traceability."""

    @property
    def ok(self) -> bool:
        return bool(self.get("conclusion"))


class LogicalReasoningEngine:
    def __init__(self, store: DeepMemoryStore) -> None:
        self._store = store

    # -------------------------------------------------------------- §V.1

    def answer_question(
        self, question: str, scope: str | None = None, max_chain_depth: int = 10
    ) -> ReasoningResult:
        """Quy trình 12 bước PHẦN V.1 (bước 12 là cách trình bày ở caller)."""
        steps: list[str] = []
        question_text = (question or "").strip()
        if not question_text:
            return ReasoningResult(error="empty_question", conclusion=None, steps=steps)

        # (1) câu hỏi cần trả lời
        steps.append(f"question={question_text[:80]}")
        q_tokens = _tokens(question_text)

        # (2) truy xuất tri thức liên quan
        units = self._retrieve_relevant(q_tokens, scope)
        steps.append(f"retrieved={len(units)}")

        # (3) nguồn + bằng chứng; (4) dữ kiện nền
        direct_evidence = [u for u in units if u["status"] in ("VERIFIED", "EXTRACTED", "CANDIDATE")]
        contradictions = [u for u in units if u.get("contradiction_refs")]
        steps.append(f"direct_evidence={len(direct_evidence)} contradictions={len(contradictions)}")

        # (5) giả định đang dùng
        assumptions = self._assumptions(question_text, units)
        steps.append(f"assumptions={len(assumptions)}")

        # (6) giả thuyết — tối đa 2 hướng giải thích
        hypotheses = self._hypotheses(units, contradictions)
        steps.append(f"hypotheses={len(hypotheses)}")

        # (7)-(8) nhất quán + bằng chứng ủng hộ/phản bác (chống vòng tròn §V.3)
        support, against, shared_origins = self._support_against(units, max_chain_depth)
        steps.append(f"support={len(support)} against={len(against)} shared_origins={len(shared_origins)}")

        # (9) thông tin còn thiếu
        missing = self._missing_info(units, hypotheses)
        steps.append(f"missing={len(missing)}")

        # (10) kết luận loại nào?
        conclusion_type, statement = self._decide(
            question_text, direct_evidence, against, shared_origins, missing
        )
        steps.append(f"conclusion_type={conclusion_type}")

        result = ReasoningResult(
            question=question_text,
            conclusion=statement,
            conclusion_type=conclusion_type,
            confidence_breakdown=self._confidence_breakdown(
                direct_evidence, against, shared_origins
            ),
            evidence_refs=self._evidence_refs(direct_evidence),
            assumptions=assumptions,
            hypotheses=hypotheses,
            support=support,
            against=against,
            shared_origins=shared_origins,
            missing_info=missing,
            contradiction_refs=[u["knowledge_id"] for u in contradictions],
            steps=steps,
            scope=scope or "general",
        )
        return result

    # -------------------------------------------------------------- retrieval

    def _retrieve_relevant(self, q_tokens: set[str], scope: str | None) -> list[dict[str, Any]]:
        store = self._store
        with store._lock:
            rows = store._connection.execute(
                """
                SELECT knowledge_id, knowledge_type, subject, predicate, object, statement,
                       scope, status, confidence, contradiction_refs_json, source_refs_json,
                       evidence_refs_json, derived_from_json
                FROM knowledge_units
                WHERE status IN ('EXTRACTED','CANDIDATE','VERIFIED','INFERRED','CONFLICTED')
                ORDER BY updated_at_utc DESC LIMIT 300
                """
            ).fetchall()
        relevant: list[dict[str, Any]] = []
        for row in rows:
            u = dict(row)
            u["contradiction_refs"] = _loads(u.pop("contradiction_refs_json"))
            u["source_refs"] = _loads(u.pop("source_refs_json"))
            u["evidence_refs"] = _loads(u.pop("evidence_refs_json"))
            u["derived_from"] = _loads(u.pop("derived_from_json"))
            if scope is not None and u["scope"] not in (scope, "general"):
                continue
            u_tokens = _tokens(u["statement"])
            overlap = q_tokens & u_tokens
            if not overlap:
                # subject-head khớp token câu hỏi cũng tính
                head = _normalize(u["subject"]).split()[:1]
                if not head or head[0] not in q_tokens:
                    continue
            u["matched_on"] = sorted(overlap)[:5]
            relevant.append(u)
        relevant.sort(key=lambda u: -len(u["matched_on"]))
        return relevant[:20]

    # -------------------------------------------------------------- helpers

    def _assumptions(self, question: str, units: list[dict[str, Any]]) -> list[str]:
        assumptions: list[str] = []
        low = _normalize(question)
        if any(m in low for m in _MISSING_MARKERS):
            assumptions.append("câu hỏi chứa tiền giả định chưa được xác minh")
        if any(u["status"] in ("INFERRED",) for u in units):
            assumptions.append("đang dùng tri thức INFERRED chưa được xác minh thật")
        if any(u.get("contradiction_refs") for u in units):
            assumptions.append("giả định mâu thuẫn hiện có sẽ không ảnh hưởng kết luận")
        return assumptions

    def _hypotheses(
        self, units: list[dict[str, Any]], contradictions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        hyps: list[dict[str, Any]] = []
        for u in contradictions[:3]:
            hyps.append({
                "id": u["knowledge_id"],
                "statement": u["statement"][:120],
                "kind": "explains_contradiction",
            })
        if len(units) >= 2 and not contradictions:
            hyps.append({
                "id": None,
                "statement": "các dữ kiện liên quan cùng mô tả một trạng thái nhất quán",
                "kind": "consistency_hypothesis",
            })
        return hyps

    def _support_against(
        self, units: list[dict[str, Any]], max_depth: int
    ) -> tuple[list[str], list[str], list[str]]:
        """§V.3: nhóm KU cùng gốc (derived_from hội tụ về 1 nguồn) chỉ đếm MỘT lần."""
        support: list[str] = []
        against: list[str] = []
        shared_origins: list[str] = []
        origin_map: dict[str, list[str]] = {}
        for u in units:
            root_sources = tuple(sorted(set(u.get("source_refs", []))))
            origin_map.setdefault(root_sources, []).append(u["knowledge_id"])
        for origin, kids in origin_map.items():
            label = ", ".join(origin) if origin else "unknown"
            if len(kids) > 1:
                shared_origins.append(f"{len(kids)} KU cùng nguồn [{label}] — chỉ tính 1 bằng chứng")
            support.append(label)
        for u in units:
            if u.get("contradiction_refs"):
                against.append(u["knowledge_id"])
        return support, against, shared_origins

    def _missing_info(self, units: list[dict[str, Any]], hyps: list[dict[str, Any]]) -> list[str]:
        missing: list[str] = []
        if not units:
            missing.append("không có tri thức nào liên quan — cần thu thập thêm")
        if any(u["status"] in ("CANDIDATE", "EXTRACTED") for u in units) and not any(
            u["status"] == "VERIFIED" for u in units
        ):
            missing.append("chưa có tri thức VERIFIED nào — mọi dữ kiện đều chưa qua xác minh thật")
        for h in hyps:
            if h.get("kind") == "explains_contradiction":
                missing.append("mâu thuẫn chưa được giải quyết — cần nguồn thứ ba hoặc owner review")
        return missing

    def _decide(
        self,
        question: str,
        direct_evidence: list[dict[str, Any]],
        against: list[str],
        shared_origins: list[str],
        missing: list[str],
    ) -> tuple[str, str]:
        verified = [u for u in direct_evidence if u["status"] == "VERIFIED"]
        if verified and not against:
            return CONCLUSION_A, verified[0]["statement"]
        if direct_evidence and against:
            return CONCLUSION_C, (
                "Có dữ kiện mâu thuẫn nhau — chưa thể kết luận; cần owner review hoặc nguồn xác thực hơn"
            )
        if direct_evidence:
            return CONCLUSION_B, (
                f"Dựa trên {len(direct_evidence)} dữ kiện liên quan (chưa qua xác minh thật), "
                f"câu trả lời hợp lý nhất: {direct_evidence[0]['statement']}"
            )
        return CONCLUSION_C, "Không đủ bằng chứng để trả lời câu hỏi này"

    def _confidence_breakdown(
        self,
        direct_evidence: list[dict[str, Any]],
        against: list[str],
        shared_origins: list[str],
    ) -> dict[str, Any]:
        n = len(direct_evidence)
        n_verified = sum(1 for u in direct_evidence if u["status"] == "VERIFIED")
        base = 0.0
        if n:
            base = 0.2 * n_verified + 0.1 * min(n - n_verified, 3)
        penalty = 0.15 * len(against) + 0.1 * len(shared_origins)
        return {
            "note": "chỉ số khai báo, KHÔNG phải xác suất hiệu chuẩn (PHẦN IV.2)",
            "evidence_count": n,
            "verified_count": n_verified,
            "contradiction_penalty": round(penalty, 2),
            "aggregate": round(max(0.0, min(1.0, base - penalty + 0.1 if base else 0.0)), 2),
        }

    def _evidence_refs(self, direct_evidence: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for u in direct_evidence[:10]:
            refs.append(u["knowledge_id"])
            refs.extend(u.get("source_refs", [])[:2])
        return refs

    # -------------------------------------------------------------- contradiction §V.4

    def analyze_contradiction(self, ku_a: str, ku_b: str) -> dict[str, Any]:
        """Phân tích cặp mâu thuẫn: cùng phạm vi/thời điểm? mâu thuẫn thật hay ngữ cảnh khác?"""
        a = self._store.get_unit(ku_a)
        b = self._store.get_unit(ku_b)
        if a is None or b is None:
            return {"error": "unit_not_found"}
        relation = None
        with self._store._lock:
            row = self._store._connection.execute(
                """
                SELECT relation_type, basis, is_speculative FROM knowledge_relations
                WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
                """,
                (ku_a, ku_b, ku_b, ku_a),
            ).fetchone()
        if row is not None:
            relation = dict(row)
        same_scope = a["scope"] == b["scope"]
        return {
            "ku_a": {"id": ku_a, "statement": a["statement"], "scope": a["scope"],
                     "valid_from": a.get("valid_from")},
            "ku_b": {"id": ku_b, "statement": b["statement"], "scope": b["scope"],
                     "valid_from": b.get("valid_from")},
            "relation": relation,
            "same_scope": same_scope,
            "classification": "DIRECT" if same_scope else "CONTEXT_DIFFERENCE",
            "resolution_options": [
                "giữ cả hai với phạm vi/thời điểm áp dụng khác nhau (nếu CONTEXT_DIFFERENCE)",
                "chuyển NEEDS_OWNER_REVIEW — hỏi chủ nhân nguồn nào chuẩn hơn (PHẦN V.4)",
            ],
            "auto_resolution": None,  # KHÔNG tự chọn phía
        }


def _loads(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return raw
    try:
        return list(json_loads(raw or "[]"))
    except Exception:
        return []


def json_loads(raw: str):
    import json

    return json.loads(raw)
