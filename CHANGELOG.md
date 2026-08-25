# Changelog

All notable changes to `frontend-animation-agent-skills` will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-08-12

### Added

#### Core Skills (MVP)
- `skills/animation-router/SKILL.md` — Library selection decision tree
- `skills/gsap/SKILL.md` — GSAP animation patterns with React, ScrollTrigger, and matchMedia
- `skills/motion-react/SKILL.md` — Motion for React with variants, AnimatePresence, and accessibility
- `skills/threejs/SKILL.md` — Three.js scene setup, disposal, and React integration
- `skills/rive/SKILL.md` — Rive state machine integration and cleanup
- `skills/animejs/SKILL.md` — Anime.js lightweight animation patterns
- `skills/motion/SKILL.md` — Motion vanilla animate(), scroll(), inView() patterns
- `skills/lottie/SKILL.md` — Lottie-web integration with renderer selection and cleanup
- `skills/animation-accessibility/SKILL.md` — WCAG 2.2 compliance for animations
- `skills/animation-performance/SKILL.md` — GPU compositing, layout thrashing, bundle size
- `skills/animation-debugging/SKILL.md` — Systematic debug workflows and issue catalogue
- `skills/animation-migration/SKILL.md` — Cross-library migration guide
- `skills/animation-code-review/SKILL.md` — Structured review rubric

#### Prompts (GitHub Copilot)
- `.github/prompts/animation-router.prompt.md`
- `.github/prompts/animate.prompt.md`
- `.github/prompts/fix-animation.prompt.md`
- `.github/prompts/review-animation.prompt.md`
- `.github/prompts/optimize-animation.prompt.md`
- `.github/prompts/migrate-animation.prompt.md`

#### Agent Instructions
- `.github/copilot-instructions.md` — GitHub Copilot global instructions
- `AGENTS.md` — Universal agent instructions
- `adapters/claude/CLAUDE.md` — Claude-specific adapter
- `adapters/cursor/.cursorrules` — Cursor-specific adapter
- `adapters/generic/AGENTS.md` — Generic adapter (Kimi, Qwen, Windsurf, etc.)

#### References
- `references/library-decision-matrix.md`
- `references/accessibility.md`
- `references/performance.md`
- `references/browser-support.md`
- `references/security.md`

#### Integrations
- `integrations/react/README.md`
- `integrations/nextjs/README.md`

#### Examples
- `examples/basic/css-fade-in.css`
- `examples/basic/gsap-stagger.tsx`
- `examples/basic/motion-react-list.tsx`

#### Evals
- `evals/cases/router-001-css-hover.md`
- `evals/cases/gsap-001-cleanup.md`
- `evals/rubrics/implementation-quality.md`

#### Documentation
- `README.md`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `docs/architecture.md`
- `docs/skill-authoring.md`
