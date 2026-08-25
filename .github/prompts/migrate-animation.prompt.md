---
mode: agent
description: Migrate animation code between libraries
---

# Migrate Animation

Convert animation code from one library to another, preserving visual behaviour while following best practices for the target library.

---

## Output Format

```
## Migration Report: [Source Library] → [Target Library]

### Migration Summary
[What is being migrated and why]

### Compatibility Assessment

| Feature | Source Support | Target Support | Notes |
|---------|---------------|----------------|-------|
| [Feature] | ✅/⚠️/❌ | ✅/⚠️/❌ | [Notes] |

### What Changes
- [Conceptual change 1]
- [Conceptual change 2]

### What Cannot Be Directly Migrated
- [Feature/behaviour that doesn't exist in target library]
- [Recommended workaround]

---

### Migrated Code

**Before ([Source Library]):**
[Original code]

**After ([Target Library]):**
[Migrated code]

---

### Dependency Changes

Remove:
```bash
npm uninstall [old-package]
```

Add:
```bash
npm install [new-package]
```

---

### Behaviour Parity Notes
[Any visual differences the developer should verify manually]

### Testing Checklist
- [ ] Animation plays on load
- [ ] Animation plays on interaction (if applicable)
- [ ] Exit/unmount animation works (if applicable)
- [ ] `prefers-reduced-motion` respected
- [ ] Cleanup works on unmount
- [ ] Mobile behaviour verified
```

---

## Migration Guides

### GSAP → Motion for React

**Concept mapping:**

| GSAP | Motion for React |
|------|-----------------|
| `gsap.from()` | `initial` + `animate` props |
| `gsap.to()` | `animate` prop |
| `gsap.fromTo()` | `initial` + `animate` props |
| `stagger` | `variants` with `staggerChildren` |
| `timeline` | `variants` with `delayChildren` + `staggerChildren` |
| `ScrollTrigger` | No direct equivalent — use `whileInView` for simple cases |
| `gsap.matchMedia()` | `useReducedMotion()` hook |
| `onComplete` callback | `onAnimationComplete` prop |

**What cannot migrate:**
- Complex pinned scroll sections (ScrollTrigger pin) — no Motion for React equivalent
- Multi-element choreographed timelines with precise control — GSAP timelines are more powerful
- SplitText animations — no direct equivalent

---

### Motion for React → GSAP

**Concept mapping:**

| Motion for React | GSAP |
|-----------------|------|
| `initial` + `animate` | `gsap.from()` / `gsap.fromTo()` |
| `exit` | Reverse timeline or `gsap.to()` on unmount |
| `variants` | Named timeline labels or reusable functions |
| `whileHover` | `element.addEventListener("mouseenter", ...)` |
| `layout` prop | Manual `gsap.to()` on measured position change |
| `useReducedMotion()` | `gsap.matchMedia()` |
| `AnimatePresence` | Manual unmount delay with `gsap.to()` + callback |

**What cannot migrate:**
- `layout` animations (auto-animating between layout states) — requires manual FLIP with GSAP
- Gesture physics (`drag` with spring) — GSAP has no built-in physics drag

---

### Anime.js → GSAP

**Concept mapping:**

| Anime.js | GSAP |
|----------|------|
| `anime({ targets, ... })` | `gsap.to(targets, { ... })` |
| `anime.timeline()` | `gsap.timeline()` |
| `delay` | `delay` |
| `easing: 'easeInOutQuad'` | `ease: 'power2.inOut'` |
| `loop: true` | `repeat: -1` |
| `direction: 'alternate'` | `yoyo: true` |
| `anime.stagger()` | `stagger` property |
| `anime.remove(targets)` | `gsap.killTweensOf(targets)` |
| `complete` callback | `onComplete` callback |

---

### GSAP → CSS

Only migrate if the animation is simple enough for CSS to handle.

**Migrations that work:**
- Simple entrance animations → `@keyframes` + `animation`
- Hover transitions → `transition`
- Infinite loops → `animation: name Xs ease infinite`
- Scroll reveals (simple) → CSS scroll-timeline or Intersection Observer + class toggle

**Do not migrate if:**
- Animation involves complex sequencing
- Scroll-driven with pinning
- Gesture-based interactions
- Timeline with precise per-element control

---

### Lottie → Rive

**When to migrate:**
- You need interactive/stateful animations (state machines)
- You need smaller file sizes (Rive format is more efficient)
- You need better runtime performance

**What requires designer work:**
- The animation must be recreated in Rive — Lottie `.json` files cannot be converted to `.riv` automatically
- State machine logic must be manually designed in Rive editor

**Code migration (loader pattern):**
```typescript
// Before (Lottie)
const animation = lottie.loadAnimation({
  container: el,
  path: "/animation.json",
  loop: true,
  autoplay: true,
});

// After (Rive)
const rive = new Rive({
  src: "/animation.riv",
  canvas: canvasEl,
  autoplay: true,
  stateMachines: "State Machine 1",
  onLoad: () => rive.resizeDrawingSurfaceToCanvas(),
});
```

---

### CSS → GSAP

**When to migrate:**
- CSS animation is hitting browser limits (no sequencing, no per-element control)
- You need scroll-linked behaviour beyond CSS scroll-timeline capabilities
- You need to animate based on dynamic data or user interaction beyond hover/focus

**Pattern:**
```typescript
// Before (CSS)
// .element { animation: slideIn 0.6s ease-out both; }

// After (GSAP)
gsap.from(elementRef.current, {
  opacity: 0,
  y: 40,
  duration: 0.6,
  ease: "power2.out",
});
```

---

## Easing Reference: Cross-Library

| Effect | CSS | GSAP | Motion | Anime.js |
|--------|-----|------|--------|----------|
| Ease in | `ease-in` | `power2.in` | `easeIn` | `easeInQuad` |
| Ease out | `ease-out` | `power2.out` | `easeOut` | `easeOutQuad` |
| Ease in-out | `ease-in-out` | `power2.inOut` | `easeInOut` | `easeInOutQuad` |
| Spring | N/A | `elastic.out` | `spring()` | `spring` |
| Bounce | N/A | `bounce.out` | N/A | `easeOutBounce` |
| Linear | `linear` | `none` | `linear` | `linear` |
