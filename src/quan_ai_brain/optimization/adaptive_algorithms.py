"""
Adaptive Algorithms Module (V26.3)

This module provides adaptive thresholding and dynamic configuration:
- Dynamic thresholds derived from percentiles of recent data
- Adaptive batch size / timeout based on P95 latency
- Cooldown periods to prevent oscillation between values
- Optional support for multiple strategies selected by context

All behaviour is deterministic, stdlib-only and fully in-memory (simulated).
No network access and no production side effects.

Version: V26.3
Author: QUAN AI BRAIN Team
"""

import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def percentile(sorted_values: List[float], pct: float) -> float:
    """Compute a percentile (0-100) of an already-sorted list.

    Uses linear interpolation between closest ranks, consistent with
    statistics.quantiles(method='inclusive') for common cases.
    """
    if not sorted_values:
        raise ValueError("percentile() requires a non-empty list")
    if pct < 0 or pct > 100:
        raise ValueError("pct must be within [0, 100]")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


@dataclass
class ThresholdResult:
    """The outcome of evaluating one sample against a dynamic threshold."""

    metric_name: str
    value: float
    threshold: float
    breached: bool
    direction: str  # 'above' or 'below'
    sample_count: int
    percentile: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_name': self.metric_name,
            'value': self.value,
            'threshold': self.threshold,
            'breached': self.breached,
            'direction': self.direction,
            'sample_count': self.sample_count,
            'percentile': self.percentile,
        }


class DynamicThreshold:
    """A threshold computed from the percentile of recent observations."""

    def __init__(self, metric_name: str, percentile_value: float = 95.0,
                 window_size: int = 100, direction: str = 'above',
                 static_fallback: Optional[float] = None,
                 absolute_tolerance: float = 0.0,
                 min_samples: int = 5):
        if percentile_value < 0 or percentile_value > 100:
            raise ValueError("percentile_value must be within [0, 100]")
        if direction not in ('above', 'below'):
            raise ValueError("direction must be 'above' or 'below'")
        self.metric_name = metric_name
        self.percentile_value = float(percentile_value)
        self.window_size = int(window_size)
        self.direction = direction
        self.static_fallback = static_fallback
        self.absolute_tolerance = float(absolute_tolerance)
        self.min_samples = int(min_samples)
        self._window: deque = deque(maxlen=self.window_size)

    def observe(self, value: float) -> None:
        self._window.append(float(value))

    def current_threshold(self) -> Optional[float]:
        if len(self._window) < self.min_samples:
            return self.static_fallback
        ordered = sorted(self._window)
        return percentile(ordered, self.percentile_value) + self.absolute_tolerance

    def evaluate(self, value: float) -> ThresholdResult:
        threshold = self.current_threshold()
        if threshold is None:
            threshold = float(value) + self.absolute_tolerance
        if self.direction == 'above':
            breached = value > threshold + 1e-12
        else:
            breached = value < threshold - 1e-12
        return ThresholdResult(
            metric_name=self.metric_name,
            value=float(value),
            threshold=float(threshold),
            breached=breached,
            direction=self.direction,
            sample_count=len(self._window),
            percentile=self.percentile_value,
        )

    def stats(self) -> Dict[str, Any]:
        if not self._window:
            return {'metric_name': self.metric_name, 'count': 0}
        ordered = sorted(self._window)
        return {
            'metric_name': self.metric_name,
            'count': len(self._window),
            'min': ordered[0],
            'max': ordered[-1],
            'mean': statistics.mean(ordered),
            'threshold': self.current_threshold(),
        }

    def reset(self) -> None:
        self._window.clear()


