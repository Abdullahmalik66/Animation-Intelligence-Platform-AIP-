# Migration: Monolithic Skills → Modular Platform

## Status
The modular layer is **additive**. Nothing in `skills/`, `references/`, `adapters/`, or `.github/` was modified. Both paths work today.

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
