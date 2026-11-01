"""
V28.5 — API Versioning & Deprecation Manager (stdlib-only)

Provides:
- :class:`APIVersionManager`: version parse (v1/v2), version routing matrix
- Deprecation metadata: ``Deprecation`` / ``Sunset`` / ``Link`` headers
- Sunset date checking (past / imminent / future)
- Migration note generator (v1 -> v2 field/endpoint mapping)

Version: V28.5
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "VersioningError",
    "UnknownVersionError",
    "VersionInfo",
    "RouteVersion",
    "DeprecationInfo",
    "APIVersionManager",
]

_VERSION_RE = re.compile(r"^v(\d+)$", re.IGNORECASE)


class VersioningError(Exception):
    """Base error for versioning module."""


class UnknownVersionError(VersioningError):
    """Raised when a version string is not registered."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VersionInfo:
    """Metadata for one API version."""

    version: str                      # canonical form, e.g. "v1"
    status: str = "stable"            # stable | deprecated | retired
    released_on: Optional[date] = None
    deprecated_on: Optional[date] = None
    sunset_on: Optional[date] = None
    replacement: Optional[str] = None
    migration_note: Optional[str] = None

    def __post_init__(self) -> None:
        self.version = normalize_version(self.version)

    @property
    def is_deprecated(self) -> bool:
        return self.status == "deprecated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "released_on": self.released_on.isoformat() if self.released_on else None,
            "deprecated_on": self.deprecated_on.isoformat() if self.deprecated_on else None,
            "sunset_on": self.sunset_on.isoformat() if self.sunset_on else None,
            "replacement": self.replacement,
            "migration_note": self.migration_note,
        }


@dataclass
class RouteVersion:
    """One row of the route versioning matrix."""

    endpoint: str                     # e.g. "/users"
    method: str
    version: str                      # canonical "v1"/"v2"
    handler: Any = None
    notes: str = ""

    def __post_init__(self) -> None:
        self.method = self.method.upper()
        self.version = normalize_version(self.version)

    def key(self) -> Tuple[str, str, str]:
        return (self.endpoint, self.method, self.version)


@dataclass
class DeprecationInfo:
    """Deprecation metadata for one version."""

    version: str
    deprecated_on: Optional[date]
    sunset_on: date
    replacement: str
    reason: str = ""

    def __post_init__(self) -> None:
        self.version = normalize_version(self.version)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_version(raw: str) -> Tuple[int, str]:
    """Parse 'v1'/'V1'/'1' into (major, canonical). Raises on garbage."""
    if raw is None:
        raise VersioningError("version is required")
    text = str(raw).strip().lower()
    if not text:
        raise VersioningError("version is required")
    m = _VERSION_RE.match(text)
    if m:
        return int(m.group(1)), f"v{int(m.group(1))}"
    if text.isdigit():
        return int(text), f"v{int(text)}"
    raise VersioningError(f"cannot parse version {raw!r} (expected 'v1'/'v2' style)")


