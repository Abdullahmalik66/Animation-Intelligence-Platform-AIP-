# frontend-animation-agent-skills

> The largest and best-maintained AI skill library for frontend animation development.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![GitHub Copilot](https://img.shields.io/badge/GitHub%20Copilot-First-blue)](./adapters/github-copilot/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

---

## What Is This?

`frontend-animation-agent-skills` is an open-source collection of AI skills, prompts, commands, and agent instructions that teach coding agents how to create, debug, optimize, review, and migrate frontend animations — correctly.

It is not a tutorial library. It is a **knowledge layer** for AI coding agents.

Just as [GSAP Skills](https://github.com/GreenSock/gsap-skills) teaches AI how to use GSAP, this repository teaches AI:

- Which animation library to use (and when to use none)
- How to implement animations correctly
- How to optimize animations for performance
- How to debug animations
- How to review animation code
- How to migrate between animation frameworks
- How to follow accessibility standards (WCAG 2.2)

---

## Supported Libraries

| Library | Skill | Status |
|---|---|---|
| **GSAP** | [`skills/gsap`](./skills/gsap/) | ✅ MVP |
| **Motion for React** | [`skills/motion-react`](./skills/motion-react/) | ✅ MVP |
| **Three.js** | [`skills/threejs`](./skills/threejs/) | ✅ MVP |
| **Rive** | [`skills/rive`](./skills/rive/) | ✅ Stable |
| **Anime.js** | [`skills/animejs`](./skills/animejs/) | ✅ Stable |
| **Motion** | [`skills/motion`](./skills/motion/) | ✅ Stable |
| **Lottie** | [`skills/lottie`](./skills/lottie/) | ✅ Stable |

---

## Supported AI Agents

| Agent | Adapter | Status |
|---|---|---|
| **GitHub Copilot** | [`adapters/github-copilot`](./adapters/github-copilot/) | ✅ Primary |
| **Claude** | [`adapters/claude`](./adapters/claude/) | ✅ Stable |
| **Cursor** | [`adapters/cursor`](./adapters/cursor/) | ✅ Stable |
| **Codex** | [`adapters/codex`](./adapters/codex/) | ✅ Stable |
| **Gemini** | [`adapters/gemini`](./adapters/gemini/) | ✅ Stable |
| **Kimi** | [`adapters/generic`](./adapters/generic/) | ✅ Generic |
| **Qwen** | [`adapters/generic`](./adapters/generic/) | ✅ Generic |
| **Windsurf** | [`adapters/generic`](./adapters/generic/) | ✅ Generic |

---

## Core Philosophy

> Do not teach one animation library. Teach animation engineering.

Libraries are implementation details. The AI should learn:

```
Requirement → Decision → Library → Implementation → Review → Optimisation
```

Not:

```
Requirement → GSAP
```

The animation router always asks: **Can CSS solve it first?**

---

## Quick Install

### GitHub Copilot (Recommended)

Copy `.github/copilot-instructions.md` to your project root:

```bash
curl -O https://raw.githubusercontent.com/your-org/frontend-animation-agent-skills/main/.github/copilot-instructions.md
```

Or clone the full repository into your project:

```bash
git clone https://github.com/your-org/frontend-animation-agent-skills.git .animation-skills
```

Then reference in your `.github/copilot-instructions.md`:

```markdown
@file .animation-skills/.github/copilot-instructions.md
```

### Claude

Copy `adapters/claude/CLAUDE.md` to your project as `CLAUDE.md`.

### Cursor

Copy `adapters/cursor/.cursorrules` to your project root as `.cursorrules`.

### Other Agents

See [`adapters/generic/AGENTS.md`](./adapters/generic/AGENTS.md) for a universal format compatible with any AI coding agent.

---

## Commands

Once installed, use these slash commands in your AI coding agent:

| Command | Description |
|---|---|
| `/animation` | Analyze requirements and recommend the best animation solution |
| `/animate` | Generate animation implementation for your use case |
| `/fix-animation` | Debug animation issues and explain the root cause |
| `/review-animation` | Review architecture, accessibility, and quality |
| `/optimize-animation` | Improve performance and reduce bundle size |
| `/migrate-animation` | Convert between animation libraries |

---

## Repository Structure

```
frontend-animation-agent-skills/
│
├── .github/
│   ├── copilot-instructions.md     # GitHub Copilot global instructions
│   ├── prompts/                    # Reusable prompt files (.prompt.md)
│   ├── workflows/                  # CI/CD for skill validation
│   ├── ISSUE_TEMPLATE/             # Bug reports, skill requests
│   └── pull_request_template.md
│
├── skills/                         # Core animation skill definitions
│   ├── animation-router/           # Library selection logic
│   ├── gsap/
│   ├── motion-react/
│   ├── threejs/
│   ├── rive/
│   ├── animejs/
│   ├── motion/
│   ├── lottie/
│   ├── animation-debugging/
│   ├── animation-performance/
│   ├── animation-accessibility/
│   ├── animation-migration/
│   └── animation-code-review/
│
├── references/                     # Decision matrices and reference docs
│   ├── library-decision-matrix.md
│   ├── accessibility.md
│   ├── performance.md
│   ├── browser-support.md
│   └── security.md
│
├── integrations/                   # Framework-specific integration guides
│   ├── react/
│   ├── nextjs/
│   ├── vue/
│   ├── nuxt/
│   ├── svelte/
│   ├── angular/
│   └── vanilla-js/
│
├── adapters/                       # Agent-specific adapter files
│   ├── github-copilot/
│   ├── claude/
│   ├── cursor/
│   ├── codex/
│   ├── gemini/
│   └── generic/
│
├── examples/                       # Working code examples
│   ├── basic/
│   ├── framework-specific/
│   └── real-world-patterns/
│
├── evals/                          # Evaluation cases and rubrics
│   ├── cases/
│   ├── expected/
│   └── rubrics/
│
├── docs/                           # Documentation
│   ├── architecture.md
│   ├── installation.md
│   ├── compatibility.md
│   └── skill-authoring.md
│
├── AGENTS.md                       # Agent instructions (universal)
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Animation Router Decision Tree

```
User Request
    │
    ▼
Can CSS solve it?
    │
   YES ──────────────────────────────▶ Use CSS (no library)
    │
    NO
    │
    ▼
Is it 3D / WebGL?
    │
   YES ──────────────────────────────▶ Three.js
    │
    NO
    │
    ▼
Is it a designer asset (Lottie/Rive file)?
    │
   YES → Is it interactive/stateful? ▶ Rive
    │    NO ─────────────────────────▶ Lottie
    │
    NO
    │
    ▼
Is it scroll-driven or timeline-complex?
    │
   YES ──────────────────────────────▶ GSAP
    │
    NO
    │
    ▼
Is it React-based with UI state?
    │
   YES ──────────────────────────────▶ Motion for React
    │
    NO
    │
    ▼
Is it lightweight / vanilla?
    │
   YES ──────────────────────────────▶ Anime.js or Motion
    │
    NO ───────────────────────────────▶ GSAP (default complex)
```

---

## Quality Standards

Every skill guarantees:

- ✅ Accessibility rules (WCAG 2.2, `prefers-reduced-motion`)
- ✅ Performance rules (60fps, GPU compositing, no layout thrash)
- ✅ Cleanup rules (event listeners, RAF cancellation, unmount handling)
- ✅ Browser support guidance
- ✅ Validation checklist
- ✅ Common mistakes catalogue
- ✅ Security considerations

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to add new skills, fix bugs, or improve existing content.

---

## Security

See [SECURITY.md](./SECURITY.md) for our security policy.

Core rules:
- Never run remote scripts
- Never trust generated code without review
- Never inject untrusted SVGs
- Treat all user input as untrusted

---

## License

[MIT](./LICENSE) — free to use in any project, commercial or open-source.

---

## Acknowledgements

Inspired by the excellent work of the [GSAP](https://greensock.com/gsap/) team, [Motion](https://motion.dev/) team, and the broader open-source animation community.

Built for developers who believe AI should be a multiplier, not a shortcut.
