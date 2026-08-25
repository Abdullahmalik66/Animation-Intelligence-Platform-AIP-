"""Tests for the v2 operational layers: schema enforcement, section fidelity,
retrieval, hybrid router, expanded inspector, validators2, Fable backend
contract, orchestrator modes and flags."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aip.schema_check import validate_all, validate_manifest, audit_sections, ConfigError  # noqa: E402
from aip.retrieval import RetrievalStore, RetrievalError  # noqa: E402
from aip.state import AnimationProjectState  # noqa: E402
from aip.inspector import inspect_project  # noqa: E402
from aip.hybrid_router import route, extract_signals  # noqa: E402
from aip.validators2 import run_pipeline, performance_validator  # noqa: E402
from aip.types import Readiness, Confidence, StopReason, SpecialistRequest  # noqa: E402
from aip.backends.fable import FableBackend, mock_transport  # noqa: E402
from aip.orchestrator import handle, _check_flags, FlagError, _build_request  # noqa: E402
from aip.assembler import assemble_context  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def make_project(td, deps=None, lock=True, assets=(), approved=()):
    deps = deps or {"react": "^18.3.0", "gsap": "^3.12.5"}
    Path(td, "package.json").write_text(json.dumps({"dependencies": deps}))
    if lock:
        Path(td, "package-lock.json").write_text(json.dumps(
            {"packages": {f"node_modules/{d}": {"version": v.lstrip("^~")}
                          for d, v in deps.items()}}))
    for a in assets:
        p = Path(td, a)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"v":"5.7","fr":30,"layers":[]}' if a.endswith(".json") else "riv")
    if approved:
        Path(td, ".aip-approved-assets.json").write_text(json.dumps({"approved": list(approved)}))
    return td


class TestSchemas(unittest.TestCase):
    def test_all_current_config_valid(self):
        validate_all()  # raises on failure

    def test_every_required_section_resolves(self):
        for row in audit_sections():
            if row["required"]:
                self.assertIn(row["match_type"], ("exact", "prefix"),
                              f"{row['module']} -> {row['section']}")

    def test_malformed_manifest_fails_clearly(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(json.dumps({"id": "x", "canonical_skill": "skills/gsap/SKILL.md"}))
        errors = validate_manifest(Path(f.name))
        self.assertTrue(any("missing required field" in e for e in errors))


class TestRetrieval(unittest.TestCase):
    def setUp(self):
        self.store = RetrievalStore()

    def test_valid_pointer(self):
        c = self.store.retrieve("skills/gsap/SKILL.md#Goal", reason="test")
        self.assertIn("## Goal", c.text)
        self.assertTrue(c.source_hash)

    def test_invalid_key(self):
        with self.assertRaises(RetrievalError):
            self.store.retrieve("no-hash-separator", reason="t")

    def test_forbidden_path(self):
        for bad in ("../etc/passwd#x", "/etc/passwd#x", "aip/state.py#x"):
            with self.assertRaises(RetrievalError):
                self.store.retrieve(bad, reason="t")

    def test_stale_hash_surfaced(self):
        c = self.store.retrieve("skills/gsap/SKILL.md#Role", reason="t",
                                expected_hash="deadbeef00000000")
        self.assertTrue(self.store.audit_log[-1]["stale_hash"])
        self.assertTrue(c.text)

    def test_duplicate_rejected(self):
        self.store.retrieve("skills/rive/SKILL.md#Goal", reason="t")
        with self.assertRaises(RetrievalError):
            self.store.retrieve("skills/rive/SKILL.md#Goal", reason="t")

    def test_budget_exceeded(self):
        s = RetrievalStore(max_total_tokens=10, max_tokens_per_request=5000)
        with self.assertRaises(RetrievalError):
            s.retrieve("skills/animation-performance/SKILL.md#Goal", reason="t")

    def test_concurrent_requests(self):
        keys = [f"skills/{t}/SKILL.md#Goal" for t in
                ("gsap", "rive", "lottie", "motion", "animejs", "threejs")]
        errs = []
        def worker(k):
            try:
                self.store.retrieve(k, reason="t")
            except RetrievalError as e:
                errs.append(e)
        threads = [threading.Thread(target=worker, args=(k,)) for k in keys]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(errs, [])
        self.assertEqual(len(self.store.audit_log), 6)


class TestHybridRouter(unittest.TestCase):
    def test_multi_intent_preserved(self):
        sigs = extract_signals("I want cards to appear one at a time as I scroll down")
        kinds = {(s.kind, s.value) for s in sigs}
        self.assertIn(("choreography", "staggered"), kinds)
        self.assertIn(("trigger", "scroll"), kinds)

    def test_scroll_stagger_needs_clarification(self):
        s = AnimationProjectState(raw_user_request="cards appear one at a time as I scroll")
        d = route(s)
        self.assertIsNotNone(d.clarification_needed)
        self.assertIsNone(d.technology)

    def test_clarification_answer_resolves(self):
        s = AnimationProjectState(raw_user_request="cards appear one at a time as I scroll")
        d = route(s, clarification_answer="appear once when in view")
        self.assertEqual(d.architecture, "viewport-triggered")
        self.assertIsNone(d.clarification_needed)

    def test_negation(self):
        s = AnimationProjectState(raw_user_request="please don't animate the header")
        d = route(s)
        self.assertEqual(d.technology, "no-animation")
        self.assertEqual(d.confidence, Confidence.HIGH)

    def test_explicit_technology_all_reachable(self):
        for phrase, tech in [("use anime.js for this", "animejs"),
                             ("use the motion library outside react", "motion"),
                             ("use the web animations api without a library", "waapi"),
                             ("use gsap", "gsap"), ("use lottie", "lottie"),
                             ("use rive", "rive"), ("use three.js", "threejs"),
                             ("just plain css please", "css")]:
            s = AnimationProjectState(raw_user_request=phrase)
            self.assertEqual(route(s).technology, tech, phrase)

    def test_unknown_escalates_not_guesses(self):
        s = AnimationProjectState(raw_user_request="tee mulle midagi ilusat")  # non-English
        d = route(s)
        self.assertEqual(d.decided_by, "llm-assisted-required")
        self.assertIsNone(d.technology)


class TestInspectorV2(unittest.TestCase):
    def test_pnpm_lock(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").write_text(json.dumps({"dependencies": {"gsap": "^3.12.0"}}))
            Path(td, "pnpm-lock.yaml").write_text("packages:\n  /gsap@3.12.5:\n    resolution: x\n")
            s = inspect_project(td, AnimationProjectState(raw_user_request="x"))
            self.assertEqual(s.resolved_versions.get("gsap"), "3.12.5")

    def test_yarn_lock(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").write_text(json.dumps({"dependencies": {"gsap": "^3.12.0"}}))
            Path(td, "yarn.lock").write_text('gsap@^3.12.0:\n  version "3.12.5"\n')
            s = inspect_project(td, AnimationProjectState(raw_user_request="x"))
            self.assertEqual(s.resolved_versions.get("gsap"), "3.12.5")

    def test_exports_from_node_modules(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td)
            nm = Path(td, "node_modules", "gsap")
            nm.mkdir(parents=True)
            (nm / "package.json").write_text(json.dumps(
                {"exports": {".": "./index.js", "./ScrollTrigger": "./st.js"},
                 "types": "types/index.d.ts"}))
            (nm / "types").mkdir()
            (nm / "types" / "index.d.ts").write_text("export function to(): void;")
            s = inspect_project(td, AnimationProjectState(raw_user_request="x"))
            self.assertIn("./ScrollTrigger", s.verified_exports["gsap"])
            self.assertTrue(any("declarations" in e.claim for e in s.evidence))

    def test_asset_discovery_and_trust(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td, deps={"lottie-web": "^5.12.2"},
                         assets=["assets/loader.json", "assets/hero.riv"],
                         approved=["assets/loader.json"])
            s = inspect_project(td, AnimationProjectState(raw_user_request="x"))
            trust = {a["path"]: a["trust"] for a in s.assets}
            self.assertEqual(trust["assets/loader.json"], "approved")
            self.assertEqual(trust["assets/hero.riv"], "unknown")
            self.assertTrue(any("trust not established" in u for u in s.unknowns))


class TestValidators2(unittest.TestCase):
    def _state(self, tech="gsap", **kw):
        s = AnimationProjectState(raw_user_request="x", selected_technology=tech,
                                  animation_value_classification="functional", **kw)
        return s

    def test_ownership_requires_structured_inventory(self):
        from aip.types import SpecialistResponse
        s = self._state()
        run_pipeline(s, SpecialistResponse())  # empty inventory
        own = next(r for r in s.validation_results if r["validator"] == "ownership")
        self.assertFalse(own["passed"])
        resp = SpecialistResponse(resource_inventory=[
            {"resource": "tl", "creator": "e", "owner": "c", "creation_point": "m",
             "update_point": "n", "teardown_point": "unmount",
             "cleanup_method": "revert", "shared_status": "l", "external_status": "n"}])
        s2 = self._state()
        run_pipeline(s2, resp)
        own2 = next(r for r in s2.validation_results if r["validator"] == "ownership")
        self.assertTrue(own2["passed"])

    def test_security_uses_populated_assets(self):
        s = self._state(tech="lottie")
        s.assets = [{"path": "a.json", "trust": "approved"}]
        run_pipeline(s, None)
        sec = next(r for r in s.validation_results if r["validator"] == "security")
        self.assertTrue(sec["passed"])
        s.assets = [{"path": "a.json", "trust": "unknown"}]
        run_pipeline(s, None)
        sec = next(r for r in s.validation_results if r["validator"] == "security")
        self.assertFalse(sec["passed"])

    def test_performance_not_unconditional(self):
        s = self._state()
        s.normalised_intent = "trigger:scroll, choreography:staggered"
        self.assertFalse(performance_validator(s)["passed"])
        s2 = self._state(tech="css")
        s2.normalised_intent = "trigger:hover"
        self.assertTrue(performance_validator(s2)["passed"])

    def test_readiness_confidence_independent_enums(self):
        s = self._state(tech="insufficient-evidence")
        run_pipeline(s, None)
        self.assertEqual(s.implementation_readiness, Readiness.INSUFFICIENT_EVIDENCE.value)
        self.assertEqual(s.confidence, Confidence.UNKNOWN.value)


class TestFableBackend(unittest.TestCase):
    def _req(self):
        return SpecialistRequest(request_id="r1", stable_prefix="GOV",
                                 dynamic_context="ctx", state_projection={},
                                 user_request="u")

    def test_blocked_without_transport(self):
        resp = FableBackend().run_request(self._req())
        self.assertEqual(resp.stop_reason, StopReason.ERROR)
        self.assertIn("BLOCKED", resp.error)

    def test_success_and_usage_capture(self):
        resp = FableBackend(transport=mock_transport()).run_request(self._req())
        self.assertEqual(resp.usage.method, "provider_reported")
        self.assertEqual(resp.stop_reason, StopReason.END_TURN)
        self.assertTrue(resp.resource_inventory)

    def test_refusal_is_application_state_no_retry(self):
        calls = []
        def transport(p):
            calls.append(1)
            return {"content": "", "stop_reason": "refusal"}
        resp = FableBackend(transport=transport).run_request(self._req())
        self.assertTrue(resp.refusal)
        self.assertEqual(len(calls), 1)  # never retried

    def test_transient_retry_then_success(self):
        state = {"n": 0}
        def transport(p):
            state["n"] += 1
            if state["n"] < 3:
                raise ConnectionError("blip")
            return mock_transport()(p)
        resp = FableBackend(transport=transport).run_request(self._req())
        self.assertEqual(resp.usage.model_calls, 3)
        self.assertFalse(resp.refusal)

    def test_timeout_exhaustion(self):
        def transport(p):
            raise TimeoutError()
        resp = FableBackend(transport=transport).run_request(self._req())
        self.assertEqual(resp.stop_reason, StopReason.TIMEOUT)


class TestOrchestrator(unittest.TestCase):
    def test_invalid_flag_combo_fails_clearly(self):
        with self.assertRaises(FlagError):
            _check_flags({"legacy_full_skill": True, "modular_context": True})

    def test_guided_returns_clarification(self):
        r = handle("cards appear one at a time as I scroll", user_mode="guided")
        self.assertEqual(r["status"], "needs_clarification")
        self.assertIn("come into view", r["clarification"].question)

    def test_guided_with_answer_completes(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td)
            r = handle("cards appear one at a time as I scroll", user_mode="guided",
                       project_dir=td, clarification_answer="appear once when in view")
            self.assertEqual(r["status"], "complete")
            self.assertEqual(r["state"].selected_technology, "gsap")

    def test_beginner_safe_default_disclosed(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td)
            r = handle("cards appear one at a time as I scroll", project_dir=td)
            self.assertEqual(r["status"], "complete")
            self.assertTrue(any("safer default" in a for a in r["state"].assumptions))
            self.assertIn("what_i_understood", r["explanation"])

    def test_expert_mode_exposes_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td)
            r = handle("use gsap to fade in the hero", user_mode="expert", project_dir=td)
            self.assertIn("routing_decision", r["explanation"])
            self.assertIn("context_manifest", r["explanation"])

    def test_fable_end_to_end_with_mock(self):
        with tempfile.TemporaryDirectory() as td:
            make_project(td)
            r = handle("use gsap to fade in the hero", project_dir=td,
                       flags={"modular_context": True, "modular_context_with_fable": True},
                       backend=FableBackend(transport=mock_transport()))
            self.assertEqual(r["status"], "complete")
            self.assertEqual(r["response"].usage.method, "provider_reported")
            own = next(v for v in r["state"].validation_results if v["validator"] == "ownership")
            self.assertTrue(own["passed"])

    def test_stable_prefix_hash_deterministic(self):
        s = AnimationProjectState(raw_user_request="x", selected_technology="gsap",
                                  selected_workflow="implementation")
        ctx = assemble_context(s)
        r1, r2 = _build_request(s, ctx), _build_request(s, ctx)
        self.assertEqual(r1.prefix_hash, r2.prefix_hash)
        self.assertTrue(r1.stable_prefix)


if __name__ == "__main__":
    unittest.main(verbosity=1)
