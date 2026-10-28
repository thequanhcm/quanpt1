"""Natural Language Query subsystem (V24.2) for QUAN AI BRAIN.

SIMULATED / HEURISTIC implementation note:
Intent detection is keyword-based (no spaCy / BERT / external models),
per the V24 sprint hard rules (stdlib only, no new dependencies).
"""

from quan_ai_brain.nlp.query_engine import (
    Filter,
    Intent,
    NLQueryEngine,
    QueryPlan,
    QueryResult,
    Sort,
    TimeFilter,
    ascii_fold,
    tokenize,
)

__all__ = [
    "Filter",
    "Intent",
    "NLQueryEngine",
    "QueryPlan",
    "QueryResult",
    "Sort",
    "TimeFilter",
    "ascii_fold",
    "tokenize",
]
