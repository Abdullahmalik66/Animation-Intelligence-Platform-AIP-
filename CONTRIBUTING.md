# Contributing to frontend-animation-agent-skills

Thank you for contributing to the largest AI skill library for frontend animation development.

---

## Ways to Contribute

- **New skills** — Add a new animation library skill
- **Improve existing skills** — Better examples, fixed errors, updated APIs
- **New examples** — Working code examples for patterns not yet covered
- **Bug fixes** — Fix incorrect information or broken code examples
- **New eval cases** — Add test cases that validate AI output quality
- **Integration guides** — Add framework-specific integration patterns

---

## Before You Start

1. Read the [Architecture doc](./docs/architecture.md)
2. Read the [Skill Authoring guide](./docs/skill-authoring.md)
3. Check existing [skills](./skills/) to understand the format
4. Check open issues before starting work on a new skill

---

## Skill Contribution Process

### 1. Create the skill file

```
skills/[library-name]/SKILL.md
```

Follow the template in [docs/skill-authoring.md](./docs/skill-authoring.md).

### 2. Self-review checklist

```
□ Goal is specific and testable
□ Return format is clear
□ All warnings are actionable
□ Code examples include prefers-reduced-motion
□ Code examples include cleanup logic
□ Code examples use named constants
□ No TypeScript any
□ RTCF has all four fields
□ At least 2 few-shot examples
□ One example covers debugging
```

### 3. Open a pull request

Use the pull request template. Include:
- What library or skill you're adding
- Why it belongs in this repository
- How you tested the skill (which AI agent, which prompts)

---

## Code Style

- TypeScript preferred for all code examples
- Named constants for all durations, delays, and easing values
- No magic numbers
- Comments explain *why*, not *what*
- No `console.log` in production examples

---

## What We Don't Accept

- Skill files without `prefers-reduced-motion` handling in examples
- Skill files without cleanup code in examples
- Skills for libraries with <1000 weekly npm downloads
- AI-generated skill files submitted without human review and testing
- Examples that animate layout properties (`width`, `height`, `top`, `left`)

---

## Reporting Issues

Use the GitHub issue templates for:
- `bug-report` — Incorrect information in a skill file
- `skill-request` — Request for a new library skill
- `improvement` — Suggest improvements to existing content

---

## Code of Conduct

Be respectful. Disagree constructively. Focus on the content, not the person.
