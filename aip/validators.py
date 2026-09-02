"""Validation pipeline v2 (Workstream 9). Structured evidence, not keywords.

Deterministic gates over populated state + typed SpecialistResponse fields
(resource_inventory, accessibility_declaration). Semantic code judgement still
belongs to the LLM/reviewer; these gates enforce evidence completeness.
"""
from __future__ import annotations

from typing import Optional

from .state import AnimationProjectState
from .types import Confidence, Readiness, SpecialistResponse

LIBRARY_TECHS = {"gsap", "animejs", "motion", "motion-react", "lottie", "rive", "threejs"}
ASSET_TECHS = {"lottie", "rive", "threejs"}
LIFECYCLE_FIELDS = {"resource", "owner", "teardown_point", "cleanup_method"}
A11Y_FIELDS = {"reduced_motion", "semantic_classification", "keyboard_operable",
               "meaningful_fallback"}
PERF_RISK_INTENTS = {"scroll", "loop", "3d"}


def _result(name: str, passed: bool, detail: str, gating: bool = False) -> dict:
    return {"validator": name, "passed": passed, "detail": detail, "gating": gating}


def _package_names(tech: str) -> list[str]:
    return {"motion-react": ["motion", "framer-motion"],
            "threejs": ["three"],
            "lottie": ["lottie-web", "@lottiefiles/dotlottie-web"],
            "rive": ["@rive-app/react-canvas", "@rive-app/canvas",
                     "@rive-app/webgl2", "@rive-app/react-webgl2"]}.get(tech, [tech])


def version_validator(state: AnimationProjectState) -> dict:
    tech = state.selected_technology
    if tech not in LIBRARY_TECHS:
        return _result("version", True, "No package dependency required")
    names = _package_names(tech)
    present = [n for n in names if n in state.installed_packages]
    if not present:
        return _result("version", False, f"{tech} not installed — GOV-VERSION gate fails", gating=True)
    exact = [n for n in present if n in state.resolved_versions]
    exports = [n for n in present if n in state.verified_exports]
    if exact and exports:
        return _result("version", True,
                       f"Exact version {state.resolved_versions[exact[0]]} + exports verified")
    missing = []
    if not exact:
        missing.append("exact resolved version")
    if not exports:
        missing.append("verified exports/declarations")
    return _result("version", False, f"GOV-VERSION incomplete: missing {', '.join(missing)}",
                   gating=False)  # present-but-unverified → required review, not hard block


def ownership_validator(state: AnimationProjectState,
                        response: Optional[SpecialistResponse]) -> dict:
    if state.selected_technology in (None, "css", "waapi", "insufficient-evidence", "no-animation"):
        return _result("ownership", True, "Declarative/native — no runtime ownership required")
    inventory = response.resource_inventory if response else []
    if not inventory:
        return _result("ownership", False,
                       "GOV-OWNERSHIP: no structured resource inventory supplied by specialist")
    bad = [r for r in inventory if not LIFECYCLE_FIELDS <= set(r)]
    if bad:
        return _result("ownership", False,
                       f"GOV-OWNERSHIP: {len(bad)} resource(s) missing owner/teardown/cleanup fields")
    return _result("ownership", True,
                   f"{len(inventory)} lifecycle-managed resource(s) with owner + teardown")


def accessibility_validator(state: AnimationProjectState,
                            response: Optional[SpecialistResponse]) -> dict:
    if state.animation_value_classification == "harmful":
        return _result("accessibility", False, "Classified harmful — blocked", gating=True)
    if state.animation_value_classification == "unknown":
        return _result("accessibility", False, "GOV-A11Y: purpose not classified", gating=True)
    if state.selected_technology in ("no-animation", None):
        return _result("accessibility", True, "No animation output")
    decl = response.accessibility_declaration if response else None
    if not decl:
        return _result("accessibility", False,
                       "GOV-A11Y: no structured accessibility declaration supplied", gating=True)
    missing = A11Y_FIELDS - set(decl)
    if missing:
        return _result("accessibility", False,
                       f"GOV-A11Y: declaration missing {sorted(missing)}", gating=True)
    if decl.get("reduced_motion") in (None, False, "none"):
        return _result("accessibility", False, "GOV-A11Y: no reduced-motion behaviour", gating=True)
    return _result("accessibility", True, "Structured accessibility declaration complete")


def security_validator(state: AnimationProjectState) -> dict:
    if state.selected_technology not in ASSET_TECHS:
        return _result("security", True, "No external asset runtime")
    if not state.assets:
        return _result("security", False,
                       "GOV-SECURITY: asset discovery found no assets — asset evidence "
                       "required for asset-runtime technology", gating=True)
    untrusted = [a for a in state.assets if a.get("trust") != "approved"]
    if untrusted:
        return _result("security", False,
                       f"GOV-SECURITY: {len(untrusted)} asset(s) without approved trust "
                       f"(same-origin ≠ trusted): {[a['path'] for a in untrusted[:3]]}",
                       gating=True)
    return _result("security", True, "All assets from approved, recorded sources")


def performance_validator(state: AnimationProjectState) -> dict:
    intent = state.normalised_intent or ""
    risky = any(k in intent for k in PERF_RISK_INTENTS) or state.selected_technology == "threejs"
    measured = any("profil" in e.claim.lower() or "measur" in e.claim.lower()
                   for e in state.evidence)
    if not risky:
        return _result("performance", True,
                       "Trivial bounded animation — measurement not required by policy (GOV-PERF)")
    if measured:
        return _result("performance", True, "Performance risk with measurement evidence supplied")
    return _result("performance", False,
                   "GOV-PERF: performance RISK identified (scroll/loop/3D) — measurement "
                   "required before 'no regression' can be claimed; risk ≠ measured regression")


def readiness_validator(state: AnimationProjectState) -> Readiness:
    if state.selected_technology in ("insufficient-evidence", None):
        return Readiness.INSUFFICIENT_EVIDENCE
    results = state.validation_results
    gating_failed = [r for r in results if not r["passed"] and r.get("gating")]
    evidence_gaps = [r for r in gating_failed
                     if "not established" in r["detail"] or "no structured" in r["detail"]
                     or "found no assets" in r["detail"] or "not classified" in r["detail"]]
    if gating_failed:
        return Readiness.INSUFFICIENT_EVIDENCE if evidence_gaps and state.unknowns \
            else Readiness.NOT_READY
    if any(not r["passed"] for r in results):
        return Readiness.READY_AFTER_REVIEWS
    return Readiness.READY


def confidence_validator(state: AnimationProjectState) -> Confidence:
    if state.selected_technology in ("insufficient-evidence", None):
        return Confidence.UNKNOWN
    verified = len([e for e in state.evidence if e.trust == "verified"])
    if state.unknowns and verified == 0:
        return Confidence.LOW
    if state.unknowns:
        return Confidence.MEDIUM
    return Confidence.HIGH if verified else Confidence.MEDIUM


def run_pipeline(state: AnimationProjectState,
                 response: Optional[SpecialistResponse] = None) -> AnimationProjectState:
    state.validation_results = [
        version_validator(state),
        ownership_validator(state, response),
        accessibility_validator(state, response),
        security_validator(state),
        performance_validator(state),
    ]
    state.implementation_readiness = readiness_validator(state).value
    state.confidence = confidence_validator(state).value
    return state
