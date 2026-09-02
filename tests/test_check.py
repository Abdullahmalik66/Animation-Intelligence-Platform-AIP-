"""Tests for the animation linter (`aip check`).

Two guarantees:
  1. Every rule fires on known-bad code.
  2. NO rule fires on known-good code (false positives destroy trust).
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from aip.check import check_path, format_report

FIXTURES = Path(__file__).parent / "fixtures"


class TestBadCodeIsCaught(unittest.TestCase):
    """Each rule must fire on the fixture built to violate it."""

    @classmethod
    def setUpClass(cls):
        cls.css = check_path(FIXTURES / "bad-animations.css")
        cls.jsx = check_path(FIXTURES / "bad-animations.jsx")
        cls.css_rules = {f.rule for f in cls.css.findings}
        cls.jsx_rules = {f.rule for f in cls.jsx.findings}

    def test_layout_property_in_transition(self):
        self.assertIn("perf/no-layout-property", self.css_rules)

    def test_missing_reduced_motion(self):
        self.assertIn("a11y/no-reduced-motion-fallback", self.css_rules)

    def test_rapid_flash_above_3hz(self):
        self.assertIn("a11y/no-rapid-flash", self.css_rules)

    def test_infinite_without_pause(self):
        self.assertIn("a11y/infinite-no-pause", self.css_rules)

    def test_gsap_scrolltrigger_leak(self):
        self.assertIn("leak/gsap-no-revert", self.jsx_rules)

    def test_observer_leak(self):
        self.assertIn("leak/observer-not-disconnected", self.jsx_rules)

    def test_raf_leak(self):
        self.assertIn("leak/raf-not-cancelled", self.jsx_rules)

    def test_webgl_leak(self):
        self.assertIn("leak/webgl-not-disposed", self.jsx_rules)

    def test_listener_leak(self):
        self.assertIn("leak/listener-not-removed", self.jsx_rules)

    def test_layout_thrash(self):
        self.assertIn("perf/no-layout-thrash", self.jsx_rules)

    def test_untrusted_remote_asset(self):
        self.assertIn("sec/untrusted-asset", self.jsx_rules)

    def test_findings_have_usable_metadata(self):
        for f in self.css.findings + self.jsx.findings:
            self.assertGreater(f.line, 0, f"{f.rule} has no line number")
            self.assertTrue(f.governance.startswith("GOV-"),
                            f"{f.rule} is not traced to a governance rule")
            self.assertTrue(f.fix_hint, f"{f.rule} gives no fix hint")
            self.assertIn(f.severity, ("error", "warning"))


class TestGoodCodeIsClean(unittest.TestCase):
    """False positives are worse than missed findings — they destroy trust."""

    def test_good_css_has_no_findings(self):
        report = check_path(FIXTURES / "good-animations.css")
        self.assertEqual(report.findings, [],
                         f"False positives: {[f.rule for f in report.findings]}")

    def test_good_jsx_has_no_findings(self):
        report = check_path(FIXTURES / "good-animations.jsx")
        self.assertEqual(report.findings, [],
                         f"False positives: {[f.rule for f in report.findings]}")


class TestCommentsAreIgnored(unittest.TestCase):
    def test_commented_out_code_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.css"
            p.write_text("/* transition: height 1s; */\n"
                         "/* @keyframes x { from { width: 0 } } */\n",
                         encoding="utf-8")
            self.assertEqual(check_path(p).findings, [])


class TestOutputFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = check_path(FIXTURES / "bad-animations.css")

    def test_json_is_parseable(self):
        data = json.loads(format_report(self.report, "json"))
        self.assertEqual(data["errors"], self.report.error_count)
        self.assertEqual(len(data["findings"]), len(self.report.findings))

    def test_sarif_is_valid_shape(self):
        data = json.loads(format_report(self.report, "sarif"))
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(len(data["runs"][0]["results"]),
                         len(self.report.findings))

    def test_github_annotations(self):
        out = format_report(self.report, "github")
        self.assertTrue(out.startswith("::"))
        self.assertIn("file=", out)

    def test_human_is_readable(self):
        out = format_report(self.report, "human", color=False)
        self.assertIn("problems", out)
        self.assertIn("perf/no-layout-property", out)


class TestAutofix(unittest.TestCase):
    def test_fix_adds_reduced_motion_guard(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "bad-animations.css"
            shutil.copy(FIXTURES / "bad-animations.css", target)

            before = check_path(target)
            self.assertTrue(any(f.rule == "a11y/no-reduced-motion-fallback"
                                for f in before.findings))

            check_path(target, fix=True)
            text = target.read_text(encoding="utf-8")
            self.assertIn("prefers-reduced-motion", text)

            after = check_path(target)
            self.assertFalse(any(f.rule == "a11y/no-reduced-motion-fallback"
                                 for f in after.findings))

    def test_fix_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "x.css"
            shutil.copy(FIXTURES / "bad-animations.css", target)
            check_path(target, fix=True)
            once = target.read_text(encoding="utf-8")
            check_path(target, fix=True)
            self.assertEqual(once, target.read_text(encoding="utf-8"))


class TestTraversal(unittest.TestCase):
    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "b.css").write_text(
                "a{transition:height 1s}", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "a.css").write_text(
                "a{transition:transform 1s}", encoding="utf-8")
            report = check_path(root)
            self.assertEqual(report.files_scanned, 1)

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            check_path("/nonexistent/path/xyz")


if __name__ == "__main__":
    unittest.main()
