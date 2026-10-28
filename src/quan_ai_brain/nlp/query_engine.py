"""
Natural Language Query Engine (V24.2) — QUAN AI BRAIN.

SIMULATED: keyword/heuristic NLP (tokenize + intent rules), NOT spaCy/BERT
as sketched in the V24 plan. Stdlib only, no network, deterministic.

Pipeline: tokenize -> intent detect -> plan (filters/sort/limit) -> execute
over an in-memory list of KU dicts -> QueryResult with explanation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

_ASCIIFOLD_MAP = {
    "áàảãạăắằẳẵặâấầẩẫậ": "a", "éèẻẽẹêếềểễệ": "e",
    "íìỉĩị": "i", "óòỏõọôốồổỗộơớờởỡợ": "o",
    "úùủũụưứừửữự": "u", "ýỳỷỹỵ": "y", "đ": "d",
}


def ascii_fold(text: str) -> str:
    """Fold Vietnamese diacritics to plain ASCII lowercase ('Tìm' -> 'tim')."""
    lowered = text.lower()
    out = []
    for ch in lowered:
        replaced = None
        for src, dst in _ASCIIFOLD_MAP.items():
            if ch in src:
                replaced = dst
                break
        if replaced is None:
            if unicodedata.category(ch).startswith("M"):
                replaced = ""
            else:
                replaced = ch
        out.append(replaced)
    return "".join(out)


_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> List[str]:
    """Lowercase, strip diacritics, split on non-alphanumerics."""
    return _TOKEN_RE.findall(ascii_fold(text))


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

class Intent:
    """Detected query intents (keyword-rule based, simulated NLP)."""

    SEARCH = "SEARCH"
    COUNT = "COUNT"
    COMPARE = "COMPARE"
    TIMELINE = "TIMELINE"
    UNKNOWN = "UNKNOWN"

    COUNT_WORDS = {
        # Vietnamese
        "dem", "bao_nhieu", "bao_nhieu_kinh_nghiem", "may", "may_kinh_nghiem",
        "tong_so", "so_luong", "co_bao_nhieu",
        # English
        "count", "how", "many", "howmany", "total", "number",
    }
    SEARCH_WORDS = {
        # Vietnamese
        "tim", "kiem_tra", "tra_cuu", "xem", "cho", "hien_thi", "lay", "can",
        "liet_ke", "mo_rong", "muon", "nhin",
        # English
        "find", "show", "search", "list", "get", "display", "look", "want",
        "need", "filter",
    }
    COMPARE_WORDS = {
        # Vietnamese
        "so_sanh", "so_voi", "khac_gi", "giua", "nhanh_hon", "tot_hon",
        "khac_biet", "hon",
        # English
        "compare", "versus", "vs", "difference", "better", "against",
    }
    TIMELINE_WORDS = {
        # Vietnamese
        "lich_su", "tuan_truoc", "thang_truoc", "hom_nay", "hom_qua",
        "gian_day", "moi_nhat", "cu_nhat", "tuan_nay", "thang_nay", "nam_ngoai",
        # English
        "history", "timeline", "last_week", "last_month", "today",
        "yesterday", "recent", "latest", "oldest", "newest", "since", "recently",
    }


# ---------------------------------------------------------------------------
# Plan dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TimeFilter:
    """Relative-time filter resolved at execution time against 'now'."""
    field: str
    keyword: str          # normalized keyword that matched, e.g. 'last_week'
    days: int             # lookback window in days
    direction: str = "past"  # 'past' | 'future' (reserved)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "keyword": self.keyword,
            "days": self.days,
            "direction": self.direction,
        }


@dataclass
class Filter:
    """Equality/substring filter on one record field."""
    field: str
    value: Any
    op: str = "eq"        # 'eq' | 'contains'

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "value": self.value, "op": self.op}


@dataclass
class Sort:
    field: str
    direction: str = "desc"   # 'asc' | 'desc'

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "direction": self.direction}


@dataclass
class QueryPlan:
    """Structured, auditable plan derived from one natural-language query."""
    raw_text: str
    intent: str
    filters: List[Filter] = field(default_factory=list)
    time_filters: List[TimeFilter] = field(default_factory=list)
    text_terms: List[str] = field(default_factory=list)
    sort: Optional[Sort] = None
    limit: int = 50
    group_by: Optional[str] = None
    compare_targets: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "intent": self.intent,
            "filters": [f.to_dict() for f in self.filters],
            "time_filters": [t.to_dict() for t in self.time_filters],
            "text_terms": list(self.text_terms),
            "sort": self.sort.to_dict() if self.sort else None,
            "limit": self.limit,
            "group_by": self.group_by,
            "compare_targets": list(self.compare_targets),
            "warnings": list(self.warnings),
        }


@dataclass
class QueryResult:
    """Execution result + machine-readable explanation."""
    query: str
    intent: str
    plan: QueryPlan
    results: List[Dict[str, Any]]
    count: int
    total_matches: int
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "plan": self.plan.to_dict(),
            "results": self.results,
            "count": self.count,
            "total_matches": self.total_matches,
            "explanation": self.explanation,
        }


# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------

_TYPE_SYNONYMS = {
    "LESSON_LEARNED": ["lesson", "lessons", "kinh_nghiem", "bai_hoc"],
    "ERROR": ["error", "errors", "loi", "su_co", "incident", "incidente"],
    "BEST_PRACTICE": ["practice", "practices", "thuc_hanh_tot", "best_practice"],
    "DECISION": ["decision", "decisions", "quyet_dinh", "dieu_huong"],
    "NOTE": ["note", "notes", "ghi_chu", "noted"],
}

_SCOPE_SYNONYMS = {
    "PRODUCTION": ["production", "prod", "san_xuat", "product"],
    "STAGING": ["staging", "stg"],
    "DEVELOPMENT": ["development", "dev", "phat_trien"],
    "TESTING": ["testing", "test", "kiem_thu"],
    "OPS": ["ops", "operations", "van_hanh"],
}

_FIELD_ALIASES = {
    # canonical -> list of record keys tried in order
    "type": ["type", "ku_type", "knowledge_type", "category"],
    "scope": ["scope", "environment", "env"],
    "status": ["status", "state"],
    "tag": ["tags", "tag"],
    "title": ["title", "name", "summary"],
    "content": ["content", "text", "body", "description", "note"],
    "created_at": ["created_at", "timestamp", "date", "time"],
}

_TIME_KEYWORDS = {
    # keyword -> (lookback days, display label)
    "today": (1, "today"),
    "hom_nay": (1, "today"),
    "yesterday": (2, "yesterday"),
    "hom_qua": (2, "yesterday"),
    "last_week": (7, "last week"),
    "tuan_truoc": (7, "last week"),
    "tuan_nay": (7, "this week"),
    "last_month": (30, "last month"),
    "thang_truoc": (30, "last month"),
    "thang_nay": (30, "this month"),
    "recent": (7, "recent"),
    "recently": (7, "recent"),
    "moi_nhat": (7, "recent"),
    "nam_ngoai": (365, "last year"),
    "last_year": (365, "last year"),
}

_TIME_FIELD_HINTS = ("created_at", "timestamp", "date", "time", "ngay", "thoi_gian")

_POSSESSIVE_RE = re.compile(r"(?:^|\s)(?:cua|of|in|trong)\s+(\S+)")


def _detect_type(tokens: List[str]) -> Optional[tuple]:
    joined = set(tokens)
    # multi-word phrase check first (e.g. 'bai hoc', 'thuc hanh tot')
    phrases = {
        "bai hoc": "LESSON_LEARNED", "kinh nghiem": "LESSON_LEARNED",
        "thuc hanh": "BEST_PRACTICE", "best practice": "BEST_PRACTICE",
    }
    text = " ".join(tokens)
    for phrase, ku_type in phrases.items():
        if phrase in text:
            return ku_type, phrase
    for ku_type, syns in _TYPE_SYNONYMS.items():
        for s in syns:
            if s in joined:
                return ku_type, s
    return None


def _detect_scope(tokens: List[str]) -> Optional[tuple]:
    joined = set(tokens)
    for scope, syns in _SCOPE_SYNONYMS.items():
        for s in syns:
            if s in joined:
                return scope, s
    return None


def _detect_status(tokens: List[str]) -> Optional[tuple]:
    joined = set(tokens)
    table = {
        "VERIFIED": ["verified", "da_xac_minh", "xac_minh"],
        "DRAFT": ["draft", "nhap"],
        "PENDING": ["pending", "cho_duyet"],
        "ARCHIVED": ["archived", "luu_tru"],
    }
    for status, syns in table.items():
        for s in syns:
            if s in joined:
                return status, s
    return None


def _detect_limit(tokens: List[str]) -> Optional[int]:
    num_words = {"mot": 1, "hai": 2, "ba": 3, "nam": 5, "muoi": 10,
                 "hai_muoi": 20, "năm": 5}
    for i, t in enumerate(tokens):
        if t.isdigit():
            # only treat as limit when adjacent to a list/count word
            prev = tokens[i - 1] if i else ""
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if prev in Intent.TIMELINE_WORDS or nxt in Intent.TIMELINE_WORDS:
                continue
            if prev in Intent.SEARCH_WORDS or prev in Intent.COUNT_WORDS or \
               nxt in Intent.SEARCH_WORDS or nxt in Intent.COUNT_WORDS or \
               prev in ("top",) or prev in ("lay", "get"):
                return int(t)
        if t == "nam" and i + 1 < len(tokens) and tokens[i + 1] in ("kinh_nghiem", "results", "items"):
            return num_words[t]
    return None


def _pick_sort(tokens: List[str]) -> Optional[Sort]:
    joined = set(tokens)
    if "moi_nhat" in joined or "newest" in joined or "latest" in joined or "recent" in joined or "recently" in joined:
        return Sort(field="created_at", direction="desc")
    if "cu_nhat" in joined or "oldest" in joined:
        return Sort(field="created_at", direction="asc")
    return None


class NLQueryEngine:
    """Parse natural-language questions and execute them over list[KU dict].

    SIMULATED NLP: deterministic keyword rules, no ML model, no network.
    """

    DEFAULT_LIMIT = 50

    def __init__(self, records: Optional[Sequence[Dict[str, Any]]] = None,
                 now: Optional[datetime] = None) -> None:
        self.records: List[Dict[str, Any]] = list(records or [])
        self.now = now or datetime.utcnow()

    # -- public API ---------------------------------------------------------

    def parse(self, query: str) -> QueryPlan:
        """Tokenize + detect intent + build the structured QueryPlan."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        tokens = tokenize(query)
        plan = QueryPlan(raw_text=query, intent=Intent.UNKNOWN)
        if not tokens:
            plan.warnings.append("empty_query")
            return plan

        plan.intent = self._detect_intent(tokens)
        plan.text_terms = [t for t in tokens if len(t) >= 3 and not t.isdigit()]
        plan.compare_targets = self._extract_compare_targets(tokens)
        plan.limit = _detect_limit(tokens) or self.DEFAULT_LIMIT
        plan.sort = _pick_sort(tokens)

        type_hit = _detect_type(tokens)
        if type_hit:
            plan.filters.append(Filter(field="type", value=type_hit[0]))
        scope_hit = _detect_scope(tokens)
        if scope_hit:
            plan.filters.append(Filter(field="scope", value=scope_hit[0]))
        status_hit = _detect_status(tokens)
        if status_hit:
            plan.filters.append(Filter(field="status", value=status_hit[0]))

        tf = self._detect_time(tokens)
        if tf:
            plan.time_filters.append(tf)

        for m in _POSSESSIVE_RE.finditer(query.lower()):
            plan.warnings.append(f"possessive_phrase:{m.group(1)}")

        return plan

    def execute(self, plan: QueryPlan,
                records: Optional[Sequence[Dict[str, Any]]] = None) -> QueryResult:
        """Run a plan against the record list; returns results + explanation."""
        rows = list(records if records is not None else self.records)

        # structural filters
        for f in plan.filters:
            keys = _FIELD_ALIASES.get(f.field, [f.field])
            rows = [r for r in rows if self._match_filter(r, keys, f)]

        # free-text terms (must appear in at least one searchable field)
        if plan.text_terms:
            rows = [r for r in rows if self._match_text(r, plan.text_terms)]

        # time filters
        for tf in plan.time_filters:
            rows = [r for r in rows if self._match_time(r, tf)]

        # sort
        if plan.sort:
            key = plan.sort.field
            reverse = plan.sort.direction == "desc"
            rows.sort(
                key=lambda r: self._sort_key(r, key),
                reverse=reverse,
            )

        total = len(rows)
        limited = rows[: plan.limit]
        explanation = self._explain(plan, total, limited)
        return QueryResult(
            query=plan.raw_text,
            intent=plan.intent,
            plan=plan,
            results=limited,
            count=len(limited),
            total_matches=total,
            explanation=explanation,
        )

    def query(self, text: str,
              records: Optional[Sequence[Dict[str, Any]]] = None) -> QueryResult:
        """Convenience: parse + execute in one call."""
        return self.execute(self.parse(text), records=records)

    # -- intent -------------------------------------------------------------

    def _detect_intent(self, tokens: List[str]) -> str:
        joined = set(tokens)
        if joined & Intent.COMPARE_WORDS:
            return Intent.COMPARE
        if joined & Intent.COUNT_WORDS:
            return Intent.COUNT
        if joined & Intent.TIMELINE_WORDS:
            return Intent.TIMELINE
        if joined & Intent.SEARCH_WORDS:
            return Intent.SEARCH
        return Intent.UNKNOWN

    def _extract_compare_targets(self, tokens: List[str]) -> List[str]:
        targets: List[str] = []
        for scope, syns in _SCOPE_SYNONYMS.items():
            if any(s in tokens for s in syns):
                targets.append(scope)
        if "vs" in tokens or "versus" in tokens or "so_sanh" in tokens:
            return targets
        return targets[:2]

    # -- time filter --------------------------------------------------------

    def _detect_time(self, tokens: List[str]) -> Optional[TimeFilter]:
        for t in tokens:
            if t in _TIME_KEYWORDS:
                days, label = _TIME_KEYWORDS[t]
                return TimeFilter(field=self._time_field_label(tokens),
                                  keyword=t, days=days)
        return None

    def _time_field_label(self, tokens: List[str]) -> str:
        for hint in _TIME_FIELD_HINTS:
            if hint in tokens:
                return hint
        return "created_at"

    # -- matching helpers ----------------------------------------------------

    def _match_filter(self, row: Dict[str, Any], keys: List[str],
                      f: Filter) -> bool:
        for k in keys:
            if k not in row:
                continue
            v = row[k]
            if f.op == "contains":
                if isinstance(v, (list, tuple, set)):
                    norm = {str(x).strip().lower() for x in v}
                    if str(f.value).lower() in norm:
                        return True
                elif str(f.value).lower() in str(v).lower():
                    return True
            else:  # eq
                if isinstance(v, str):
                    if v.strip().upper() == str(f.value).upper():
                        return True
                elif v == f.value:
                    return True
        return False

    def _match_text(self, row: Dict[str, Any], terms: List[str]) -> bool:
        hay_parts: List[str] = []
        for canon in ("title", "content"):
            for k in _FIELD_ALIASES[canon]:
                v = row.get(k)
                if isinstance(v, str):
                    hay_parts.append(v)
        for v in row.get("tags", []) or []:
            hay_parts.append(str(v))
        hay = ascii_fold(" ".join(hay_parts))
        return all(t in hay for t in terms)

    def _match_time(self, row: Dict[str, Any], tf: TimeFilter) -> bool:
        for canon in ("created_at",):
            for k in _FIELD_ALIASES[canon]:
                v = row.get(k)
                if v is None:
                    continue
                dt = self._parse_dt(v)
                if dt is None:
                    continue
                cutoff = self.now - timedelta(days=tf.days)
                return dt >= cutoff
        return False

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _sort_key(row: Dict[str, Any], field: str) -> Any:
        for k in _FIELD_ALIASES.get(field, [field]):
            v = row.get(k)
            if v is not None:
                dt = NLQueryEngine._parse_dt(v)
                return dt or v
        return datetime.min

    # -- explanation ----------------------------------------------------------

    def _explain(self, plan: QueryPlan, total: int,
                 returned: List[Dict[str, Any]]) -> str:
        parts: List[str] = []
        intent_desc = {
            Intent.SEARCH: "Search records",
            Intent.COUNT: "Count records",
            Intent.COMPARE: "Compare groups",
            Intent.TIMELINE: "Timeline / recent records",
            Intent.UNKNOWN: "Unrecognized intent (fallback text search)",
        }
        parts.append(intent_desc.get(plan.intent, plan.intent))
        if plan.filters:
            fdesc = ", ".join(f"{f.field}={f.value}" for f in plan.filters)
            parts.append(f"filters: [{fdesc}]")
        if plan.time_filters:
            parts.append(", ".join(
                f"time: last {tf.days}d on {tf.field}" for tf in plan.time_filters))
        if plan.text_terms:
            parts.append(f"terms: {plan.text_terms}")
        if plan.sort:
            parts.append(f"sorted by {plan.sort.field} {plan.sort.direction}")
        parts.append(f"matched {total}, returned {len(returned)} (limit {plan.limit})")
        if plan.intent == Intent.COUNT:
            parts.append(f"answer: {total}")
        return " | ".join(parts)
