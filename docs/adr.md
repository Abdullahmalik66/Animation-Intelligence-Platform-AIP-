# Architecture Decision Records

## ADR-001 — Modular context layer built *around* monolithic skills
**Status:** Accepted (2026-08-25)
Skills in `skills/*/SKILL.md` remain the canonical knowledge source. The platform layer (`aip/`, `manifests/`, `shared/`, `schemas/`) selects and extracts sections at assembly time instead of rewriting skills. Extraction is loss-aware: every shared rule in `shared/governance.md` carries provenance to its source file/section; unmatched sections become retrieval pointers, never silent drops.
**Rollback:** feature flag `legacy_full_skill=True` loads whole SKILL.md files exactly as before.

## ADR-002 — Python stdlib-only orchestration
**Status:** Accepted
The repo had zero runtime code and no dependency policy. The deterministic layer (inspection, routing heuristics, assembly, validation, token estimation, tests) uses Python ≥3.10 stdlib only. No packages are installed. Token counts are chars/4 **estimates** and labelled as such everywhere; exact counts require a model tokenizer/API, which is not available in this repository.

## ADR-003 — NOOA pilot deferred; abstraction implemented
**Status:** Deferred, abstraction in place
NVIDIA Object-Oriented Agents is **not installed** and this repository has no Python packaging, no approved dependency source, and no network-verified NOOA API documentation available in this environment. Fabricating its API would violate the mandate. Instead:
- `aip.pipeline.SpecialistBackend` is the framework-neutral seam (typed state in, assembled context in, result out).
- `PromptPacketBackend` is the default deterministic implementation.
- Feature flag `nooa_pilot` exists but is off.
**To activate:** verify NOOA's installed version and API, implement `SpecialistBackend` in a new `aip/backends/nooa.py`, pilot with `gsap` and `rive` specialists per the mandate, keep the flag opt-in.

## ADR-004 — Compression optional and failure-safe
**Status:** Accepted
`aip.assembler.ContextCompressor` is a provider-neutral interface (`compress`/`retrieve`). Default is pass-through. Headroom is not installed and external services are not approved for repository content; any provider must be explicitly configured. Compression failures fall back to the uncompressed selected context (tested). Compression never removes release-gating rules — those are excluded from trimming entirely.

## ADR-005 — Two-stage routing: deterministic hypotheses, LLM authority preserved
**Status:** Accepted
Stage 1 (technology/architecture) and Stage 2 (workflow) in `aip/router.py` are deterministic heuristics that produce machine-readable, explainable routes. Ambiguity yields `insufficient-evidence` + recorded unknowns, never a guess (e.g. "moves as I scroll" requires scroll-linked vs viewport-triggered disambiguation). The canonical `skills/animation-router/SKILL.md` remains the semantic authority for the LLM; the deterministic router selects context, it does not overrule the model on genuine trade-offs.

## ADR-006 — Release-gating rules are budget-exempt
**Status:** Accepted
`GOV-VERSION`, `GOV-OWNERSHIP`, `GOV-A11Y`, `GOV-SECURITY`, `GOV-READINESS` are never trimmed to meet a token budget. If only gating content remains and the budget is still exceeded, the manifest records `budget_exceeded: true` rather than dropping safety content.

## ADR-007 — Git initialised as rollback substrate
**Status:** Accepted
The repository was not under version control (a discovered risk). `git init` was performed and the pre-change state tagged `legacy-monolithic-baseline` before any modification.
