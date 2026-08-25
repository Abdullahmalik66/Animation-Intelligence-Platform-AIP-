"""Scenario suite: baseline (legacy full-skill) vs modular context (Phase 1 + 13).

Runs 15 representative scenarios through both feature-flag paths and compares
routing, safety gates, readiness, and estimated context tokens. Token figures
are chars/4 ESTIMATES. Exits non-zero on release-gate failure.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aip.pipeline import handle_request  # noqa: E402

SCENARIOS = [
    {"id": "no-animation", "request": "Should the price text flash red repeatedly to get attention?", "expect_workflow": "implementation"},
    {"id": "css-hover", "request": "Make the button grow slightly on hover", "expect_tech": "css"},
    {"id": "waapi-runtime", "request": "I need to pause and seek the fade programmatically without a library", "expect_workflow": "implementation"},
    {"id": "animejs-impl", "request": "Animate the SVG logo path with a vanilla js animation", "expect_workflow": "implementation"},
    {"id": "gsap-scrolltrigger-debug", "request": "My GSAP ScrollTrigger pin is broken after route change, fix it", "expect_workflow": "debugging"},
    {"id": "motion-vanilla-cleanup", "request": "Review my Motion animation cleanup on element removal", "expect_workflow": "code-review"},
    {"id": "motion-react-presence", "request": "Cards should fade out when removed from the list in React", "expect_workflow": "implementation"},
    {"id": "lottie-asset", "request": "Add the loading animation our designer exported from After Effects", "expect_tech_in": ["lottie", "rive", "css"]},
    {"id": "rive-state-machine", "request": "Add the interactive character that reacts to cursor from our .riv file", "expect_tech": "rive"},
    {"id": "threejs-disposal", "request": "Why does memory grow in my 3D product viewer on every page change? debug it", "expect_workflow": "debugging"},
    {"id": "a11y-remediation", "request": "Make our hero animation respect reduced motion accessibility settings", "expect_workflow": "accessibility-review"},
    {"id": "perf-investigation", "request": "The scroll animation is slow and janky on mobile", "expect_workflow": "performance-review"},
    {"id": "migration", "request": "Migrate our animations from framer-motion to gsap", "expect_workflow": "migration"},
    {"id": "unknown-package", "request": "Add a staggered entrance with whatever animation library we have", "expect_workflow": "implementation"},
    {"id": "beginner-scroll", "request": "I want the cards to appear one at a time when someone scrolls down", "expect_workflow": "implementation"},
]

FIXTURE_PKG = {
    "dependencies": {"react": "^18.3.0", "gsap": "^3.12.5", "motion": "^11.0.0",
                     "@rive-app/react-canvas": "^4.9.0", "three": "^0.160.0",
                     "lottie-web": "^5.12.2"}}


def run(out_path: str | None = None) -> int:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "package.json").write_text(json.dumps(FIXTURE_PKG))
        rows, failures = [], []
        for sc in SCENARIOS:
            legacy = handle_request(sc["request"], project_dir=td,
                                    flags={"legacy_full_skill": True, "modular_context": False})
            modular = handle_request(sc["request"], project_dir=td)
            ls, ms = legacy["state"], modular["state"]

            row = {
                "scenario": sc["id"],
                "tech_legacy": ls.selected_technology, "tech_modular": ms.selected_technology,
                "workflow": ms.selected_workflow,
                "readiness": ms.implementation_readiness,
                "confidence": ms.confidence,
                "tokens_legacy_est": legacy["manifest"]["assembled_token_estimate"],
                "tokens_modular_est": modular["manifest"]["assembled_token_estimate"],
                "examples_loaded": ms.selected_examples,
                "code_withheld_correctly": ms.selected_technology == "insufficient-evidence"
                                            and ms.implementation_readiness in
                                            ("Insufficient Evidence", "Not Ready")
                                            or ms.selected_technology != "insufficient-evidence",
            }
            # Release gates
            if ls.selected_technology != ms.selected_technology:
                failures.append(f"{sc['id']}: routing divergence legacy={ls.selected_technology} modular={ms.selected_technology}")
            if "expect_tech" in sc and ms.selected_technology != sc["expect_tech"]:
                failures.append(f"{sc['id']}: expected tech {sc['expect_tech']}, got {ms.selected_technology}")
            if "expect_tech_in" in sc and ms.selected_technology not in sc["expect_tech_in"]:
                failures.append(f"{sc['id']}: tech {ms.selected_technology} not in {sc['expect_tech_in']}")
            if "expect_workflow" in sc and ms.selected_workflow != sc["expect_workflow"]:
                failures.append(f"{sc['id']}: expected workflow {sc['expect_workflow']}, got {ms.selected_workflow}")
            gating = [i for i in modular["manifest"].get("included", [])
                      if i.get("release_gating")]
            required = {"GOV-A11Y", "GOV-READINESS"}
            present = {g["id"] for g in gating}
            if ms.selected_workflow in ("implementation", "migration") and not required <= present:
                failures.append(f"{sc['id']}: release-gating rules missing from context: {required - present}")
            rows.append(row)

        total_legacy = sum(r["tokens_legacy_est"] for r in rows)
        total_modular = sum(r["tokens_modular_est"] for r in rows)
        report = {
            "note": "All token figures are chars/4 ESTIMATES, not API-reported usage.",
            "scenarios": rows,
            "totals": {"legacy_est": total_legacy, "modular_est": total_modular,
                       "estimated_reduction_pct": round(100 * (1 - total_modular / total_legacy), 1)
                       if total_legacy else None},
            "failures": failures,
            "release_gate": "PASS" if not failures else "FAIL",
        }
        out = Path(out_path or Path(__file__).resolve().parent.parent / "docs" / "analysis" / "scenario-report.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(f"Scenarios: {len(rows)} | legacy est tokens: {total_legacy} | "
              f"modular est tokens: {total_modular} | gate: {report['release_gate']}")
        for f in failures:
            print("  FAIL:", f)
        return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
