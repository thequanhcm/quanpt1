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
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

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


def _bigrams(tokens: List[str]) -> Set[str]:
    """Join adjacent token pairs with '_' so multi-word phrases match
    ('so sanh' -> 'so_sanh', 'last week' -> 'last_week')."""
    return {f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)}


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

    COUNT_PHRASES = [
        "dem", "bao_nhieu", "co_bao_nhieu", "tong_so", "so_luong",
        "count", "how_many", "howmany", "total",
    ]
    SEARCH_PHRASES = [
        "tim", "kiem_tra", "tra_cuu", "xem", "hien_thi", "lay", "liet_ke",
        "find", "show", "search", "list", "get", "display", "look_for",
        "filter",
    ]
    COMPARE_PHRASES = [
        "so_sanh", "so_voi", "khac_gi", "khac_biet",
        "compare", "versus", "vs", "difference",
    ]
    # Core timeline words outrank SEARCH. Pure time ranges ('last week')
    # do NOT set TIMELINE intent — they only add a TimeFilter to the plan.
    TIMELINE_CORE_PHRASES = [
        "lich_su", "history", "timeline",
    ]


# ---------------------------------------------------------------------------
# Synonym tables (values are canonical KU field values)
# ---------------------------------------------------------------------------

_TYPE_SYNONYMS = {
    "LESSON_LEARNED": ["lesson", "lessons", "kinh_nghiem", "bai_hoc"],
    "ERROR": ["error", "errors", "loi", "su_co", "incident"],
    "BEST_PRACTICE": ["practice", "practices", "best_practice"],
    "DECISION": ["decision", "decisions", "quyet_dinh"],
    "NOTE": ["note", "notes", "ghi_chu"],
}

_SCOPE_SYNONYMS = {
    "PRODUCTION": ["production", "prod", "san_xuat"],
    "STAGING": ["staging", "stg"],
    "DEVELOPMENT": ["development", "dev", "phat_trien"],
    "TESTING": ["testing", "kiem_thu"],
    "OPS": ["ops", "operations", "van_hanh"],
}

_STATUS_SYNONYMS = {
    "VERIFIED": ["verified", "da_xac_minh", "xac_minh"],
    "DRAFT": ["draft", "nhap"],
    "PENDING": ["pending", "cho_duyet"],
    "ARCHIVED": ["archived", "luu_tru"],
}

_TIME_KEYWORDS = {
    "today": 1, "hom_nay": 1,
    "yesterday": 2, "hom_qua": 2,
    "last_week": 7, "tuan_truoc": 7, "tuan_nay": 7,
    "recent": 7, "recently": 7,
    "last_month": 30, "thang_truoc": 30, "thang_nay": 30,
    "last_year": 365, "nam_ngoai": 365,
}

_SORT_NEWEST = {"moi_nhat", "newest", "latest"}
_SORT_OLDEST = {"cu_nhat", "oldest"}

# filler words that never make sense as free-text search terms
_STOPWORDS = {
    "cac", "cua", "va", "tu", "trong", "cho", "toi", "duoc", "khong",
    "gi", "nao", "vay", "la", "tren", "vao", "nhieu", "bao", "so",
    "the", "all", "from", "for", "please", "that", "this", "what",
    "which", "was", "were", "have", "has", "and", "give", "want", "need",
    "do", "we", "me", "my",
}


def _flatten_phrases(phrases: List[str]) -> Set[str]:
    """Split 'so_sanh' -> {'so', 'sanh'} for token-level exclusion."""
    out: Set[str] = set()
    for p in phrases:
        out.update(p.split("_"))
    return out


ALL_KEYWORD_TOKENS: Set[str] = set()
for _phrases in (Intent.COUNT_PHRASES, Intent.SEARCH_PHRASES,
                 Intent.COMPARE_PHRASES, Intent.TIMELINE_CORE_PHRASES):
    ALL_KEYWORD_TOKENS |= _flatten_phrases(_phrases)
for _table in (_TYPE_SYNONYMS, _SCOPE_SYNONYMS, _STATUS_SYNONYMS):
    for _syns in _table.values():
        ALL_KEYWORD_TOKENS |= _flatten_phrases(_syns)
ALL_KEYWORD_TOKENS |= _flatten_phrases(list(_TIME_KEYWORDS.keys()))
ALL_KEYWORD_TOKENS |= _SORT_NEWEST | _SORT_OLDEST


def _match_synonyms(tokens: Set[str], bigrams: Set[str],
                    table: Dict[str, List[str]]) -> Optional[Tuple[str, str]]:
    """Return (canonical_value, matched_phrase) for the first hit."""
    for value, syns in table.items():
        for s in syns:
            if "_" in s:
                if s in bigrams:
                    return value, s
            elif s in tokens:
                return value, s
    return None


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
        return {"field": self.field, "keyword": self.keyword,
                "days": self.days, "direction": self.direction}


@dataclass
class Filter:
    """Equality filter on one record field."""
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
# Field aliases (records may use different key names)
# ---------------------------------------------------------------------------

_FIELD_ALIASES = {
    "type": ["type", "ku_type", "knowledge_type", "category"],
    "scope": ["scope", "environment", "env"],
    "status": ["status", "state"],
    "created_at": ["created_at", "timestamp", "date", "time"],
}

_TIME_FIELD_HINTS = ("created_at", "timestamp", "date", "time", "ngay",
                     "thoi_gian")


