"""Validation pipeline (Phase 12). Deterministic gate checks over state.

These validators check evidence presence and gate status — the deterministic
half of validation. Semantic code review remains an LLM specialist task.
"""
from __future__ import annotations

from .state import AnimationProjectState

LIBRARY_TECHS = {"gsap", "animejs", "motion", "motion-react", "lottie", "rive", "threejs"}
ASSET_TECHS = {"lottie", "rive", "threejs"}


def _result(name: str, passed: bool, detail: str) -> dict:
    return {"validator": name, "passed": passed, "detail": detail}


def version_validator(state: AnimationProjectState) -> dict:
    tech = state.selected_technology
    if tech not in LIBRARY_TECHS:
        return _result("version", True, "No package dependency required")
    resolved = any(t in state.resolved_versions or t in state.installed_packages
                   for t in _package_names(tech))
    if resolved:
        exact = any(t in state.resolved_versions for t in _package_names(tech))
        return _result("version", True,
                       "Exact version resolved from lockfile" if exact
                       else "Declared range only — exact version unresolved")
    return _result("version", False, f"{tech} not found in installed packages — GOV-VERSION gate fails")


def _package_names(tech: str) -> list[str]:
    return {"motion-react": ["motion", "framer-motion"],
            "threejs": ["three"],
            "lottie": ["lottie-web", "@lottiefiles/dotlottie-web"],
            "rive": ["@rive-app/react-canvas", "@rive-app/canvas",
                     "@rive-app/webgl2", "@rive-app/react-webgl2"]}.get(tech, [tech])


def ownership_validator(state: AnimationProjectState) -> dict:
    if state.selected_technology in (None, "css", "insufficient-evidence"):
        return _result("ownership", True, "Declarative CSS — no runtime ownership")
    documented = any("ownership" in a.lower() or "cleanup" in a.lower() or "teardown" in a.lower()
                     for a in (state.assumptions + [e.claim for e in state.evidence]))
    return _result("ownership", documented,
                   "Ownership/teardown documented" if documented
                   else "GOV-OWNERSHIP: teardown owner not documented")


def accessibility_validator(state: AnimationProjectState) -> dict:
    if state.animation_value_classification == "harmful":
        return _result("accessibility", False, "Classified harmful — blocked")
    classified = state.animation_value_classification != "unknown"
    return _result("accessibility", classified,
                   f"Purpose: {state.animation_value_classification}; reduced-motion "
                   "state must be defined by specialist (GOV-A11Y)" if classified
                   else "GOV-A11Y: purpose not classified")


def security_validator(state: AnimationProjectState) -> dict:
    if state.selected_technology not in ASSET_TECHS:
        return _result("security", True, "No external asset runtime")
    trusted = all(a.get("trust") == "approved" for a in state.assets) if state.assets else False
    return _result("security", trusted,
                   "Assets from approved sources" if trusted
                   else "GOV-SECURITY: asset provenance not approved/unknown")


def performance_validator(state: AnimationProjectState) -> dict:
    return _result("performance", True,
                   "Risk assessment only — no measured regression claims permitted "
                   "without profiling evidence (GOV-PERF)")


def readiness_validator(state: AnimationProjectState) -> str:
    results = state.validation_results
    failed = [r for r in results if not r["passed"]]
    gating_failed = [r for r in failed if r["validator"] in ("version", "accessibility", "security")]
    if state.selected_technology == "insufficient-evidence" or \
       any("gate fails" in r["detail"] for r in gating_failed):
        return "Insufficient Evidence" if state.unknowns else "Not Ready"
    if gating_failed:
        return "Not Ready"
    if failed:
        return "Ready after Required Reviews"
    return "Ready"


def confidence_validator(state: AnimationProjectState) -> str:
    if state.selected_technology == "insufficient-evidence":
        return "Unknown"
    verified = len([e for e in state.evidence if e.trust == "verified"])
    if state.unknowns and verified == 0:
        return "Low"
    if state.unknowns:
        return "Medium"
    return "High" if verified else "Medium"


def run_pipeline(state: AnimationProjectState) -> AnimationProjectState:
    state.validation_results = [
        version_validator(state),
        ownership_validator(state),
        accessibility_validator(state),
        security_validator(state),
        performance_validator(state),
    ]
    state.implementation_readiness = readiness_validator(state)
    state.confidence = confidence_validator(state)
    return state
