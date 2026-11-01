"""V10 — Owner-Gated Memory Review Session (MASTER PROMPT V10).

Lệnh `SÀNG LỌC` tạo một đợt sàng lọc MẪU (scope giới hạn, có review_session_id
duy nhất): phân tích CHỈ ĐỌC, hiển thị 4 nhóm bắt buộc trên giao diện, chờ
Quanpt1 phản hồi, chỉ cập nhật đúng phạm vi được xác nhận, lưu lịch sử
trước–sau (review_changes) và hỗ trợ hoàn tác.

Ràng buộc cốt lõi:
- KHÔNG ghi vào bảng tri thức trong lúc phân tích (chỉ bảng vận hành review).
- KHÔNG tự hợp nhất/xoá/nâng trạng thái hàng loạt; thay đổi quan trọng phải
  preview before/after rồi confirm lần 2 (PHẦN V.4, VI.3).
- KHÔNG mở rộng phạm vi khi chưa có xác nhận của chủ (PHẦN VIII).
- NO_DECISION giữ tri thức ở trạng thái chờ — không tự chọn phương án.
"""
from __future__ import annotations

import json
from typing import Any

from quan_ai_brain.cognition.logical_reasoning import LogicalReasoningEngine
from quan_ai_brain.memory.deep_memory import (
    DeepMemoryStore,
    _antonym_flip,
    _has_negation,
    _jaccard,
    _new_id,
    _now,
    _tokens,
)
from quan_ai_brain.core.redaction import redact_text

# ---------------------------------------------------------------- constants

SESSION_STATUSES = (
    "IDLE", "ANALYZING", "REVIEW_READY", "WAITING_OWNER",
    "APPLYING_CONFIRMED_CHANGES", "COMPLETED", "PAUSED", "FAILED",
)

FINDING_TYPES = (
    "DUPLICATE", "SIMILAR", "CONTRADICTION", "STALE",
    "MISSING_RELATION", "INSUFFICIENT_INFO",
)

RESPONSE_KINDS = (
    "CLARIFY", "ADD_FACT", "CORRECT", "CONFIRM_RELATION",
    "CONFIRM_INFERENCE", "REJECT_INFERENCE", "LIMIT_SCOPE",
    "MORE_REVIEW", "NO_DECISION",
)

CERTAINTY_LEVELS = ("HYPOTHESIS", "UNVERIFIED_INFERENCE", "VERIFIED", "INSUFFICIENT_EVIDENCE")

ACTIVE_STATUSES = ("IDLE", "ANALYZING", "REVIEW_READY", "WAITING_OWNER", "APPLYING_CONFIRMED_CHANGES", "PAUSED")

DEFAULT_SCOPE_LIMIT = 20
_DUPLICATE_JACCARD = 0.6
_SIMILAR_JACCARD = 0.35


def _loads(raw: Any) -> Any:
    if isinstance(raw, (list, dict)) or raw is None:
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


