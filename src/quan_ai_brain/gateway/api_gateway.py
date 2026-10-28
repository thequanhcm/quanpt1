"""
V28.1 — API Gateway (in-process, stdlib-only simulation)

Provides:
- Route table: method + path pattern with ``{param}`` placeholders
- Middleware chain: authentication -> rate limiting -> cache -> handler
- Token-bucket rate limiter (per-client, injectable clock)
- Response cache with TTL
- Request/response stats and exception-to-status mapping

IMPORTANT SCOPE NOTE (honesty):
This is an *in-process* gateway simulator for QUAN AI BRAIN. It does NOT open
sockets, does NOT proxy to real upstreams and is NOT a replacement for Kong /
NGINX / FastAPI. Handlers are plain Python callables. Everything is
stdlib-only and deterministic (clocks are injectable for tests).

Version: V28.1
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import itertools
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "GatewayError",
    "RouteNotFoundError",
    "Request",
    "Response",
    "Route",
    "APIKeyAuthenticator",
    "TokenBucketRateLimiter",
    "ResponseCache",
    "APIGateway",
]

_REQ_SEQ = itertools.count(1)


class GatewayError(Exception):
    """Base error for the gateway module."""


class RouteNotFoundError(GatewayError):
    """Raised by explicit route lookups when nothing matches."""


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

@dataclass
class Request:
    """A gateway request (plain dataclass, no HTTP transport involved)."""

    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, Any] = field(default_factory=dict)
    body: Any = None
    client_id: str = "anonymous"
    request_id: str = field(default_factory=lambda: f"req-{next(_REQ_SEQ):08d}")
    created_at: float = field(default_factory=time.time)
    path_params: Dict[str, str] = field(default_factory=dict)
    principal: Any = None

    def __post_init__(self) -> None:
        self.method = self.method.upper()

    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Case-insensitive header lookup."""
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default


@dataclass
class Response:
    """A gateway response."""

    status: int = 200
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)

    def set_header(self, name: str, value: str) -> "Response":
        self.headers[name] = value
        return self

    def clone(self) -> "Response":
        return Response(status=self.status, body=self.body, headers=dict(self.headers))


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

_PARAM_RE = re.compile(r"\{(\w+)\}")


@dataclass
class Route:
    """A single route in the gateway route table."""

    method: str
    pattern: str
    handler: Callable[[Request], Any]
    cache_ttl: float = 0.0
    bypass_rate_limit: bool = False
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _regex: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.method = self.method.upper()
        self._regex = compile_route_pattern(self.pattern)

    def match(self, path: str) -> Optional[Dict[str, str]]:
        m = self._regex.match(path)
        if m is None:
            return None
        return {key: value for key, value in m.groupdict().items()}

    def cache_key(self, request: Request) -> str:
        """Deterministic cache key: method + path + sorted query."""
        if request.query:
            query_repr = "&".join(
                f"{key}={request.query[key]!r}" for key in sorted(request.query)
            )
            return f"{self.method} {self.pattern}?{request.path}?{query_repr}"
        return f"{self.method} {self.pattern}?{request.path}"


def compile_route_pattern(pattern: str):
    """Compile ``/v1/users/{user_id}/orders`` into a regex with named groups."""
    if not pattern.startswith("/"):
        raise GatewayError(f"route pattern must start with '/': {pattern!r}")
    pieces: List[str] = []
    pos = 0
    for m in _PARAM_RE.finditer(pattern):
        pieces.append(re.escape(pattern[pos:m.start()]))
        pieces.append(f"(?P<{m.group(1)}>[^/]+)")
        pos = m.end()
    pieces.append(re.escape(pattern[pos:]))
    return re.compile("^" + "".join(pieces) + "$")


# ---------------------------------------------------------------------------
# Middleware components
# ---------------------------------------------------------------------------

class APIKeyAuthenticator:
    """API-key authenticator (in-memory key registry, no crypto)."""

    API_KEY_HEADER = "X-API-Key"

    def __init__(self) -> None:
        self._keys: Dict[str, Any] = {}

    def register_key(self, api_key: str, principal: Any) -> "APIKeyAuthenticator":
        if not api_key:
            raise GatewayError("api_key must be a non-empty string")
        self._keys[api_key] = principal
        return self

    def revoke_key(self, api_key: str) -> bool:
        return self._keys.pop(api_key, None) is not None

    def authenticate(self, request: Request) -> Optional[Any]:
        key = request.header(self.API_KEY_HEADER)
        if key is None:
            return None
        return self._keys.get(key)


