"""Orchestrator v2.

Real mode behaviour (guided returns NeedsClarification), stable/dynamic prompt
split with deterministic prefix hash, executable retrieval, structured backend,
JSONL observability, validated feature-flag combinations.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .state import AnimationProjectState
from .inspector import inspect_project
from .hybrid_router import route, clarification_from
from .assembler import assemble_context, ContextCompressor
from .retrieval import RetrievalStore, RetrievalError
from .validators import run_pipeline
from .schema_check import validate_all
from .types import (NeedsClarification, SpecialistRequest, SpecialistResponse,
                    StopReason, TraceRecord)
from .gateway import ModelGateway, ProviderRegistry

ROOT = Path(__file__).resolve().parent.parent


def _trace_path() -> Path:
    """Traces live in the user's cache dir, never in their working tree."""
    if override := os.environ.get("AIP_TRACE_PATH"):
        return Path(override).expanduser()
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "aip" / "traces.jsonl"


TRACE_PATH = _trace_path()

_FLAG_ALIASES: dict[str, str] = {}

VALID_FLAG_SETS = {
    frozenset({"legacy_full_skill"}),
    frozenset({"modular_context"}),
    frozenset({"modular_context", "modular_context_with_model"}),
    frozenset({"modular_context", "modular_context_with_retrieval"}),
    frozenset({"modular_context", "modular_context_with_model",
               "modular_context_with_retrieval"}),
    frozenset({"modular_context", "modular_context_with_compression"}),
    frozenset({"modular_context", "modular_context_with_model",
               "modular_context_with_retrieval", "modular_context_with_compression"}),
}


class FlagError(ValueError):
    pass


def _normalise_flags(flags: dict[str, bool]) -> dict[str, bool]:
    return {_FLAG_ALIASES.get(k, k): v for k, v in flags.items()}


def _check_flags(flags: dict[str, bool]) -> None:
    flags = _normalise_flags(flags)
    active = frozenset(k for k, v in flags.items() if v and k != "nooa_pilot")
    if active not in VALID_FLAG_SETS:
        raise FlagError(
            f"Invalid feature-flag combination: {sorted(active)}. "
            f"Valid: {[sorted(s) for s in VALID_FLAG_SETS]}")


def handle(raw_request: str,
           project_dir: Optional[str] = None,
           user_mode: str = "beginner",
           clarification_answer: Optional[str] = None,
           flags: Optional[dict[str, bool]] = None,
           backend: Optional[Any] = None,          # legacy: object with run_request()
           gateway: Optional[ModelGateway] = None,  # canonical provider-neutral path
           provider: Optional[str] = None,
           selection_policy: str = "fixed_provider",
           compressor: Optional[ContextCompressor] = None,
           retrieval: Optional[RetrievalStore] = None) -> dict[str, Any]:
    flags = _normalise_flags({**{"modular_context": True}, **(flags or {})})
    _check_flags(flags)
    validate_all()  # fail fast on invalid manifests — never assemble from bad config

    state = AnimationProjectState(raw_user_request=raw_request, user_mode=user_mode)
    if project_dir:
        inspect_project(project_dir, state)
    else:
        state.unknowns.append("No project directory supplied — stack unverified")

    decision = route(state, clarification_answer=clarification_answer)

    # Guided mode: real clarification behaviour — no speculative generation.
    clarification = clarification_from(decision)
    if clarification and user_mode == "guided" and not clarification_answer:
        _trace(state, flags, pointers=(0, 0))
        return {"status": "needs_clarification", "clarification": clarification,
                "state": state, "decision": decision}
    if clarification and user_mode == "beginner" and not clarification_answer:
        # Beginner: choose the safe default (viewport-triggered) and disclose it.
        decision = route(state, clarification_answer="appear once when in view")
        state.assumptions.append(
            "Assumed cards appear once when scrolled into view (the safer default); "
            "say 'tied to scroll position' if you want continuous motion.")

    ctx = assemble_context(state, compressor=compressor
                           if flags.get("modular_context_with_compression") else None)

    response: Optional[SpecialistResponse] = None
    retrieval = retrieval or RetrievalStore()
    pointers_emitted = sum(1 for c in ctx.chunks if c.startswith("[Retrieval pointer"))
    pointers_resolved = 0

    selection = None
    if flags.get("modular_context_with_model") and (gateway or backend):
        req = _build_request(state, ctx)
        if gateway:
            response, selection = gateway.run(
                req, workflow=state.selected_workflow or "default",
                policy=selection_policy, fixed=provider)
        else:  # deprecated legacy path (backend.run_request)
            response = backend.run_request(req)
        # Model-in-the-loop retrieval: bounded, audited (Workstream 12).
        if flags.get("modular_context_with_retrieval") and response:
            for key in response.retrieval_requests[:5]:
                try:
                    chunk = retrieval.retrieve(key, reason="specialist request")
                    ctx.chunks.append(chunk.text)
                    pointers_resolved += 1
                except RetrievalError as exc:
                    state.unknowns.append(f"Retrieval denied: {exc}")

    run_pipeline(state, response)
    trace = _trace(state, flags, (pointers_emitted, pointers_resolved), response)

    return {
        "status": "refused" if response and response.refusal else "complete",
        "state": state,
        "decision": decision,
        "selection": selection,
        "manifest": ctx.manifest,
        "response": response,
        "explanation": _explain(state, decision, response, user_mode),
        "trace": trace,
    }


