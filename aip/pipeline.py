"""Pipeline orchestration, user modes, explainer, observability, feature flags.

This is the framework-neutral orchestration boundary (Phase 8 abstraction):
NOOA or another agent framework can implement `SpecialistBackend` without
changing the pipeline. No agent framework is installed; the default backend
returns a context packet + prompt for whichever LLM integration the host
provides (e.g. Copilot/Claude adapters).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Protocol

from .state import AnimationProjectState
from .inspector import inspect_project
from .router import translate_intent, route_stage1_technology, route_stage2_workflow
from .assembler import assemble_context, ContextCompressor, AssembledContext
from .validators import run_pipeline

ROOT = Path(__file__).resolve().parent.parent

FEATURE_FLAGS = {
    "legacy_full_skill": False,        # load whole SKILL.md files (rollback path)
    "modular_context": True,           # default
    "modular_context_with_compression": False,
    "nooa_pilot": False,               # requires NOOA install + documented decision (see docs/adr)
}


class SpecialistBackend(Protocol):
    """Abstraction so the platform is not coupled to one agent framework."""

    def run(self, state: AnimationProjectState, context: AssembledContext) -> str: ...


class PromptPacketBackend:
    """Default deterministic backend: emits the assembled prompt packet.
    The host agent (Copilot/Claude/etc.) executes it."""

    def run(self, state: AnimationProjectState, context: AssembledContext) -> str:
        projection = state.projection(AnimationProjectState.SPECIALIST_VIEW)
        return (
            "# Stable governance\n(see selected shared modules below)\n\n"
            f"# Selected modular knowledge\n{context.text}\n\n"
            f"# Structured project state\n```json\n{json.dumps(projection, indent=2, default=str)}\n```\n\n"
            f"# User request\n{state.raw_user_request}\n"
        )


def handle_request(raw_request: str,
                   project_dir: Optional[str] = None,
                   user_mode: str = "beginner",
                   flags: Optional[dict] = None,
                   backend: Optional[SpecialistBackend] = None,
                   compressor: Optional[ContextCompressor] = None) -> dict:
    flags = {**FEATURE_FLAGS, **(flags or {})}
    state = AnimationProjectState(raw_user_request=raw_request, user_mode=user_mode)

    if project_dir:
        inspect_project(project_dir, state)
    else:
        state.unknowns.append("No project directory supplied — stack unverified")

    translate_intent(state)
    route_stage1_technology(state)
    route_stage2_workflow(state)

    if flags["legacy_full_skill"]:
        context = _legacy_full_context(state)
    else:
        comp = compressor if flags["modular_context_with_compression"] else None
        context = assemble_context(state, compressor=comp)

    run_pipeline(state)
    backend = backend or PromptPacketBackend()
    prompt = backend.run(state, context)

    report = _observability_report(state)
    return {"state": state, "prompt": prompt, "manifest": context.manifest,
            "explanation": explain(state), "observability": report}


def _legacy_full_context(state: AnimationProjectState) -> AssembledContext:
    """Rollback path: whole canonical SKILL.md files, as today."""
    chunks = []
    included = []
    router = ROOT / "skills" / "animation-router" / "SKILL.md"
    chunks.append(router.read_text(encoding="utf-8"))
    included.append({"id": "animation-router", "kind": "legacy-full"})
    tech = state.selected_technology
    skill = ROOT / "skills" / (tech or "") / "SKILL.md"
    if tech and skill.is_file():
        chunks.append(skill.read_text(encoding="utf-8"))
        included.append({"id": tech, "kind": "legacy-full"})
    from .assembler import estimate_tokens
    total = sum(estimate_tokens(c) for c in chunks)
    ctx = AssembledContext(chunks=chunks, manifest={
        "request_id": state.request_id, "mode": "legacy_full_skill",
        "included": included, "excluded": [],
        "assembled_token_estimate": total,
        "token_note": "chars/4 estimates — not exact model tokenisation"})
    state.context_manifest = ctx.manifest
    return ctx


def explain(state: AnimationProjectState) -> str:
    """Beginner-friendly explanation. Never hides uncertainty or blockers."""
    tech_names = {"css": "built-in browser styling (no extra library)",
                  "waapi": "the browser's built-in animation system",
                  "gsap": "GSAP, a professional animation library",
                  "motion-react": "Motion for React, an animation library for React apps",
                  "motion": "the Motion animation library",
                  "animejs": "the Anime.js animation library",
                  "lottie": "Lottie, which plays designer-made animations",
                  "rive": "Rive, which plays interactive designer-made graphics",
                  "threejs": "Three.js, which draws 3D graphics",
                  "insufficient-evidence": "nothing yet — more information is needed"}
    lines = [
        "## What I understood",
        f"You asked: “{state.raw_user_request}”",
        f"I read this as: {state.normalised_intent or 'unclear — please clarify'}.",
        "",
        "## What the system chose",
        f"Approach: {tech_names.get(state.selected_technology or '', state.selected_technology or 'undecided')}.",
        "",
        "## Accessibility and reduced-motion behaviour",
        "People who turn on “reduce motion” in their device settings will get a calmer, "
        "non-moving version. This is built in, not optional.",
        "",
        "## Anything that still needs attention",
    ]
    if state.unknowns:
        lines += [f"- Unclear: {u}" for u in state.unknowns]
    if state.blockers:
        lines += [f"- Blocked: {b}" for b in state.blockers]
    if not state.unknowns and not state.blockers:
        lines.append("- Nothing outstanding.")
    lines += ["", f"Readiness: {state.implementation_readiness} · Confidence: {state.confidence}"]
    return "\n".join(lines)


def _observability_report(state: AnimationProjectState) -> dict:
    m = state.context_manifest or {}
    return {
        "request_id": state.request_id,
        "route": {"technology": state.selected_technology,
                  "workflow": state.selected_workflow,
                  "architecture": state.selected_architecture},
        "modules_selected": [i["id"] for i in m.get("included", [])],
        "modules_excluded": [e["id"] for e in m.get("excluded", [])],
        "context_tokens_estimated": m.get("assembled_token_estimate"),
        "context_tokens_uncompressed": m.get("uncompressed_token_estimate"),
        "token_note": m.get("token_note"),
        "validation": state.validation_results,
        "readiness": state.implementation_readiness,
        "confidence": state.confidence,
    }