class TokenBucketRateLimiter:
    """Token-bucket rate limiter, one bucket per client.

    ``capacity``     — max burst size (tokens).
    ``refill_rate``  — tokens added per second of elapsed time.
    ``clock``        — injectable monotonic clock (tests use fake clocks).
    """

    def __init__(
        self,
        capacity: float = 10.0,
        refill_rate: float = 1.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if capacity <= 0 or refill_rate < 0:
            raise GatewayError("capacity must be positive; refill_rate must be >= 0")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.clock = clock or time.monotonic
        self._buckets: Dict[str, Tuple[float, float]] = {}  # client -> (tokens, last_ts)
        self.rejected = 0
        self.accepted = 0

    def _refill(self, client_id: str, now: float) -> float:
        tokens, last = self._buckets.get(client_id, (self.capacity, now))
        tokens = min(self.capacity, tokens + (now - last) * self.refill_rate)
        return tokens

    def allow(self, client_id: str, cost: float = 1.0) -> bool:
        """Return True (and consume ``cost`` tokens) if the client may proceed."""
        if client_id not in self._buckets:
            # New client starts with a full bucket.
            self._buckets[client_id] = (self.capacity, self.clock())
        now = self.clock()
        tokens = self._refill(client_id, now)
        allowed = tokens >= cost
        if allowed:
            tokens -= cost
            self.accepted += 1
        else:
            self.rejected += 1
        self._buckets[client_id] = (tokens, now)
        return allowed

    def tokens(self, client_id: str) -> float:
        now = self.clock()
        return self._refill(client_id, now) if client_id in self._buckets else self.capacity


class ResponseCache:
    """TTL response cache (in-memory dict, injectable clock)."""

    def __init__(
        self,
        default_ttl: float = 60.0,
        max_entries: int = 1024,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.default_ttl = float(default_ttl)
        self.max_entries = int(max_entries)
        self.clock = clock or time.monotonic
        self._store: Dict[str, Tuple[float, Response]] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Response]:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        expires_at, response = entry
        if self.clock() >= expires_at:
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return response

    def set(self, key: str, response: Response, ttl: Optional[float] = None) -> None:
        if len(self._store) >= self.max_entries:
            # Simple FIFO eviction of the oldest entry.
            oldest = next(iter(self._store))
            del self._store[oldest]
            self.evictions += 1
        effective_ttl = self.default_ttl if ttl is None else float(ttl)
        self._store[key] = (self.clock() + effective_ttl, response)

    def invalidate(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def __len__(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class APIGateway:
    """In-process API gateway.

    Request pipeline (in order):
      1. route match            -> 404 / 405 on failure
      2. auth middleware        -> 401 on failure
      3. rate limiter           -> 429 when bucket empty
      4. response cache (GET)   -> serve cached response with ``X-Cache: HIT``
      5. handler                -> wrapped into :class:`Response`
      6. cache store            -> for cacheable successful GETs
    """

    def __init__(
        self,
        authenticator: Optional[APIKeyAuthenticator] = None,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        cache: Optional[ResponseCache] = None,
    ) -> None:
        self.authenticator = authenticator
        self.rate_limiter = rate_limiter
        # NOTE: ``is not None`` (not truthiness) — ResponseCache defines
        # __len__, so an empty cache would otherwise be discarded.
        self.cache = cache if cache is not None else ResponseCache(default_ttl=0.0)
        self._routes: List[Route] = []
        self._stats: Dict[str, int] = {
            "requests_total": 0,
            "responses_2xx": 0,
            "responses_4xx": 0,
            "responses_5xx": 0,
            "cache_hits": 0,
            "auth_failures": 0,
            "rate_limited": 0,
            "not_found": 0,
            "method_not_allowed": 0,
        }
        # Maps exception types raised by handlers to HTTP-ish status codes.
        self.exception_status_map: List[Tuple[type, int]] = []

    # -- configuration ------------------------------------------------------

    def add_route(
        self,
        method: str,
        pattern: str,
        handler: Callable[[Request], Any],
        cache_ttl: float = 0.0,
        bypass_rate_limit: bool = False,
        name: Optional[str] = None,
        **metadata: Any,
    ) -> Route:
        route = Route(
            method=method,
            pattern=pattern,
            handler=handler,
            cache_ttl=cache_ttl,
            bypass_rate_limit=bypass_rate_limit,
            name=name,
            metadata=metadata,
        )
        self._routes.append(route)
        return route

    def map_exception(self, exc_type: type, status: int) -> "APIGateway":
        """Map an exception type raised inside handlers to a status code."""
        self.exception_status_map.append((exc_type, status))
        return self

    @property
    def routes(self) -> List[Route]:
        return list(self._routes)

    # -- matching ------------------------------------------------------------

    def match(self, method: str, path: str) -> Tuple[Optional[Route], Dict[str, str]]:
        method = method.upper()
        path_matched_other_method = False
        for route in self._routes:
            params = route.match(path)
            if params is None:
                continue
            if route.method == method:
                return route, params
            path_matched_other_method = True
        self._stats["method_not_allowed" if path_matched_other_method else "not_found"] += 1
        return None, {}

    def require_match(self, method: str, path: str) -> Tuple[Route, Dict[str, str]]:
        route, params = self.match(method, path)
        if route is None:
            raise RouteNotFoundError(f"no route for {method} {path}")
        return route, params

    def handle(self, request: Request) -> Response:
        self._stats["requests_total"] += 1

        route, params, path_conflict = self._match_detailed(request.method, request.path)
        if route is None:
            status = 405 if path_conflict else 404
            return self._error_response(
                status,
                "method_not_allowed" if status == 405 else "not_found",
                f"no handler for {request.method} {request.path}",
            )
        request.path_params = params

        # 2. Authentication middleware
        if self.authenticator is not None:
            principal = self.authenticator.authenticate(request)
            if principal is None:
                self._stats["auth_failures"] += 1
                return self._error_response(
                    401, "unauthorized", "missing or invalid API key"
                )
            request.principal = principal

        # 3. Rate limiting middleware
        if self.rate_limiter is not None and not route.bypass_rate_limit:
            if not self.rate_limiter.allow(request.client_id):
                self._stats["rate_limited"] += 1
                response = self._error_response(
                    429,
                    "rate_limit_exceeded",
                    f"token bucket exhausted for client '{request.client_id}'",
                )
                response.headers["Retry-After"] = "1"
                return response

        # 4. Response cache (GET only)
        cacheable = request.method == "GET" and route.cache_ttl > 0
        cache_key: Optional[str] = None
        if cacheable:
            cache_key = route.cache_key(request)
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                response = cached.clone()
                response.headers["X-Cache"] = "HIT"
                self._count_status(response.status)
                return response

        # 5. Handler
        try:
            result = route.handler(request)
        except Exception as exc:  # noqa: BLE001 — gateway boundary converts to response
            status = self._status_for_exception(exc)
            return self._error_response(
                status,
                "handler_error",
                f"{type(exc).__name__}: {exc}",
            )

        response = self._coerce_response(result)
        if cacheable and response.status == 200 and cache_key is not None:
            self.cache.set(cache_key, response, route.cache_ttl)
        response.headers.setdefault("X-Cache", "MISS" if cacheable else "BYPASS")
        self._count_status(response.status)
        return response

    def handle_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        query: Optional[Dict[str, Any]] = None,
        body: Any = None,
        client_id: str = "anonymous",
    ) -> Response:
        request = Request(
            method=method,
            path=path,
            headers=headers or {},
            query=query or {},
            body=body,
            client_id=client_id,
        )
        return self.handle(request)

    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    # -- internals -------------------------------------------------------------

    def _match_detailed(self, method: str, path: str) -> Tuple[Optional[Route], Dict[str, str], bool]:
        """Return (route, params, path_matched_other_method); updates miss counters."""
        method = method.upper()
        path_matched_other_method = False
        for route in self._routes:
            params = route.match(path)
            if params is None:
                continue
            if route.method == method:
                return route, params, False
            path_matched_other_method = True
        self._stats["method_not_allowed" if path_matched_other_method else "not_found"] += 1
        return None, {}, path_matched_other_method

    def _status_for_exception(self, exc: Exception) -> int:
        for exc_type, status in self.exception_status_map:
            if isinstance(exc, exc_type):
                return status
        return 500

    @staticmethod
    def _coerce_response(result: Any) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
            return Response(status=result[0], body=result[1])
        return Response(status=200, body=result)

    def _error_response(self, status: int, code: str, message: str) -> Response:
        body = {"error": code, "message": message, "status": status}
        self._count_status(status)
        return Response(status=status, body=body, headers={"Content-Type": "application/json"})

    def _count_status(self, status: int) -> None:
        if 200 <= status < 300:
            self._stats["responses_2xx"] += 1
        elif 400 <= status < 500:
            self._stats["responses_4xx"] += 1
        elif status >= 500:
            self._stats["responses_5xx"] += 1