class MemoryReviewSession:
    """Một đợt sàng lọc owner-gated trên DeepMemoryStore (V9)."""

    def __init__(self, store: DeepMemoryStore, scope_limit: int = DEFAULT_SCOPE_LIMIT) -> None:
        if not 1 <= int(scope_limit) <= 200:
            raise ValueError("scope_limit must be between 1 and 200")
        self._store = store
        self._engine = LogicalReasoningEngine(store)
        self._scope_limit = int(scope_limit)
        self._create_schema()  # idempotent — bảo đảm 5 bảng review tồn tại khi handler query ngay

    # ---------------------------------------------------------------- schema

    def _create_schema(self) -> None:
        with self._store._lock, self._store._connection:
            self._store._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_review_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scope_json TEXT NOT NULL DEFAULT '[]',
                    selection_reasons_json TEXT NOT NULL DEFAULT '{}',
                    stats_json TEXT NOT NULL DEFAULT '{}',
                    closed_at_utc TEXT
                );
                CREATE TABLE IF NOT EXISTS review_findings (
                    finding_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    finding_type TEXT NOT NULL,
                    ku_a TEXT,
                    ku_b TEXT,
                    evidence TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    scope_impact TEXT NOT NULL DEFAULT '',
                    proposed_action TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    created_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_inferences (
                    inference_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    input_kus_json TEXT NOT NULL DEFAULT '[]',
                    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                    assumptions_json TEXT NOT NULL DEFAULT '[]',
                    proposed_conclusion TEXT NOT NULL DEFAULT '',
                    contradicting_evidence_json TEXT NOT NULL DEFAULT '[]',
                    missing_info_json TEXT NOT NULL DEFAULT '[]',
                    scope TEXT NOT NULL DEFAULT 'general',
                    certainty TEXT NOT NULL DEFAULT 'HYPOTHESIS',
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    created_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_questions (
                    question_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    problem TEXT NOT NULL,
                    evidence TEXT NOT NULL DEFAULT '',
                    current_view TEXT NOT NULL DEFAULT '',
                    interpretations_json TEXT NOT NULL DEFAULT '[]',
                    question TEXT NOT NULL,
                    impact TEXT NOT NULL DEFAULT '',
                    scope_hint TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    answer_text TEXT,
                    answered_at_utc TEXT,
                    finding_ref TEXT,
                    created_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_changes (
                    change_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    target_ku TEXT NOT NULL,
                    change_kind TEXT NOT NULL,
                    before_json TEXT NOT NULL DEFAULT '{}',
                    after_json TEXT NOT NULL DEFAULT '{}',
                    reason TEXT NOT NULL DEFAULT '',
                    owner_response_json TEXT NOT NULL DEFAULT '{}',
                    confirm_state TEXT NOT NULL DEFAULT 'PENDING',
                    applied_at_utc TEXT,
                    undo_json TEXT NOT NULL DEFAULT '{}',
                    result TEXT NOT NULL DEFAULT ''
                );
                """
            )

    # ---------------------------------------------------------------- start (PHẦN III)

    def start(self) -> dict[str, Any]:
        """Tạo session mới; nếu còn session đang mở → trả lại session đó (Test 9)."""
        self._create_schema()
        existing = self.find_open_session()
        if existing is not None:
            return {"session_id": existing["session_id"], "already_open": True,
                    "status": existing["status"], "stats": _loads(existing["stats_json"]),
                    "message": "Đang có đợt sàng lọc chưa kết thúc — tiếp tục xem xét đợt này."}
        session_id = _new_id("rev")
        selected, reasons = self._select_sample()
        scope = [u["knowledge_id"] for u in selected]
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "INSERT INTO memory_review_sessions (session_id, created_at_utc, status, scope_json, selection_reasons_json) "
                "VALUES (?,?,?,?,?)",
                (session_id, _now(), "ANALYZING", json.dumps(scope, ensure_ascii=False),
                 json.dumps(reasons, ensure_ascii=False)),
            )
        try:
            stats = self._analyze(session_id, selected, scope)
        except Exception as exc:
            self._set_session_status(session_id, "FAILED", error=str(exc))
            raise
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "UPDATE memory_review_sessions SET status='REVIEW_READY', stats_json=? WHERE session_id=?",
                (json.dumps(stats, ensure_ascii=False), session_id),
            )
        return {"session_id": session_id, "already_open": False, "status": "REVIEW_READY", "stats": stats}

    def find_open_session(self) -> dict[str, Any] | None:
        with self._store._lock:
            row = self._store._connection.execute(
                f"SELECT * FROM memory_review_sessions WHERE status IN "
                f"({','.join('?' * len(ACTIVE_STATUSES))}) AND session_id != 'x' "
                f"ORDER BY created_at_utc DESC LIMIT 1",
                tuple(ACTIVE_STATUSES),
            ).fetchone()
        if row is None:
            return None
        session = dict(row)
        if session["status"] in ("IDLE", "ANALYZING", "REVIEW_READY", "WAITING_OWNER",
                                 "APPLYING_CONFIRMED_CHANGES", "PAUSED"):
            return session
        return None

    # ---------------------------------------------------------------- selection (PHẦN III 3.2)

    def _select_sample(self) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Chọn tập mẫu minh bạch + lý do từng bản ghi (tái lập được)."""
        with self._store._lock:
            rows = self._store._connection.execute(
                """
                SELECT knowledge_id, knowledge_type, subject, predicate, object, statement,
                       scope, status, confidence, version, created_at_utc, updated_at_utc,
                       source_refs_json, derived_from_json
                FROM knowledge_units
                WHERE status NOT IN ('SUPERSEDED', 'ARCHIVED', 'REJECTED')
                ORDER BY updated_at_utc DESC LIMIT 400
                """
            ).fetchall()
        units = []
        for r in rows:
            u = dict(r)
            u["tokens"] = _tokens(u["statement"])
            units.append(u)

        selected: dict[str, dict[str, Any]] = {}
        reasons: dict[str, str] = {}

        def take(u: dict[str, Any], reason: str) -> bool:
            if len(selected) >= self._scope_limit:
                return False
            kid = u["knowledge_id"]
            if kid in selected:
                reasons[kid] = f"{reasons[kid]}; {reason}"
                return True
            selected[kid] = u
            reasons[kid] = reason
            return True

        # 1) RULE + CONCLUSION — quy tắc/kết luận quan trọng
        for u in units:
            if u["knowledge_type"] in ("RULE", "CONCLUSION"):
                if not take(u, "quy tắc/kết luận quan trọng"):
                    break
        # 2) Cặp có quan hệ CONTRADICTS/REFINES — liên quan trực tiếp
        if len(selected) < self._scope_limit:
            with self._store._lock:
                rels = self._store._connection.execute(
                    "SELECT from_id, to_id, relation_type FROM knowledge_relations "
                    "WHERE relation_type IN ('CONTRADICTS','REFINES','SUPERSEDES') LIMIT 100"
                ).fetchall()
            for rel in rels:
                for kid in (rel["from_id"], rel["to_id"]):
                    u = next((x for x in units if x["knowledge_id"] == kid), None)
                    if u is not None:
                        if not take(u, f"nằm trong quan hệ {rel['relation_type']}"):
                            break
                if len(selected) >= self._scope_limit:
                    break
        # 3) Token overlap cao nhất — trùng/tương đồng tiềm năng
        if len(selected) < self._scope_limit:
            scored: list[tuple[float, str, str]] = []
            for i in range(len(units)):
                for j in range(i + 1, len(units)):
                    jac = _jaccard(units[i]["tokens"], units[j]["tokens"])
                    if jac >= _SIMILAR_JACCARD:
                        scored.append((jac, units[i]["knowledge_id"], units[j]["knowledge_id"]))
            scored.sort(reverse=True)
            for _, ka, kb in scored:
                for kid in (ka, kb):
                    u = next((x for x in units if x["knowledge_id"] == kid), None)
                    if u is not None:
                        if not take(u, f"token-overlap cao với tri thức khác (trùng tiềm năng {scored[0][0] if scored else 0:.2f})"):
                            break
                if len(selected) >= self._scope_limit:
                    break
        # 4) Đổ thêm EXTRACTED mới nhất cho đủ cap
        for u in units:
            if len(selected) >= self._scope_limit:
                break
            take(u, "bổ sung theo thứ tự cập nhật mới nhất")
        return list(selected.values()), reasons

    # ---------------------------------------------------------------- analyze — CHỈ ĐỌC (PHẦN IV)

    def _analyze(self, session_id: str, selected: list[dict[str, Any]], scope: list[str]) -> dict[str, Any]:
        n_units = len(selected)
        n_findings = self._find_findings(session_id, selected)
        n_inferences = self._find_inferences(session_id, selected)
        n_questions = self._derive_questions(session_id)
        return {
            "scope_size": n_units,
            "findings": n_findings,
            "inferences": n_inferences,
            "questions": n_questions,
            "changes_pending": 0,
            "changes_applied": 0,
        }

    def _find_findings(self, session_id: str, selected: list[dict[str, Any]]) -> int:
        """Nhóm 2 — findings có bằng chứng + lý do; KHÔNG tự hợp nhất/xoá."""
        created = 0
        for i in range(len(selected)):
            for j in range(i + 1, len(selected)):
                a, b = selected[i], selected[j]
                jac = _jaccard(a["tokens"], b["tokens"])
                same_pred = a["predicate"] == b["predicate"]
                if jac >= _DUPLICATE_JACCARD:
                    created += self._add_finding(
                        session_id, "DUPLICATE", a, b,
                        evidence=f"jaccard={jac:.2f} | A: {a['statement'][:60]} | B: {b['statement'][:60]}",
                        reason="nội dung trùng lặp cao theo so sánh token (không tự hợp nhất)",
                        confidence=min(0.95, jac),
                        action="chờ chủ xác nhận hợp nhất hay giữ cả hai",
                    )
                elif same_pred and jac >= _SIMILAR_JACCARD:
                    neg_a, neg_b = _has_negation(a["statement"]), _has_negation(b["statement"])
                    if neg_a != neg_b or _antonym_flip(a["statement"], b["statement"]):
                        created += self._add_finding(
                            session_id, "CONTRADICTION", a, b,
                            evidence=f"polarity ngược (neg {neg_a} vs {neg_b}) | A: {a['statement'][:60]} | B: {b['statement'][:60]}",
                            reason="cùng predicate, polarity/trái nghĩa — có thể mâu thuẫn thật hoặc khác điều kiện",
                            confidence=0.7,
                            action="chờ chủ phân biệt mâu thuẫn thật vs khác phạm vi/thời điểm (PHẦN IV)",
                        )
                    else:
                        created += self._add_finding(
                            session_id, "SIMILAR", a, b,
                            evidence=f"jaccard={jac:.2f}, cùng predicate | A: {a['statement'][:60]} | B: {b['statement'][:60]}",
                            reason="tương đồng khác cách diễn đạt",
                            confidence=jac,
                            action="chờ chủ xác nhận bổ sung hay trùng",
                        )
        # MISSING_RELATION: cùng subject nhưng chưa có quan hệ nào
        by_subject: dict[str, list[dict[str, Any]]] = {}
        for u in selected:
            by_subject.setdefault(_norm_key(u["subject"]), []).append(u)
        for subj, group in by_subject.items():
            if len(group) < 2:
                continue
            with self._store._lock:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        ka, kb = group[i]["knowledge_id"], group[j]["knowledge_id"]
                        row = self._store._connection.execute(
                            "SELECT 1 FROM knowledge_relations WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)",
                            (ka, kb, kb, ka),
                        ).fetchone()
                        if row is None:
                            created += self._add_finding(
                                session_id, "MISSING_RELATION", group[i], group[j],
                                evidence=f"cùng subject '{group[i]['subject'][:40]}' nhưng không có quan hệ nào",
                                reason="quan hệ logic còn thiếu (đề xuất, không tự tạo)",
                                confidence=0.4,
                                action="chờ chủ xác nhận loại quan hệ phù hợp",
                            )
        return created

    def _add_finding(self, session_id: str, ftype: str, a: dict[str, Any], b: dict[str, Any],
                     *, evidence: str, reason: str, confidence: float, action: str) -> int:
        if ftype not in FINDING_TYPES:
            raise ValueError(f"unknown finding type: {ftype}")
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT 1 FROM review_findings WHERE session_id=? AND finding_type=? AND "
                "((ku_a=? AND ku_b=?) OR (ku_a=? AND ku_b=?))",
                (session_id, ftype, a["knowledge_id"], b["knowledge_id"], b["knowledge_id"], a["knowledge_id"]),
            ).fetchone()
        if row is not None:
            return 0
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "INSERT INTO review_findings (finding_id, session_id, finding_type, ku_a, ku_b, "
                "evidence, reason, confidence, scope_impact, proposed_action, created_at_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (_new_id("f"), session_id, ftype, a["knowledge_id"], b["knowledge_id"],
                 redact_text(evidence), redact_text(reason), confidence,
                 a["scope"] if a["scope"] == b["scope"] else f"{a['scope']} vs {b['scope']}",
                 redact_text(action), _now()),
            )
        return 1

    def _find_inferences(self, session_id: str, selected: list[dict[str, Any]]) -> int:
        """Nhóm 3 — suy luận từ engine V9, certainty trung thực."""
        created = 0
        # Chọn tối đa 3 chủ đề đại diện (RULE/CONCLUSION trước, rồi FACT mới nhất)
        focus = [u for u in selected if u["knowledge_type"] in ("RULE", "CONCLUSION")][:2]
        focus += [u for u in selected if u["knowledge_type"] == "FACT"][:1]
        for u in focus:
            q = f"{u['statement'][:100]} — điều này đúng và áp dụng trong phạm vi nào?"
            result = self._engine.answer_question(q, scope=None)
            certainty = {
                "A": "VERIFIED",
                "B": "UNVERIFIED_INFERENCE",
                "C": "HYPOTHESIS" if result.get("missing_info") else "HYPOTHESIS",
            }.get(result.get("conclusion_type"), "HYPOTHESIS")
            if not result.get("evidence_refs"):
                certainty = "INSUFFICIENT_EVIDENCE"
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "INSERT INTO review_inferences (inference_id, session_id, question, input_kus_json, "
                    "evidence_refs_json, assumptions_json, proposed_conclusion, contradicting_evidence_json, "
                    "missing_info_json, scope, certainty, created_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        _new_id("inf"), session_id, redact_text(q),
                        json.dumps([u["knowledge_id"]], ensure_ascii=False),
                        json.dumps(result.get("evidence_refs", [])[:8], ensure_ascii=False),
                        json.dumps(result.get("assumptions", []), ensure_ascii=False),
                        redact_text(str(result.get("conclusion") or "")),
                        json.dumps(result.get("against", [])[:5], ensure_ascii=False),
                        json.dumps(result.get("missing_info", []), ensure_ascii=False),
                        u["scope"], certainty, _now(),
                    ),
                )
            created += 1
        return created

    MAX_QUESTIONS = 10  # PHẦN IV: không tạo câu hỏi chỉ để tăng số lượng

    def _derive_questions(self, session_id: str) -> int:
        """Nhóm 4 — chỉ hỏi khi có căn cứ; KHÔNG tạo mâu thuẫn giả (PHẦN IV).

        Ưu tiên mâu thuẫn trước, trùng lặp sau; chặn tối đa MAX_QUESTIONS câu.
        """
        created = 0
        with self._store._lock:
            findings = self._store._connection.execute(
                "SELECT * FROM review_findings WHERE session_id=? AND finding_type IN "
                "('CONTRADICTION','DUPLICATE','MISSING_RELATION') "
                "ORDER BY CASE finding_type WHEN 'CONTRADICTION' THEN 0 "
                "WHEN 'MISSING_RELATION' THEN 1 ELSE 2 END, confidence DESC",
                (session_id,),
            ).fetchall()
        for f in findings:
            if created >= self.MAX_QUESTIONS:
                break
            fid = f["finding_id"]
            with self._store._lock:
                dup = self._store._connection.execute(
                    "SELECT 1 FROM review_questions WHERE session_id=? AND finding_ref=?",
                    (session_id, fid),
                ).fetchone()
            if dup is not None:
                continue
            a = self._store.get_unit(f["ku_a"]) if f["ku_a"] else None
            b = self._store.get_unit(f["ku_b"]) if f["ku_b"] else None
            if a is None or b is None:
                continue
            if f["finding_type"] == "CONTRADICTION":
                question = (
                    f"Hai tri thức sau khác polarity: (1) \"{a['statement'][:80]}\" và "
                    f"(2) \"{b['statement'][:80]}\". Đây là mâu thuẫn thật hay khác điều kiện/phạm vi áp dụng?"
                )
                interpretations = [
                    {"option": 1, "view": "mâu thuẫn thật — một trong hai sai"},
                    {"option": 2, "view": "khác điều kiện áp dụng — giữ cả hai với phạm vi riêng"},
                ]
                impact = "Quyết định tri thức nào dùng cho suy luận sau này."
            elif f["finding_type"] == "DUPLICATE":
                question = (
                    f"Hai tri thức gần trùng nhau ({f['confidence']:.0%}): (1) \"{a['statement'][:80]}\" và "
                    f"(2) \"{b['statement'][:80]}\". Anh muốn giữ cả hai, hợp nhất, hay đánh dấu một bản làm nguồn chính?"
                )
                interpretations = [
                    {"option": 1, "view": "giữ cả hai (không hợp nhất)"},
                    {"option": 2, "view": "hợp nhất thành một (V10 sẽ tạo bản mới supersede cả hai)"},
                ]
                impact = "Ảnh hưởng số lượng tri thức và hướng suy luận."
            else:  # MISSING_RELATION
                question = (
                    f"Hai tri thức cùng chủ đề nhưng chưa có quan hệ: (1) \"{a['statement'][:70]}\" và "
                    f"(2) \"{b['statement'][:70]}\". Anh xác nhận nên thêm quan hệ loại nào (nếu có)?"
                )
                interpretations = [
                    {"option": 1, "view": "thêm RELATED_TO (nếu câu trả lời xác nhận)"},
                    {"option": 2, "view": "không thêm — hai tri thức độc lập"},
                ]
                impact = "Bổ sung quan hệ giúp suy luận liên kết tốt hơn ở các đợt sau."
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "INSERT INTO review_questions (question_id, session_id, problem, evidence, current_view, "
                    "interpretations_json, question, impact, scope_hint, finding_ref, created_at_utc) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        _new_id("q"), session_id, redact_text(f["reason"][:150]),
                        redact_text(f["evidence"][:200]),
                        f"Hệ thống đang giữ cả hai ở trạng thái {a['status']} / {b['status']} — chưa chọn phía.",
                        json.dumps(interpretations, ensure_ascii=False),
                        redact_text(question), redact_text(impact),
                        a["scope"] if a["scope"] == b["scope"] else "cần làm rõ phạm vi",
                        fid,
                        _now(),
                    ),
                )
            created += 1
        return created

    # ---------------------------------------------------------------- read payloads (UI 4 nhóm)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT * FROM memory_review_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        session = dict(row)
        scope = _loads(session["scope_json"])
        reasons = _loads(session["selection_reasons_json"])
        units = []
        for kid in scope[:50]:
            u = self._store.get_unit(kid)
            if u is not None:
                u["selection_reason"] = reasons.get(kid, "")
                units.append(u)
        with self._store._lock:
            findings = [dict(r) for r in self._store._connection.execute(
                "SELECT * FROM review_findings WHERE session_id=? ORDER BY confidence DESC", (session_id,)
            ).fetchall()]
            inferences = [dict(r) for r in self._store._connection.execute(
                "SELECT * FROM review_inferences WHERE session_id=?", (session_id,)
            ).fetchall()]
            questions = [dict(r) for r in self._store._connection.execute(
                "SELECT * FROM review_questions WHERE session_id=? ORDER BY created_at_utc", (session_id,)
            ).fetchall()]
            changes = [dict(r) for r in self._store._connection.execute(
                "SELECT * FROM review_changes WHERE session_id=?", (session_id,)
            ).fetchall()]
        for q in questions:
            q["interpretations"] = _loads(q["interpretations_json"])
        # nhóm 4 rỗng → thông điệp trung thực bắt buộc (PHẦN IV)
        no_questions_message = None
        if not questions:
            no_questions_message = (
                "Trong phạm vi đợt sàng lọc này, chưa phát hiện câu hỏi bắt buộc cần Quanpt1 xác nhận."
            )
        return {
            "session": session,
            "units": units,
            "findings": findings,
            "inferences": inferences,
            "questions": questions,
            "changes": changes,
            "no_questions_message": no_questions_message,
        }

    # ---------------------------------------------------------------- responses (PHẦN VI)

    def respond(self, session_id: str, target_type: str, target_id: str,
                response_kind: str, text: str) -> dict[str, Any]:
        if response_kind not in RESPONSE_KINDS:
            raise ValueError(f"unknown response kind: {response_kind}")
        if target_type not in ("question", "finding", "inference"):
            raise ValueError("target_type must be question|finding|inference")
        session = self._require_session(session_id)
        if session["status"] not in ("REVIEW_READY", "WAITING_OWNER"):
            raise ValueError(f"session {session_id} is {session['status']}, cannot respond now")
        self._set_session_status(session_id, "WAITING_OWNER")
        table = {"question": "review_questions", "finding": "review_findings",
                 "inference": "review_inferences"}[target_type]
        id_col = {"question": "question_id", "finding": "finding_id",
                  "inference": "inference_id"}[target_type]
        with self._store._lock:
            row = self._store._connection.execute(
                f"SELECT * FROM {table} WHERE {id_col}=? AND session_id=?", (target_id, session_id)
            ).fetchone()
        if row is None:
            raise ValueError(f"{target_type} {target_id} not found in session {session_id}")
        answered_at = _now()
        with self._store._lock, self._store._connection:
            if target_type in ("question", "inference"):
                self._store._connection.execute(
                    f"UPDATE {table} SET status=?, answer_text=COALESCE(answer_text,'') || ?, answered_at_utc=? "
                    f"WHERE {id_col}=?",
                    ("ANSWERED" if response_kind != "NO_DECISION" else "WAITING",
                     ("\n" if row["answer_text"] else "") + redact_text(f"[{response_kind}] {text}"),
                     answered_at, target_id),
                )
            else:
                self._store._connection.execute(
                    f"UPDATE {table} SET status=? WHERE finding_id=?",
                    ("ACKNOWLEDGED" if response_kind != "NO_DECISION" else "WAITING", target_id),
                )
        result: dict[str, Any] = {
            "target_type": target_type, "target_id": target_id,
            "response_kind": response_kind, "recorded_at": answered_at,
        }
        # Xây change proposal cho các loại cần thay đổi tri thức
        if response_kind in ("CORRECT", "CLARIFY", "CONFIRM_RELATION", "CONFIRM_INFERENCE",
                             "REJECT_INFERENCE", "LIMIT_SCOPE"):
            change = self.build_change(session_id, target_type, target_id, response_kind, text, dict(row))
            result["change_proposed"] = change
        return result

    def _require_session(self, session_id: str) -> dict[str, Any]:
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT * FROM memory_review_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"review session not found: {session_id}")
        return dict(row)

    def _set_session_status(self, session_id: str, status: str, error: str = "") -> None:
        if status not in SESSION_STATUSES:
            raise ValueError(f"unknown session status: {status}")
        with self._store._lock, self._store._connection:
            if status == "COMPLETED":
                self._store._connection.execute(
                    "UPDATE memory_review_sessions SET status=?, closed_at_utc=? WHERE session_id=?",
                    (status, _now(), session_id),
                )
            else:
                self._store._connection.execute(
                    "UPDATE memory_review_sessions SET status=? WHERE session_id=?", (status, session_id),
                )
        if error:
            with self._store._lock, self._store._connection:
                stats = self._require_session(session_id).get("stats_json") or "{}"
                merged = dict(_loads(stats))
                merged["error"] = error
                self._store._connection.execute(
                    "UPDATE memory_review_sessions SET stats_json=? WHERE session_id=?",
                    (json.dumps(merged, ensure_ascii=False), session_id),
                )

    # ---------------------------------------------------------------- changes (PHẦN VI.3 + VII)

    def build_change(self, session_id: str, target_type: str, target_id: str,
                     response_kind: str, text: str, target_row: dict[str, Any]) -> dict[str, Any]:
        """Tạo change PENDING + snapshot before — CHƯA ghi vào tri thức."""
        if response_kind not in RESPONSE_KINDS:
            raise ValueError(f"unknown response kind: {response_kind}")
        # xác định KU mục tiêu
        if target_type == "question":
            ku_a = target_row.get("ku_a")
            if ku_a is None:
                f_row = self._store._connection.execute(
                    "SELECT ku_a FROM review_findings WHERE finding_id=?",
                    (target_row.get("finding_ref") or "",),
                ).fetchone()
                ku_a = f_row["ku_a"] if f_row else None
            target_ku = ku_a
        elif target_type == "finding":
            target_ku = target_row.get("ku_a")
        else:
            input_kus = _loads(target_row.get("input_kus_json") or "[]")
            target_ku = input_kus[0] if input_kus else None
        if not target_ku:
            raise ValueError("no target knowledge unit for this response")
        before = self._store.get_unit(target_ku)
        if before is None:
            raise ValueError(f"target KU not found: {target_ku}")
        change_id = _new_id("chg")
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "INSERT INTO review_changes (change_id, session_id, target_ku, change_kind, "
                "before_json, reason, owner_response_json, confirm_state) VALUES (?,?,?,?,?,?,?, 'PENDING')",
                (change_id, session_id, target_ku, response_kind,
                 json.dumps({k: before.get(k) for k in (
                     "knowledge_id", "statement", "status", "scope", "confidence",
                     "version", "review_status")}, ensure_ascii=False),
                 redact_text(f"{response_kind}: {text[:200]}"),
                 json.dumps({"target_type": target_type, "target_id": target_id,
                             "response_kind": response_kind, "text": redact_text(text)},
                            ensure_ascii=False)),
            )
        return {"change_id": change_id, "target_ku": target_ku, "change_kind": response_kind,
                "confirm_state": "PENDING",
                "note": "Chưa ghi vào tri thức — cần preview + confirm (PHẦN VI.3)."}

    def preview_change(self, session_id: str, change_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        if session["status"] not in ("REVIEW_READY", "WAITING_OWNER"):
            raise ValueError(f"session is {session['status']}, cannot preview now")
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT * FROM review_changes WHERE change_id=? AND session_id=?", (change_id, session_id)
            ).fetchone()
        if row is None:
            raise ValueError(f"change not found: {change_id}")
        change = dict(row)
        before = self._store.get_unit(change["target_ku"])
        if before is None:
            raise ValueError("target KU vanished — data integrity issue")
        kind = change["change_kind"]
        after: dict[str, Any] = dict(before)
        if kind in ("CORRECT", "CLARIFY"):
            after["review_status"] = "OWNER_CLARIFIED"
            after["confidence"] = min(0.95, float(before.get("confidence", 0.5)) + 0.2)
        elif kind in ("CONFIRM_RELATION", "CONFIRM_INFERENCE"):
            after["status"] = "VERIFIED" if before["status"] == "VERIFIED" else "CANDIDATE"
            after["verification_method"] = "owner_confirmed_v10"
        elif kind == "REJECT_INFERENCE":
            after["status"] = before["status"]  # inference rejected — KU giữ nguyên, ghi vào inference
        elif kind == "LIMIT_SCOPE":
            after["scope"] = "limited_by_owner"
        response = _loads(change["owner_response_json"])
        return {
            "change_id": change_id,
            "target_ku": change["target_ku"],
            "change_kind": kind,
            "before": {k: before.get(k) for k in ("statement", "status", "scope", "confidence", "version")},
            "after": {k: after.get(k) for k in ("statement", "status", "scope", "confidence", "version")},
            "reason": change["reason"],
            "owner_response": response,
            "impact": "Thay đổi tạo KU phiên bản mới (SUPERSEDES) giữ toàn bộ lịch sử — có thể hoàn tác.",
            "requires_second_confirm": kind in ("CORRECT", "CLARIFY", "CONFIRM_RELATION",
                                                 "CONFIRM_INFERENCE", "LIMIT_SCOPE"),
        }

    def confirm_and_apply(self, session_id: str, change_id: str, confirm: bool) -> dict[str, Any]:
        """Bước 2: chủ xác nhận sau preview → mới ghi tri thức (Test 6/7)."""
        if not confirm:
            return self.cancel_change(session_id, change_id)
        session = self._require_session(session_id)
        if session["status"] not in ("WAITING_OWNER", "REVIEW_READY", "APPLYING_CONFIRMED_CHANGES"):
            raise ValueError(f"session is {session['status']}, cannot apply now")
        self._set_session_status(session_id, "APPLYING_CONFIRMED_CHANGES")
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT * FROM review_changes WHERE change_id=? AND session_id=?", (change_id, session_id)
            ).fetchone()
        if row is None:
            raise ValueError(f"change not found: {change_id}")
        change = dict(row)
        if change["confirm_state"] == "APPLIED":
            raise ValueError("change already applied")
        before_unit = self._store.get_unit(change["target_ku"])
        if before_unit is None:
            self._set_session_status(session_id, "FAILED", "target KU missing at apply time")
            raise ValueError("target KU missing — integrity failure, nothing applied")
        kind = change["change_kind"]
        response = _loads(change["owner_response_json"])
        applied_at = _now()
        result: dict[str, Any]
        undo: dict[str, Any] = {}
        if kind in ("CORRECT", "CLARIFY"):
            new_id = self._store.supersede_unit(
                change["target_ku"], statement=before_unit["statement"],
                updates={"review_status": "OWNER_CLARIFIED",
                         "confidence": min(0.95, float(before_unit.get("confidence", 0.5)) + 0.2)},
                owner_answer=str(response.get("text", "")),
            )
            result = {"applied": "supersede", "new_ku": new_id,
                      "old_ku": change["target_ku"], "old_status": before_unit["status"]}
            undo = {"mode": "supersede_back", "from": new_id, "to": change["target_ku"]}
        elif kind in ("CONFIRM_RELATION", "CONFIRM_INFERENCE"):
            new_status = "CANDIDATE" if before_unit["status"] == "EXTRACTED" else before_unit["status"]
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET status=?, verification_method=?, updated_at_utc=? "
                    "WHERE knowledge_id=?",
                    (new_status, "owner_confirmed_v10", applied_at, change["target_ku"]),
                )
            result = {"applied": "status_update", "ku": change["target_ku"],
                      "old_status": before_unit["status"], "new_status": new_status}
            undo = {"mode": "restore_status", "ku": change["target_ku"], "old_status": before_unit["status"],
                    "old_verification": before_unit.get("verification_method", "unverified")}
        elif kind == "REJECT_INFERENCE":
            inf_id = (response.get("target_id") or "")
            if inf_id:
                with self._store._lock, self._store._connection:
                    self._store._connection.execute(
                        "UPDATE review_inferences SET status='REJECTED' WHERE inference_id=? AND session_id=?",
                        (inf_id, session_id),
                    )
            result = {"applied": "inference_rejected", "inference": inf_id}
            undo = {}
        elif kind == "LIMIT_SCOPE":
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET scope=?, updated_at_utc=? WHERE knowledge_id=?",
                    ("limited_by_owner", applied_at, change["target_ku"]),
                )
            result = {"applied": "scope_limit", "ku": change["target_ku"],
                      "old_scope": before_unit.get("scope")}
            undo = {"mode": "restore_scope", "ku": change["target_ku"], "old_scope": before_unit.get("scope")}
        else:
            raise ValueError(f"change kind {kind} is not applyable")
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "UPDATE review_changes SET confirm_state='APPLIED', after_json=?, applied_at_utc=?, "
                "undo_json=?, result=? WHERE change_id=?",
                (json.dumps(self._store.get_unit(change["target_ku"]) or {}, ensure_ascii=False, default=str),
                 applied_at, json.dumps(undo, ensure_ascii=False),
                 json.dumps(result, ensure_ascii=False), change_id),
            )
        self._set_session_status(session_id, "WAITING_OWNER")
        return {"change_id": change_id, "confirm_state": "APPLIED", "result": result,
                "applied_at": applied_at, "undo_available": bool(undo)}

    def cancel_change(self, session_id: str, change_id: str) -> dict[str, Any]:
        with self._store._lock, self._store._connection:
            cur = self._store._connection.execute(
                "UPDATE review_changes SET confirm_state='CANCELLED', result=? "
                "WHERE change_id=? AND session_id=? AND confirm_state IN ('PENDING','PREVIEWED')",
                ('{"cancelled": true, "at": "%s"}' % _now(), change_id, session_id),
            )
        if cur.rowcount == 0:
            raise ValueError(f"change {change_id} not cancellable (not found or already applied)")
        return {"change_id": change_id, "confirm_state": "CANCELLED"}

    def undo_change(self, session_id: str, change_id: str) -> dict[str, Any]:
        """Hoàn tác không phá dữ liệu: supersede ngược / khôi phục status cũ (PHẦN VII)."""
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT * FROM review_changes WHERE change_id=? AND session_id=? AND confirm_state='APPLIED'",
                (change_id, session_id),
            ).fetchone()
        if row is None:
            raise ValueError(f"applied change not found: {change_id}")
        undo = _loads(row["undo_json"])
        if not undo:
            raise ValueError("change has no undo path (e.g. inference rejection)")
        mode = undo.get("mode")
        result: dict[str, Any]
        if mode == "supersede_back":
            current = self._store.get_unit(undo["from"])
            original = self._store.get_unit(undo["to"])
            if current is None or original is None:
                raise ValueError("undo chain broken — report to owner")
            restore_id = self._store.supersede_unit(
                undo["from"], statement=original["statement"],
                updates={"review_status": "RESTORED_BY_UNDO"},
                owner_answer="undo của change " + change_id,
            )
            result = {"undone": True, "restored_as": restore_id}
        elif mode == "restore_status":
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET status=?, verification_method=?, updated_at_utc=? WHERE knowledge_id=?",
                    (undo["old_status"], undo.get("old_verification", "unverified"), _now(), undo["ku"]),
                )
            result = {"undone": True, "ku": undo["ku"], "status_restored": undo["old_status"]}
        elif mode == "restore_scope":
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET scope=?, updated_at_utc=? WHERE knowledge_id=?",
                    (undo["old_scope"], _now(), undo["ku"]),
                )
            result = {"undone": True, "ku": undo["ku"], "scope_restored": undo["old_scope"]}
        else:
            raise ValueError(f"unknown undo mode: {mode}")
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "UPDATE review_changes SET confirm_state='UNDONE', result=? WHERE change_id=?",
                (json.dumps({"undone": True, "at": _now(), **result}, ensure_ascii=False), change_id),
            )
        return {"change_id": change_id, "confirm_state": "UNDONE", **result}

    # ---------------------------------------------------------------- close / stats

    def close(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        if session["status"] == "COMPLETED":
            return {"session_id": session_id, "status": "COMPLETED", "already": True}
        stats = _loads(session["stats_json"])
        with self._store._lock:
            stats["changes_applied"] = self._store._connection.execute(
                "SELECT COUNT(*) FROM review_changes WHERE session_id=? AND confirm_state='APPLIED'",
                (session_id,),
            ).fetchone()[0]
            stats["questions_answered"] = self._store._connection.execute(
                "SELECT COUNT(*) FROM review_questions WHERE session_id=? AND status='ANSWERED'",
                (session_id,),
            ).fetchone()[0]
        self._set_session_status(session_id, "COMPLETED")
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                "UPDATE memory_review_sessions SET stats_json=? WHERE session_id=?",
                (json.dumps(stats, ensure_ascii=False), session_id),
            )
        return {"session_id": session_id, "status": "COMPLETED", "stats": stats}


def _norm_key(text: str) -> str:
    return " ".join(str(text or "").lower().split())
