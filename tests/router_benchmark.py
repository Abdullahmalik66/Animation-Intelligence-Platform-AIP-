"""Router benchmark (Workstream 19). Human-labelled dataset; measures
acceptable-route accuracy, unsafe-route rate, clarification precision,
no-animation precision, workflow accuracy. Exit 1 if below thresholds."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aip.state import AnimationProjectState  # noqa: E402
from aip.hybrid_router import route  # noqa: E402
from aip.inspector import inspect_project  # noqa: E402

# request, deps, acceptable technologies (None = llm-escalation OK),
# unacceptable, expected workflow, clarification expected
DATASET = [
    ("make the button grow on hover", {}, ["css"], ["gsap", "threejs"], "implementation", False),
    ("cards appear one at a time as I scroll down", {"react": "^18", "gsap": "^3.12"}, [None], ["threejs"], "implementation", True),
    ("cards appear one by one when the page loads", {"react": "^18", "motion": "^11"}, ["motion-react", "css"], ["threejs"], "implementation", False),
    ("don't animate the sidebar, it's distracting", {}, ["no-animation"], ["gsap", "css"], "implementation", False),
    ("fix my broken scrolltrigger pin", {"gsap": "^3.12"}, ["gsap"], ["lottie"], "debugging", False),
    ("review this framer-motion list for accessibility", {"framer-motion": "^11"}, ["motion-react"], [], "accessibility-review", False),
    ("migrate from anime.js to gsap", {"animejs": "^3"}, ["gsap", "animejs"], ["threejs"], "migration", False),
    ("add the interactive character that reacts to cursor", {"@rive-app/react-canvas": "^4"}, ["rive"], ["lottie", "css"], "implementation", False),
    ("play the designer's after effects export while loading", {"lottie-web": "^5"}, ["lottie", "css", "rive"], ["threejs"], "implementation", False),
    ("3d product viewer that spins", {"three": "^0.160"}, ["threejs"], ["css"], "implementation", False),
    ("the scroll animation is janky on mobile", {"gsap": "^3.12"}, ["gsap", None], [], "performance-review", False),
    ("is our lottie file from a trusted source?", {"lottie-web": "^5"}, ["lottie", None], [], "security-review", False),
    ("use the web animations api without a library to fade", {}, ["waapi"], ["gsap"], "implementation", False),
    ("animate the svg with anime.js", {"animejs": "^4"}, ["animejs"], [], "implementation", False),
    ("fais apparaître les cartes une par une", {}, [None], [], "implementation", False),  # non-English → escalate
    ("spinning logo in the header forever", {}, ["css"], ["threejs"], "implementation", False),
]


def run() -> int:
    correct = unsafe = clar_tp = clar_fp = clar_fn = wf_ok = 0
    rows = []
    for req, deps, acceptable, unacceptable, wf, clar_expected in DATASET:
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").write_text(json.dumps({"dependencies": deps}))
            s = AnimationProjectState(raw_user_request=req)
            inspect_project(td, s)
            d = route(s)
        tech = d.technology
        acceptable_hit = (tech in acceptable) or (tech is None and None in acceptable)
        if acceptable_hit:
            correct += 1
        if tech in unacceptable:
            unsafe += 1
        got_clar = d.clarification_needed is not None
        if got_clar and clar_expected:
            clar_tp += 1
        elif got_clar:
            clar_fp += 1
        elif clar_expected:
            clar_fn += 1
        if d.workflow == wf:
            wf_ok += 1
        rows.append({"request": req, "technology": tech, "workflow": d.workflow,
                     "clarification": got_clar, "acceptable": acceptable_hit,
                     "decided_by": d.decided_by})
    n = len(DATASET)
    report = {
        "acceptable_route_accuracy": round(correct / n, 3),
        "unsafe_route_rate": round(unsafe / n, 3),
        "clarification_precision": round(clar_tp / max(1, clar_tp + clar_fp), 3),
        "clarification_recall": round(clar_tp / max(1, clar_tp + clar_fn), 3),
        "workflow_accuracy": round(wf_ok / n, 3),
        "rows": rows,
    }
    out = Path(__file__).resolve().parent.parent / "docs" / "analysis" / "router-benchmark.json"
    out.write_text(json.dumps(report, indent=2))
    print({k: v for k, v in report.items() if k != "rows"})
    ok = report["acceptable_route_accuracy"] >= 0.85 and report["unsafe_route_rate"] == 0.0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
