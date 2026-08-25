---
mode: agent
description: Debug animation issues and provide a fix
---

# Fix Animation

Debug the provided animation issue. Output a structured diagnosis and fix.

## Your Task

1. Identify the root cause of the animation issue
2. Explain why it happens
3. Provide a minimal, targeted fix
4. Explain how to prevent the issue in the future

---

## Output Format

```
## Animation Debug Report

### Issue Summary
[One-line description of the problem]

### Root Cause
[Clear explanation of why this is happening]

### Category
[One of: Performance / Memory Leak / Incorrect Cleanup / Accessibility / Browser Compatibility / Logic Error / Timing / CSS Conflict]

### Severity
[Critical / High / Medium / Low]

### Fix

[Code showing the fix with inline explanation]

### Prevention
[How to avoid this in the future — rule or pattern to follow]

### Related Rules
[Links to relevant skill files or reference docs]
```

---

## Common Animation Issues Catalogue

### GSAP

**Issue: Animation doesn't run in React**
- Cause: GSAP targets DOM before component mounts (no ref guard)
- Fix: Wrap in `useEffect` with a `ref`, use `gsap.context()`

**Issue: ScrollTrigger doesn't recalculate after content loads**
- Cause: ScrollTrigger calculates positions on init, not after dynamic content
- Fix: Call `ScrollTrigger.refresh()` after content loads

**Issue: Animation runs twice in React 18**
- Cause: React 18 Strict Mode double-invokes `useEffect`
- Fix: Use `gsap.context()` — it handles cleanup correctly on double-invoke

**Issue: Memory leak with ScrollTrigger**
- Cause: ScrollTrigger instances not killed on unmount
- Fix: `ScrollTrigger.getAll().forEach(st => st.kill())` or use `gsap.context().revert()`

**Issue: `gsap.to()` in render function causes infinite loop**
- Cause: Animation re-created every render
- Fix: Move animation to `useEffect` with proper dependency array

### Motion for React

**Issue: Exit animation doesn't play**
- Cause: Component removed from DOM before exit animation completes; missing `AnimatePresence`
- Fix: Wrap with `<AnimatePresence>`, ensure component is conditionally rendered inside it

**Issue: Layout animation causes flicker**
- Cause: `layout` prop without proper `layoutId` on shared elements
- Fix: Add matching `layoutId` to both elements; wrap in `<LayoutGroup>`

**Issue: Animations break during React Suspense**
- Cause: Component unmounts during Suspense fallback
- Fix: Use `AnimatePresence mode="wait"` around the Suspense boundary

### Three.js

**Issue: Memory leak — GPU memory growing**
- Cause: Geometry, material, or texture not disposed on unmount
- Fix: Explicitly call `.dispose()` on all Three.js objects in cleanup

**Issue: Canvas not resizing correctly**
- Cause: Renderer size not updated on window resize
- Fix: Add ResizeObserver, call `renderer.setSize()` and update camera aspect

**Issue: Animation loop continues after component unmount**
- Cause: `cancelAnimationFrame` not called in cleanup
- Fix: Store RAF ID in a ref, cancel in useEffect cleanup

### Lottie

**Issue: Lottie not playing**
- Cause: `autoplay: false` set, or `prefers-reduced-motion` check pausing it
- Fix: Check `autoplay` setting and reduced motion logic

**Issue: Lottie animation distorted**
- Cause: Missing `preserveAspectRatio` in `rendererSettings`
- Fix: Add `preserveAspectRatio: 'xMidYMid slice'` or appropriate value

**Issue: Memory leak**
- Cause: `lottie.destroy()` not called on unmount
- Fix: Call `animation.destroy()` in `useEffect` cleanup

### CSS Animation

**Issue: Animation not playing on first load**
- Cause: Element not in DOM when animation triggers, or `animation-fill-mode` not set
- Fix: Add `animation-fill-mode: both`

**Issue: Animation jank / dropped frames**
- Cause: Animating layout properties (`width`, `height`, `margin`, `top`)
- Fix: Replace with `transform` equivalents

**Issue: `prefers-reduced-motion` not respected**
- Cause: Animation not wrapped in `@media (prefers-reduced-motion: no-preference)`
- Fix: Move all motion CSS inside the media query; provide static state outside

### General

**Issue: Animation conflicts with CSS transition**
- Cause: Both a CSS transition and a JS animation targeting the same property
- Fix: Remove the CSS transition for properties being controlled by JS animation

**Issue: FOUC — elements visible before animation runs**
- Cause: Initial state not set before animation starts
- Fix: Set initial state via CSS (`opacity: 0; transform: translateY(20px)`) before JS runs, or use `gsap.set()` / `initial` prop

**Issue: Animation not working on iOS Safari**
- Cause: Missing `-webkit-` prefix, or using unsupported CSS feature
- Fix: Check browser support reference, add fallbacks
