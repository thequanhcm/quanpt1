"""V29.1 — Neural-Symbolic AI (TOY / SIMULATED, stdlib-only).

HONESTY NOTE (read this first)
------------------------------
Everything "neural" in this module is a *simulation* built from Python
lists, deterministic hashing and hand-written arithmetic. There is NO real
trained neural network, no gradient learning, no transformer weights and
no external ML library here. The module demonstrates the *architecture* of
a neural-symbolic pipeline (embed -> attention pool -> neural gate ->
symbolic forward chaining -> hybrid answer) and must never be presented as
a replacement for a real neural model.

Components:
- HashEmbedder: deterministic hash-based token vectors (list[float]).
- AttentionPooler: hand-written softmax attention over token vectors.
- Fact / Rule / SymbolicRuleEngine: facts + rules -> forward chaining.
- NeuralSymbolicBridge: neural score gates rule confidence; hybrid query.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

__version__ = "V29.1"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase tokenizer that keeps unicode (Vietnamese) letters."""
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t]


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Symbolic side
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    """A symbolic fact: predicate(args...) with a confidence in [0, 1]."""
    predicate: str
    args: tuple[str, ...]
    confidence: float = 1.0
    source: str = "asserted"

    @property
    def key(self) -> str:
        return f"{self.predicate}({','.join(self.args)})"

    def to_text(self) -> str:
        """Flat text form used for the (toy) neural embedding."""
        return " ".join([self.predicate, *self.args])

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "args": list(self.args),
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class Rule:
    """A Horn-style rule: premises => conclusion.

    Args starting with '?' are variables; anything else must match exactly.
    """
    name: str
    premises: tuple[tuple[str, ...], ...]
    conclusion: tuple[str, ...]
    base_confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "premises": [list(p) for p in self.premises],
            "conclusion": list(self.conclusion),
            "base_confidence": self.base_confidence,
        }


def _match_pattern(pattern: tuple[str, ...], fact: Fact,
                   bindings: dict[str, str]) -> dict[str, str] | None:
    """Unify one premise pattern against a fact, extending bindings."""
    if pattern[0] != fact.predicate or len(pattern) - 1 != len(fact.args):
        return None
    bound = dict(bindings)
    for p_arg, f_arg in zip(pattern[1:], fact.args):
        if p_arg.startswith("?"):
            if p_arg in bound and bound[p_arg] != f_arg:
                return None
            bound[p_arg] = f_arg
        elif p_arg != f_arg:
            return None
    return bound


class SymbolicRuleEngine:
    """Forward-chaining rule engine over facts (stdlib only)."""

    def __init__(self) -> None:
        self.facts: list[Fact] = []
        self.rules: list[Rule] = []
        self._fact_keys: set[str] = set()

    # -- mutation -----------------------------------------------------------
    def add_fact(self, predicate: str, args: Sequence[str],
                 confidence: float = 1.0, source: str = "asserted") -> Fact:
        fact = Fact(predicate, tuple(args), _clamp(confidence), source)
        if fact.key not in self._fact_keys:
            self.facts.append(fact)
            self._fact_keys.add(fact.key)
        return fact

    def add_rule(self, name: str, premises: Sequence[Sequence[str]],
                 conclusion: Sequence[str],
                 base_confidence: float = 1.0) -> Rule:
        rule = Rule(
            name=name,
            premises=tuple(tuple(p) for p in premises),
            conclusion=tuple(conclusion),
            base_confidence=_clamp(base_confidence),
        )
        self.rules.append(rule)
        return rule

    # -- querying -----------------------------------------------------------
    def query(self, predicate: str,
              args: Sequence[str] | None = None) -> list[Fact]:
        """Exact lookup by predicate (+ optional exact args)."""
        out = []
        for fact in self.facts:
            if fact.predicate != predicate:
                continue
            if args is not None and tuple(args) != fact.args:
                continue
            out.append(fact)
        return out

    def ask_pattern(self, pattern: Sequence[str]) -> list[tuple[Fact, dict]]:
        """Match a single pattern (with ?vars) against known facts."""
        pat = tuple(pattern)
        matches: list[tuple[Fact, dict]] = []
        for fact in self.facts:
            bound = _match_pattern(pat, fact, {})
            if bound is not None:
                matches.append((fact, bound))
        return matches

    # -- inference ----------------------------------------------------------
    def _apply_rule(self, rule: Rule) -> list[tuple[tuple[str, ...], float]]:
        results: list[tuple[tuple[str, ...], float]] = []
        seen: set[tuple[str, ...]] = set()

        def rec(index: int, bindings: dict[str, str], conf: float) -> None:
            if index == len(rule.premises):
                args = tuple(bindings.get(a, a) for a in rule.conclusion[1:])
                if args not in seen:
                    seen.add(args)
                    results.append((args, conf))
                return
            pattern = rule.premises[index]
            for fact in self.facts:
                bound = _match_pattern(pattern, fact, bindings)
                if bound is not None:
                    rec(index + 1, bound, min(conf, fact.confidence))

        rec(0, {}, rule.base_confidence)
        return results

    def forward_chain(self, max_steps: int = 50) -> list[Fact]:
        """Run forward chaining to fixpoint; return newly derived facts."""
        derived: list[Fact] = []
        for _ in range(max_steps):
            changed = False
            for rule in self.rules:
                for args, conf in self._apply_rule(rule):
                    key = f"{rule.conclusion[0]}({','.join(args)})"
                    if key in self._fact_keys:
                        continue
                    fact = Fact(rule.conclusion[0], args, conf,
                                source=rule.name)
                    self.facts.append(fact)
                    self._fact_keys.add(key)
                    derived.append(fact)
                    changed = True
            if not changed:
                break
        return derived

    def stats(self) -> dict[str, int]:
        return {"facts": len(self.facts), "rules": len(self.rules)}


