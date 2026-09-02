"""Provider-neutral gateway tests + reusable adapter conformance suite
(Workstreams 19, 24). No provider SDK, no billable calls."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aip.gateway import (ModelGateway, ProviderRegistry, ProviderStatus,  # noqa: E402
                         ProviderError, ProviderErrorKind, ModelCapabilities,
                         Support, select_provider, RetryPolicy)
from aip.backends.mock import MockAdapter, ReplayAdapter  # noqa: E402
from aip.types import ModelRequest, StopReason  # noqa: E402
from aip.orchestrator import handle, _check_flags  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def req(rid="r1"):
    return ModelRequest(request_id=rid, stable_prefix="GOV", dynamic_context="ctx",
                        state_projection={}, user_request="u")


class AdapterConformance:
    """Reusable conformance mixin: every adapter must pass these."""
    def make_adapter(self):
        raise NotImplementedError

    def test_basic_text_response(self):
        resp = self.make_adapter().invoke(req())
        self.assertTrue(resp.content)
        self.assertEqual(resp.stop_reason, StopReason.END_TURN)

    def test_usage_reporting_method_labelled(self):
        resp = self.make_adapter().invoke(req())
        self.assertIn(resp.usage.method,
                      ("provider_reported", "tokenizer_reported",
                       "estimated_chars_div_4", "unknown"))

    def test_no_raw_leak_outside_metadata(self):
        resp = self.make_adapter().invoke(req())
        # canonical fields only; provider payload confined to raw_metadata
        self.assertIsInstance(resp.raw_metadata, dict)


class TestMockConformance(AdapterConformance, unittest.TestCase):
    def make_adapter(self):
        return MockAdapter()


class TestReplayConformance(AdapterConformance, unittest.TestCase):
    def make_adapter(self):
        import json, tempfile
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        f.write(json.dumps({"content": "recorded answer", "stop_reason": "end_turn",
                            "usage": {"method": "provider_reported",
                                      "input_tokens": 100, "output_tokens": 20}}) + "\n")
        f.close()
        return ReplayAdapter(fixture_path=f.name)


class TestCapabilities(unittest.TestCase):
    def test_unknown_is_not_false(self):
        caps = ModelCapabilities()  # everything Unknown
        ok, gaps = caps.satisfies({"structured_output": Support.SUPPORTED})
        self.assertFalse(ok)
        self.assertIn("Unknown", gaps[0])  # explicit, not silently False

    def test_incompatible_workflow_rejected(self):
        reg = ProviderRegistry()
        weak = MockAdapter(provider_id="weak",
                           capabilities=ModelCapabilities(text_input=Support.SUPPORTED,
                                                          structured_output=Support.UNSUPPORTED))
        reg.register(weak)
        d = select_provider(reg, workflow="implementation")
        self.assertIsNone(d.provider_id)
        self.assertTrue(any("structured_output" in r for r in d.rejected))


class TestSelectionPolicy(unittest.TestCase):
    def _registry(self):
        reg = ProviderRegistry()
        reg.register(MockAdapter(provider_id="a"))
        reg.register(MockAdapter(provider_id="b"))
        return reg

    def test_fixed_provider(self):
        d = select_provider(self._registry(), "implementation",
                            policy="fixed_provider", fixed="b")
        self.assertEqual(d.provider_id, "b")

    def test_allowlist_enforced(self):
        d = select_provider(self._registry(), "implementation",
                            policy="balanced", allowlist=["b"])
        self.assertEqual(d.provider_id, "b")
        self.assertTrue(any("allowlist" in r for r in d.rejected))

    def test_local_only(self):
        reg = ProviderRegistry()
        remote = MockAdapter(provider_id="remote")
        remote.capabilities = ModelCapabilities(text_input=Support.SUPPORTED,
                                                structured_output=Support.SUPPORTED,
                                                local_execution=Support.UNSUPPORTED)
        reg.register(remote)
        d = select_provider(reg, "implementation", policy="balanced", local_only=True)
        self.assertIsNone(d.provider_id)

    def test_no_available_provider_explained(self):
        d = select_provider(ProviderRegistry(), "implementation")
        self.assertIsNone(d.provider_id)
        self.assertIn("No compatible provider", d.rationale)

    def test_routing_independent_of_provider(self):
        # Animation route decided before provider selection: technology identical
        # whichever provider is registered.
        import tempfile, json as _json
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").write_text(_json.dumps(
                {"dependencies": {"react": "^18", "gsap": "^3.12"}}))
            r1 = handle("use gsap to fade in the hero", project_dir=td)
            reg = ProviderRegistry(); reg.register(MockAdapter())
            r2 = handle("use gsap to fade in the hero", project_dir=td,
                        flags={"modular_context": True,
                               "modular_context_with_model": True},
                        gateway=ModelGateway(registry=reg), provider="mock")
            self.assertEqual(r1["state"].selected_technology,
                             r2["state"].selected_technology)


class TestErrorNormalisation(unittest.TestCase):
    def _gw(self, adapter, fallback=None):
        reg = ProviderRegistry()
        reg.register(adapter)
        if fallback:
            reg.register(fallback)
        return ModelGateway(registry=reg,
                            retry=RetryPolicy(max_attempts=3, backoff_s=0.0),
                            fallback_order=[fallback.provider_id] if fallback else [])

    def test_refusal_never_retried_and_not_transport_error(self):
        a = MockAdapter(raise_kind=ProviderErrorKind.CONTENT_REFUSAL)
        resp, _ = self._gw(a).run(req(), fixed="mock")
        self.assertTrue(resp.refusal)
        self.assertEqual(resp.stop_reason, StopReason.REFUSAL)
        self.assertEqual(a._calls, 1)
        self.assertIsNotNone(resp.refusal_record)

    def test_transient_retry_bounded(self):
        a = MockAdapter(raise_kind=ProviderErrorKind.CONNECTION_FAILURE, fail_times=2)
        resp, _ = self._gw(a).run(req(), fixed="mock")
        self.assertEqual(resp.retry_count, 2)
        self.assertFalse(resp.refusal)

    def test_terminal_not_retried(self):
        a = MockAdapter(raise_kind=ProviderErrorKind.AUTHENTICATION_FAILURE)
        resp, _ = self._gw(a).run(req(), fixed="mock")
        self.assertEqual(a._calls, 1)
        self.assertIn("AuthenticationFailure", resp.error)

    def test_fallback_on_unavailability_not_on_refusal(self):
        broken = MockAdapter(provider_id="mock",
                             raise_kind=ProviderErrorKind.PROVIDER_UNAVAILABLE)
        backup = MockAdapter(provider_id="backup")
        resp, _ = self._gw(broken, fallback=backup).run(req(), fixed="mock")
        self.assertTrue(resp.fallback_used)
        refusing = MockAdapter(provider_id="mock",
                               raise_kind=ProviderErrorKind.CONTENT_REFUSAL)
        resp2, _ = self._gw(refusing, fallback=backup).run(req(), fixed="mock")
        self.assertTrue(resp2.refusal)
        self.assertFalse(resp2.fallback_used)  # safety not bypassed


class TestCoreIndependence(unittest.TestCase):
    NEUTRAL_MODULES = ("gateway", "orchestrator", "assembler", "types", "state",
                       "hybrid_router", "validators", "retrieval", "check")

    def test_no_vendor_names_in_neutral_modules(self):
        """The core must never name a specific provider."""
        for mod in self.NEUTRAL_MODULES:
            src = (ROOT / "aip" / f"{mod}.py").read_text(encoding="utf-8").lower()
            for vendor in ("fable", "anthropic", "openai", "gemini"):
                self.assertNotIn(f"from .backends.{vendor}", src, mod)
                self.assertNotIn(f"import {vendor}", src, mod)

    def test_fable_is_fully_removed(self):
        """Fable was vapourware — no SDK, no credentials, permanently blocked.
        It must not reappear anywhere in the runtime."""
        self.assertFalse((ROOT / "aip" / "backends" / "fable.py").exists())
        for path in (ROOT / "aip").rglob("*.py"):
            src = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("fable", src, f"{path.name} still references fable")

    def test_deleted_v1_modules_stay_deleted(self):
        for name in ("pipeline.py", "router.py", "validators2.py"):
            self.assertFalse((ROOT / "aip" / name).exists(),
                             f"aip/{name} should have been removed")
        self.assertFalse((ROOT / "platform").exists())

    def test_registry_zero_one_many(self):
        empty = ProviderRegistry()
        self.assertEqual(empty.list_available(), [])
        one = ProviderRegistry(); one.register(MockAdapter())
        self.assertEqual(len(one.list_available()), 1)
        many = ProviderRegistry()
        many.register(MockAdapter(provider_id="a"))
        many.register(MockAdapter(provider_id="b"))
        self.assertEqual(len(many.list_available()), 2)

    def test_fable_flag_alias_is_rejected(self):
        from aip.orchestrator import FlagError
        with self.assertRaises(FlagError):
            _check_flags({"modular_context": True,
                          "modular_context_with_fable": True})


class TestTracesStayOutOfRepo(unittest.TestCase):
    def test_trace_path_is_not_inside_repo(self):
        from aip.orchestrator import TRACE_PATH
        self.assertNotIn(str(ROOT), str(TRACE_PATH),
                         "traces must never be written into the user's repo")


if __name__ == "__main__":
    unittest.main(verbosity=1)
