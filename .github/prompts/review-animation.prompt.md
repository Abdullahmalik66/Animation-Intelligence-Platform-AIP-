---
mode: agent
description: Review animation code for quality, accessibility, and performance
---

# Review Animation

Review the provided animation code and produce a structured quality report.

---

## Output Format

```
## Animation Code Review

### Overview
[Brief summary of what the animation code does]

### Score: [X/10]
[One sentence justification for the score]

---

### ✅ Strengths
- [What the code does well]

---

### 🔴 Critical Issues (Must Fix)
[Issues that will cause bugs, accessibility failures, memory leaks, or security problems]

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | [Issue] | [Line/function] | [Recommended fix] |

---

### 🟠 High Issues (Should Fix)
[Issues that degrade quality, performance, or maintainability significantly]

| # | Issue | Location | Fix |
|---|-------|----------|-----|

---

### 🟡 Medium Issues (Consider Fixing)
[Improvements that would meaningfully improve the code]

| # | Issue | Location | Fix |
|---|-------|----------|-----|

---

### 🔵 Low / Style Issues
[Minor improvements, naming, comments, etc.]

| # | Issue | Location | Fix |
|---|-------|----------|-----|

---

### Accessibility Checklist

| Check | Status | Notes |
|-------|--------|-------|
| `prefers-reduced-motion` handled | ✅/❌ | |
| Static fallback provided | ✅/❌ | |
| Animation >5s has controls | ✅/❌ | N/A if <5s |
| No info conveyed by motion alone | ✅/❌ | |
| Color contrast maintained during animation | ✅/❌ | |

---

### Performance Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Only `transform`/`opacity` animated | ✅/❌ | |
| No forced synchronous layouts | ✅/❌ | |
| Cleanup on unmount | ✅/❌ | |
| No infinite loops without guards | ✅/❌ | |
| `will-change` used appropriately | ✅/❌ | |

---

### Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| No remote/untrusted asset URLs | ✅/❌ | |
| SVG sanitized before injection | ✅/❌ | N/A |
| No secrets in animation config | ✅/❌ | |

---

### Recommended Refactor (if score < 7)

[Provide the improved version of the most critical section, or the full file if small]
```

---

## Review Rubric

### Score /10 Breakdown

| Area | Weight | Perfect Score Criteria |
|------|--------|----------------------|
| Correctness | 25% | Animation works as intended across browsers |
| Accessibility | 25% | Full WCAG 2.2 compliance, reduced motion handled |
| Performance | 20% | No layout thrash, GPU composited, proper cleanup |
| Code Quality | 15% | No magic numbers, typed, commented correctly |
| Maintainability | 10% | Easy to modify, named constants, clear structure |
| Security | 5% | No untrusted URLs, no secret exposure |

### Score Meanings

- **9–10**: Production-ready, exemplary
- **7–8**: Good, minor improvements suggested
- **5–6**: Acceptable but notable issues, should fix before shipping
- **3–4**: Significant problems, refactor recommended
- **1–2**: Do not ship — critical issues present

---

## Common Review Findings

### Critical (Automatic Score Reduction)

1. **No `prefers-reduced-motion` handling** — accessibility failure
2. **No cleanup on unmount** — memory leak guaranteed
3. **Animating layout properties** — causes jank and performance issues
4. **GSAP animation outside `useEffect`** — runs on every render
5. **Loading animation assets from external untrusted URLs**
6. **Three.js `.dispose()` missing** — GPU memory leak

### High

1. **Magic numbers for durations/easing** — unmaintainable
2. **No TypeScript types on animation values**
3. **Inline `animate` props instead of variants** (Motion for React) — performance issue
4. **ScrollTrigger not refreshed after dynamic content**
5. **Missing `AnimatePresence` for exit animations** (Motion for React)

### Medium

1. **No comments explaining non-obvious easing or timing choices**
2. **`will-change` on every element** — wastes memory
3. **Animating too many elements simultaneously without `stagger`**
4. **No error boundary around Three.js canvas**

### Low

1. **Inconsistent naming** (some durations named, some not)
2. **Unused imports from animation libraries**
3. **CSS transitions conflicting with JS animations on same property**
