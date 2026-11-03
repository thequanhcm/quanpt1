"""V9 Slice 1 — Deep Cognitive Memory: knowledge units, relations, traceability.

Chuyển kho hội thoại (episodes chat_turn) thành đơn vị tri thức chuẩn (PHẦN IV
MASTER PROMPT V9) với quan hệ có căn cứ (PHẦN III 3.4) và truy vết nguồn gốc
(PHẦN XV Ưu tiên 1+2).

Thiết kế:
- ADDITIVE-ONLY lên brain.db: 5 bảng mới CREATE IF NOT EXISTS, không ALTER/xoá
  bảng cũ (bảng `episodes`, `memories`, `semantic_memory`, `candidate_knowledge`
  giữ nguyên hoàn toàn).
- Trích xuất DETERMINISTIC (không LLM) để mọi kết quả kiểm chứng được.
- subject/predicate/object là dạng chuẩn hóa để index/gom nhóm — KHÔNG phải
  parse ngữ pháp; câu gốc luôn giữ nguyên trong `statement`.
- Mọi text lưu qua redact_text() — không ghi secret vào tri thức (PHẦN XII.10).
- Idempotency qua memory_exchange_log UNIQUE(correlation_id, source_module,
  target_module, payload_type, payload_ref) — chạy lại không nhân bản (Test G).
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.tools.path_guard import PathGuard

# ---------------------------------------------------------------- constants

KNOWLEDGE_TYPES = ("FACT", "OPINION", "QUESTION", "RULE", "PROCESS", "CONCLUSION")

KU_STATUSES = (
    "RAW", "EXTRACTED", "CANDIDATE", "VERIFIED", "INFERRED", "CONFLICTED",
    "NEEDS_OWNER_REVIEW", "REJECTED", "SUPERSEDED", "ARCHIVED",
)

RELATION_TYPES = (
    "SUPPORTS", "CONTRADICTS", "DERIVED_FROM", "REFINES", "SUPERSEDES",
    "DEPENDS_ON", "RELATED_TO", "APPLIES_TO", "VERIFIED_BY", "REJECTED_BY",
)

_QUESTION_MARKERS = (
    "ai", "gì", "gì", "nào", "nào", "bao nhiêu", "bao lâu", "khi nào",
    "ở đâu", "tại sao", "thế nào", "như thế nào", "vì sao", "đâu",
)
_QUESTION_SUFFIXES = ("không?", "được không", "phải không", "có phải", "chứ?")

_RULE_MARKERS = ("luôn", "phải", "nhớ giúp", "quy tắc", "không được", "cấm", "bắt buộc")

_OPINION_MARKERS = (
    "tôi nghĩ", "có lẽ", "có thể", "chắc là", "theo tôi", "theo em",
    "dường như", "khả năng", "tôi cho rằng", "em đoán",
)

_CONCLUSION_MARKERS = ("vậy nên", "kết luận", "tóm lại", "như vậy", "từ đó")

_NEGATION_MARKERS = ("không", "chưa", "chẳng", "đừng", "chớ", "không thể", "không có")

_ANTONYM_PAIRS = (
    ("online", "offline"), ("pass", "fail"), ("đúng", "sai"),
    ("đã", "chưa"), ("xong", "chưa xong"), ("ok", "lỗi"),
    ("on", "off"), ("active", "inactive"),
)

_STOPWORDS = frozenset(
    "và hoặc của các được là có trong một cho với này đó khi để từ theo trên "
    "không những về cũng như anh em tôi bạn bot trợ lý rồi sẽ mà đi ra vào "
    "thì nhưng vì nếu đã vẫn của ở cái gì nào".split()
)

_MAX_KU_PER_EPISODE = 5
_MAX_RELATIONS_PER_UNIT = 20
_LINK_BATCH = 200
_JUNK_PATTERNS = ("#!/", "\ndef ", "\nimport ", "\nfrom ", "version = ", "{", "}", "<", ">")
_JUNK_MAX_LEN = 120

_PREDICATE_BY_TYPE = {
    "FACT": "asserts",
    "OPINION": "opines",
    "QUESTION": "asks",
    "RULE": "prescribes",
    "PROCESS": "describes_procedure",
    "CONCLUSION": "concludes",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Lớp 2 chống secret (PHẦN X.6): redact_text chỉ mask Bearer/key=value;
# token thô trong câu tự nhiên (ghp_/sk-/AKIA...) phải mask thêm tại đây.
_RAW_TOKEN_RE = re.compile(
    r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_\-]{20,}|"
    r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,})\b"
)


def _deep_redact(text: str) -> str:
    return _RAW_TOKEN_RE.sub("[REDACTED]", redact_text(text))


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if 4 <= len(p.strip()) <= 300]


def _normalize(text: str) -> str:
    lowered = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", " ", text.lower())
    return re.sub(r"\s+", " ", lowered).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) >= 4 and t not in _STOPWORDS}


def _classify(sentence: str) -> str:
    raw = sentence.strip()
    low = _normalize(sentence)
    if raw.endswith("?") or low.endswith("?") or any(m in low for m in _QUESTION_MARKERS) or any(low.endswith(s) for s in _QUESTION_SUFFIXES):
        return "QUESTION"
    if any(m in low for m in _RULE_MARKERS):
        return "RULE"
    if any(m in low for m in _CONCLUSION_MARKERS):
        return "CONCLUSION"
    if any(m in low for m in _OPINION_MARKERS):
        return "OPINION"
    return "FACT"


def _has_negation(text: str) -> bool:
    low = _normalize(text)
    return any(m in low for m in _NEGATION_MARKERS)


def _antonym_flip(a: str, b: str) -> bool:
    na, nb = _normalize(a), _normalize(b)
    for x, y in _ANTONYM_PAIRS:
        if (x in na and y in nb) or (y in na and x in nb):
            return True
    return False


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _confidence(source_kind: str, direct_evidence: bool = True, contradicted: bool = False) -> float:
    """Tổng hợp khai báo 4 thành phần (V9 PHẦN IV.2) — KHÔNG phải xác suất hiệu chuẩn."""
    src = {"owner_chat": 0.4, "verified_doc": 0.35, "episode": 0.25, "external": 0.15}.get(source_kind, 0.25)
    evd = 0.3 if direct_evidence else 0.05
    cons = 0.0 if contradicted else 0.2
    ver = 0.0  # chưa có xác minh thật ở Slice 1
    return round(src + evd + cons + ver, 2)


# ---------------------------------------------------------------- store


class DeepMemoryStore:
    """Lớp tri thức cấu trúc V9 trên cùng brain.db — additive, không đụng bảng cũ."""

    def __init__(self, db_path: str | Path = "data/brain.db", workspace: str | Path | None = None) -> None:
        self._lock = RLock()
        requested = Path(db_path)
        if str(requested) == ":memory:":
            self.db_path = ":memory:"
        else:
            if workspace is not None:
                guard = PathGuard(workspace)
                if requested.is_absolute():
                    resolved = requested.resolve(strict=False)
                    resolved.relative_to(guard.workspace)  # raise nếu ra ngoài workspace
                    self.db_path = resolved
                else:
                    self.db_path = guard.resolve(requested)
            else:
                self.db_path = requested.resolve(strict=False)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._create_schema()

    # ------------------------------------------------ schema (additive-only)

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_units (
                    knowledge_id      TEXT PRIMARY KEY,
                    knowledge_type    TEXT NOT NULL,
                    subject           TEXT NOT NULL,
                    predicate         TEXT NOT NULL,
                    object            TEXT NOT NULL,
                    statement         TEXT NOT NULL,
                    source_refs_json  TEXT NOT NULL DEFAULT '[]',
                    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                    created_at_utc    TEXT NOT NULL,
                    updated_at_utc    TEXT NOT NULL,
                    valid_from_utc    TEXT,
                    valid_until_utc   TEXT,
                    scope             TEXT NOT NULL DEFAULT 'general',
                    status            TEXT NOT NULL DEFAULT 'EXTRACTED',
                    confidence        REAL NOT NULL DEFAULT 0.5,
                    verification_method TEXT NOT NULL DEFAULT 'unverified',
                    derived_from_json TEXT NOT NULL DEFAULT '[]',
                    contradiction_refs_json TEXT NOT NULL DEFAULT '[]',
                    version           INTEGER NOT NULL DEFAULT 1,
                    review_status     TEXT NOT NULL DEFAULT 'PENDING',
                    extraction_meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_ku_status ON knowledge_units(status);
                CREATE INDEX IF NOT EXISTS idx_ku_subject ON knowledge_units(subject);
                CREATE INDEX IF NOT EXISTS idx_ku_scope ON knowledge_units(scope);

                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    relation_id    TEXT PRIMARY KEY,
                    from_id        TEXT NOT NULL,
                    relation_type  TEXT NOT NULL,
                    to_id          TEXT NOT NULL,
                    basis          TEXT NOT NULL DEFAULT '',
                    is_speculative INTEGER NOT NULL DEFAULT 0,
                    created_at_utc TEXT NOT NULL,
                    created_by     TEXT NOT NULL DEFAULT 'v9_extractor',
                    UNIQUE(from_id, relation_type, to_id)
                );
                CREATE INDEX IF NOT EXISTS idx_rel_from ON knowledge_relations(from_id);
                CREATE INDEX IF NOT EXISTS idx_rel_to ON knowledge_relations(to_id);
                CREATE INDEX IF NOT EXISTS idx_rel_type ON knowledge_relations(relation_type);

                CREATE TABLE IF NOT EXISTS memory_exchange_log (
                    message_id      TEXT PRIMARY KEY,
                    source_module   TEXT NOT NULL,
                    target_module   TEXT NOT NULL,
                    payload_type    TEXT NOT NULL,
                    payload_ref     TEXT NOT NULL,
                    created_at_utc  TEXT NOT NULL,
                    correlation_id  TEXT NOT NULL,
                    provenance_refs_json TEXT NOT NULL DEFAULT '[]',
                    status          TEXT NOT NULL DEFAULT 'DELIVERED',
                    UNIQUE(correlation_id, source_module, target_module, payload_type, payload_ref)
                );

                CREATE TABLE IF NOT EXISTS memory_review_runs (
                    run_id          TEXT PRIMARY KEY,
                    started_at_utc  TEXT NOT NULL,
                    finished_at_utc TEXT,
                    status          TEXT NOT NULL DEFAULT 'RUNNING',
                    checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    stats_json      TEXT NOT NULL DEFAULT '{}',
                    batch_limit     INTEGER NOT NULL DEFAULT 50
                );

                CREATE TABLE IF NOT EXISTS owner_questions (
                    question_id    TEXT PRIMARY KEY,
                    run_id         TEXT,
                    problem        TEXT NOT NULL,
                    evidence       TEXT NOT NULL,
                    current_view   TEXT NOT NULL,
                    interpretations_json TEXT NOT NULL,
                    question       TEXT NOT NULL,
                    impact         TEXT NOT NULL,
                    scope_hint     TEXT NOT NULL,
                    status         TEXT NOT NULL DEFAULT 'OPEN',
                    answer_text    TEXT,
                    answered_at_utc TEXT,
                    created_at_utc TEXT NOT NULL
                );

                -- Legacy tables: no-op trên brain.db thật (đã tồn tại); bảo đảm
                -- test DB riêng biệt và DB mới trống vẫn dùng được.
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'recorded',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    approved_by TEXT NOT NULL DEFAULT '',
                    regression_passed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS candidate_knowledge (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'quarantined',
                    decision_note TEXT NOT NULL DEFAULT ''
                );
                """
            )

    # ------------------------------------------------ episodes (đọc bảng cũ, read-only)

    def iter_chat_turns(self, batch_size: int = 100) -> Iterator[dict[str, Any]]:
        """Đọc episodes kind='chat_turn' theo con trỏ — không ghi vào bảng cũ."""
        cursor = ""
        while True:
            with self._lock:
                rows = self._connection.execute(
                    """
                    SELECT id, created_at_utc, kind, summary, source_ref, status, metadata_json
                    FROM episodes
                    WHERE kind = 'chat_turn' AND id > ?
                    ORDER BY id LIMIT ?
                    """,
                    (cursor, batch_size),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                item = dict(row)
                try:
                    item["metadata"] = json.loads(item.pop("metadata_json"))
                except (json.JSONDecodeError, TypeError):
                    item["metadata"] = {}
                yield item
            cursor = rows[-1]["id"]

    # ------------------------------------------------ exchange log (idempotency)

    def _log_exchange(
        self, source_module: str, target_module: str, payload_type: str,
        payload_ref: str, correlation_id: str, provenance: list[str] | None = None,
    ) -> bool:
        """True = ghi mới; False = đã tồn tại (bỏ qua — chống vòng lặp PHẦN VI.3)."""
        with self._lock, self._connection:
            cur = self._connection.execute(
                """
                INSERT OR IGNORE INTO memory_exchange_log
                    (message_id, source_module, target_module, payload_type, payload_ref,
                     created_at_utc, correlation_id, provenance_refs_json, status)
                VALUES (?,?,?,?,?,?,?,?, 'DELIVERED')
                """,
                (
                    _new_id("m"), source_module, target_module, payload_type, payload_ref,
                    _now(), correlation_id, json.dumps(provenance or [], ensure_ascii=False),
                ),
            )
            return cur.rowcount > 0

    # ------------------------------------------------ extraction (Slice 1 lõi)

    def _decompose(self, sentence: str, ktype: str) -> tuple[str, str, str]:
        """SPO chuẩn hóa để index — câu gốc luôn nguyên trong statement."""
        predicate = _PREDICATE_BY_TYPE[ktype]
        text = sentence.strip()
        if ktype == "QUESTION":
            return text[:48], predicate, text[:160]
        markers = _RULE_MARKERS if ktype == "RULE" else []
        cut = len(text)
        low = text.lower()
        for m in markers:
            pos = low.find(m)
            if pos > 2:
                cut = min(cut, pos)
        if ktype in ("RULE",) and cut < len(text):
            subject = text[:cut].strip(" ,.:;")[:48]
            obj = text[cut:][:160]
        else:
            words = text.split()
            subject = " ".join(words[:6])[:48]
            obj = " ".join(words[6:])[:160] or text[:160]
        return (subject or text[:48], predicate, obj or text[:160])

    def extract_from_chat_turns(self, limit: int = 50) -> dict[str, Any]:
        """Trích xuất KU từ chat_turn CHƯA xử lý (idempotent theo exchange log)."""
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        stats = {"episodes_scanned": 0, "episodes_processed": 0, "skipped_already_logged": 0,
                 "units_created": 0, "by_type": {}}
        for episode in self.iter_chat_turns(batch_size=100):
            if stats["episodes_scanned"] >= limit:
                break
            stats["episodes_scanned"] += 1
            correlation = f"v9s1:extract:{episode['id']}"
            if not self._log_exchange("episodic_memory", "semantic_memory",
                                      "knowledge_extracted", episode["id"], correlation,
                                      provenance=[f"episode:{episode['id']}"]):
                stats["skipped_already_logged"] += 1
                continue
            meta = episode.get("metadata") or {}
            query = str(meta.get("user_query", "") or "")
            reply = str(meta.get("assistant_reply", "") or "")
            session_id = str(meta.get("session_id", "") or "")
            scope = f"session:{session_id}" if session_id else "general"
            created_units: list[str] = []
            for text in _split_sentences(query) + _split_sentences(reply):
                if len(created_units) >= _MAX_KU_PER_EPISODE:
                    break
                ktype = _classify(text)
                subject, predicate, obj = self._decompose(text, ktype)
                ku_id = self._insert_unit(
                    knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
                    statement=text, source_refs=[f"episode:{episode['id']}"],
                    evidence_refs=[f"episode:{episode['id']}"], scope=scope,
                    status="EXTRACTED",
                    confidence=_confidence("episode"),
                    meta={"engine": "v9-deterministic-r1", "episode_kind": episode["kind"]},
                )
                if ku_id:
                    created_units.append(ku_id)
                    stats["by_type"][ktype] = stats["by_type"].get(ktype, 0) + 1
            stats["units_created"] += len(created_units)
            stats["episodes_processed"] += 1
        return stats

    def _insert_unit(
        self, *, knowledge_type: str, subject: str, predicate: str, object: str,
        statement: str, source_refs: list[str], evidence_refs: list[str], scope: str,
        status: str, confidence: float, meta: dict[str, Any] | None = None,
    ) -> str | None:
        if knowledge_type not in KNOWLEDGE_TYPES or status not in KU_STATUSES:
            raise ValueError("unknown knowledge_type or status")
        statement = _deep_redact(statement.strip())
        if not statement:
            return None
        ku_id = _new_id("k")
        now = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO knowledge_units (
                    knowledge_id, knowledge_type, subject, predicate, object, statement,
                    source_refs_json, evidence_refs_json, created_at_utc, updated_at_utc,
                    scope, status, confidence, extraction_meta_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ku_id, knowledge_type, _deep_redact(subject), predicate, _deep_redact(object),
                    statement, json.dumps(source_refs, ensure_ascii=False),
                    json.dumps(evidence_refs, ensure_ascii=False), now, now,
                    scope, status, confidence, json.dumps(meta or {}, ensure_ascii=False),
                ),
            )
        return ku_id

    # ------------------------------------------------ linking + compare

    def _relation_exists(self, from_id: str, rtype: str, to_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM knowledge_relations WHERE from_id=? AND relation_type=? AND to_id=?",
                (from_id, rtype, to_id),
            ).fetchone()
        return row is not None

    def _insert_relation(self, from_id: str, rtype: str, to_id: str, basis: str,
                         speculative: bool, created_by: str = "v9_linker") -> str | None:
        if rtype not in RELATION_TYPES:
            raise ValueError(f"unknown relation type: {rtype}")
        if from_id == to_id:
            return None
        if self._relation_exists(from_id, rtype, to_id):
            return None
        # chống double-link ngược chiều cho quan hệ đối xứng
        if rtype in ("RELATED_TO", "CONTRADICTS") and self._relation_exists(to_id, rtype, from_id):
            return None
        with self._lock:
            count = self._connection.execute(
                "SELECT COUNT(*) FROM knowledge_relations WHERE from_id=?", (from_id,)
            ).fetchone()[0]
        if count >= _MAX_RELATIONS_PER_UNIT:
            return None
        rel_id = _new_id("r")
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO knowledge_relations
                    (relation_id, from_id, relation_type, to_id, basis, is_speculative,
                     created_at_utc, created_by)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (rel_id, from_id, rtype, to_id, _deep_redact(basis), int(speculative), _now(), created_by),
            )
        return rel_id

    def link_units(self, batch: int = _LINK_BATCH) -> dict[str, Any]:
        """Liên kết có căn cứ trong cùng scope — mọi quan hệ đều ghi basis (Test B)."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT knowledge_id, knowledge_type, subject, predicate, object, statement, scope
                FROM knowledge_units
                WHERE status IN ('EXTRACTED', 'CANDIDATE', 'VERIFIED', 'INFERRED')
                ORDER BY created_at_utc DESC LIMIT ?
                """,
                (batch,),
            ).fetchall()
        units = [dict(r) for r in rows]
        stats = {"pairs_compared": 0, "relations_created": 0, "by_type": {}}

        def add(from_id: str, rtype: str, to_id: str, basis: str, spec: bool) -> None:
            rel = self._insert_relation(from_id, rtype, to_id, basis, spec)
            if rel:
                stats["relations_created"] += 1
                stats["by_type"][rtype] = stats["by_type"].get(rtype, 0) + 1

        for i in range(len(units)):
            for j in range(i + 1, len(units)):
                a, b = units[i], units[j]
                if a["scope"] != b["scope"]:
                    continue
                stats["pairs_compared"] += 1
                na, nb = _normalize(a["subject"]), _normalize(b["subject"])
                if not na or not nb:
                    continue
                same_subject = na == nb
                if same_subject and a["predicate"] == b["predicate"]:
                    # polarity xét trên TOÀN statement (mâu thuẫn thường nằm ở đầu câu ngắn)
                    neg_a, neg_b = _has_negation(a["statement"]), _has_negation(b["statement"])
                    if neg_a != neg_b or _antonym_flip(a["statement"], b["statement"]):
                        add(a["knowledge_id"], "CONTRADICTS", b["knowledge_id"],
                            f"same subject+predicate, opposite polarity: "
                            f"[{a['statement'][:60]}] vs [{b['statement'][:60]}]", False)
                        self._mark_contradicted(a["knowledge_id"], b["knowledge_id"])
                        self._mark_contradicted(b["knowledge_id"], a["knowledge_id"])
                    else:
                        add(a["knowledge_id"], "RELATED_TO", b["knowledge_id"],
                            "same subject+predicate, consistent object", False)
                    continue
                # cùng chủ thể đầu câu (deterministic head match) — mâu thuẫn trực tiếp
                head_a, head_b = _normalize(a["subject"]).split()[0:1], _normalize(b["subject"]).split()[0:1]
                if head_a and head_a == head_b and a["predicate"] == b["predicate"]:
                    if _antonym_flip(a["statement"], b["statement"]):
                        add(a["knowledge_id"], "CONTRADICTS", b["knowledge_id"],
                            f"same subject head + antonym polarity: "
                            f"[{a['statement'][:60]}] vs [{b['statement'][:60]}]", False)
                        self._mark_contradicted(a["knowledge_id"], b["knowledge_id"])
                        self._mark_contradicted(b["knowledge_id"], a["knowledge_id"])
                        continue
                sa, sb = a["statement"], b["statement"]
                if len(sa) > len(sb) and _normalize(sb) and _normalize(sb) in _normalize(sa):
                    add(a["knowledge_id"], "REFINES", b["knowledge_id"], "statement containment", False)
                    continue
                if len(sb) > len(sa) and _normalize(sa) and _normalize(sa) in _normalize(sb):
                    add(b["knowledge_id"], "REFINES", a["knowledge_id"], "statement containment", False)
                    continue
                overlap = _tokens(a["statement"]) & _tokens(b["statement"])
                if len(overlap) >= 2:
                    add(a["knowledge_id"], "RELATED_TO", b["knowledge_id"],
                        f"token overlap: {sorted(overlap)[:4]}", True)
        return stats

    def _mark_contradicted(self, ku_id: str, other_id: str) -> None:
        """CONTRADICTS không tự chọn phía — chỉ hạ thành phần nhất quán + ghi ref."""
        with self._lock:
            row = self._connection.execute(
                "SELECT confidence, contradiction_refs_json FROM knowledge_units WHERE knowledge_id=?",
                (ku_id,),
            ).fetchone()
            if row is None:
                return
            refs = json.loads(row["contradiction_refs_json"] or "[]")
            if other_id not in refs:
                refs.append(other_id)
            new_conf = round(_confidence("episode", contradicted=True), 2)
            self._connection.execute(
                """
                UPDATE knowledge_units
                SET contradiction_refs_json=?, confidence=?, updated_at_utc=?
                WHERE knowledge_id=?
                """,
                (json.dumps(refs, ensure_ascii=False), new_conf, _now(), ku_id),
            )

    def compare_duplicates(self, batch: int = _LINK_BATCH) -> dict[str, Any]:
        """PHẦN VII Compare: phát hiện trùng tương tự — KHÔNG tự merge (Test I triết lý)."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT knowledge_id, statement, scope FROM knowledge_units
                WHERE status IN ('EXTRACTED', 'CANDIDATE', 'VERIFIED', 'INFERRED')
                ORDER BY created_at_utc DESC LIMIT ?
                """,
                (batch,),
            ).fetchall()
        units = [dict(r) for r in rows]
        token_sets = [(u["knowledge_id"], _tokens(u["statement"]), u["scope"]) for u in units]
        stats = {"pairs_compared": 0, "duplicates_found": 0}
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                id_a, toks_a, scope_a = token_sets[i]
                id_b, toks_b, scope_b = token_sets[j]
                if scope_a != scope_b:
                    continue
                stats["pairs_compared"] += 1
                if _jaccard(toks_a, toks_b) >= 0.8:
                    rel = self._insert_relation(id_a, "RELATED_TO", id_b,
                                                "high token similarity (jaccard>=0.8)", False,
                                                created_by="v9_compare")
                    if rel:
                        stats["duplicates_found"] += 1
        return stats

    # ------------------------------------------------ traceability (PHẦN XV ưu tiên 1)

    def get_unit(self, knowledge_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM knowledge_units WHERE knowledge_id=?", (knowledge_id,)
            ).fetchone()
        if row is None:
            return None
        unit = dict(row)
        for key in ("source_refs_json", "evidence_refs_json", "derived_from_json",
                    "contradiction_refs_json", "extraction_meta_json"):
            unit[key.replace("_json", "")] = json.loads(unit.pop(key) or "[]")
        with self._lock:
            rels = self._connection.execute(
                """
                SELECT relation_id, from_id, relation_type, to_id, basis, is_speculative,
                       created_at_utc, created_by
                FROM knowledge_relations WHERE from_id=? OR to_id=?
                """,
                (knowledge_id, knowledge_id),
            ).fetchall()
        unit["relations"] = [dict(r) for r in rels]
        return unit

    def trace(self, knowledge_id: str, max_depth: int = 10) -> dict[str, Any]:
        """Truy vết về nguồn: chuỗi DERIVED_FROM (chống vòng) + episodes gốc."""
        chain: list[str] = []
        visited: set[str] = set()

        def walk(kid: str, depth: int) -> None:
            if kid in visited or depth > max_depth:
                return
            visited.add(kid)
            chain.append(kid)
            unit = self.get_unit(kid)
            if unit is None:
                return
            for parent in unit.get("derived_from", []):
                walk(parent, depth + 1)

        walk(knowledge_id, 0)
        sources: list[dict[str, Any]] = []
        unresolved_refs: list[str] = []
        for kid in chain:
            unit = self.get_unit(kid)
            if unit is None:
                continue
            for ref in unit.get("source_refs", []):
                if ref.startswith("episode:"):
                    ep_id = ref.split(":", 1)[1]
                    with self._lock:
                        row = self._connection.execute(
                            "SELECT id, created_at_utc, kind, summary FROM episodes WHERE id=?",
                            (ep_id,),
                        ).fetchone()
                    if row is not None:
                        sources.append(dict(row))
                    elif not any(s.get("id") == ep_id for s in sources):
                        sources.append({"id": ep_id, "resolved": False})
                        unresolved_refs.append(ref)
        return {"root": knowledge_id, "chain": chain,
                "cycles_detected": len(chain) != len(visited),
                "source_episodes": sources, "unresolved_refs": unresolved_refs}

    # ------------------------------------------------ supersede + feedback audit (Slice 4)

    def supersede_unit(
        self, old_id: str, *, statement: str, updates: dict[str, Any],
        owner_answer: str = "",
    ) -> str:
        """Tạo KU mới version+1 thay thế KU cũ trong cùng scope — KHÔNG xoá lịch sử.
        KU cũ → status SUPERSEDED, giữ superseded_by để truy vết (Test F)."""
        old = self.get_unit(old_id)
        if old is None:
            raise ValueError(f"unit not found: {old_id}")
        new_id = _new_id("k")
        now = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO knowledge_units (
                    knowledge_id, knowledge_type, subject, predicate, object, statement,
                    source_refs_json, evidence_refs_json, created_at_utc, updated_at_utc,
                    valid_from_utc, valid_until_utc, scope, status, confidence,
                    verification_method, derived_from_json, contradiction_refs_json,
                    version, review_status, extraction_meta_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id, old["knowledge_type"], old["subject"], old["predicate"], old["object"],
                    _deep_redact(statement or old["statement"]),
                    json.dumps(old["source_refs"], ensure_ascii=False),
                    json.dumps(old["evidence_refs"], ensure_ascii=False),
                    now, now, old.get("valid_from_utc"), old.get("valid_until_utc"),
                    updates.get("scope", old["scope"]),
                    updates.get("status", old["status"]),
                    updates.get("confidence", old["confidence"]),
                    updates.get("verification_method", old.get("verification_method", "unverified")),
                    json.dumps([old_id], ensure_ascii=False),  # derived_from → cũ
                    json.dumps(old.get("contradiction_refs", []), ensure_ascii=False),
                    int(old.get("version", 1)) + 1,
                    updates.get("review_status", "OWNER_CLARIFIED"),
                    json.dumps({
                        "superseded_from": old_id,
                        "owner_answer_preview": _deep_redact(owner_answer[:200]),
                        "update_reason": "owner_feedback",
                    }, ensure_ascii=False),
                ),
            )
            # KU cũ → SUPERSEDED
            self._connection.execute(
                "UPDATE knowledge_units SET status='SUPERSEDED', updated_at_utc=? WHERE knowledge_id=?",
                (now, old_id),
            )
            # quan hệ SUPERSEDES cũ→mới
            self._connection.execute(
                """
                INSERT OR IGNORE INTO knowledge_relations
                    (relation_id, from_id, relation_type, to_id, basis, is_speculative,
                     created_at_utc, created_by)
                VALUES (?,?,?,?,?,0,?, 'v9_owner_feedback')
                """,
                (_new_id("r"), old_id, "SUPERSEDES", new_id,
                 f"owner feedback v{old.get('version', 1)}→v{int(old.get('version', 1)) + 1}", now),
            )
        return new_id

    def log_feedback(
        self, *, question_id: str, answer_text: str, answered_by: str, answered_at: str,
        feedback_kind: str, scope: str, version_updates: list[dict[str, Any]],
    ) -> None:
        """Audit trail phản hồi chủ (PHẦN IX) — qua exchange log, idempotent."""
        self._log_exchange(
            "owner", "deep_memory", "owner_feedback_applied", question_id,
            f"v9s4:feedback:{question_id}",
            provenance=[f"question:{question_id}",
                        *(u.get("knowledge_id", "") for u in version_updates)],
        )

    # ------------------------------------------------ stats + junk report

    def deep_stats(self) -> dict[str, Any]:
        with self._lock:
            by_status = {
                r["status"]: r["n"] for r in self._connection.execute(
                    "SELECT status, COUNT(*) AS n FROM knowledge_units GROUP BY status"
                ).fetchall()
            }
            by_type = {
                r["knowledge_type"]: r["n"] for r in self._connection.execute(
                    "SELECT knowledge_type, COUNT(*) AS n FROM knowledge_units GROUP BY knowledge_type"
                ).fetchall()
            }
            rel_by_type = {
                r["relation_type"]: r["n"] for r in self._connection.execute(
                    "SELECT relation_type, COUNT(*) AS n FROM knowledge_relations GROUP BY relation_type"
                ).fetchall()
            }
            questions_open = self._connection.execute(
                "SELECT COUNT(*) FROM owner_questions WHERE status='OPEN'"
            ).fetchone()[0]
            exchanges = self._connection.execute("SELECT COUNT(*) FROM memory_exchange_log").fetchone()[0]
            last_run = self._connection.execute(
                "SELECT run_id, started_at_utc, status FROM memory_review_runs ORDER BY started_at_utc DESC LIMIT 1"
            ).fetchone()
        return {
            "knowledge_units_total": sum(by_status.values()),
            "units_by_status": by_status,
            "units_by_type": by_type,
            "relations_total": sum(rel_by_type.values()),
            "relations_by_type": rel_by_type,
            "owner_questions_open": questions_open,
            "exchange_messages_total": exchanges,
            "last_review_run": dict(last_run) if last_run is not None else None,
        }

    def report_semantic_junk(self, limit: int = 500) -> dict[str, Any]:
        """PHẦN II mục 5: phát hiện rác ingest trong semantic_memory — CHỈ báo cáo,
        KHÔNG sửa/xoá bảng cũ (quyết định lưu trữ thuộc owner review)."""
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, statement FROM semantic_memory ORDER BY created_at_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()
        junk = []
        for row in rows:
            stmt = row["statement"] or ""
            if len(stmt) > _JUNK_MAX_LEN or any(p in stmt for p in _JUNK_PATTERNS):
                junk.append({"id": row["id"], "reason": "ingest artifact pattern", "preview": stmt[:60]})
        return {"scanned": len(rows), "junk_candidates": len(junk), "items": junk[:20]}

    # ------------------------------------------------ owner questions (Slice 3+4)

    def has_exchange(self, correlation_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM memory_exchange_log WHERE correlation_id=? LIMIT 1",
                (correlation_id,),
            ).fetchone()
        return row is not None

    def create_owner_question(
        self, *, problem: str, evidence: str, current_view: str, interpretations_json: str,
        question: str, impact: str, scope_hint: str, question_key: str | None = None,
        run_id: str | None = None,
    ) -> str:
        """Idempotent theo question_key (nếu có) — không hỏi lại câu đang OPEN (§VIII.3)."""
        q_id = question_key or _new_id("q")
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM owner_questions WHERE question_id=? AND status='OPEN'",
                (q_id,),
            ).fetchone()
        if row is not None:
            return q_id  # đã tồn tại, không tạo trùng
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO owner_questions (
                    question_id, run_id, problem, evidence, current_view,
                    interpretations_json, question, impact, scope_hint, status, created_at_utc
                ) VALUES (?,?,?,?,?,?,?,?,?, 'OPEN', ?)
                """,
                (q_id, run_id, redact_text(problem), redact_text(evidence),
                 redact_text(current_view), interpretations_json, redact_text(question),
                 redact_text(impact), redact_text(scope_hint), _now()),
            )
        return q_id

    def mark_units_conflicted(self, id_a: str, id_b: str) -> None:
        """Nâng trạng thái CONFLICTED cho cả hai phía — không xoá, không chọn phía."""
        with self._lock, self._connection:
            for kid in (id_a, id_b):
                self._connection.execute(
                    "UPDATE knowledge_units SET status='CONFLICTED', updated_at_utc=? WHERE knowledge_id=?",
                    (_now(), kid),
                )

    def list_owner_questions(self, status: str = "OPEN", limit: int = 50) -> list[dict[str, Any]]:
        if status not in ("OPEN", "ANSWERED", "SUPERSEDED", "EXPIRED", "ALL"):
            raise ValueError("invalid status filter")
        sql = ("SELECT * FROM owner_questions {where} ORDER BY created_at_utc DESC LIMIT ?")
        where = "" if status == "ALL" else "WHERE status=?"
        with self._lock:
            rows = self._connection.execute(
                sql.format(where=where), (status, limit) if status != "ALL" else (limit,)
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["interpretations"] = json.loads(item.pop("interpretations_json") or "[]")
            except json.JSONDecodeError:
                item["interpretations"] = []
            out.append(item)
        return out

    def get_owner_question(self, question_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM owner_questions WHERE question_id=?", (question_id,)
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        try:
            item["interpretations"] = json.loads(item.pop("interpretations_json") or "[]")
        except json.JSONDecodeError:
            item["interpretations"] = []
        return item

    # ------------------------------------------------ review runs (checkpoint CRUD)

    def create_review_run(self, batch_limit: int = 50) -> str:
        run_id = _new_id("run")
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO memory_review_runs (run_id, started_at_utc, status, batch_limit) VALUES (?,?, 'RUNNING', ?)",
                (run_id, _now(), batch_limit),
            )
        return run_id

    def update_run_checkpoint(self, run_id: str, stage: str, cursor: str, processed_ids: list[str]) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE memory_review_runs SET checkpoint_json=? WHERE run_id=?",
                (json.dumps({"stage": stage, "cursor": cursor, "processed_ids": processed_ids},
                            ensure_ascii=False), run_id),
            )

    def finish_review_run(self, run_id: str, status: str, stats: dict[str, Any]) -> None:
        if status not in ("COMPLETED", "FAILED", "INTERRUPTED"):
            raise ValueError("invalid run status")
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE memory_review_runs SET finished_at_utc=?, status=?, stats_json=? WHERE run_id=?",
                (_now(), status, json.dumps(stats, ensure_ascii=False), run_id),
            )

    def get_review_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM memory_review_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        run = dict(row)
        run["checkpoint"] = json.loads(run.pop("checkpoint_json") or "{}")
        run["stats"] = json.loads(run.pop("stats_json") or "{}")
        return run

    def close(self) -> None:
        with self._lock:
            self._connection.close()