def _build_request(state: AnimationProjectState, ctx) -> SpecialistRequest:
    """Stable/dynamic split for prompt caching (Workstream 11)."""
    stable = [c for c, m in zip(ctx.chunks, ctx.manifest["included"])
              if m["kind"] == "shared"]
    dynamic = [c for c, m in zip(ctx.chunks, ctx.manifest["included"])
               if m["kind"] != "shared"]
    stable_text = "\n\n---\n\n".join(stable)
    return SpecialistRequest(
        request_id=state.request_id,
        stable_prefix=stable_text,
        prefix_hash=hashlib.sha256(stable_text.encode()).hexdigest()[:16],
        dynamic_context="\n\n---\n\n".join(dynamic),
        state_projection=state.projection(AnimationProjectState.SPECIALIST_VIEW),
        user_request=state.raw_user_request)


def _explain(state, decision, response, mode: str) -> dict[str, Any]:
    tech_names = {"css": "built-in browser styling (no extra library)",
                  "waapi": "the browser's built-in animation system",
                  "gsap": "GSAP, a professional animation library",
                  "motion-react": "Motion for React, an animation library for React apps",
                  "motion": "the Motion animation library",
                  "animejs": "the Anime.js animation library",
                  "lottie": "Lottie, which plays designer-made animations",
                  "rive": "Rive, which plays interactive designer-made graphics",
                  "threejs": "Three.js, which draws 3D graphics",
                  "no-animation": "no animation — it isn't needed here",
                  "insufficient-evidence": "nothing yet — more information is needed"}
    beginner = {
        "what_i_understood": f"You asked: “{state.raw_user_request}”. I read this as: "
                             + ", ".join(f"{s.kind} {s.value}" for s in decision.signals),
        "what_will_happen_on_screen": decision.rationale,
        "what_the_system_chose": tech_names.get(state.selected_technology or "",
                                                state.selected_technology or "undecided"),
        "what_was_created_or_reviewed": (response.content if response
                                         else "No code generated in this run "
                                         "(no live model backend configured)."),
        "how_to_test_it": "Reload the page and scroll/interact; also enable "
                          "'reduce motion' in system settings and confirm the calm version.",
        "accessibility_behaviour": "People with 'reduce motion' enabled get a "
                                   "non-moving version. Built in, not optional.",
        "anything_still_unclear": state.unknowns + state.blockers + state.assumptions,
        "readiness": state.implementation_readiness,
        "confidence": state.confidence,
    }
    if mode == "beginner":
        return beginner
    expert_extra = {
        "routing_decision": asdict(decision),
        "evidence": [asdict(e) for e in state.evidence],
        "modules_loaded": state.selected_modules,
        "validation": state.validation_results,
        "usage": asdict(response.usage) if response else None,
        "context_manifest": state.context_manifest,
    }
    return {**beginner, **expert_extra} if mode == "expert" else beginner


def _trace(state, flags, pointers, response: Optional[SpecialistResponse] = None) -> dict:
    rec = TraceRecord(
        request_id=state.request_id,
        route={"technology": state.selected_technology,
               "workflow": state.selected_workflow},
        modules_selected=state.selected_modules,
        modules_excluded=[e["id"] for e in (state.context_manifest or {}).get("excluded", [])],
        pointers_emitted=pointers[0], pointers_resolved=pointers[1],
        usage=asdict(response.usage) if response else
              {"method": "estimated_chars_div_4",
               "input_tokens": (state.context_manifest or {}).get("assembled_token_estimate")},
        readiness=state.implementation_readiness, confidence=state.confidence,
        feature_flags={k: bool(v) for k, v in flags.items()},
        refusal=bool(response and response.refusal),
        fallback_used=bool(response and response.fallback_used))
    d = asdict(rec)
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(d) + "\n")
    return d
