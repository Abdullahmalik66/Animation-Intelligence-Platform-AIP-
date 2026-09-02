"""Unit tests for the platform layer. Stdlib unittest only."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aip.state import AnimationProjectState  # noqa: E402
from aip.inspector import inspect_project, installed_animation_technologies  # noqa: E402
from aip.assembler import assemble_context, load_governance_rules, ContextCompressor  # noqa: E402
from aip.validators import run_pipeline  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class TestGovernance(unittest.TestCase):
    def test_all_rule_ids_parse(self):
        rules = load_governance_rules()
        for rid in ["GOV-VERSION", "GOV-A11Y", "GOV-SECURITY", "GOV-OWNERSHIP",
                    "GOV-READINESS", "GOV-CONFIDENCE", "GOV-DEPTH", "GOV-EVIDENCE",
                    "GOV-PERF", "GOV-REVIEW-FIRST", "GOV-ROUTING"]:
            self.assertIn(rid, rules)

    def test_provenance_present(self):
        for text in load_governance_rules().values():
            self.assertIn("Provenance:", text)


class TestManifests(unittest.TestCase):
    def test_manifests_reference_existing_canonical_files(self):
        for mf in (ROOT / "manifests").glob("*.json"):
            data = json.loads(mf.read_text())
            if "canonical_skill" in data:
                self.assertTrue((ROOT / data["canonical_skill"]).is_file(),
                                f"{mf.name}: missing {data['canonical_skill']}")
                for mod in data.get("modules", []):
                    self.assertTrue((ROOT / mod["source"]).is_file(),
                                    f"{mf.name}: missing module source {mod['source']}")

    def test_required_manifest_fields(self):
        required = {"id", "purpose", "triggers", "exclusions",
                    "required_shared_modules", "canonical_skill", "workflows"}
        for mf in (ROOT / "manifests").glob("*.json"):
            data = json.loads(mf.read_text())
            if "canonical_skill" in data:
                self.assertTrue(required <= set(data), f"{mf.name} missing {required - set(data)}")


class TestInspector(unittest.TestCase):
    def test_lockfile_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").write_text(json.dumps(
                {"dependencies": {"gsap": "^3.12.0", "react": "^18.0.0"}}))
            Path(td, "package-lock.json").write_text(json.dumps(
                {"packages": {"node_modules/gsap": {"version": "3.12.5"}}}))
            s = inspect_project(td, AnimationProjectState(raw_user_request="x"))
            self.assertEqual(s.resolved_versions["gsap"], "3.12.5")
            self.assertEqual(s.framework, "react")
            self.assertEqual(installed_animation_technologies(s), ["gsap"])

    def test_missing_project_marks_unknown(self):
        s = AnimationProjectState(raw_user_request="x")
        with tempfile.TemporaryDirectory() as td:
            inspect_project(td, s)
        self.assertTrue(any("package.json" in u for u in s.unknowns))



class TestAssembler(unittest.TestCase):
    def test_examples_excluded_for_review(self):
        s = AnimationProjectState(raw_user_request="review this",
                                  selected_technology="gsap",
                                  selected_workflow="code-review")
        ctx = assemble_context(s)
        self.assertFalse(s.selected_examples)
        self.assertTrue(any(e["id"] == "examples/*" for e in ctx.manifest["excluded"]))

    def test_release_gating_never_dropped(self):
        s = AnimationProjectState(raw_user_request="build it",
                                  selected_technology="rive",
                                  selected_workflow="implementation")
        ctx = assemble_context(s, budgets={"standard": 100})  # absurdly small budget
        ids = {i["id"] for i in ctx.manifest["included"] if i.get("release_gating")}
        self.assertIn("GOV-A11Y", ids)
        self.assertIn("GOV-SECURITY", ids)

    def test_compressor_failure_is_safe(self):
        class Broken(ContextCompressor):
            def compress(self, chunks, policy=None):
                raise RuntimeError("boom")
        s = AnimationProjectState(raw_user_request="build",
                                  selected_technology="css",
                                  selected_workflow="implementation")
        ctx = assemble_context(s, compressor=Broken())
        self.assertTrue(ctx.chunks)  # uncompressed context survived


class TestValidatorsAndModes(unittest.TestCase):
    def test_insufficient_evidence_readiness(self):
        s = AnimationProjectState(raw_user_request="x",
                                  selected_technology="insufficient-evidence")
        s.unknowns.append("stack unknown")
        run_pipeline(s)
        self.assertEqual(s.implementation_readiness, "Insufficient Evidence")
        self.assertEqual(s.confidence, "Unknown")


    def test_state_projection_hides_internal_fields(self):
        s = AnimationProjectState(raw_user_request="x")
        s.token_usage = {"secret": 1}
        proj = s.projection(["raw_user_request", "token_usage"])
        self.assertNotIn("token_usage", proj)


if __name__ == "__main__":
    unittest.main(verbosity=2)