class AdaptiveConfig:
    """Adaptive batch size / timeout derived from observed latency P95."""

    DEFAULT_BOUNDS = {
        'batch_size': (10, 1000),
        'timeout': (1.0, 300.0),
    }

    def __init__(self, initial_batch_size: int = 100, initial_timeout: float = 30.0,
                 window_size: int = 100, latency_pctl: float = 95.0,
                 min_batch_size: int = 10, max_batch_size: int = 1000,
                 min_timeout: float = 1.0, max_timeout: float = 300.0):
        self.window: deque = deque(maxlen=window_size)
        self.latency_pctl = float(latency_pctl)
        self.min_batch_size = int(min_batch_size)
        self.max_batch_size = int(max_batch_size)
        self.min_timeout = float(min_timeout)
        self.max_timeout = float(max_timeout)
        self.batch_size = int(initial_batch_size)
        self.timeout = float(initial_timeout)
        self.adjustment_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def record_latency(self, latency: float) -> None:
        self.window.append(float(latency))

    def _p95(self) -> Optional[float]:
        if not self.window:
            return None
        return percentile(sorted(self.window), self.latency_pctl)

    def _clip_batch(self, value: float) -> int:
        return max(self.min_batch_size, min(self.max_batch_size, int(round(value))))

    def _clip_timeout(self, value: float) -> float:
        return max(self.min_timeout, min(self.max_timeout, round(value, 3)))

    def adjust(self) -> Dict[str, Any]:
        """Recompute batch size / timeout from recent latency percentiles.

        Heuristic (documented, deterministic):
        - p95 latency below 50% of timeout -> there is headroom; increase
          batch size by 20% (throughput up), keep timeout.
        - p95 latency above 90% of timeout -> risk of timeouts; decrease
          batch size by 30% and raise timeout by 25% (reliability up).
        - otherwise: keep current values (stable zone).
        Values are clipped to configured bounds and each change is recorded
        in the adjustment history.
        """
        p95 = self._p95()
        if p95 is None:
            return {'adjusted': False, 'reason': 'no_data',
                    'batch_size': self.batch_size, 'timeout': self.timeout}

        old_batch, old_timeout = self.batch_size, self.timeout
        if p95 < 0.5 * self.timeout:
            self.batch_size = self._clip_batch(self.batch_size * 1.2)
            reason = 'headroom_increase_batch'
        elif p95 > 0.9 * self.timeout:
            self.batch_size = self._clip_batch(self.batch_size * 0.7)
            self.timeout = self._clip_timeout(self.timeout * 1.25)
            reason = 'pressure_reduce_batch_raise_timeout'
        else:
            reason = 'stable'

        entry = {
            'adjusted': reason != 'stable',
            'reason': reason,
            'p95': round(p95, 4),
            'old_batch_size': old_batch,
            'new_batch_size': self.batch_size,
            'old_timeout': old_timeout,
            'new_timeout': self.timeout,
            'sample_count': len(self.window),
            'timestamp': datetime.utcnow().isoformat(),
        }
        self.adjustment_history.append(entry)
        return entry

    def get_config(self) -> Dict[str, Any]:
        return {'batch_size': self.batch_size, 'timeout': self.timeout}

    def stats(self) -> Dict[str, Any]:
        p95 = self._p95()
        return {
            'sample_count': len(self.window),
            'latency_p95': round(p95, 4) if p95 is not None else None,
            'batch_size': self.batch_size,
            'timeout': self.timeout,
            'adjustments': len(self.adjustment_history),
        }


class CooldownController:
    """Cooldown gate: suppresses state changes until a quiet period elapses.

    Used to avoid oscillation - after a change is applied, further changes
    for the same channel are blocked for ``cooldown_seconds`` unless
    ``force`` is used.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.cooldown_seconds = float(cooldown_seconds)
        self._last_change: Dict[str, datetime] = {}
        self._change_counts: Dict[str, int] = {}

    def _now(self) -> datetime:
        return datetime.utcnow()

    def is_ready(self, channel: str, now: Optional[datetime] = None) -> bool:
        now = now or self._now()
        last = self._last_change.get(channel)
        if last is None:
            return True
        return (now - last).total_seconds() >= self.cooldown_seconds

    def remaining(self, channel: str, now: Optional[datetime] = None) -> float:
        now = now or self._now()
        last = self._last_change.get(channel)
        if last is None:
            return 0.0
        return max(0.0, self.cooldown_seconds - (now - last).total_seconds())

    def try_change(self, channel: str, now: Optional[datetime] = None,
                   force: bool = False) -> bool:
        """Attempt to register a change on a channel.

        Returns True when the change is allowed (and records it), False when
        the channel is still cooling down.
        """
        if not force and not self.is_ready(channel, now=now):
            return False
        now = now or self._now()
        self._last_change[channel] = now
        self._change_counts[channel] = self._change_counts.get(channel, 0) + 1
        return True

    def change_count(self, channel: str) -> int:
        return self._change_counts.get(channel, 0)

    def reset(self, channel: Optional[str] = None) -> None:
        if channel is None:
            self._last_change.clear()
            self._change_counts.clear()
        else:
            self._last_change.pop(channel, None)
            self._change_counts.pop(channel, None)


@dataclass
class ContextRule:
    """Maps a context predicate to a strategy name."""

    name: str
    predicate: Callable[[Dict[str, Any]], bool]
    strategy: str
    priority: int = 0


class AdaptiveStrategySelector:
    """Selects a strategy based on context rules (highest priority wins)."""

    def __init__(self, default_strategy: str = 'default'):
        self.default_strategy = default_strategy
        self.rules: List[ContextRule] = []
        self._selection_counts: Dict[str, int] = {}

    def add_rule(self, name: str, strategy: str,
                 predicate: Callable[[Dict[str, Any]], bool],
                 priority: int = 0) -> ContextRule:
        rule = ContextRule(name=name, predicate=predicate, strategy=strategy,
                           priority=priority)
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)
        return rule

    def select(self, context: Dict[str, Any]) -> str:
        for rule in self.rules:
            try:
                if rule.predicate(context):
                    self._selection_counts[rule.strategy] = \
                        self._selection_counts.get(rule.strategy, 0) + 1
                    return rule.strategy
            except Exception:
                logger.warning("Rule %s raised; skipping", rule.name)
        self._selection_counts[self.default_strategy] = \
            self._selection_counts.get(self.default_strategy, 0) + 1
        return self.default_strategy

    def selection_counts(self) -> Dict[str, int]:
        return dict(self._selection_counts)
