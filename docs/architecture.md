# Architecture

How `frontend-animation-agent-skills` is structured and why.

---

## Design Principles

### 1. Agent-Agnostic Core

All animation knowledge lives in `skills/` and `references/`. These files are plain Markdown and work with any AI system that can read files.

Agent-specific configuration (prompt formats, file naming) is isolated in `adapters/`.

### 2. Skills as the Knowledge Layer

Each skill (`SKILL.md`) is self-contained:
- Goal
- Return format
- Warnings
- Context dump (the knowledge)
- RTCF (Role/Task/Constraints/Format)
- Few-shot examples

This format works for any prompt-following AI.

### 3. Commands as Workflows

The six commands (`/animation`, `/animate`, etc.) are implemented as:
- `.github/prompts/*.prompt.md` — for GitHub Copilot
- Documented in `AGENTS.md` and `adapters/` — for other agents

### 4. Router-First

The `animation-router` skill is always the entry point. No animation should be generated without first running the router's decision chain.

---

## Directory Purposes

| Directory | Purpose |
|---|---|
| `.github/` | GitHub Copilot configuration and CI |
| `skills/` | Core animation knowledge (library-neutral entry) |
| `references/` | Decision matrices and reference tables |
| `integrations/` | Framework-specific patterns (React, Next.js, etc.) |
| `adapters/` | Agent-specific config files |
| `examples/` | Working code examples |
| `evals/` | Test cases and rubrics for AI output validation |
| `docs/` | Human documentation |

---

## Skill Structure

Every skill follows this template:

```
# [Library] Skill

## Goal
## Return Format
## Warnings
## Context Dump
## RTCF
## Few Shot Examples
```

This structure ensures:
- AI knows what it's responsible for (Goal)
- AI knows how to format its answer (Return Format)
- AI knows what to avoid (Warnings)
- AI has the knowledge it needs (Context Dump)
- AI has a clear prompt structure (RTCF)
- AI has examples to follow (Few Shot)

---

## Adding a New Skill

See [skill-authoring.md](./skill-authoring.md).