# ---------------------------------------------------------------------------
# Neural side (SIMULATED — hash vectors + hand-written attention)
# ---------------------------------------------------------------------------

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def softmax(scores: Sequence[float]) -> list[float]:
    if not scores:
        return []
    peak = max(scores)
    exps = [math.exp(s - peak) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


class AttentionPooler:
    """Hand-written single-head attention pooling over token vectors.

    weights = softmax(v_i . q / (sqrt(dim) * temperature)); output is the
    weighted sum of the token vectors. Pure Python on list[float].
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(temperature, 1e-6)

    def attention_weights(self, vectors: Sequence[Sequence[float]],
                          query: Sequence[float] | None = None) -> list[float]:
        if not vectors:
            return []
        dim = len(vectors[0])
        if query is None:
            query = [sum(v[i] for v in vectors) / len(vectors)
                     for i in range(dim)]
        scale = math.sqrt(dim) * self.temperature
        scores = [sum(v[i] * query[i] for i in range(dim)) / scale
                  for v in vectors]
        return softmax(scores)

    def pool(self, vectors: Sequence[Sequence[float]],
             query: Sequence[float] | None = None) -> list[float]:
        if not vectors:
            return []
        weights = self.attention_weights(vectors, query)
        dim = len(vectors[0])
        return [
            sum(weights[i] * vectors[i][j] for i in range(len(vectors)))
            for j in range(dim)
        ]


class HashEmbedder:
    """Deterministic hash-based embedder (toy neural encoder).

    Each token maps to a fixed pseudo-random unit vector derived from an
    md5 digest seeded by (seed, token). Texts embed via attention pooling.
    Deterministic: same input -> same vector on every run.
    """

    def __init__(self, dim: int = 32, seed: int = 42,
                 pooler: AttentionPooler | None = None) -> None:
        self.dim = dim
        self.seed = seed
        self.pooler = pooler or AttentionPooler()

    def embed_token(self, token: str) -> list[float]:
        digest = hashlib.md5(
            f"{self.seed}:{token}".encode("utf-8")).digest()
        raw: list[float] = []
        i = 0
        while len(raw) < self.dim:
            raw.append((digest[i % len(digest)] / 255.0) * 2.0 - 1.0)
            i += 1
        norm = math.sqrt(sum(v * v for v in raw))
        if norm == 0.0:
            norm = 1.0
        return [v / norm for v in raw]

    def embed_text(self, text: str) -> list[float]:
        vectors = [self.embed_token(t) for t in tokenize(text)]
        if not vectors:
            return [0.0] * self.dim
        return self.pooler.pool(vectors)

    def similarity(self, text_a: str, text_b: str) -> float:
        return cosine_similarity(self.embed_text(text_a),
                                 self.embed_text(text_b))


# ---------------------------------------------------------------------------
# Bridge: neural score gates symbolic confidence; hybrid inference
# ---------------------------------------------------------------------------

@dataclass
class HybridMatch:
    fact: Fact
    symbolic_confidence: float
    neural_score: float
    gated_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": self.fact.to_dict(),
            "symbolic_confidence": self.symbolic_confidence,
            "neural_score": self.neural_score,
            "gated_confidence": self.gated_confidence,
        }


@dataclass
class HybridResult:
    query: str
    matches: list[HybridMatch] = field(default_factory=list)

    @property
    def best(self) -> HybridMatch | None:
        return self.matches[0] if self.matches else None

    @property
    def confidence(self) -> float:
        best = self.best
        return best.gated_confidence if best else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "confidence": self.confidence,
            "matches": [m.to_dict() for m in self.matches],
        }


class NeuralSymbolicBridge:
    """Bridge between the toy neural embedder and the symbolic engine.

    - neural_score: cosine similarity between fact text and query text,
      rescaled from [-1, 1] to [0, 1].
    - gate: symbolic confidence is *gated* (discounted) by the neural
      score: gated = sym_conf * (alpha + (1 - alpha) * neural_score).
    - hybrid_query: rank engine facts by gated confidence.
    """

    def __init__(self, embedder: HashEmbedder | None = None,
                 alpha: float = 0.5) -> None:
        self.embedder = embedder or HashEmbedder()
        self.alpha = _clamp(alpha)

    def neural_score(self, fact: Fact | str, query: str) -> float:
        fact_text = fact.to_text() if isinstance(fact, Fact) else fact
        sim = cosine_similarity(self.embedder.embed_text(fact_text),
                                self.embedder.embed_text(query))
        return _clamp((sim + 1.0) / 2.0)

    def gate(self, symbolic_confidence: float, neural_score: float) -> float:
        return _clamp(symbolic_confidence *
                      (self.alpha + (1.0 - self.alpha) * _clamp(neural_score)))

    def extract_symbols(self, text: str,
                        known_terms: Iterable[str]) -> list[str]:
        """Neural extraction of symbols: tokens that match a known
        vocabulary (predicates / entities), in order, deduplicated."""
        known = {t.lower() for t in known_terms}
        found: list[str] = []
        for token in tokenize(text):
            if token in known and token not in found:
                found.append(token)
        return found

    def hybrid_query(self, engine: SymbolicRuleEngine, query: str,
                     top_k: int = 5) -> HybridResult:
        matches: list[HybridMatch] = []
        for fact in engine.facts:
            sym = fact.confidence
            neural = self.neural_score(fact, query)
            matches.append(HybridMatch(
                fact=fact,
                symbolic_confidence=sym,
                neural_score=neural,
                gated_confidence=self.gate(sym, neural),
            ))
        matches.sort(key=lambda m: m.gated_confidence, reverse=True)
        return HybridResult(query=query, matches=matches[:max(top_k, 0)])
