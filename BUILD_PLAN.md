# BUILD PLAN — AIP v3

> **Status:** Active. This document supersedes `PROJECT_FINAL_ARCHITECTURE_REVIEW.md`
> as the statement of intent. That file describes what was *architected*.
> This file describes what we are *building and shipping*.

---

## 1. The one-sentence goal

> A developer building a website runs **one command**, and from that moment their
> AI agent writes world-class animation code — and their CI catches it when
> anyone (human or AI) writes bad animation code.

---

## 2. What went wrong (honest assessment)

The repository is architecturally excellent and practically unusable. Five
concrete failures:

| # | Failure | Evidence in repo |
|---|---|---|
| 1 | **Dead on first run.** The default provider is a mock that returns the literal string `"mock implementation"`. | `aip/backends/mock.py:51` |
| 2 | **The only "real" provider is vapourware.** Fable has no SDK, no credentials, and is registered `UNAVAILABLE`. Every call returns `"Fable live integration BLOCKED"`. | `aip/backends/fable.py:47-51`, `aip/__main__.py:39` |
| 3 | **Installation is a mess.** There is no install — you `git clone` ~14,000 lines of Markdown, Python, tests, ADRs and benchmark artefacts into your web project. | `README.md` quickstart |
| 4 | **The docs lie.** README claims Codex/Gemini adapters are "✅ Stable"; those directories do not exist. Install URLs are `github.com/your-org/...` placeholders that 404. | `README.md`, `adapters/` |
| 5 | **Zero value without an AI.** Every capability is gated behind wiring up an agent. A frontend dev gets nothing on day one. | whole repo |

**Root cause:** the project was built inside-out — architecture first, adoption
last. Every item below reverses that.

---

## 3. What we are building

Three separable products, in priority order.

### Product A — `aip check` (the linter) 🔴 **HIGHEST LEVERAGE**

A zero-config, zero-AI, zero-network static analyser for animation code.

```bash
npx aip check ./src
```

```
src/components/Hero.tsx
  12:5  error    Animating `height` causes layout recalculation on every frame  perf/no-layout-property
  28:3  error    ScrollTrigger created but never killed — leaks on unmount      leak/gsap-no-revert
  41:1  warning  No prefers-reduced-motion fallback for this animation          a11y/no-reduced-motion-fallback

3 problems (2 errors, 1 warning) — 2 auto-fixable with --fix
```

**Why this first:** it is the only part of the system that delivers value to
someone who has never heard of AI agents. It uses knowledge that *already exists*
in `shared/governance.md` — we are giving existing rules a code path that reads
real source files. It also becomes the verification layer for everything else:
templates and LLM output are checked by the same linter.

### Product B — `aip init` (the agent knowledge pack)

```bash
npx aip init            # detects Claude Code / Cursor / Copilot, writes ONE file
```

Writes **exactly one file**, ~200 lines, into a marked block that can be updated
and removed cleanly. **Nothing else lands in the user's repo.** The 14,000 lines
of skills live inside the installed package, not in `git status`.

Primary target: **Claude Code** — as a proper skill/plugin, not a copied Markdown file.

### Product C — `aip ask` (the generator)

```bash
npx aip ask "cards fade in one at a time as I scroll" --write src/Cards.tsx
```

Router → technology + architecture → **real code**. Two paths:
- **Offline (default):** curated templates. No API key, no network, always works.
- **AI (optional):** if `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` is present, or when
  running inside Claude Code, the assembled context packet drives a real model.

Output is always passed through Product A before being shown. **The tool
validates its own output.**

---

## 4. What we are deleting

| Path | Reason |
|---|---|
| `aip/backends/fable.py` | Vapourware. No SDK, no credentials, permanently blocked. Its useful parts (retry, redaction, prompt-split) already exist in `gateway.py`. |
| `platform/` | Verbatim v1 duplicate of `aip/`. |
| `aip/pipeline.py`, `aip/validators.py`, `aip/router.py` | v1 duplicates of `orchestrator.py`, `validators2.py`, `hybrid_router.py`. |
| `skills/animation-router/SKILL.md.bak` | Committed backup file. |
| `nooa_pilot` flag + ADR-003 seam | Reserved integration for a framework nobody is adopting. |

**Renames:** `validators2.py` → `validators.py` (the "2" advertises an unfinished refactor).

---

## 5. Provider strategy — replacing Fable

Fable is removed. The gateway stays (it is genuinely well-designed and
vendor-neutral). We register real adapters:

| Adapter | Status | Notes |
|---|---|---|
| `TemplateAdapter` | **Default.** Always available. | Deterministic code generation from curated templates. No network, no key, no cost. Replaces `MockAdapter` as the default. |
| `ClaudeCodeAdapter` | **Primary AI path.** | Detects `CLAUDECODE=1` / `CLAUDE_CODE_*` env. Does not call the API — it *is* already inside a model. Emits the assembled context packet for the host agent to act on. Zero extra cost to the user. |
| `AnthropicAdapter` | Optional | `ANTHROPIC_API_KEY`. Claude Sonnet/Opus/Haiku. |
| `OpenAIAdapter` | Optional | `OPENAI_API_KEY`. |
| `OllamaAdapter` | Optional | Local, `http://localhost:11434`. |
| `MockAdapter` | Tests only | Deregistered from the CLI. |

