"""
Intelligent Cache Module (V26.5)

This module provides a smart in-memory cache:
- TTL (time-to-live) based expiry
- LRU eviction when capacity is reached
- Adaptive capacity that grows/shrinks based on observed hit rate
- Prefetch hooks to warm keys before they are requested
- Invalidation by exact key or key prefix
- Hit/miss/eviction statistics

All behaviour is deterministic, stdlib-only and fully in-memory (simulated).
No network access, no Redis, no production side effects.

Version: V26.5
Author: QUAN AI BRAIN Team
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with expiry tracking."""

    key: str
    value: Any
    expires_at: Optional[float] = None  # monotonic clock seconds
    created_at: float = field(default_factory=time.monotonic)
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'hit_count': self.hit_count,
            'metadata': self.metadata,
        }


@dataclass
class CacheStats:
    """Running hit/miss/eviction statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    sets: int = 0
    deletes: int = 0
    invalidations: int = 0
    prefetches: int = 0
    capacity_adjustments: int = 0

    @property
    def total_lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_lookups == 0:
            return 0.0
        return self.hits / self.total_lookups

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'expirations': self.expirations,
            'sets': self.sets,
            'deletes': self.deletes,
            'invalidations': self.invalidations,
            'prefetches': self.prefetches,
            'capacity_adjustments': self.capacity_adjustments,
            'total_lookups': self.total_lookups,
            'hit_rate': round(self.hit_rate, 4),
        }


class TTLIndex:
    """Tracks expiry times per key for O(1) removal and scanning."""

    def __init__(self):
        self._expiry: Dict[str, float] = {}

    def add(self, key: str, expires_at: Optional[float]) -> None:
        if expires_at is None:
            self._expiry.pop(key, None)
        else:
            self._expiry[key] = expires_at

    def remove(self, key: str) -> None:
        self._expiry.pop(key, None)

    def get(self, key: str) -> Optional[float]:
        return self._expiry.get(key)

    def keys(self) -> List[str]:
        return list(self._expiry.keys())

    def due_keys(self, now: Optional[float] = None) -> List[str]:
        now = time.monotonic() if now is None else now
        return [k for k, exp in self._expiry.items() if now >= exp]

    def __len__(self) -> int:
        return len(self._expiry)


class IntelligentCache:
    """In-memory cache with TTL + LRU + adaptive capacity + prefetch hooks.

    Constructor parameters accept callables so tests can control the clock:
    - ``clock``: zero-arg callable returning current time in seconds
      (defaults to ``time.monotonic``).
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300.0,
                 name: str = 'default',
                 adaptive_capacity: bool = True,
                 min_size: int = 10, max_allowed_size: int = 10000,
                 grow_threshold: float = 0.85, shrink_threshold: float = 0.40,
                 grow_factor: float = 1.5, shrink_factor: float = 0.5,
                 adjustment_interval: int = 50,
                 clock: Optional[Callable[[], float]] = None,
                 loader: Optional[Callable[[str], Any]] = None,
                 prefetch_loader: Optional[Callable[[List[str]], Any]] = None):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.name = name
        self.max_size = int(max_size)
        self.ttl_seconds = float(ttl_seconds)
        self.adaptive_capacity = bool(adaptive_capacity)
        self.min_size = int(min_size)
        self.max_allowed_size = int(max_allowed_size)
        self.grow_threshold = float(grow_threshold)
        self.shrink_threshold = float(shrink_threshold)
        self.grow_factor = float(grow_factor)
        self.shrink_factor = float(shrink_factor)
        self.adjustment_interval = int(adjustment_interval)
        self._clock = clock or time.monotonic
        self._loader = loader
        self._prefetch_loader = prefetch_loader
        self._entries: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._ttl_index = TTLIndex()
        self.stats = CacheStats()
        self._lookups_since_adjustment = 0
        self.capacity_history: List[Dict[str, Any]] = []
        self.prefetch_keys: List[str] = []
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None) -> CacheEntry:
        with self._lock:
            now = self._clock()
            expires_at = now + (ttl if ttl is not None else self.ttl_seconds)
            if key in self._entries:
                old = self._entries.pop(key)
                self._ttl_index.remove(key)
                del old  # replaced below
            elif len(self._entries) >= self.max_size:
                self._evict_lru()
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                created_at=now,
                metadata=metadata or {},
            )
            self._entries[key] = entry
            self._ttl_index.add(key, entry.expires_at)
            self.stats.sets += 1
            return entry

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Clock-aware expiry check (uses the injected clock, not global time)."""
        if entry.expires_at is None:
            return False
        return self._clock() >= entry.expires_at

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            self._lookups_since_adjustment += 1
            entry = self._entries.get(key)
            if entry is None:
                self.stats.misses += 1
                self._maybe_adjust_capacity()
                value = self._load_through(key)
                if value is not None:
                    self.set(key, value)
                return value if value is not None else default
            if self._is_expired(entry):
                self._remove_entry(key)
                self.stats.expirations += 1
                self.stats.misses += 1
                self._maybe_adjust_capacity()
                value = self._load_through(key)
                if value is not None:
                    self.set(key, value)
                return value if value is not None else default
            # LRU refresh
            self._entries.move_to_end(key)
            entry.hit_count += 1
            self.stats.hits += 1
            self._maybe_adjust_capacity()
            return entry.value

    def _load_through(self, key: str) -> Any:
        if self._loader is None:
            return None
        try:
            return self._loader(key)
        except Exception as exc:
            logger.warning("Loader failed for key %s: %s", key, exc)
            return None

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._entries:
                self._remove_entry(key)
                self.stats.deletes += 1
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._entries.get(key)
            return entry is not None and not self._is_expired(entry)

    def _remove_entry(self, key: str) -> None:
        self._entries.pop(key, None)
        self._ttl_index.remove(key)

    def _evict_lru(self) -> Optional[CacheEntry]:
        """Evict the least-recently-used entry (must hold the lock)."""
        if not self._entries:
            return None
        key, entry = self._entries.popitem(last=False)
        self._ttl_index.remove(key)
        self.stats.evictions += 1
        logger.debug("Evicted LRU key %s", key)
        return entry

    def evict_expired(self) -> List[str]:
        """Remove all expired entries; returns the removed keys."""
        with self._lock:
            now = self._clock()
            due = [k for k, e in self._entries.items() if e.expires_at is not None
                   and now >= e.expires_at]
            for key in due:
                self._remove_entry(key)
                self.stats.expirations += 1
            return due

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------
    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._entries:
                self._remove_entry(key)
                self.stats.invalidations += 1
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate every key starting with ``prefix``; returns count."""
        with self._lock:
            keys = [k for k in self._entries if k.startswith(prefix)]
            for key in keys:
                self._remove_entry(key)
                self.stats.invalidations += 1
            return len(keys)

    def keys(self, prefix: Optional[str] = None) -> List[str]:
        with self._lock:
            keys = [k for k, e in self._entries.items() if not e.is_expired]
        if prefix is not None:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, key: str) -> bool:
        return self.exists(key)

    # ------------------------------------------------------------------
    # Prefetch
    # ------------------------------------------------------------------
    def register_prefetch_hook(self, loader: Callable[[List[str]], Any]) -> None:
        """Register a hook invoked with the list of keys to warm."""
        self._prefetch_loader = loader

    def prefetch(self, keys: List[str]) -> int:
        """Warm the given keys using the prefetch hook (or per-key loader).

        Returns the number of keys actually stored.
        """
        if not keys:
            return 0
        stored = 0
        with self._lock:
            self.prefetch_keys.extend(keys)
        if self._prefetch_loader is not None:
            values = self._prefetch_loader(list(keys))
            if isinstance(values, dict):
                iterable = values.items()
            elif isinstance(values, (list, tuple)) and len(values) == len(keys):
                iterable = zip(keys, values)
            else:
                iterable = []
            for key, value in iterable:
                self.set(key, value)
                stored += 1
                self.stats.prefetches += 1
        else:
            for key in keys:
                value = self._load_through(key)
                if value is not None:
                    self.set(key, value)
                    stored += 1
                    self.stats.prefetches += 1
        return stored

    # ------------------------------------------------------------------
    # Adaptive capacity
    # ------------------------------------------------------------------
    def _maybe_adjust_capacity(self) -> None:
        """Grow/shrink capacity based on hit rate (must hold the lock)."""
        if not self.adaptive_capacity:
            return
        if self._lookups_since_adjustment < self.adjustment_interval:
            return
        self._lookups_since_adjustment = 0
        hit_rate = self.stats.hit_rate
        if self.stats.total_lookups == 0:
            return
        old_size = self.max_size
        if hit_rate >= self.grow_threshold and self.max_size < self.max_allowed_size:
            self.max_size = min(self.max_allowed_size,
                                int(self.max_size * self.grow_factor))
        elif hit_rate < self.shrink_threshold and self.max_size > self.min_size:
            self.max_size = max(self.min_size, int(self.max_size * self.shrink_factor))
        else:
            return
        self.stats.capacity_adjustments += 1
        self.capacity_history.append({
            'old_size': old_size,
            'new_size': self.max_size,
            'hit_rate': round(hit_rate, 4),
            'timestamp': datetime.utcnow().isoformat(),
        })
        logger.info("Cache %s capacity %s -> %s (hit_rate=%.2f)",
                    self.name, old_size, self.max_size, hit_rate)

    def force_adjust_capacity(self, hit_rate: Optional[float] = None) -> Dict[str, Any]:
        """Manually trigger a capacity adjustment for a given hit rate."""
        with self._lock:
            if hit_rate is not None:
                self.stats.hits = int(hit_rate * 100)
                self.stats.misses = 100 - self.stats.hits
                self._lookups_since_adjustment = self.adjustment_interval
            else:
                self._lookups_since_adjustment = self.adjustment_interval
            before = self.max_size
            self._maybe_adjust_capacity()
            return {
                'old_size': before,
                'new_size': self.max_size,
                'hit_rate': round(self.stats.hit_rate, 4),
                'adjusted': before != self.max_size,
            }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = self.stats.to_dict()
            stats.update({
                'name': self.name,
                'size': len(self._entries),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
            })
            return stats

    def reset_stats(self) -> None:
        with self._lock:
            self.stats = CacheStats()
            self._lookups_since_adjustment = 0

    def clear(self) -> int:
        """Remove all entries; returns the number removed."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._ttl_index = TTLIndex()
            return count
