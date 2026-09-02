# AIP — Animation Intelligence Platform

**A zero-config linter for web animation code.** It catches the bugs that ship to
production: memory leaks, jank, and accessibility violations.

No AI. No network. No API keys. No config file.

```bash
python -m aip check src/
```

```
bad-animations.jsx
    13:5  error    ScrollTrigger created but never reverted or killed. This leaks
                   on unmount and duplicates on remount.            leak/gsap-no-revert
                   → Return () => ctx.revert() from your effect.
    33:7  error    requestAnimationFrame loop with no cancelAnimationFrame. The
                   loop keeps running after the component unmounts. leak/raf-not-cancelled
                   → Store the frame id and cancelAnimationFrame(id) on cleanup.

13 problems (10 errors, 3 warnings)
4 files scanned.
```

Every finding comes with the fix on the `→` line, not just the complaint.

Exit code is `1` when there are errors, so it drops straight into CI.

---

## Why

Animation bugs are uniquely bad. They don't throw. Tests pass. Types check.
The page just gets slower every time a user navigates, or it makes someone with
a vestibular disorder physically sick.

Existing tooling doesn't help:

- ESLint doesn't know a GSAP timeline needs `revert()`.
- Lighthouse tells you the page is slow, not which `@keyframes` did it.
- Type checkers can't see that your `IntersectionObserver` outlives the component.

AIP encodes the rules an experienced animation engineer applies in code review,
and runs them in milliseconds.

---

## Install

Requires Python 3.10+. No dependencies.

```bash
git clone https://github.com/your-org/frontend-animation-agent-skills
cd frontend-animation-agent-skills
python -m aip check .
```

A `pip install aip` / `npx aip` distribution is on the roadmap (see
[`BUILD_PLAN.md`](BUILD_PLAN.md)).

---

## Usage

```bash
python -m aip check <path>            # lint a file or directory
python -m aip check src/ --fix        # apply safe mechanical fixes
python -m aip check src/ --format json
```

`--format` accepts `human` (default), `json`, `sarif`, and `github`.

- `json` — for scripts and agents.
- `sarif` — upload to GitHub code scanning.
- `github` — emits `::error file=...` workflow annotations.

Scanned extensions: `.css`, `.scss`, `.sass`, `.less`, `.js`, `.jsx`, `.ts`,
`.tsx`, `.mjs`, `.cjs`. `node_modules`, build output, and dotfiles are skipped.

### `--fix`

Only applies changes that cannot alter behaviour — e.g. rewriting an animated
`left`/`top` to a `transform`, or appending a `prefers-reduced-motion` block.
Anything requiring judgement (where to put a cleanup function) is reported, never
rewritten.

---

## Rules

### Memory leaks — `leak/*`

| Rule | Catches |
| --- | --- |
| `leak/gsap-no-revert` | GSAP timeline/tween created in an effect with no `revert()` or `kill()` |
| `leak/raf-not-cancelled` | `requestAnimationFrame` loop with no `cancelAnimationFrame` |
| `leak/observer-not-disconnected` | `IntersectionObserver`/`ResizeObserver`/`MutationObserver` never disconnected |
| `leak/webgl-not-disposed` | Three.js geometries/materials/textures never `dispose()`d |
| `leak/listener-not-removed` | `addEventListener` in an effect with no matching removal |

These are errors. Each one is a component that permanently retains memory after
unmount, and they compound across navigations in an SPA.

### Accessibility — `a11y/*`

| Rule | Catches |
| --- | --- |
| `a11y/no-reduced-motion-fallback` | Animation with no `prefers-reduced-motion` guard |
| `a11y/no-rapid-flash` | Flashing faster than 3Hz — a seizure risk (WCAG 2.3.1) |
| `a11y/infinite-no-pause` | `infinite` animation longer than 5s with no pause control (WCAG 2.2.2) |

### Performance — `perf/*`

| Rule | Catches |
| --- | --- |
| `perf/no-layout-property` | Animating `left`, `top`, `width`, `height`, `margin` — forces layout on every frame |
| `perf/no-layout-thrash` | Reading `offsetWidth`/`getBoundingClientRect` inside a rAF loop that also writes |

### Other

| Rule | Catches |
| --- | --- |
| `sec/untrusted-asset` | Lottie/Rive assets loaded from an unpinned third-party origin |
| `arch/over-engineered` | A heavy animation library imported for something CSS does natively |

---

## CI

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
- run: python -m aip check src/ --format github
```

Failing the build on `leak/*` and `a11y/*` is the point. Those are the classes of
bug that are effectively invisible in review.

---

## For AI agents

`aip check --format json` gives an agent a precise, structured critique of code
it just wrote, with no model call. The intended loop:

1. Agent writes animation code.
2. Agent runs `python -m aip check <file> --format json`.
3. Agent reads `rule`, `message`, and `line` and repairs its own output.

Each finding includes the fix, not just the complaint. One-command agent wiring
(`aip init`) is the next milestone.

The `skills/` directory holds authoring guidance for animation libraries (GSAP,
Motion, Three.js, Lottie, Rive, Anime.js) intended to be loaded as agent context.

---

## What this is not

Being direct about scope, because the repo previously overpromised:

- **Not an AI code generator.** `aip run` exists but routes requests against a
  mock provider. Treat it as experimental.
- **Not a runtime profiler.** It reads source code. It never executes your app,
  so it cannot measure actual frame rate.
- **Not a replacement for testing on real hardware.** It catches known-bad
  patterns, not everything.

The linter is the product. Everything else is in progress.

---

## Repository layout

```
aip/check.py       the linter — rules, autofix, output formats
aip/cli.py         command line entry point
skills/            per-library animation guidance for agents
references/        accessibility, performance, browser support notes
manifests/         library capability metadata
tests/             linter tests + good/bad fixtures
scripts/smoke.py   cold-start sanity check
```

## Development

```bash
python -m unittest discover tests -v   # test suite (no dependencies)
python scripts/smoke.py                # cold-start sanity check
python -m aip check tests/fixtures/    # see the linter fire
```

Adding a rule: write it in `aip/check.py`, register it in `CSS_RULES` or
`JS_RULES`, then add a positive case to `tests/fixtures/bad-animations.*` **and**
a negative case to `tests/fixtures/good-animations.*`. False positives are worse
than missed bugs — a noisy linter gets disabled.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`BUILD_PLAN.md`](BUILD_PLAN.md).

## License

See [`LICENSE`](LICENSE).
