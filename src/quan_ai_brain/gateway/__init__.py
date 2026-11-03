"""V28 — Enterprise Integration & API Gateway (in-process, stdlib-only).

Modules:
- api_gateway.py  (M1) — in-process API gateway simulator
- connectors.py   (M2) — mock enterprise connectors + circuit breaker
- message_queue.py(M3) — in-memory message broker
- webhooks.py     (M4) — webhook dispatcher with HMAC signing + retry/DLQ
- versioning.py   (M5) — API version manager (parse/matrix/deprecation)

Scope: simulation only — no real network, no external services.
"""

from quan_ai_brain.gateway.api_gateway import (
    APIGateway,
    APIKeyAuthenticator,
    Request,
    Response,
    ResponseCache,
    Route,
    RouteNotFoundError,
    TokenBucketRateLimiter,
)
from quan_ai_brain.gateway.connectors import (
    ALL_MOCK_CONNECTOR_CLASSES,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    Connector,
    ConnectorError,
    MockM365Connector,
    MockSAPConnector,
    MockSalesforceConnector,
    MockSlackConnector,
)
from quan_ai_brain.gateway.message_queue import (
    BrokerError,
    InMemoryMessageBroker,
    Message,
    Subscription,
)
from quan_ai_brain.gateway.webhooks import (
    DeliveryResult,
    WebhookDispatcher,
    WebhookEndpoint,
    WebhookError,
    compute_signature,
    verify_signature,
)
from quan_ai_brain.gateway.versioning import (
    APIVersionManager,
    UnknownVersionError,
    VersioningError,
)

__all__ = [
    # M1
    "APIGateway",
    "APIKeyAuthenticator",
    "Request",
    "Response",
    "ResponseCache",
    "Route",
    "RouteNotFoundError",
    "TokenBucketRateLimiter",
    # M2
    "ALL_MOCK_CONNECTOR_CLASSES",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "Connector",
    "ConnectorError",
    "MockM365Connector",
    "MockSAPConnector",
    "MockSalesforceConnector",
    "MockSlackConnector",
    # M3
    "BrokerError",
    "InMemoryMessageBroker",
    "Message",
    "Subscription",
    # M4
    "DeliveryResult",
    "WebhookDispatcher",
    "WebhookEndpoint",
    "WebhookError",
    "compute_signature",
    "verify_signature",
    # M5
    "APIVersionManager",
    "UnknownVersionError",
    "VersioningError",
]

__version__ = "28.0.0"
