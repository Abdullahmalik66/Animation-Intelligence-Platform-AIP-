"""Mock and replay provider adapters — the offline testing baseline.

The platform is fully testable with these; no SDK, no credentials, no cost.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..gateway import (ModelCapabilities, ProviderError, ProviderErrorKind, Support)
from ..types import ModelRequest, ModelResponse, StopReason, UsageMetrics

FULL_CAPS = ModelCapabilities(
    text_input=Support.SUPPORTED, structured_output=Support.SUPPORTED,
    json_schema_output=Support.SUPPORTED, tool_calling=Support.SUPPORTED,
    streaming=Support.SUPPORTED, prompt_caching=Support.SUPPORTED,
    system_messages=Support.SUPPORTED, provider_reported_usage=Support.SUPPORTED,
    cache_usage_reporting=Support.SUPPORTED, refusal_reporting=Support.SUPPORTED,
    local_execution=Support.SUPPORTED)

DEFAULT_STRUCTURED = {
    "resource_inventory": [{"resource": "timeline", "creator": "effect",
                            "owner": "component", "creation_point": "mount",
                            "update_point": "n/a", "teardown_point": "unmount",
                            "cleanup_method": "ctx.revert()",
                            "shared_status": "local", "external_status": "none"}],
    "accessibility_declaration": {"reduced_motion": "static fallback",
                                  "semantic_classification": "decorative",
                                  "keyboard_operable": True,
                                  "meaningful_fallback": True},
}


@dataclass
class MockAdapter:
    provider_id: str = "mock"
    model: str = "mock-1"
    capabilities: ModelCapabilities = field(default_factory=lambda: FULL_CAPS)
    script: Optional[dict] = None          # override fields
    raise_kind: Optional[ProviderErrorKind] = None
    fail_times: int = 0                    # raise N times, then succeed
    _calls: int = 0

    def invoke(self, request: ModelRequest) -> ModelResponse:
        self._calls += 1
        if self.raise_kind and self._calls <= (self.fail_times or 10**9):
            raise ProviderError(self.raise_kind, f"mock {self.raise_kind.value}")
        base = ModelResponse(
            content="mock implementation",
            structured_output=DEFAULT_STRUCTURED,
            usage=UsageMetrics(method="provider_reported",
                               input_tokens=len(request.dynamic_context) // 4,
                               cache_write_tokens=len(request.stable_prefix) // 4,
                               cache_read_tokens=0, output_tokens=120),
            provider_request_id=f"mock-{self._calls}",
            resource_inventory=DEFAULT_STRUCTURED["resource_inventory"],
            accessibility_declaration=DEFAULT_STRUCTURED["accessibility_declaration"])
        for k, v in (self.script or {}).items():
            setattr(base, k, v)
        return base


@dataclass
class ReplayAdapter:
    """Replays recorded canonical responses from a JSONL fixture keyed by
    request_id (or sequentially). Deterministic; zero network."""
    fixture_path: str
    provider_id: str = "replay"
    model: str = "recorded"
    capabilities: ModelCapabilities = field(default_factory=lambda: FULL_CAPS)
    _records: list[dict] = field(default_factory=list)
    _cursor: int = 0

    def __post_init__(self):
        p = Path(self.fixture_path)
        if p.is_file():
            self._records = [json.loads(line) for line in
                             p.read_text(encoding="utf-8").splitlines() if line.strip()]

    def invoke(self, request: ModelRequest) -> ModelResponse:
        by_id = next((r for r in self._records
                      if r.get("request_id") == request.request_id), None)
        rec = by_id
        if rec is None:
            if self._cursor >= len(self._records):
                raise ProviderError(ProviderErrorKind.PROVIDER_UNAVAILABLE,
                                    "replay fixture exhausted")
            rec = self._records[self._cursor]
            self._cursor += 1
        usage = rec.get("usage") or {}
        return ModelResponse(
            content=rec.get("content", ""),
            structured_output=rec.get("structured_output"),
            stop_reason=StopReason(rec.get("stop_reason", "end_turn")),
            refusal=rec.get("stop_reason") == "refusal",
            usage=UsageMetrics(method=usage.get("method", "provider_reported"),
                               input_tokens=usage.get("input_tokens"),
                               output_tokens=usage.get("output_tokens")),
            provider_request_id=rec.get("provider_request_id"),
            resource_inventory=(rec.get("structured_output") or {}).get("resource_inventory", []),
            accessibility_declaration=(rec.get("structured_output") or {}).get("accessibility_declaration"))
