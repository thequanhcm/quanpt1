"""V29.3 — Explainable AI (XAI, toy, stdlib-only).

HONESTY NOTE
------------
This module implements *toy* XAI primitives: per-feature perturbation
attribution, brute-force counterfactual search over a feature grid, and
template-based bilingual (VI/EN) explanation text. It is NOT SHAP, NOT
LIME, and the calibration is a simple binning scheme — adequate for
demonstration and regression tests, not for production model auditing.

Components:
- FeatureAttribution: perturb-each-feature delta attribution.
- CounterfactualExplainer: which feature change flips the label.
- ExplanationGenerator: VI/EN natural-language templates.
- ConfidenceCalibrator: binning on historical accuracy.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence

__version__ = "V29.3"

ScoreFn = Callable[[Sequence[float]], float]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# Feature attribution by perturbation
# ---------------------------------------------------------------------------

@dataclass
class FeatureAttribution:
    """Attribution scores for one prediction."""
    base_score: float
    scores: dict[str, float]  # feature -> delta when perturbed
    features: dict[str, float]  # feature -> value in the instance

    @property
    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.scores.items(), key=lambda kv: kv[1],
                      reverse=True)

    @property
    def top_feature(self) -> Optional[tuple[str, float]]:
        ranked = self.ranked
        return ranked[0] if ranked else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_score": self.base_score,
            "scores": dict(self.scores),
            "features": dict(self.features),
            "ranked": [[k, v] for k, v in self.ranked],
        }


class AttributionExplainer:
    """Leave-one-out attribution: replace each feature with its baseline
    (default 0.0) and report the *contribution* = base_score - perturbed
    score. Positive contribution = the feature pushed the score up."""

    def __init__(self, score_fn: ScoreFn,
                 feature_names: Sequence[str],
                 baseline: Optional[Sequence[float]] = None) -> None:
        self.score_fn = score_fn
        self.feature_names = list(feature_names)
        self.baseline = list(baseline) if baseline is not None else None

    def explain(self, instance: Sequence[float]) -> FeatureAttribution:
        values = [float(v) for v in instance]
        if len(values) != len(self.feature_names):
            raise ValueError(
                f"instance has {len(values)} features, "
                f"expected {len(self.feature_names)}")
        base = float(self.score_fn(values))
        contributions: dict[str, float] = {}
        for i, name in enumerate(self.feature_names):
            perturbed = list(values)
            if self.baseline is not None:
                perturbed[i] = float(self.baseline[i])
            else:
                perturbed[i] = 0.0
            contributions[name] = base - float(self.score_fn(perturbed))
        return FeatureAttribution(base_score=base, scores=contributions,
                                  features=dict(zip(self.feature_names, values)))


# ---------------------------------------------------------------------------
# Counterfactual explanations
# ---------------------------------------------------------------------------

@dataclass
class Counterfactual:
    """A minimal feature change that flips the predicted label."""
    changes: dict[str, float]  # feature -> new value
    new_score: float
    original_score: float
    flipped: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "changes": dict(self.changes),
            "new_score": self.new_score,
            "original_score": self.original_score,
            "flipped": self.flipped,
        }


class CounterfactualExplainer:
    """Brute-force search: for each feature, try a small grid of values
    (applied one at a time) and report the first change that flips the
    decision. Returns all flip candidates sorted by |change| magnitude."""

    def __init__(self, score_fn: ScoreFn, feature_names: Sequence[str],
                 threshold: float = 0.5, steps: int = 11) -> None:
        self.score_fn = score_fn
        self.feature_names = list(feature_names)
        self.threshold = threshold
        self.steps = max(2, steps)

    def explain(self, instance: Sequence[float],
                max_results: int = 5) -> list[Counterfactual]:
        values = [float(v) for v in instance]
        original = float(self.score_fn(values))
        original_label = original >= self.threshold
        candidates: list[Counterfactual] = []

        for i, name in enumerate(self.feature_names):
            grid = [1.0 * k / (self.steps - 1) for k in range(self.steps)]
            for value in grid:
                if abs(value - values[i]) < 1e-9:
                    continue
                modified = list(values)
                modified[i] = value
                new_score = float(self.score_fn(modified))
                if (new_score >= self.threshold) != original_label:
                    candidates.append(Counterfactual(
                        changes={name: value},
                        new_score=new_score,
                        original_score=original,
                        flipped=True,
                    ))
                    break  # one minimal flip per feature
        candidates.sort(key=lambda c: sum(
            abs(v - values[self.feature_names.index(k)])
            for k, v in c.changes.items()))
        return candidates[:max(0, max_results)]

    def find_counterfactuals(self, instance: Sequence[float],
                             max_results: int = 5) -> list[Counterfactual]:
        """Alias kept for API compatibility."""
        return self.explain(instance, max_results=max_results)


# ---------------------------------------------------------------------------
# Bilingual (VI/EN) explanation templates
# ---------------------------------------------------------------------------

class ExplanationLanguage(str, Enum):
    VI = "vi"
    EN = "en"


@dataclass
class Explanation:
    text: str
    language: str
    base_score: float
    top_feature: Optional[str]
    counterfactuals: list[Counterfactual]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "base_score": self.base_score,
            "top_feature": self.top_feature,
            "counterfactuals": [c.to_dict() for c in self.counterfactuals],
            "metadata": dict(self.metadata),
        }


class ExplanationGenerator:
    """Template-based VI/EN explanation generation."""

    def __init__(self, language: str = "vi") -> None:
        lang = (language or "vi").lower()
        self.language = (ExplanationLanguage.VI if lang.startswith("vi")
                         else ExplanationLanguage.EN)

    def explain(self, attribution: FeatureAttribution,
                decision: str = "",
                counterfactuals: Optional[list[Counterfactual]] = None) -> Explanation:
        cf = counterfactuals or []
        top = attribution.top_feature
        ranked = attribution.ranked

        if self.language == ExplanationLanguage.VI:
            if top:
                direction = "tăng" if top[1] >= 0 else "giảm"
                text = (f"Quyết định {decision or 'hiện tại'} (điểm "
                        f"{attribution.base_score:.2f}) chủ yếu do "
                        f"«{top[0]}» {direction} điểm "
                        f"{abs(top[1]):.2f}.")
            else:
                text = f"Quyết định {decision or 'hiện tại'} (điểm {attribution.base_score:.2f})."
            if ranked:
                others = ", ".join(f"{k} ({v:+.2f})" for k, v in ranked[1:4])
                if others:
                    text += f" Các yếu tố khác: {others}."
            if cf:
                name, value = next(iter(cf[0].changes.items()))
                text += (f" Nếu «{name}» = {value:.2f} thì kết quả sẽ đảo "
                         f"ngược lại.")
        else:
            if top:
                direction = "raised" if top[1] >= 0 else "lowered"
                text = (f"The decision {decision or 'as-is'} (score "
                        f"{attribution.base_score:.2f}) is mostly driven by "
                        f"'{top[0]}' which {direction} the score by "
                        f"{abs(top[1]):.2f}.")
            else:
                text = f"The decision {decision or 'as-is'} (score {attribution.base_score:.2f})."
            if ranked:
                others = ", ".join(f"{k} ({v:+.2f})" for k, v in ranked[1:4])
                if others:
                    text += f" Other factors: {others}."
            if cf:
                name, value = next(iter(cf[0].changes.items()))
                text += (f" If '{name}' were {value:.2f}, the decision "
                         f"would flip.")

        return Explanation(
            text=text,
            language=self.language.value,
            base_score=attribution.base_score,
            top_feature=top[0] if top else None,
            counterfactuals=cf,
        )


# ---------------------------------------------------------------------------
# Confidence calibration (binning on historical accuracy)
# #

# ---------------------------------------------------------------------------

class ConfidenceCalibrator:
    """Calibrate raw scores into probabilities using accuracy-per-bin.

    Records (score, correct) history; `calibrate(score)` returns the
    observed accuracy of the bin the score falls into (empirical
    calibration), optionally blended with the raw score.
    """

    def __init__(self, n_bins: int = 10,
                 blend_raw_weight: float = 0.3) -> None:
        if n_bins < 1:
            raise ValueError("n_bins must be >= 1")
        self.n_bins = n_bins
        self.blend_raw_weight = blend_raw_weight
        self._history: list[tuple[float, int]] = []

    def record(self, score: float, correct: bool) -> None:
        self._history.append((_clamp01(score), 1 if correct else 0))

    @property
    def history(self) -> list[tuple[float, int]]:
        return list(self._history)

    def _bin_index(self, score: float) -> int:
        s = _clamp01(score)
        if s >= 1.0:
            return self.n_bins - 1
        return int(s * self.n_bins)

    def bin_accuracy(self, score: float) -> Optional[float]:
        idx = self._bin_index(score)
        in_bin = [c for s, c in self._history
                  if self._bin_index(s) == idx]
        if not in_bin:
            return None
        return sum(in_bin) / len(in_bin)

    def calibrate(self, score: float) -> float:
        """Calibrated probability = blend of raw score and bin accuracy
        (falls back to raw score when the bin has no history)."""
        s = _clamp01(score)
        acc = self.bin_accuracy(s)
        if acc is None:
            return s
        w = self.blend_raw_weight
        return _clamp01(w * s + (1.0 - w) * acc)

    def reliability_diagram(self) -> list[dict[str, Any]]:
        """Per-bin: count, mean score, accuracy (None if empty)."""
        bins: list[dict[str, Any]] = []
        for idx in range(self.n_bins):
            in_bin = [(s, c) for s, c in self._history
                      if self._bin_index(s) == idx]
            if in_bin:
                mean_score = statistics.mean(s for s, _ in in_bin)
                acc = sum(c for _, c in in_bin) / len(in_bin)
            else:
                mean_score, acc = None, None
            bins.append({
                "bin": idx,
                "range": (idx / self.n_bins, (idx + 1) / self.n_bins),
                "count": len(in_bin),
                "mean_score": mean_score,
                "accuracy": acc,
            })
        return bins

    def expected_calibration_error(self) -> Optional[float]:
        """ECE over non-empty bins."""
        non_empty = [b for b in self.reliability_diagram() if b["count"] > 0]
        if not non_empty:
            return None
        total = sum(b["count"] for b in non_empty)
        ece = 0.0
        for b in non_empty:
            gap = abs((b["accuracy"] or 0.0) - (b["mean_score"] or 0.0))
            ece += (b["count"] / total) * gap
        return ece


class ExplainableAI:
    """Facade tying attribution + counterfactuals + NL generation."""

    def __init__(self, score_fn: ScoreFn, feature_names: Sequence[str],
                 language: str = "vi", threshold: float = 0.5) -> None:
        self.attribution_explainer = AttributionExplainer(score_fn, feature_names)
        self.counterfactual_explainer = CounterfactualExplainer(
            score_fn, feature_names, threshold=threshold)
        self.generator = ExplanationGenerator(language)

    def explain(self, instance: Sequence[float], decision: str = "",
                with_counterfactuals: bool = True) -> Explanation:
        attribution = self.attribution_explainer.explain(instance)
        counterfactuals = (self.counterfactual_explainer.explain(instance)
                           if with_counterfactuals else [])
        return self.generator.explain(attribution, decision=decision,
                                      counterfactuals=counterfactuals)
