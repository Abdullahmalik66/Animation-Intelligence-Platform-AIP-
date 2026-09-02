"""Model Gateway: capability-aware, policy-driven, provider-neutral execution.

Owns bounded transient retry, refusal normalisation, error taxonomy, fallback
policy and usage normalisation. Provider adapters only translate native wire
formats into canonical types.

Core independence rule: this module imports no provider SDK and no
provider-named symbols.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol

from .types import (ModelRequest, ModelResponse, StopReason, UsageMetrics)


# --- Capabilities (Workstream 3) --------------------------------------------

class Support(str, Enum):
    SUPPORTED = "Supported"
    UNSUPPORTED = "Unsupported"
    UNKNOWN = "Unknown"
    CONDITIONAL = "Conditional"


@dataclass
class ModelCapabilities:
    """Adapter-declared; never inferred from a model name. Missing = Unknown."""
    text_input: Support = Support.UNKNOWN
    structured_output: Support = Support.UNKNOWN
    json_schema_output: Support = Support.UNKNOWN
    tool_calling: Support = Support.UNKNOWN
    streaming: Support = Support.UNKNOWN
    prompt_caching: Support = Support.UNKNOWN
    system_messages: Support = Support.UNKNOWN
    provider_reported_usage: Support = Support.UNKNOWN
    cache_usage_reporting: Support = Support.UNKNOWN
    refusal_reporting: Support = Support.UNKNOWN
    image_input: Support = Support.UNKNOWN
    local_execution: Support = Support.UNKNOWN
    context_window: Optional[int] = None
    max_output: Optional[int] = None

    def satisfies(self, required: dict[str, Support]) -> tuple[bool, list[str]]:
        gaps = []
        for cap, need in required.items():
            have = getattr(self, cap, Support.UNKNOWN)
            if need == Support.SUPPORTED and have != Support.SUPPORTED:
                gaps.append(f"{cap}={have.value} (need Supported)")
        return (not gaps, gaps)


# --- Error taxonomy (Workstream 7) -------------------------------------------

class ProviderErrorKind(str, Enum):
    AUTHENTICATION_FAILURE = "AuthenticationFailure"
    AUTHORISATION_FAILURE = "AuthorisationFailure"
    RATE_LIMITED = "RateLimited"
    TIMEOUT = "Timeout"
    CONNECTION_FAILURE = "ConnectionFailure"
    PROVIDER_UNAVAILABLE = "ProviderUnavailable"
    INVALID_REQUEST = "InvalidRequest"
    CONTEXT_LIMIT_EXCEEDED = "ContextLimitExceeded"
    UNSUPPORTED_CAPABILITY = "UnsupportedCapability"
    MALFORMED_RESPONSE = "MalformedResponse"
    STRUCTURED_OUTPUT_FAILURE = "StructuredOutputFailure"
    TOOL_CALL_FAILURE = "ToolCallFailure"
    CONTENT_REFUSAL = "ContentRefusal"
    SAFETY_INTERVENTION = "SafetyIntervention"
    CANCELLED = "Cancelled"
    UNKNOWN = "UnknownProviderFailure"


TRANSIENT = {ProviderErrorKind.RATE_LIMITED, ProviderErrorKind.TIMEOUT,
             ProviderErrorKind.CONNECTION_FAILURE, ProviderErrorKind.PROVIDER_UNAVAILABLE}
TERMINAL_NO_RETRY = {ProviderErrorKind.AUTHENTICATION_FAILURE,
                     ProviderErrorKind.AUTHORISATION_FAILURE,
                     ProviderErrorKind.INVALID_REQUEST,
                     ProviderErrorKind.CONTEXT_LIMIT_EXCEEDED,
                     ProviderErrorKind.UNSUPPORTED_CAPABILITY,
                     ProviderErrorKind.CONTENT_REFUSAL,
                     ProviderErrorKind.SAFETY_INTERVENTION,
                     ProviderErrorKind.CANCELLED}


class ProviderError(Exception):
    def __init__(self, kind: ProviderErrorKind, message: str = "",
                 retryable: Optional[bool] = None):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable if retryable is not None else kind in TRANSIENT


# --- Adapter protocol + registry (Workstreams 2, 4) ---------------------------

class ProviderAdapter(Protocol):
    provider_id: str
    model: str
    capabilities: ModelCapabilities

    def invoke(self, request: ModelRequest) -> ModelResponse:
        """Translate to native call and back to canonical ModelResponse.
        Native errors must be raised as ProviderError. Never leak raw payloads
        outside ModelResponse.raw_metadata."""
        ...


class ProviderStatus(str, Enum):
    CONFIGURED = "Configured"
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    MISCONFIGURED = "Misconfigured"
    DISABLED = "Disabled"
    UNKNOWN = "Unknown"


@dataclass
class ProviderDescriptor:
    provider_id: str
    model: str
    status: ProviderStatus
    capabilities: ModelCapabilities
    reason: str = ""


@dataclass
class ProviderRegistry:
    _adapters: dict[str, ProviderAdapter] = field(default_factory=dict)
    _status: dict[str, ProviderStatus] = field(default_factory=dict)

    def register(self, adapter: ProviderAdapter,
                 status: ProviderStatus = ProviderStatus.CONFIGURED) -> None:
        self._adapters[adapter.provider_id] = adapter
        self._status[adapter.provider_id] = status

    def get(self, provider_id: str) -> ProviderAdapter:
        if provider_id not in self._adapters:
            raise ProviderError(ProviderErrorKind.PROVIDER_UNAVAILABLE,
                                f"Provider {provider_id!r} not registered")
        return self._adapters[provider_id]

    def list_available(self) -> list[ProviderDescriptor]:
        return [ProviderDescriptor(a.provider_id, a.model,
                                   self._status[pid], a.capabilities)
                for pid, a in self._adapters.items()]

    def find_compatible(self, required: dict[str, Support]) -> list[ProviderDescriptor]:
        out = []
        for d in self.list_available():
            if d.status in (ProviderStatus.DISABLED, ProviderStatus.MISCONFIGURED):
                continue
            ok, gaps = d.capabilities.satisfies(required)
            if ok:
                out.append(d)
        return out


# --- Selection policy (Workstream 5) ------------------------------------------

@dataclass
class SelectionDecision:
    provider_id: Optional[str]
    model: Optional[str]
    required_capabilities: dict[str, str]
    policy: str
    alternatives_considered: list[str]
    rejected: list[str]
    unknowns: list[str]
    rationale: str


WORKFLOW_REQUIREMENTS: dict[str, dict[str, Support]] = {
    # retrieval loop needs tool calling OR the app-managed loop; structured
    # validators need structured output. Conservative defaults.
    "implementation": {"text_input": Support.SUPPORTED,
                       "structured_output": Support.SUPPORTED},
    "default": {"text_input": Support.SUPPORTED},
}


def select_provider(registry: ProviderRegistry, workflow: str,
                    policy: str = "fixed_provider",
                    fixed: Optional[str] = None,
                    allowlist: Optional[list[str]] = None,
                    local_only: bool = False) -> SelectionDecision:
    """Policy-driven, conservative default (fixed_provider). Runs AFTER the
    animation route is decided — never influences technology choice."""
    required = WORKFLOW_REQUIREMENTS.get(workflow, WORKFLOW_REQUIREMENTS["default"])
    candidates = registry.find_compatible(required)
    considered = [f"{d.provider_id}:{d.model}" for d in registry.list_available()]
    rejected, unknowns = [], []

    def _allowed(d: ProviderDescriptor) -> bool:
        if allowlist and d.provider_id not in allowlist:
            rejected.append(f"{d.provider_id}: not in allowlist")
            return False
        if local_only and d.capabilities.local_execution != Support.SUPPORTED:
            rejected.append(f"{d.provider_id}: not local-only capable")
            return False
        return True

    candidates = [d for d in candidates if _allowed(d)]
    for d in registry.list_available():
        ok, gaps = d.capabilities.satisfies(required)
        if not ok:
            rejected.append(f"{d.provider_id}: {'; '.join(gaps)}")

    chosen: Optional[ProviderDescriptor] = None
    if policy == "fixed_provider" and fixed:
        chosen = next((d for d in candidates if d.provider_id == fixed), None)
        if chosen is None:
            rejected.append(f"{fixed}: fixed provider not compatible/available")
    elif candidates:
        chosen = candidates[0]  # no un-evidenced ranking; registration order

    return SelectionDecision(
        provider_id=chosen.provider_id if chosen else None,
        model=chosen.model if chosen else None,
        required_capabilities={k: v.value for k, v in required.items()},
        policy=policy, alternatives_considered=considered,
        rejected=rejected, unknowns=unknowns,
        rationale="No evidence-based ranking configured; policy + capability "
                  "filter only" if chosen else "No compatible provider")


# --- Gateway (retry / refusal / fallback moved OUT of adapters) ---------------

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_s: float = 0.5


@dataclass
class ModelGateway:
    registry: ProviderRegistry
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    fallback_order: list[str] = field(default_factory=list)

    def run(self, request: ModelRequest, workflow: str = "default",
            policy: str = "fixed_provider",
            fixed: Optional[str] = None,
            allowlist: Optional[list[str]] = None,
            local_only: bool = False) -> tuple[ModelResponse, SelectionDecision]:
        decision = select_provider(self.registry, workflow, policy, fixed,
                                   allowlist, local_only)
        if decision.provider_id is None:
            return ModelResponse(stop_reason=StopReason.ERROR,
                                 error="No compatible provider available: "
                                       + "; ".join(decision.rejected)), decision
        resp = self._invoke_with_retry(decision.provider_id, request)
        if (resp.stop_reason in (StopReason.ERROR, StopReason.TIMEOUT)
                and not resp.refusal):
            for fb in self.fallback_order:
                if fb == decision.provider_id or fb not in [
                        d.provider_id for d in self.registry.list_available()]:
                    continue
                fb_resp = self._invoke_with_retry(fb, request)
                if fb_resp.stop_reason not in (StopReason.ERROR, StopReason.TIMEOUT):
                    fb_resp.fallback_used = True
                    return fb_resp, decision
        return resp, decision

    def _invoke_with_retry(self, provider_id: str, request: ModelRequest) -> ModelResponse:
        adapter = self.registry.get(provider_id)
        attempt = 0
        last: Optional[ProviderError] = None
        while attempt < self.retry.max_attempts:
            attempt += 1
            start = time.monotonic()
            try:
                resp = adapter.invoke(request)
            except ProviderError as exc:
                last = exc
                if exc.kind == ProviderErrorKind.CONTENT_REFUSAL:
                    # Canonical refusal: application state, never retried.
                    return ModelResponse(
                        refusal=True, stop_reason=StopReason.REFUSAL,
                        provider=adapter.provider_id, model=adapter.model,
                        retry_count=attempt - 1,
                        refusal_record={"provider": adapter.provider_id,
                                        "category": "content",
                                        "user_safe_message":
                                            "The model declined this request.",
                                        "retryable": False,
                                        "fallback_allowed": False})
                if not exc.retryable or exc.kind in TERMINAL_NO_RETRY:
                    break
                time.sleep(self.retry.backoff_s * attempt)
                continue
            resp.provider = resp.provider or adapter.provider_id
            resp.model = resp.model or adapter.model
            resp.retry_count = attempt - 1
            if resp.usage.latency_s is None:
                resp.usage.latency_s = time.monotonic() - start
            resp.usage.model_calls = attempt
            return resp
        kind = last.kind.value if last else "unknown"
        stop = StopReason.TIMEOUT if last and last.kind == ProviderErrorKind.TIMEOUT \
            else StopReason.ERROR
        return ModelResponse(stop_reason=stop, provider=provider_id,
                             retry_count=attempt,
                             error=f"{kind}: {last}" if last else "unknown failure",
                             usage=UsageMetrics(model_calls=attempt))