def normalize_version(raw: str) -> str:
    return parse_version(raw)[1]


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class APIVersionManager:
    """Route versioning matrix + deprecation policy + migration notes."""

    DEFAULT_DEPRECATION_WINDOW_DAYS = 180

    def __init__(self, today: Optional[date] = None) -> None:
        self._versions: Dict[str, VersionInfo] = {}
        self._matrix: Dict[Tuple[str, str, str], RouteVersion] = {}
        self._deprecations: Dict[str, DeprecationInfo] = {}
        self._field_renames: Dict[Tuple[str, str], Dict[str, str]] = {}
        self._today_getter: Callable[[], date] = (lambda: today) if today else date.today
        self._today_fixed = today

    # -- versions ---------------------------------------------------------------

    def register_version(
        self,
        version: str,
        status: str = "stable",
        released_on: Optional[date] = None,
    ) -> VersionInfo:
        canonical = normalize_version(version)
        info = VersionInfo(
            version=canonical,
            status=status,
            released_on=released_on or self._today(),
        )
        self._versions[canonical] = info
        return info

    def versions(self) -> List[VersionInfo]:
        return sorted(self._versions.values(), key=lambda info: info.version)

    def version(self, version: str) -> VersionInfo:
        canonical = normalize_version(version)
        if canonical not in self._versions:
            raise UnknownVersionError(f"unknown version {canonical!r}")
        return self._versions[canonical]

    def is_supported(self, version: str) -> bool:
        canonical = normalize_version(version)
        info = self._versions.get(canonical)
        return info is not None and info.status != "retired"

    # -- matrix ----------------------------------------------------------------

    def map_route(
        self,
        endpoint: str,
        method: str,
        version: str,
        handler: Any = None,
        notes: str = "",
    ) -> RouteVersion:
        rv = RouteVersion(endpoint=endpoint, method=method, version=version,
                          handler=handler, notes=notes)
        self._matrix[rv.key()] = rv
        return rv

    def get_route(self, endpoint: str, method: str, version: str) -> Optional[RouteVersion]:
        rv = self._matrix.get((endpoint, method.upper(), normalize_version(version)))
        return rv

    def versions_for_endpoint(self, endpoint: str, method: str) -> List[str]:
        found = {
            rv.version
            for (ep, m, ver), rv in self._matrix.items()
            if ep == endpoint and m == method.upper()
        }
        return sorted(found)

    def matrix_rows(self) -> List[RouteVersion]:
        return list(self._matrix.values())

    def matrix_to_dicts(self) -> List[Dict[str, Any]]:
        return [
            {
                "endpoint": rv.endpoint,
                "method": rv.method,
                "version": rv.version,
                "handler": repr(rv.handler),
                "notes": rv.notes,
            }
            for rv in self._matrix.values()
        ]

    def deprecate(
        self,
        version: str,
        sunset_on: date,
        replacement: str,
        reason: str = "",
        deprecated_on: Optional[date] = None,
    ) -> DeprecationInfo:
        canonical = normalize_version(version)
        info = self.version(canonical)          # raises UnknownVersionError
        if normalize_version(replacement) == canonical:
            raise VersioningError("replacement must differ from deprecated version")
        dep = DeprecationInfo(
            version=canonical,
            deprecated_on=deprecated_on or self._today(),
            sunset_on=sunset_on,
            replacement=normalize_version(replacement),
            reason=reason,
        )
        self._deprecations[canonical] = dep
        info.status = "deprecated"
        info.deprecated_on = dep.deprecated_on
        info.sunset_on = sunset_on
        info.replacement = dep.replacement
        return dep

    # -- deprecation headers / sunset -------------------------------------------

    def deprecation_headers(self, version: str) -> Dict[str, str]:
        """Headers to attach when serving a deprecated version; {} if current."""
        canonical = normalize_version(version)
        dep = self._deprecations.get(canonical)
        if dep is None:
            return {}
        headers: Dict[str, str] = {
            "Deprecation": "true",
            "Sunset": dep.sunset_on.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Link": f'<{dep.replacement}>; rel="successor-version"',
        }
        if dep.deprecated_on is not None:
            headers["X-Deprecated-On"] = dep.deprecated_on.isoformat()
        return headers

    def sunset_status(self, version: str) -> str:
        """One of: 'unknown' | 'scheduled' | 'imminent' | 'sunset'."""
        canonical = normalize_version(version)
        dep = self._deprecations.get(canonical)
        if dep is None:
            return "unknown"
        today = self._today()
        days_left = (dep.sunset_on - today).days
        if days_left < 0:
            return "sunset"
        if days_left <= 30:
            return "imminent"
        return "scheduled"

    def days_until_sunset(self, version: str) -> Optional[int]:
        dep = self._deprecations.get(normalize_version(version))
        if dep is None:
            return None
        return (dep.sunset_on - self._today()).days

    # -- migration notes ----------------------------------------------------------

    def register_field_rename(
        self, version_from: str, version_to: str, mapping: Dict[str, str]
    ) -> None:
        canonical_from = normalize_version(version_from)
        canonical_to = normalize_version(version_to)
        key = (canonical_from, canonical_to)
        bucket = self._field_renames.setdefault(key, {})
        bucket.update(mapping)

    def migration_note(self, version_from: str, version_to: str) -> Dict[str, Any]:
        """Generate a migration note between two registered versions."""
        from_v = normalize_version(version_from)
        to_v = normalize_version(version_to)
        if from_v not in self._versions:
            raise UnknownVersionError(f"unknown version {from_v!r}")
        if to_v not in self._versions:
            raise UnknownVersionError(f"unknown version {to_v!r}")
        renames = dict(self._field_renames.get((from_v, to_v), {}))
        missing = [rv for rv in self._matrix.values() if rv.version == from_v and self.get_route(rv.endpoint, rv.method, to_v) is None]
        return {
            "from_version": from_v,
            "to_version": to_v,
            "status": "available",
            "field_renames": renames,
            "endpoints_removed_in_target": [
                {"endpoint": rv.endpoint, "method": rv.method} for rv in missing
            ],
            "steps": [
                f"1. Inventory all calls to {from_v} endpoints.",
                f"2. Apply field renames: "
                + (", ".join(f"{k} -> {v}" for k, v in renames.items()) or "(none)"),
                f"3. Re-test against {to_v} on staging.",
                f"4. Switch clients to {to_v}; keep {from_v} until sunset"
                + (f" ({self._deprecations[from_v].sunset_on.isoformat()})" if from_v in self._deprecations else ""),
            ],
            "generated_on": self._today().isoformat(),
        }

    # -- internals ---------------------------------------------------------------

    def _today(self) -> date:
        return self._today_getter()
