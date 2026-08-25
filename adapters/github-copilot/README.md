# GitHub Copilot Adapter

## Files

This adapter provides GitHub Copilot-specific configuration:

- `../../.github/copilot-instructions.md` — Global instructions (primary configuration)
- `../../.github/prompts/` — Reusable prompt files

## Installation

### Option 1: Copy to Your Project

```bash
# Copy the global instructions
cp .github/copilot-instructions.md /path/to/your/project/.github/copilot-instructions.md

# Copy the prompt files
cp -r .github/prompts/ /path/to/your/project/.github/prompts/
```

### Option 2: Reference from this Repository

Clone this repository into your project and reference the files:

```bash
git clone https://github.com/your-org/frontend-animation-agent-skills.git .animation-skills
```

Then in your `.github/copilot-instructions.md`:

```markdown
# Animation Skills

See [Animation Skills](.animation-skills/AGENTS.md) for full instructions.

<!-- Key rules summary -->
Always handle prefers-reduced-motion.
Animate only transform and opacity.
Clean up all animations on unmount.
```

## Features

- Global instructions via `copilot-instructions.md`
- Slash commands via `.prompt.md` files (`/animation`, `/animate`, etc.)
- File references via `#file:` syntax

## Usage

After installation, use these in any Copilot Chat:

```
/animation I need a scroll-driven card reveal
/animate Create a modal entrance animation with Motion for React
/fix-animation My GSAP ScrollTrigger runs twice
/review-animation #file:src/components/HeroAnimation.tsx
/optimize-animation #file:src/animations/gsap-scroll.ts
/migrate-animation Convert this GSAP animation to Motion for React
```
