"""Plain-language intake translator (Phase 11) and two-stage router (Phase 6).

The translator produces intake HYPOTHESES; the router validates them. Rules
here are deterministic heuristics for routing/context selection — the LLM
specialist remains responsible for ambiguous trade-offs. Canonical routing
authority remains skills/animation-router/SKILL.md (GOV-ROUTING).
"""
from __future__ import annotations

import re

from .state import AnimationProjectState
from .inspector import installed_animation_technologies

# (pattern, intent hypothesis, needs_disambiguation)
INTAKE_HYPOTHESES: list[tuple[str, str, bool]] = [
    (r"one at a time|one by one|stagger", "staggered-entrance", False),
    (r"scroll|as i scroll|when.*scroll", "scroll-linked-or-viewport-triggered", True),
    (r"interactive character|reacts to|responds to (click|hover|cursor)", "stateful-designer-asset", False),
    (r"spinning|rotating logo", "decorative-loop", False),
    (r"3d|three.?d|product viewer", "3d-scene", False),
    (r"loading (animation|spinner)|while.*load", "status-indicator", False),
    (r"hover", "hover-micro-interaction", False),
    (r"fade|appear|show up", "entrance", False),
    (r"page (transition|change)|between pages", "route-transition", True),
]

WORKFLOW_PATTERNS: list[tuple[str, str]] = [
    (r"\b(fix|broken|not working|debug|why (does|is))\b", "debugging"),
    (r"\b(review|audit|check (my|this))\b", "code-review"),
    (r"\b(accessib|reduced motion|screen reader|a11y)\b", "accessibility-review"),
    (r"\b(slow|jank|performance|fps|dropped frames)\b", "performance-review"),
    (r"\b(migrate|convert|switch (from|to)|replace .* with)\b", "migration"),
    (r"\b(secure|security|csp|trusted|provenance)\b", "security-review"),
    (r"\b(production.?ready|ready to ship|launch)\b", "production-readiness"),
]


def translate_intent(state: AnimationProjectState) -> AnimationProjectState:
    text = state.raw_user_request.lower()
    for pattern, intent, ambiguous in INTAKE_HYPOTHESES:
        if re.search(pattern, text):
            state.normalised_intent = intent
            if ambiguous:
                state.unknowns.append(
                    f"Intent '{intent}' needs disambiguation (e.g. scroll-linked vs viewport-triggered)")
            break
    else:
        state.normalised_intent = "unclassified"
        state.unknowns.append("Intent not matched by intake hypotheses — router must interpret")
    return state


def route_stage1_technology(state: AnimationProjectState) -> AnimationProjectState:
    """Stage 1: architecture/technology. Deterministic defaults; ambiguous
    cases yield 'insufficient-evidence' rather than a guess."""
    intent = state.normalised_intent or "unclassified"
    installed = installed_animation_technologies(state)

    def pick(preferred: list[str], fallback: str) -> str:
        for tech in preferred:
            if tech in installed:
                return tech
        return fallback

    if intent == "hover-micro-interaction":
        tech, arch = "css", "native-css"
    elif intent == "entrance":
        tech, arch = "css", "native-css"
    elif intent == "staggered-entrance":
        if state.framework in ("react", "nextjs"):
            tech = pick(["motion-react", "gsap"], "css")
        else:
            tech = pick(["gsap", "animejs"], "css")
        arch = "library" if tech != "css" else "native-css"
    elif intent == "scroll-linked-or-viewport-triggered":
        # Viewport-triggered → IntersectionObserver+CSS; scroll-linked → GSAP/CSS scroll-timeline.
        tech, arch = "insufficient-evidence", "needs-disambiguation"
    elif intent == "stateful-designer-asset":
        tech, arch = "rive", "designer-runtime"
    elif intent == "3d-scene":
        tech, arch = "threejs", "webgl"
    elif intent == "status-indicator":
        tech, arch = pick(["lottie", "rive"], "css"), "status-semantics-first"
    elif intent == "decorative-loop":
        tech, arch = "css", "value-challenge"  # router must challenge value first
    else:
        tech, arch = "insufficient-evidence", "unrouted"

    state.selected_technology = tech
    state.selected_architecture = arch
    if intent == "decorative-loop":
        state.animation_value_classification = "decorative"
    elif intent in ("status-indicator",):
        state.animation_value_classification = "communicative"
    elif tech != "insufficient-evidence":
        state.animation_value_classification = "functional"
    return state


def route_stage2_workflow(state: AnimationProjectState) -> AnimationProjectState:
    text = state.raw_user_request.lower()
    for pattern, workflow in WORKFLOW_PATTERNS:
        if re.search(pattern, text):
            state.selected_workflow = workflow
            return state
    state.selected_workflow = "implementation"
    return state