**Selection order:** explicit `--provider` → Claude Code host → any configured API
key → `TemplateAdapter`. **The chain never dead-ends.** `aip doctor` explains in
plain English which path is active and why.

---

## 6. Claude Code as the primary surface

The concept is: *someone runs this inside Claude Code.* So Claude Code is not one
adapter among eight — it is the flagship integration.

```
.claude/
  skills/
    animation/
      SKILL.md          # ~200 lines. Progressive disclosure entry point.
```

The skill body is small. It tells Claude:
1. Before writing any animation, run `aip route "<request>"` to get the
   technology decision + the minimal governance packet.
2. After writing, run `aip check <file>` and fix anything it reports.
3. Deep knowledge stays on disk; fetch sections on demand via `aip context <key>`.

This is exactly what the existing assembler + retrieval + router were designed
for — we are finally connecting them to a real agent instead of a mock.

Also ship: `aip init claude|cursor|copilot|codex|windsurf|gemini|generic`, all
generated from **one template** so they cannot drift (today `AGENTS.md` is 244
lines, `CLAUDE.md` is 57, `.cursorrules` is 72 — already drifted).

---

## 7. Distribution — killing the mess

| Artefact | Contains | Ships as |
|---|---|---|
| CLI + runtime | `aip/`, `manifests/`, `schemas/` | PyPI wheel |
| Knowledge pack | `skills/`, `shared/`, `references/`, `integrations/`, templates | **bundled inside the wheel as package data** |
| Repo-only | `docs/`, `tests/`, `evals/`, ADRs, review docs | stays on GitHub, **never ships** |

Plus an `npx aip` shim, because the audience lives in Node and will not
`pip install` anything.

**Hard rule:** the tool never writes into the user's working tree except when
explicitly asked (`aip init`, `aip ask --write`). Traces move from
`docs/analysis/traces.jsonl` to `~/.cache/aip/`.

---

## 8. Governance: strict vs. relaxed

The gates are currently so strict they produce silence. `GOV-VERSION` refuses to
emit library code without exact lockfile evidence; `GOV-SECURITY` marks the
user's *own* `/public/hero.json` untrusted. In a pnpm workspace or Bun project the
inspector resolves nothing → `Insufficient Evidence` → no output, no explanation.

- **`--relaxed` (new default):** warn, but still produce code.
- **`--strict`:** current behaviour, for enterprise CI.
- Local assets under `public/`, `static/`, `assets/` are **trusted by default**.
- When a gate blocks output, say so in plain English with the exact fix.
  **Never return silence.**

---

## 9. Build order

```
▸ PHASE 0  Cleanup & truth                    ← deletions, honest README, traces out of repo
▸ PHASE 1  aip check                          ← THE unlock. 12 rules. Zero AI.
▸ PHASE 2  aip init + npx shim                ← one command, one file, no mess
▸ PHASE 3  TemplateAdapter + real providers   ← aip ask produces real code offline
▸ PHASE 4  Claude Code skill                  ← flagship integration
▸ PHASE 5  Frameworks, freshness, demo, proof ← Vue/Svelte/Astro, CI badges, demo GIF
```

### Phase 1 rule set (all derived from existing `GOV-*` rules)

| Rule ID | Detects | Governance |
|---|---|---|
| `a11y/no-reduced-motion-fallback` | animation with no `prefers-reduced-motion` in scope | GOV-A11Y |
| `a11y/no-rapid-flash` | cycle < 333ms toggling opacity/background (>3Hz) | GOV-A11Y |
| `a11y/infinite-no-pause` | `iteration-count: infinite` with no pause control | GOV-A11Y |
| `perf/no-layout-property` | animating `width`/`height`/`top`/`left`/`margin` | GOV-PERF |
| `perf/no-layout-thrash` | layout read inside RAF/scroll handler followed by write | GOV-PERF |
| `leak/gsap-no-revert` | `gsap.context()`/`ScrollTrigger.create()` with no `revert()`/`kill()` | GOV-OWNERSHIP |
| `leak/observer-not-disconnected` | `new IntersectionObserver` with no `.disconnect()` | GOV-OWNERSHIP |
| `leak/raf-not-cancelled` | `requestAnimationFrame` loop with no `cancelAnimationFrame` | GOV-OWNERSHIP |
| `leak/webgl-not-disposed` | Three.js geometry/material/texture never `.dispose()`d | GOV-OWNERSHIP |
| `leak/listener-not-removed` | `addEventListener` in effect with no removal | GOV-OWNERSHIP |
| `arch/over-engineered` | GSAP/Three.js imported but only used for a hover/fade | GOV-ROUTING |
| `sec/untrusted-asset` | remote `.lottie`/`.riv`/`.glb` with no integrity/CSP note | GOV-SECURITY |

Output formats: human (default), `--format json`, `--format sarif`, `--format github`.

---

## 10. Definition of done

A developer who has never heard of this project can, in under five minutes:

1. `npx aip check ./src` → sees **real bugs in their own code**, no setup, no AI.
2. `npx aip init` → **one file** appears, their agent now writes correct animations.
3. `npx aip ask "..." --write` → **real, accessible, leak-free code** lands in a file.
4. `git status` shows **only the files they asked for**.

---

## 11. Non-goals

- Not an animation library. We ship **zero runtime JavaScript** to end users.
- Not a component kit. We do not replace GSAP, Motion, or Three.js.
- Not a hosted service. Everything runs locally.
- Not fine-tuning a model. The intelligence is in structure, not weights.
