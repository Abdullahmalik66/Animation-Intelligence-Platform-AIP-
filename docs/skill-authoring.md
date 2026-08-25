# Skill Authoring Guide

How to write a new animation skill for `frontend-animation-agent-skills`.

---

## Skill Template

Create a new directory in `skills/` and add a `SKILL.md`:

```markdown
# [Library Name] Skill

## Goal

What this skill enables the AI to do. One or two sentences.

## Return Format

Describe exactly how the AI should format its response.
Code format, sections, level of detail.

## Warnings

List everything the AI must avoid or be careful about.
Use ❌ for hard prohibitions and ⚠️ for cautions.

## Context Dump

All the knowledge the AI needs to implement this correctly.
Include:
- Core API patterns
- Complete code examples
- Common patterns with named constants
- Library-specific rules
- Easing reference
- Performance considerations
- Accessibility patterns

## RTCF

**Role:** [What expert is the AI playing?]

**Task:** [What exactly should it do?]

**Constraints:** [What must it always/never do?]

**Format:** [Exact output format]

## Few Shot Examples

### Example 1

**Input:**
[A realistic user request]

**Output:**
[The ideal AI response]

---

### Example 2

**Input:**
[A debugging or more complex request]

**Output:**
[The ideal AI response]
```

---

## Quality Checklist

Before submitting a new skill:

```
□ Goal is specific and testable
□ Return format is unambiguous
□ All warnings are actionable
□ Context dump has working code examples
□ All code examples include prefers-reduced-motion
□ All code examples include cleanup logic
□ All code examples use named constants (no magic numbers)
□ RTCF is complete with all four fields
□ At least 2 few-shot examples
□ Examples cover both happy path and debugging
□ No library-specific patterns missing
□ No TypeScript any in code examples
```

---

## Quality Standards

Every skill MUST include:

- ✅ `prefers-reduced-motion` handling in all code examples
- ✅ Cleanup code (destroy, cancel, revert) in all examples
- ✅ Named constants for durations and delays
- ✅ TypeScript types (no `any`)
- ✅ Warnings about the most common mistakes
- ✅ At least one debugging example

---

## Naming Convention

```
skills/[library-name]/SKILL.md
```

Examples:
- `skills/gsap/SKILL.md`
- `skills/motion-react/SKILL.md`
- `skills/animation-debugging/SKILL.md`

---

## Submitting

Open a pull request using the `skill-request` template. See [CONTRIBUTING.md](../CONTRIBUTING.md).
