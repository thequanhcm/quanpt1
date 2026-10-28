"""V29.2 — Common Sense Reasoning (toy, stdlib-only).

HONESTY NOTE
------------
This is a small hand-curated concept store (~30 built-in concepts) with a
BFS relation search — NOT ConceptNet/Cyc and not a large-scale knowledge
graph. It demonstrates common-sense style inference (is_a / has /
capable_of / causes chains, contradiction checks, context boosts) over a
toy vocabulary.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional

__version__ = "V29.2"


class RelationType(str, Enum):
    IS_A = "is_a"
    HAS = "has"
    CAPABLE_OF = "capable_of"
    CAUSES = "causes"


@dataclass
class Concept:
    name: str
    description_vi: str = ""
    description_en: str = ""
    relations: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description_vi": self.description_vi,
            "description_en": self.description_en,
            "relations": {k: list(v) for k, v in self.relations.items()},
        }


@dataclass
class InferencePath:
    """A multi-hop inference path conceptA --[rel]--> conceptB ..."""
    start: str
    end: str
    steps: list[tuple[RelationType, str]]  # (relation, next_concept)
    confidence: float = 1.0

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def concepts_on_path(self) -> list[str]:
        chain = [self.start]
        chain.extend(next_c for _, next_c in self.steps)
        return chain

    def explain(self, lang: str = "vi") -> str:
        lang = (lang or "vi").lower()
        verb_map = {
            RelationType.IS_A: ("là", "is a"),
            RelationType.HAS: ("có", "has"),
            RelationType.CAPABLE_OF: ("có thể", "can"),
            RelationType.CAUSES: ("gây ra", "causes"),
        }
        parts = [self.start]
        for rel, nxt in self.steps:
            vi, en = verb_map[rel]
            verb = vi if lang.startswith("vi") else en
            parts.append(f"{verb} {nxt}")
        return " -> ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "steps": [[rel.value, nxt] for rel, nxt in self.steps],
            "confidence": self.confidence,
        }


@dataclass
class ContradictionReport:
    concept: str
    contradictory: list[tuple[RelationType, str]] = field(default_factory=list)

    @property
    def has_contradiction(self) -> bool:
        return bool(self.contradictory)

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "has_contradiction": self.has_contradiction,
            "contradictory": [[r.value, t] for r, t in self.contradictory],
        }


# Built-in concept store (30 concepts). Vietnamese-first descriptions.
_BUILTIN_CONCEPTS: list[dict] = [
    {"name": "người", "vi": "Con người", "en": "human",
     "relations": {"is_a": ["sinh_vật"], "capable_of": ["uống", "suy_nghĩ", "di_chuyển"],
                   "has": ["cơ_thể"]}},
    {"name": "sinh_vật", "vi": "Sinh vật", "en": "organism",
     "relations": {"is_a": ["vật_thể"], "capable_of": ["sống", "tăng_trưởng"]}},
    {"name": "vật_thể", "vi": "Vật thể", "en": "entity", "relations": {}},
    {"name": "động_vật", "vi": "Động vật", "en": "animal",
     "relations": {"is_a": ["sinh_vật"], "capable_of": ["di_chuyển", "uống"]}},
    {"name": "cá", "vi": "Cá", "en": "fish", "relations": {"is_a": ["động_vật"], "capable_of": ["bơi"]}},
    {"name": "chim", "vi": "Chim", "en": "bird", "relations": {"is_a": ["động_vật"], "capable_of": ["bay"]}},
    {"name": "máy", "vi": "Máy", "en": "machine",
     "relations": {"is_a": ["vật_thể"], "has": ["động_cơ"]}},
    {"name": "máy_tính", "vi": "Máy tính", "en": "computer",
     "relations": {"is_a": ["máy"], "capable_of": ["tính_toán"], "has": ["bộ_nhớ", "cpu"]}},
    {"name": "robot", "vi": "Robot", "en": "robot",
     "relations": {"is_a": ["máy"], "capable_of": ["di_chuyển", "tính_toán"], "has": ["cảm_biến"]}},
    {"name": "nước", "vi": "Nước", "en": "water",
     "relations": {"causes": ["ướt", "bớt_khát"], "has": ["chất_lỏng"]}},
    {"name": "lửa", "vi": "Lửa", "en": "fire", "relations": {"causes": ["nóng", "cháy"], "capable_of": ["đốt"]}},
    {"name": "nóng", "vi": "Nóng", "en": "hot", "relations": {"causes": ["khát"]}},
    {"name": "ướt", "vi": "Ướt", "en": "wet", "relations": {}},
    {"name": "cháy", "vi": "Cháy", "en": "burning", "relations": {"causes": ["nóng"]}},
    {"name": "khát", "vi": "Khát", "en": "thirsty", "relations": {}},
    {"name": "sống", "vi": "Sống", "en": "alive", "relations": {}},
    {"name": "tăng_trưởng", "vi": "Tăng trưởng", "en": "growth", "relations": {}},
    {"name": "suy_nghĩ", "vi": "Suy nghĩ", "en": "thinking", "relations": {}},
    {"name": "di_chuyển", "vi": "Di chuyển", "en": "moving", "relations": {}},
    {"name": "bơi", "vi": "Bơi", "en": "swimming", "relations": {}},
    {"name": "bay", "vi": "Bay", "en": "flying", "relations": {}},
    {"name": "tính_toán", "vi": "Tính toán", "en": "computing", "relations": {}},
    {"name": "đốt", "vi": "Đốt", "en": "burning_things", "relations": {}},
    {"name": "cơ_thể", "vi": "Cơ thể", "en": "body", "relations": {}},
    {"name": "động_cơ", "vi": "Động cơ", "en": "engine", "relations": {}},
    {"name": "bộ_nhớ", "vi": "Bộ nhớ", "en": "memory", "relations": {}},
    {"name": "cpu", "vi": "CPU", "en": "cpu", "relations": {}},
    {"name": "cảm_biến", "vi": "Cảm biến", "en": "sensor", "relations": {}},
    {"name": "chất_lỏng", "vi": "Chất lỏng", "en": "liquid", "relations": {}},
    {"name": "uống", "vi": "Uống", "en": "drinking", "relations": {}},
    {"name": "bớt_khát", "vi": "Bớt khát", "en": "less_thirsty", "relations": {}},
]


class ConceptStore:
    """A small concept store with typed relations and BFS search."""

    def __init__(self, load_builtin: bool = True) -> None:
        self.concepts: dict[str, Concept] = {}
        self._edges: dict[str, list[tuple[RelationType, str]]] = {}
        if load_builtin:
            for spec in _BUILTIN_CONCEPTS:
                concept = Concept(
                    name=spec["name"],
                    description_vi=spec["vi"],
                    description_en=spec["en"],
                    relations={k: list(v) for k, v in spec["relations"].items()},
                )
                self.add_concept(concept)

    def add_concept(self, concept: Concept) -> Concept:
        if concept.name not in self.concepts:
            self.concepts[concept.name] = concept
            self._edges[concept.name] = []
            for rel, targets in concept.relations.items():
                try:
                    rel_type = RelationType(rel)
                except ValueError:
                    continue
                for target in targets:
                    self._edges[concept.name].append((rel_type, target))
        return self.concepts[concept.name]

    def add_relation(self, source: str, relation: RelationType,
                     target: str) -> None:
        if source not in self.concepts:
            self.add_concept(Concept(name=source))
        if target not in self.concepts:
            self.add_concept(Concept(name=target))
        if (relation, target) not in self._edges[source]:
            self._edges[source].append((relation, target))
            relations = self.concepts[source].relations
            relations.setdefault(relation.value, [])
            if target not in relations[relation.value]:
                relations[relation.value].append(target)

    def get(self, name: str) -> Optional[Concept]:
        return self.concepts.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self.concepts

    def __len__(self) -> int:
        return len(self.concepts)

    def neighbors(self, name: str) -> list[tuple[RelationType, str]]:
        return list(self._edges.get(name, []))

    def find_path(self, start: str, end: str,
                  max_depth: int = 4) -> Optional[InferencePath]:
        """BFS search for a relation path start -> ... -> end."""
        if start == end:
            return InferencePath(start, end, [], 1.0)
        visited: set[str] = {start}
        queue: deque[tuple[str, InferencePath]] = deque()
        queue.append((start, InferencePath(start, end, [])))
        while queue:
            current, path = queue.popleft()
            if path.length >= max_depth:
                continue
            for rel, nxt in self.neighbors(current):
                if nxt in visited:
                    continue
                new_steps = path.steps + [(rel, nxt)]
                if nxt == end:
                    return InferencePath(
                        start=start, end=end, steps=new_steps,
                        confidence=max(0.5, 0.95 ** len(new_steps)),
                    )
                visited.add(nxt)
                queue.append((nxt, InferencePath(start, end, new_steps)))
        return None

    def find_paths_from(self, start: str,
                        max_depth: int = 2) -> list[InferencePath]:
        """All inference paths up to max_depth starting at `start`."""
        paths: list[InferencePath] = []
        visited: set[str] = {start}
        queue: deque[tuple[str, InferencePath]] = deque(
            [(start, InferencePath(start, start, []))])
        while queue:
            current, path = queue.popleft()
            if path.length >= max_depth:
                continue
            for rel, nxt in self.neighbors(current):
                if nxt in visited:
                    continue
                visited.add(nxt)
                new_steps = path.steps + [(rel, nxt)]
                paths.append(InferencePath(
                    start, nxt, new_steps,
                    max(0.5, 0.95 ** len(new_steps)),
                ))
                queue.append((nxt, InferencePath(start, nxt, new_steps)))
        return paths


class CommonSenseReasoner:
    """Common-sense style inference over the ConceptStore."""

    # fixed toy opposite pairs for the contradiction check
    OPPOSITE_PAIRS: tuple[tuple[str, str], ...] = (
        ("khát", "bớt_khát"), ("nóng", "ướt"), ("cháy", "ướt"),
    )

    def __init__(self, store: Optional[ConceptStore] = None) -> None:
        self.store = store or ConceptStore()

    def infer(self, concept: str, max_depth: int = 2) -> list[InferencePath]:
        """All 1..max_depth-hop inferences from a concept (BFS)."""
        return self.store.find_paths_from(concept, max_depth=max_depth)

    def explain_chain(self, start: str, end: str,
                      lang: str = "vi") -> Optional[str]:
        path = self.store.find_path(start, end)
        if path is None:
            return None
        return path.explain(lang)

    def check_contradiction(self, concept: str) -> ContradictionReport:
        """Toy check: does a concept cause both members of an opposite pair?"""
        report = ContradictionReport(concept=concept)
        causes = {t for rel, t in self.store.neighbors(concept)
                  if rel == RelationType.CAUSES}
        for a, b in self.OPPOSITE_PAIRS:
            if a in causes and b in causes:
                report.contradictory.append((RelationType.CAUSES, f"{a} & {b}"))
        return report

    def context_boost(self, paths: list[InferencePath],
                      context: Optional[Iterable[str]] = None) -> list[InferencePath]:
        """Re-rank paths: +0.1 confidence if a path touches the context set."""
        ctx = set(context or [])
        boosted: list[InferencePath] = []
        for path in paths:
            conf = path.confidence
            if ctx and any(c in ctx for c in path.concepts_on_path):
                conf = min(1.0, conf + 0.1)
            boosted.append(InferencePath(
                start=path.start, end=path.end, steps=list(path.steps),
                confidence=conf,
            ))
        boosted.sort(key=lambda p: p.confidence, reverse=True)
        return boosted

    def answer(self, question_vi: str,
               context: Optional[Iterable[str]] = None) -> dict[str, Any]:
        """Toy QA over the store, e.g. 'người có thể uống nước không?'."""
        q = (question_vi or "").lower()
        # order concepts by their position in the question, not store order
        found = sorted((c for c in self.store.concepts if c in q),
                       key=q.index)
        result: dict[str, Any] = {
            "question": question_vi,
            "found_concepts": found,
            "answer": None,
            "explanation": None,
            "confidence": 0.0,
        }
        if len(found) >= 2:
            start, end = found[0], found[1]
            path = self.store.find_path(start, end)
            if path is not None:
                boosted = self.context_boost([path], context)[0]
                is_capable = any(rel == RelationType.CAPABLE_OF
                                 for rel, _ in boosted.steps)
                result["answer"] = bool(is_capable)
                result["explanation"] = boosted.explain("vi")
                result["confidence"] = boosted.confidence
        return result
