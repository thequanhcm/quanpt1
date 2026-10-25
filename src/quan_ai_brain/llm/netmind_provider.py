"""NetMind cloud provider for QUAN AI BRAIN (GLM-5.3 family via Viettel AI Gateway).

Sprint 1 — GLM-5.3 NetMind Provider Integration (approved D2, 2026-10-25).

Design contract (mirrors LLMProvider/OllamaClient conventions):
- Standard library only (urllib.request + ssl). No third-party dependencies.
- Fail-closed by default: NETMIND_EXTERNAL_DATA_ALLOWED=false blocks every request
  with NETMIND_DISABLED (owner consent first — no data ever leaves PC Core silently).
- API key is read from the NETMIND_API_KEY environment variable at call time.
  It is NEVER accepted as a constructor argument, NEVER stored on the instance,
  NEVER printed, logged, or persisted. Redaction runs on every outbound error path.
- Routing decisions are written to the append-only AuditLogger (metadata only:
  provider, model, latency, token counts — never prompt content).
- Data-minimization: outbound payload contains only the messages needed for the
  request. No workspace paths, no secrets (redact_text applied defensively).
- Transparent degradation: network/HTTP failures return structured LLMResponse with
  success=False; fallback to mock is the CALLER's explicit decision (never automatic
  here) so a mock answer can never masquerade as a real GLM-5.3 reply.

Verified against the live gateway (Sprint 0/1 probes, 2026-10-25):
- Catalog (GET /models, HTTP 200): MiniMax/MiniMax-M3, MiniMax/MiniMax-M3-VIP,
  MiniMax/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B-FP8, Qwen/Qwen3.5-122B-A10B-FP8,
  zai-org/GLM-5.3-Flash.  zai-org/GLM-5.3 and zai-org/GLM-5.3-FlashX are NOT served
  to this account -> both tiers map to GLM-5.3-Flash by default.
- Default reasoning burns tokens silently; {"reasoning_effort": "low"} disables it
  (verified: reasoning_tokens 60 -> 0, correct Vietnamese answer in ~0.2s).
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Iterator

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.llm.models import LLMRequest, LLMResponse, ModelInfo

DEFAULT_NETMIND_BASE_URL = "https://stream-netmind.viettel.vn/aigw/ai/v1"
NETMIND_CHAT_MODEL = "zai-org/GLM-5.3-Flash"
NETMIND_DEEP_REASONING_MODEL = "Qwen/Qwen3.5-122B-A10B-FP8"

# Sprint 2 (approved by owner 2026-10-25): deep reasoning tier.
# Probe evidence: Qwen3.5-122B ALWAYS reasons (reasoning_effort param has no
# effect); with max_tokens=2500 it completed in 22.0s (2255 reasoning + 72
# content tokens, finish_reason=stop) vs empty answers at 200/900 budgets.
DEEP_REASONING_DEFAULT_MAX_TOKENS = 2500
DEEP_REASONING_EFFORT_NONE = None  # param is ignored by this model; send nothing

CHAT_MODELS = (NETMIND_CHAT_MODEL, NETMIND_DEEP_REASONING_MODEL)

# Model IDs excluded from the reasoning_effort parameter (verified no-effect).
_MODELS_IGNORE_REASONING_EFFORT = frozenset({NETMIND_DEEP_REASONING_MODEL})

_CATALOG_MODELS = [
    ModelInfo(
        name=NETMIND_CHAT_MODEL,
        tag=NETMIND_CHAT_MODEL,
        size_bytes=0,
        modified_at="",
        digest="",
        details={
            "provider": "netmind",
            "kind": "chat",
            "serves_tiers": ["fast", "reasoning"],
            "catalog_verified": "2026-10-25",
        },
    ),
    ModelInfo(
        name=NETMIND_DEEP_REASONING_MODEL,
        tag=NETMIND_DEEP_REASONING_MODEL,
        size_bytes=0,
        modified_at="",
        digest="",
        details={
            "provider": "netmind",
            "kind": "deep_reasoning",
            "serves_tiers": ["deep"],
            "always_reasons": True,
            "default_max_tokens": DEEP_REASONING_DEFAULT_MAX_TOKENS,
            "catalog_verified": "2026-10-25",
        },
    ),
]


class NetMindProvider:
    """Cloud LLM provider for the NetMind gateway. Fail-closed, redacted, audited."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,  # Reduced from 30.0 for faster fail (chat timeout)
        max_retries: int = 1,
        reasoning_effort: str | None = "low",
        external_data_allowed: bool | None = None,
        audit_logger: Any = None,
    ) -> None:
        # NOTE: Sprint 2 verified (E2E 2026-10-25): the DEFAULT gateway serves the
        # verified model IDs. NETMIND_DESKTOP_LLM_BASE_URL points at a different
        # LiteLLM endpoint that returns 404 for zai-org/GLM-5.3-Flash — it must
        # NOT override the verified default. Only NETMIND_BASE_URL may override.
        self.base_url = (base_url or os.environ.get("NETMIND_BASE_URL") or DEFAULT_NETMIND_BASE_URL).rstrip("/")
        self.default_timeout = max(1.0, min(float(timeout), 300.0))
        self.max_retries = max(0, min(int(max_retries), 3))
        self.reasoning_effort = reasoning_effort
        if external_data_allowed is None:
            raw = os.environ.get("NETMIND_EXTERNAL_DATA_ALLOWED", "false")
            external_data_allowed = str(raw).strip().lower() in ("1", "true", "yes", "on")
        self.external_data_allowed = bool(external_data_allowed)
        self.last_routing: dict[str, Any] | None = None
        # Optional AuditLogger (quan_ai_brain.core.audit.AuditLogger) — metadata only.
        self._audit = audit_logger

    # ------------------------------------------------------------------ key
    @staticmethod
    def _get_api_key() -> str:
        """Read the API key from the environment at call time. Never cached."""
        key = os.environ.get("NETMIND_API_KEY", "") or os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")
        return key.strip()

    # ------------------------------------------------------------- availability
    def is_online(self, timeout: float = 2.0) -> bool:
        """True when data export is allowed, a key is present, and /models answers."""
        if not self.external_data_allowed:
            return False
        if not self._get_api_key():
            return False
        try:
            self.list_models(timeout=timeout)
            return True
        except Exception:
            return False

    def health(self, timeout: float = 6.0) -> dict[str, Any]:
        """Diagnostic snapshot. Reports configured truthfully even when disabled."""
        key_present = bool(self._get_api_key())
        catalog_ok = False
        models: list[str] = []
        error: str | None = None
        if self.external_data_allowed and key_present:
            try:
                infos = self.list_models(timeout=timeout)
                models = [m.name for m in infos]
                catalog_ok = True
            except Exception as exc:  # noqa: BLE001 — diagnostics must not raise
                error = type(exc).__name__
        return {
            "provider": "netmind",
            "base_url": self.base_url,
            "external_data_allowed": self.external_data_allowed,
            "api_key_present": key_present,
            "catalog_reachable": catalog_ok,
            "available_models": models,
            "default_model": NETMIND_CHAT_MODEL,
            "reasoning_effort": self.reasoning_effort,
            "error": error,
            "status": "READY" if catalog_ok else (
                "DISABLED_BY_POLICY" if not self.external_data_allowed else (
                    "NO_API_KEY" if not key_present else "UNREACHABLE"
                )
            ),
        }

    def list_models(self, timeout: float = 6.0) -> list[ModelInfo]:
        """GET {base}/models and map the gateway catalog to ModelInfo entries."""
        data = self._request_json("GET", "/models", timeout=timeout)
        raw = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            raise ValueError("NetMind /models response missing 'data' list")
        infos: list[ModelInfo] = []
        for item in raw:
            if isinstance(item, dict) and item.get("id"):
                infos.append(ModelInfo(name=str(item["id"]), tag=str(item["id"]), details={"provider": "netmind"}))
        return infos or list(_CATALOG_MODELS)

    # ------------------------------------------------------------------ chat
    def stream_chat(
        self,
        request: LLMRequest | str,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        """Stream a chat completion from NetMind as an iterator of structured events.

        Event shapes (dicts, JSON-serializable, prompt-content-free except delta):
          {"type": "meta",    "model": str}                     — first, after gates pass
          {"type": "delta",   "text": str}                      — incremental content
          {"type": "final",   "model": str, "elapsed_ms": float,
           "completion_tokens": int|None, "finish_reason": str|None}
          {"type": "error",   "code": str, "message": str}      — gates or transport failed

        Fail-closed contract (mirrors generate()): owner consent first, then key,
        then model allow-list. Errors are yielded as events — this method never
        raises for network/HTTP/gate failures. A mock fallback is the CALLER's
        decision (never automatic) so a mock can never masquerade as GLM-5.3.
        """
        if isinstance(request, str):
            request = LLMRequest(prompt=request, **kwargs)

        started = time.perf_counter()

        # 1. Owner consent gate — fail-closed.
        if not self.external_data_allowed:
            yield {"type": "error", "code": "NETMIND_DISABLED", "message": (
                "NetMind external data policy flag is disabled (NETMIND_EXTERNAL_DATA_ALLOWED=false). "
                "Set NETMIND_EXTERNAL_DATA_ALLOWED=true only with owner approval."
            )}
            return

        # 2. Key gate.
        key = self._get_api_key()
        if not key:
            yield {"type": "error", "code": "NO_API_KEY", "message": (
                "NETMIND_API_KEY (or HERMES_CUSTOM_NETMIND_API_KEY) is not set in the environment."
            )}
            return

        # 3. Model allow-list.
        model = (request.model or NETMIND_CHAT_MODEL).strip()
        if model not in CHAT_MODELS:
            yield {"type": "error", "code": "MODEL_NOT_IN_NETMIND_CATALOG", "message": (
                f"Model '{model}' is not in the verified NetMind catalog. "
                f"Allowed: {', '.join(CHAT_MODELS)}."
            )}
            return

        # 4. Minimal payload.
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }
        if self.reasoning_effort and model not in _MODELS_IGNORE_REASONING_EFFORT:
            payload["reasoning_effort"] = self.reasoning_effort
        max_tokens = request.metadata.get("max_tokens") if isinstance(request.metadata, dict) else None
        if max_tokens is None and model == NETMIND_DEEP_REASONING_MODEL:
            max_tokens = DEEP_REASONING_DEFAULT_MAX_TOKENS
        if isinstance(max_tokens, int) and 1 <= max_tokens <= 32768:
            payload["max_tokens"] = max_tokens

        yield {"type": "meta", "model": model}

        # 5. Single live-streaming attempt (bounded retries would replay deltas).
        # Deltas are yielded AS THEY ARRIVE (true streaming); partial chunks are
        # discarded only on mid-stream transport failure (truncation must never
        # be presented as a complete answer — caller receives a structured error).
        final_event: dict[str, Any] | None = None
        error_event: dict[str, Any] | None = None
        for event in self._iter_chat_stream_events(
            payload,
            timeout=request.timeout_seconds or self.default_timeout,
        ):
            if event["type"] == "delta":
                yield event
            elif event["type"] == "final":
                final_event = event
            elif event["type"] == "error":
                error_event = event

        if error_event is not None:
            yield error_event
            return

        if final_event is None:
            yield {"type": "error", "code": "STREAM_ENDED_WITHOUT_FINAL", "message": (
                "Gateway closed the stream before a final event arrived."
            )}
            return

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        final_event["elapsed_ms"] = elapsed_ms
        self.last_routing = {
            "provider": "netmind",
            "model": model,
            "reason": "stream",
            "elapsed_ms": elapsed_ms,
            "success": bool(final_event.get("completion_tokens")),
        }
        self._audit_record("llm_routing", self.last_routing)
        yield final_event

    # ------------------------------------------------------------------ chat
    def generate(self, request: LLMRequest | str, **kwargs: Any) -> LLMResponse:
        """Send a chat completion to NetMind. Returns structured LLMResponse.

        Never raises for network/HTTP errors — returns success=False with a redacted
        error code. Raises only ValueError for invalid model names.
        """
        if isinstance(request, str):
            request = LLMRequest(prompt=request, **kwargs)

        started = time.perf_counter()
        self.last_routing = None

        # 1. Owner consent gate — fail-closed.
        if not self.external_data_allowed:
            return self._error_response(
                request, "NETMIND_DISABLED", started,
                "NetMind external data policy is disabled (NETMIND_EXTERNAL_DATA_ALLOWED=false). "
                "Set NETMIND_EXTERNAL_DATA_ALLOWED=true only with owner approval.",
            )

        # 2. Key gate (root-cause config error before model validation).
        key = self._get_api_key()
        if not key:
            return self._error_response(
                request, "NO_API_KEY", started,
                "NETMIND_API_KEY (or HERMES_CUSTOM_NETMIND_API_KEY) is not set in the environment.",
            )

        # 3. Model allow-list — exact catalog IDs only.
        model = (request.model or NETMIND_CHAT_MODEL).strip()
        if model not in CHAT_MODELS:
            return self._error_response(
                request, "MODEL_NOT_IN_NETMIND_CATALOG", started,
                f"Model '{model}' is not in the verified NetMind catalog. Allowed: {', '.join(CHAT_MODELS)}.",
            )

        # 4. Build minimal payload (messages only — nothing else leaves the machine).
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": False,
        }
        if self.reasoning_effort and model not in _MODELS_IGNORE_REASONING_EFFORT:
            payload["reasoning_effort"] = self.reasoning_effort
        max_tokens = request.metadata.get("max_tokens") if isinstance(request.metadata, dict) else None
        if max_tokens is None and model == NETMIND_DEEP_REASONING_MODEL:
            # Verified (Sprint 2 probe): Qwen3.5-122B always reasons (~2255 tokens)
            # before answering; a default budget is REQUIRED or it returns empty.
            max_tokens = DEEP_REASONING_DEFAULT_MAX_TOKENS
        if isinstance(max_tokens, int) and 1 <= max_tokens <= 32768:
            payload["max_tokens"] = max_tokens

        # 5. Bounded retry loop.
        attempts = self.max_retries + 1
        last_code, last_msg = "UNKNOWN", "No attempt was made"
        for attempt in range(1, attempts + 1):
            code, msg, data = self._post_chat(payload, timeout=request.timeout_seconds or self.default_timeout)
            if data is not None:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                choices = data.get("choices") or []
                content = ""
                finish_reason = None
                if choices and isinstance(choices[0], dict):
                    message = choices[0].get("message") or {}
                    content = message.get("content") or ""
                    finish_reason = choices[0].get("finish_reason")
                usage = data.get("usage") or {}
                response = LLMResponse(
                    text=content,
                    model=data.get("model", model),
                    provider="netmind",
                    is_mock=False,
                    elapsed_ms=elapsed_ms,
                    success=bool(content),
                    error_code=None if content else "EMPTY_CONTENT",
                    error_message=None if content else "Gateway returned an empty completion (reasoning budget may be exhausted).",
                    raw_metadata={
                        "gateway": "netmind",
                        "finish_reason": finish_reason,
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "reasoning_tokens": ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")),
                        "attempt": attempt,
                    },
                )
                self.last_routing = {
                    "provider": "netmind",
                    "model": model,
                    "reason": f"tier={request.metadata.get('tier', 'general') if isinstance(request.metadata, dict) else 'general'}; reasoning_effort={self.reasoning_effort}",
                    "elapsed_ms": elapsed_ms,
                    "attempt": attempt,
                    "success": response.success,
                }
                self._audit_record("llm_routing", self.last_routing)
                return response
            last_code, last_msg = code, msg
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 8))  # capped exponential backoff

        response = self._error_response(request, last_code, started, last_msg)
        self.last_routing = {
            "provider": "netmind",
            "model": model,
            "reason": "all attempts failed",
            "elapsed_ms": response.elapsed_ms,
            "attempts": attempts,
            "success": False,
            "error_code": last_code,
        }
        self._audit_record("llm_routing", self.last_routing)
        return response

    # ------------------------------------------------------------- internals
    def _ssl_context(self) -> ssl.SSLContext:
        return ssl.create_default_context()

    def _post_chat(self, payload: dict[str, Any], timeout: float) -> tuple[str, str, dict[str, Any] | None]:
        """POST /chat/completions once. Returns (error_code, safe_message, data|None)."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._get_api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=max(1.0, float(timeout)), context=self._ssl_context()) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return "INVALID_RESPONSE_TYPE", "Gateway returned non-dictionary JSON", None
            return "", "", data
        except urllib.error.HTTPError as exc:
            try:
                snippet = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001
                snippet = ""
            return f"HTTP_{exc.code}", redact_text(f"Gateway HTTP {exc.code}: {exc.reason} {snippet}"), None
        except TimeoutError as exc:
            return "TIMEOUT", redact_text(f"NetMind gateway request timed out: {exc}"), None
        except (urllib.error.URLError, OSError) as exc:
            return "CONNECTION_ERROR", redact_text(f"NetMind gateway unreachable: {exc}"), None
        except json.JSONDecodeError as exc:
            return "JSON_DECODE_ERROR", redact_text(f"Failed to decode gateway response: {exc}"), None

    def _request_json(self, method: str, path: str, timeout: float) -> dict[str, Any]:
        key = self._get_api_key()
        if not key:
            raise ConnectionError("NETMIND_API_KEY is not set in the environment")
        req = urllib.request.Request(
            self.base_url + path,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def _iter_chat_stream_events(
        self,
        payload: dict[str, Any],
        timeout: float,
    ) -> Iterator[dict[str, Any]]:
        """POST /chat/completions with stream=True. Yields live SSE events.

        Yields {"type":"delta","text":...} as each chunk arrives, then exactly one
        {"type":"final", ...} (with completion_tokens and finish_reason) or one
        {"type":"error", ...}. Deltas already yielded are NOT re-yielded on error;
        the caller decides whether to discard partial text.
        """
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._get_api_key()}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        completion_tokens: int | None = None
        finish_reason: str | None = None
        saw_content = False
        try:
            with urllib.request.urlopen(req, timeout=max(1.0, float(timeout)), context=self._ssl_context()) as resp:
                ctype = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else ""
                if "text/event-stream" not in ctype:
                    yield {"type": "error", "code": "NOT_EVENT_STREAM", "message": redact_text(
                        f"Gateway did not return an SSE stream (Content-Type: {ctype})"
                    )}
                    return
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "":
                        continue
                    if data_str == "":
                        break
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    choices = event.get("choices") or []
                    if not choices or not isinstance(choices[0], dict):
                        continue
                    choice = choices[0]
                    if choice.get("finish_reason"):
                        finish_reason = str(choice["finish_reason"])
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        saw_content = True
                        completion_tokens = (completion_tokens or 0) + 1
                        yield {"type": "delta", "text": text}
            yield {
                "type": "final",
                "model": payload.get("model", ""),
                "completion_tokens": completion_tokens,
                "finish_reason": finish_reason or ("stop" if saw_content else "empty"),
            }
        except urllib.error.HTTPError as exc:
            try:
                snippet = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001
                snippet = ""
            yield {"type": "error", "code": f"HTTP_{exc.code}", "message": redact_text(
                f"Gateway HTTP {exc.code}: {exc.reason} {snippet}"
            )}
        except TimeoutError as exc:
            yield {"type": "error", "code": "TIMEOUT", "message": redact_text(
                f"NetMind gateway stream timed out: {exc}"
            )}
        except (urllib.error.URLError, OSError) as exc:
            yield {"type": "error", "code": "CONNECTION_ERROR", "message": redact_text(
                f"NetMind gateway unreachable: {exc}"
            )}
        except json.JSONDecodeError as exc:
            yield {"type": "error", "code": "JSON_DECODE_ERROR", "message": redact_text(
                f"Failed to decode gateway stream: {exc}"
            )}

    @staticmethod
    def _error_response(request: LLMRequest, code: str, started: float, message: str) -> LLMResponse:
        return LLMResponse(
            text="",
            model=request.model if isinstance(request, LLMRequest) else str(request),
            provider="netmind",
            is_mock=False,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            success=False,
            error_code=code,
            error_message=message,
        )

    def _audit_record(self, event_type: str, details: dict[str, Any]) -> None:
        """Best-effort metadata-only audit write. Never raises; never logs prompts."""
        if self._audit is None:
            return
        try:
            self._audit.record(event_type, details)
        except Exception:  # noqa: BLE001 — audit failures must never break chat
            pass
