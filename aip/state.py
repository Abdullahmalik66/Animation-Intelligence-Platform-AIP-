"""Typed shared project state (Phase 5). Stdlib dataclasses only."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

MODEL_HIDDEN_FIELDS = {"security_policy_internal", "token_usage", "context_manifest"}


@dataclass
class Evidence:
    claim: str
    source: str          # e.g. "package.json", "lockfile", "user-supplied"
    trust: str           # "verified" | "user-supplied" | "assumed"
    detail: str = ""


@dataclass
class AnimationProjectState:
    """One animation request. Specialists receive projections, not free text."""
    raw_user_request: str
    user_mode: str = "beginner"  # beginner | guided | expert
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    normalised_intent: Optional[str] = None
    animation_value_classification: str = "unknown"
    framework: Optional[str] = None
    framework_version: Optional[str] = None
    runtime: Optional[str] = None
    bundler: Optional[str] = None
    package_manager: Optional[str] = None
    installed_packages: dict[str, str] = field(default_factory=dict)
    resolved_versions: dict[str, str] = field(default_factory=dict)
    verified_exports: dict[str, list[str]] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    browser_support_policy: Optional[str] = None
    accessibility_policy: Optional[str] = None
    performance_budget: Optional[dict[str, Any]] = None
    selected_architecture: Optional[str] = None
    selected_technology: Optional[str] = None
    selected_workflow: Optional[str] = None
    selected_modules: list[str] = field(default_factory=list)
    selected_examples: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    implementation_readiness: Optional[str] = None
    confidence: Optional[str] = None
    context_manifest: Optional[dict[str, Any]] = None
    token_usage: Optional[dict[str, Any]] = None
    validation_results: list[dict[str, Any]] = field(default_factory=list)

    def projection(self, fields: list[str]) -> dict[str, Any]:
        """Model-facing view: only requested fields, hidden fields excluded."""
        data = asdict(self)
        return {k: data[k] for k in fields
                if k in data and k not in MODEL_HIDDEN_FIELDS}

    ROUTER_VIEW = ["normalised_intent", "animation_value_classification",
                   "framework", "installed_packages", "assets",
                   "browser_support_policy", "unknowns"]
    SPECIALIST_VIEW = ["normalised_intent", "framework", "framework_version",
                       "installed_packages", "resolved_versions",
                       "verified_exports", "assets", "selected_technology",
                       "selected_workflow", "assumptions", "unknowns",
                       "blockers"]
    EXPLAINER_VIEW = ["raw_user_request", "normalised_intent",
                      "selected_technology", "selected_workflow",
                      "implementation_readiness", "confidence",
                      "assumptions", "unknowns", "blockers"]
