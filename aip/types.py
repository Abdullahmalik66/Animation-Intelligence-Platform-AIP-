"""Typed contracts (Workstream 2). Enums + structured boundary models."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Readiness(str, Enum):
    READY = "Ready"
    READY_AFTER_REVIEWS = "Ready after Required Reviews"
    NOT_READY = "Not Ready"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


class StopReason(str, Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    REFUSAL = "refusal"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class IntentSignal:
    """One extracted feature — multi-signal extraction never collapses to a
    single label (Workstream 6)."""
    kind: str          # target | choreography | trigger | technology | negation | workflow
    value: str
    source_span: str = ""


@dataclass
class RoutingDecision:
    value_classification: str
    architecture: Optional[str]
    technology: Optional[str]
    workflow: str
    signals: list[IntentSignal] = field(default_factory=list)
    clarification_needed: Optional[str] = None   # one plain-language question
    rationale: str = ""
    evidence_used: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    decided_by: str = "deterministic"            # deterministic | llm-assisted


@dataclass
class RetrievalPointer:
    retrieval_key: str
    source: str
    sections: list[str]
    required: bool
    reason: str


@dataclass
class ContextChunk:
    id: str
    kind: str            # shared | technology | workflow | example | pointer
    text: str
    source: str = ""
    heading_path: list[str] = field(default_factory=list)
    source_hash: str = ""
    release_gating: bool = False
    required: bool = False
    retrieval_key: str = ""
    trust: str = "repository"


@dataclass
class UsageMetrics:
    method: str = "estimated_chars_div_4"  # estimated_chars_div_4 | provider_reported | tokenizer_reported
    input_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_s: Optional[float] = None
    model_calls: int = 0
    retrieval_calls: int = 0


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result_summary: str = ""


@dataclass
class SpecialistRequest:
    request_id: str
    stable_prefix: str          # cacheable governance/contract sections
    dynamic_context: str        # selected knowledge + evidence
    state_projection: dict[str, Any]
    user_request: str
    prefix_hash: str = ""


@dataclass
class SpecialistResponse:
    content: str = ""
    structured_output: Optional[dict[str, Any]] = None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    usage: UsageMetrics = field(default_factory=UsageMetrics)
    provider_request_id: Optional[str] = None
    stop_reason: StopReason = StopReason.END_TURN
    refusal: bool = False
    fallback_used: bool = False
    retrieval_requests: list[str] = field(default_factory=list)
    resource_inventory: list[dict[str, Any]] = field(default_factory=list)
    accessibility_declaration: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class NeedsClarification:
    """Guided-mode structured result: one question, no speculative code."""
    question: str
    why_it_matters: str
    options: list[str] = field(default_factory=list)


@dataclass
class TraceRecord:
    request_id: str
    timestamp: float = field(default_factory=time.time)
    route: dict[str, Any] = field(default_factory=dict)
    modules_selected: list[str] = field(default_factory=list)
    modules_excluded: list[str] = field(default_factory=list)
    pointers_emitted: int = 0
    pointers_resolved: int = 0
    usage: Optional[dict[str, Any]] = None
    readiness: Optional[str] = None
    confidence: Optional[str] = None
    feature_flags: dict[str, bool] = field(default_factory=dict)
    refusal: bool = False
    fallback_used: bool = False
