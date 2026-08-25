"""Fable 5 backend adapter (Workstream 10).

LIVE INTEGRATION STATUS: BLOCKED — no SDK installed in this repository and no
credentials configured. This module implements the full offline contract
(request shaping, stable/dynamic prompt split, refusal handling, retry policy,
usage capture, redaction) against an injected transport, plus a MockTransport
for tests. Activation path: `pip install aip[fable]`, set AIP_FABLE_API_KEY,
pass a real transport built from the verified SDK. Do NOT hard-code request
fields beyond this transport boundary — the transport owns provider specifics.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..types import (SpecialistRequest, SpecialistResponse, StopReason,
                     UsageMetrics)

Transport = Callable[[dict], dict]
"""Takes a provider-neutral request dict, returns a provider-neutral result:
{content, stop_reason, usage:{input_tokens,cache_read_tokens,cache_write_tokens,
output_tokens}, request_id, tool_calls, structured_output, error?}"""

REDACT_KEYS = ("api_key", "authorization", "token", "secret")


def _redact(d: dict) -> dict:
    return {k: ("[REDACTED]" if any(s in k.lower() for s in REDACT_KEYS) else v)
            for k, v in d.items()}


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_s: float = 0.5
    timeout_s: float = 60.0


@dataclass
class FableBackend:
    transport: Optional[Transport] = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    fallback: Optional[Transport] = None

    def run_request(self, req: SpecialistRequest) -> SpecialistResponse:
        if self.transport is None:
            return SpecialistResponse(
                stop_reason=StopReason.ERROR, error=(
                    "Fable live integration BLOCKED: no transport configured "
                    "(SDK not installed / credentials unavailable). "
                    "See docs/migration.md for the activation path."))
        payload = {
            # Stable-first ordering for prompt caching (Workstream 11).
            "system": req.stable_prefix,
            "prefix_hash": req.prefix_hash or hashlib.sha256(
                req.stable_prefix.encode()).hexdigest()[:16],
            "context": req.dynamic_context,
            "state": req.state_projection,
            "user": req.user_request,
            "request_id": req.request_id,
        }
        attempt, last_error = 0, None
        while attempt < self.retry.max_attempts:
            attempt += 1
            start = time.monotonic()
            try:
                raw = self.transport(payload)
            except TimeoutError:
                last_error = "timeout"
                continue  # transient — bounded retry
            except ConnectionError as exc:
                last_error = f"transport: {exc}"
                time.sleep(self.retry.backoff_s * attempt)
                continue
            latency = time.monotonic() - start
            resp = self._parse(raw, latency, attempt)
            if resp.refusal:
                # Application state, NOT transport failure. Never retry identical content.
                return resp
            if resp.stop_reason == StopReason.ERROR and raw.get("retryable"):
                last_error = resp.error
                time.sleep(self.retry.backoff_s * attempt)
                continue
            return resp
        # Retries exhausted → optional fallback (must respect safety policy: not for refusals).
        if self.fallback:
            try:
                raw = self.fallback(payload)
                resp = self._parse(raw, 0.0, attempt)
                resp.fallback_used = True
                return resp
            except Exception as exc:  # noqa: BLE001
                last_error = f"fallback failed: {exc}"
        return SpecialistResponse(stop_reason=StopReason.TIMEOUT
                                  if last_error == "timeout" else StopReason.ERROR,
                                  error=last_error, usage=UsageMetrics(model_calls=attempt))

    @staticmethod
    def _parse(raw: dict, latency: float, calls: int) -> SpecialistResponse:
        stop = raw.get("stop_reason", "end_turn")
        refusal = stop == "refusal"
        usage_raw = raw.get("usage") or {}
        usage = UsageMetrics(
            method="provider_reported" if usage_raw else "estimated_chars_div_4",
            input_tokens=usage_raw.get("input_tokens"),
            cache_read_tokens=usage_raw.get("cache_read_tokens"),
            cache_write_tokens=usage_raw.get("cache_write_tokens"),
            output_tokens=usage_raw.get("output_tokens"),
            latency_s=latency, model_calls=calls)
        try:
            stop_enum = StopReason(stop)
        except ValueError:
            stop_enum = StopReason.END_TURN
        return SpecialistResponse(
            content=raw.get("content", ""),
            structured_output=raw.get("structured_output"),
            usage=usage,
            provider_request_id=raw.get("request_id"),
            stop_reason=stop_enum,
            refusal=refusal,
            error=raw.get("error"),
            resource_inventory=(raw.get("structured_output") or {}).get("resource_inventory", []),
            accessibility_declaration=(raw.get("structured_output") or {}).get("accessibility_declaration"),
        )


def mock_transport(script: Optional[dict] = None) -> Transport:
    """Deterministic test transport."""
    def _call(payload: dict) -> dict:
        base = {
            "content": "mock implementation",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": len(payload["context"]) // 4,
                      "output_tokens": 120, "cache_read_tokens": 0,
                      "cache_write_tokens": len(payload["system"]) // 4},
            "request_id": "mock-req-1",
            "structured_output": {
                "resource_inventory": [{"resource": "timeline", "creator": "effect",
                                        "owner": "component", "creation_point": "mount",
                                        "update_point": "n/a", "teardown_point": "unmount",
                                        "cleanup_method": "ctx.revert()",
                                        "shared_status": "local", "external_status": "none"}],
                "accessibility_declaration": {"reduced_motion": "static fallback",
                                              "semantic_classification": "decorative",
                                              "keyboard_operable": True,
                                              "meaningful_fallback": True},
            },
        }
        base.update(script or {})
        return base
    return _call