def _detect_limit(tokens: List[str]) -> Optional[int]:
    search_like = set(_flatten_phrases(Intent.SEARCH_PHRASES)) | \
        set(_flatten_phrases(Intent.COUNT_PHRASES)) | {"top"}
    for i, t in enumerate(tokens):
        if t.isdigit():
            prev = tokens[i - 1] if i else ""
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if prev in search_like or nxt in search_like:
                return int(t)
    return None


def _pick_sort(tokens: Set[str], bigrams: Set[str]) -> Optional[Sort]:
    phrases = tokens | bigrams
    if phrases & _SORT_NEWEST:
        return Sort(field="created_at", direction="desc")
    if phrases & _SORT_OLDEST:
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

        bigrams = _bigrams(tokens)
        token_set = set(tokens)

        plan.intent = self._detect_intent(token_set, bigrams)
        plan.compare_targets = self._extract_compare_targets(token_set, bigrams)
        plan.limit = _detect_limit(tokens) or self.DEFAULT_LIMIT
        plan.sort = _pick_sort(token_set, bigrams)

        type_hit = _match_synonyms(token_set, bigrams, _TYPE_SYNONYMS)
        if type_hit:
            plan.filters.append(Filter(field="type", value=type_hit[0]))
        scope_hit = _match_synonyms(token_set, bigrams, _SCOPE_SYNONYMS)
        if scope_hit:
            plan.filters.append(Filter(field="scope", value=scope_hit[0]))
        status_hit = _match_synonyms(token_set, bigrams, _STATUS_SYNONYMS)
        if status_hit:
            plan.filters.append(Filter(field="status", value=status_hit[0]))

        tf = self._detect_time(token_set, bigrams)
        if tf:
            plan.time_filters.append(tf)

        # free-text terms: tokens not consumed by structured keywords
        plan.text_terms = [t for t in tokens
                           if len(t) >= 3 and not t.isdigit()
                           and t not in ALL_KEYWORD_TOKENS
                           and t not in _STOPWORDS]
        return plan

    def execute(self, plan: QueryPlan,
                records: Optional[Sequence[Dict[str, Any]]] = None) -> QueryResult:
        """Run a plan against the record list; returns results + explanation."""
        rows = list(records if records is not None else self.records)

        # structural filters
        for f in plan.filters:
            keys = _FIELD_ALIASES.get(f.field, [f.field])
            rows = [r for r in rows if self._match_filter(r, keys, f)]

        # free-text terms (must all appear in searchable fields)
        if plan.text_terms:
            rows = [r for r in rows if self._match_text(r, plan.text_terms)]

        # time filters
        for tf in plan.time_filters:
            rows = [r for r in rows if self._match_time(r, tf)]

        # sort
        if plan.sort:
            key_field = plan.sort.field
            reverse = plan.sort.direction == "desc"
            rows.sort(key=lambda r: self._sort_key(r, key_field),
                      reverse=reverse)

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

    def _detect_intent(self, tokens: Set[str], bigrams: Set[str]) -> str:
        phrases = tokens | bigrams
        if set(Intent.COMPARE_PHRASES) & phrases:
            return Intent.COMPARE
        if set(Intent.COUNT_PHRASES) & phrases:
            return Intent.COUNT
        if set(Intent.TIMELINE_CORE_PHRASES) & phrases:
            return Intent.TIMELINE
        if set(Intent.SEARCH_PHRASES) & phrases:
            return Intent.SEARCH
        return Intent.UNKNOWN

    def _extract_compare_targets(self, tokens: Set[str],
                                 bigrams: Set[str]) -> List[str]:
        if not (set(Intent.COMPARE_PHRASES) & (tokens | bigrams)):
            return []
        targets: List[str] = []
        for scope, syns in _SCOPE_SYNONYMS.items():
            for s in syns:
                if ("_" in s and s in bigrams) or ("_" not in s and s in tokens):
                    targets.append(scope)
                    break
        return targets[:2]

    # -- time filter --------------------------------------------------------

    def _detect_time(self, tokens: Set[str],
                     bigrams: Set[str]) -> Optional[TimeFilter]:
        phrases = tokens | bigrams
        for kw, days in _TIME_KEYWORDS.items():
            if kw in phrases:
                return TimeFilter(field=self._time_field_label(tokens),
                                  keyword=kw, days=days)
        return None

    @staticmethod
    def _time_field_label(tokens: Set[str]) -> str:
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
        for k in ("title", "name", "summary", "content", "text", "body",
                  "description", "note"):
            v = row.get(k)
            if isinstance(v, str):
                hay_parts.append(v)
        for v in row.get("tags", []) or []:
            hay_parts.append(str(v))
        hay = ascii_fold(" ".join(hay_parts))
        return all(t in hay for t in terms)

    def _match_time(self, row: Dict[str, Any], tf: TimeFilter) -> bool:
        for k in _FIELD_ALIASES["created_at"]:
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
    def _sort_key(row: Dict[str, Any], field_name: str) -> Any:
        for k in _FIELD_ALIASES.get(field_name, [field_name]):
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
                f"time: last {tf.days}d on {tf.field}"
                for tf in plan.time_filters))
        if plan.text_terms:
            parts.append(f"terms: {plan.text_terms}")
        if plan.sort:
            parts.append(f"sorted by {plan.sort.field} {plan.sort.direction}")
        parts.append(f"matched {total}, returned {len(returned)} "
                     f"(limit {plan.limit})")
        if plan.intent == Intent.COUNT:
            parts.append(f"answer: {total}")
        return " | ".join(parts)
