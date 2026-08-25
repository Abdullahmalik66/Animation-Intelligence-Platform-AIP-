# Eval Case: GSAP — Cleanup Correctness

## Case ID
`gsap-001`

## Category
GSAP / Cleanup

## Input

```
Generate a React component that fades in a heading and paragraph using GSAP.
```

## Expected Output Criteria

The generated code MUST:
- Use `useEffect` (not render function)
- Use `gsap.context()` with the container ref
- Return `() => ctx.revert()` in the cleanup
- Use `gsap.matchMedia()` with both `no-preference` and `reduce` conditions
- Set elements visible under reduced motion (`gsap.set()`)
- Use named constants for duration and ease

## Rubric

| Criteria | Weight | Pass Condition |
|---|---|---|
| `useEffect` used | 15% | Animation inside useEffect |
| `gsap.context()` used | 20% | Scoped to a ref |
| `ctx.revert()` returned | 20% | In cleanup function |
| `gsap.matchMedia()` used | 20% | Both conditions present |
| Reduced motion handled | 15% | Elements visible under reduce |
| Named constants | 10% | Duration and ease are named |

## Fail Conditions (Auto-Fail)

- Animation created outside `useEffect`
- No cleanup returned
- No `prefers-reduced-motion` handling
