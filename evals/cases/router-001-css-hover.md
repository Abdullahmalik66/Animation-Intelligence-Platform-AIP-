# Eval Case: Animation Router — Correct CSS Recommendation

## Case ID
`router-001`

## Category
Animation Router

## Input

```
I need to animate a button that changes colour when hovered.
Framework: React
Existing dependencies: none
```

## Expected Output

```
Recommendation: CSS
Reason: A hover colour transition is a single-state CSS interaction — exactly what CSS transitions exist for.
Alternatives: None warranted
Bundle cost: 0kb
Accessibility: Use @media (prefers-reduced-motion: no-preference) wrapper; button must be functional without animation
```

## Rubric

| Criteria | Pass | Fail |
|---|---|---|
| Recommends CSS (not a library) | ✅ | Recommends GSAP or Motion |
| Mentions zero bundle cost | ✅ | Mentions library bundle |
| Mentions reduced motion | ✅ | No accessibility mention |
| Does NOT write code in this step | ✅ | Writes implementation code |
