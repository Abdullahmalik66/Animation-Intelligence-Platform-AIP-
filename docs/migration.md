# Migration: Monolithic Skills → Modular Platform

## Status (v2 — production-completion pass)
Additive. Canonical skills untouched. Two orchestrators exist:
- `aip/pipeline.py` — v1 (legacy comparison path, unchanged)
- `aip/orchestrator.py` — v2 operational path: hybrid multi-signal router, guided clarification, executable retrieval, structured Fable backend contract, structured validators, JSONL traces, validated flag combinations, CLI consumer (`python3 -m aip`).

## Fable 5 live integration — BLOCKED
No SDK installed and no credentials configured in this repository. Implemented instead: full offline adapter contract (`aip/backends/fable.py`) with refusal-as-application-state, bounded transient retry, timeout, fallback policy, provider usage capture, redaction, and a mock transport with contract tests. **Activation path:** `pip install .[fable]`, set credentials, implement a `Transport` from the verified SDK, pass it to `FableBackend`. Do not claim live integration until then. Model-in-the-loop equivalence (Workstream 18) is likewise blocked pending live access; the harness comparison currently covers routing/safety/token estimates only.

## Release gate (must all hold before modular becomes the default production path)
- [x] Safety decisions equivalent or better — scenario suite compares legacy vs modular routing; gate PASS (15/15)
- [x] No critical governance rule lost — release-gating `GOV-*` rules asserted present in assembled context; budget-exempt
- [x] Code passes tests — 16 unit tests + scenario suite green
- [x] Beginner explanations produced and expose unknowns (tested)
- [x] Token use demonstrably lower — **estimated** 367,962 → 18,803 tokens across 15 scenarios (chars/4 heuristic; exact API-reported usage not yet measured — see Limitations)
- [ ] API-measured token usage on real model calls (blocked: no API access in this repo; wire `SpecialistBackend` to a real client and record `input_tokens`/`cache_read_tokens`)

## Phased migration
1. **Now:** modular assembly available via `aip.pipeline.handle_request`; legacy remains default for agent adapters (they still read SKILL.md directly).
2. **Next:** point one adapter (e.g. Claude) at generated modular packets; compare outcomes with `evals/` cases.
3. **Later:** deprecate direct whole-file loading in adapters; keep `legacy_full_skill` flag indefinitely as rollback.

## Rollback procedure (tested paths)
- **Behavioural:** `handle_request(..., flags={"legacy_full_skill": True, "modular_context": False})` — exercised by every scenario-suite run.
- **Repository:** `git checkout legacy-monolithic-baseline` restores the exact pre-platform state.
- Canonical skills were never edited, so no knowledge restoration is ever required.

## Known limitations
- Token figures are chars/4 estimates until a model API is wired in.
- `route_stage1/2` heuristics are context-selection aids; ambiguous requests correctly fall to `insufficient-evidence` and rely on the LLM router skill.
- Section extraction depends on `##` heading structure in skills; missing sections degrade to explicit retrieval pointers (visible in the manifest), never silent loss.
- NOOA and Headroom evaluations are design-complete but install-blocked (ADR-003, ADR-004).
