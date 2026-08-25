---
mode: agent
description: Optimize animation performance
---

# Optimize Animation

Analyze the provided animation code for performance issues and provide targeted fixes.

---

## Output Format

```
## Animation Performance Report

### Performance Summary
[One paragraph overview of the performance state]

### Issues Found

| # | Issue | Severity | Location | Impact |
|---|-------|----------|----------|--------|
| 1 | [Issue] | Critical/High/Medium/Low | [Location] | [Impact description] |

---

### Fix [#N]: [Issue Name]

**Problem:**
[What is wrong and why it's a problem]

**Before:**
[Problematic code]

**After:**
[Fixed code]

**Impact:**
[Expected improvement — frame rate, paint cost, memory, etc.]

---

### Validation

How to measure the improvement:
- [Specific DevTools step or tool]

### Estimated Impact Summary

| Metric | Before (est.) | After (est.) |
|--------|--------------|-------------|
| Frame rate | | |
| Paint cost | | |
| Memory | | |
| Bundle size | | |
```

---

## Performance Issue Catalogue

### Critical — Fix Immediately

#### Animating Layout Properties
**Properties to never animate:** `width`, `height`, `top`, `left`, `right`, `bottom`, `margin`, `padding`, `border-width`, `font-size`

These trigger **layout → paint → composite** — the most expensive pipeline.

**Fix:** Replace with `transform` equivalents:
- `width`/`height` changes → `scaleX()`/`scaleY()`
- `top`/`left` movement → `translateX()`/`translateY()`
- `padding` expansion → `scale()`

#### Forced Synchronous Layout (Layout Thrashing)
Reading layout properties (`offsetWidth`, `getBoundingClientRect()`) after writing styles in the same frame forces the browser to recalculate layout immediately.

```typescript
// BAD — read after write in loop
elements.forEach(el => {
  el.style.width = el.offsetWidth + 10 + "px"; // read, then write — thrashes
});

// GOOD — batch reads, then batch writes
const widths = elements.map(el => el.offsetWidth); // all reads
elements.forEach((el, i) => {
  el.style.width = widths[i] + 10 + "px"; // all writes
});
```

#### Memory Leak from Missing Cleanup
Three.js, Lottie, Rive, and GSAP all retain GPU/CPU memory if not explicitly cleaned up.

Critical cleanup:
```typescript
// Three.js
geometry.dispose();
material.dispose();
texture.dispose();
renderer.dispose();

// GSAP
ctx.revert();

// Lottie
animation.destroy();

// Rive
rive.cleanup();
```

### High — Fix Before Shipping

#### Overusing `will-change`
`will-change` promotes elements to their own compositor layer, which costs GPU memory. Using it on every element wastes memory and can hurt performance.

```css
/* BAD */
* { will-change: transform; }

/* GOOD — only where measured benefit exists, removed after animation */
.card-entering { will-change: transform, opacity; }
```

Remove `will-change` after animation completes:
```typescript
element.addEventListener("animationend", () => {
  element.style.willChange = "auto";
}, { once: true });
```

#### RAF Stacking (Double RAF)
```typescript
// BAD — RAF inside RAF
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    // This delays unnecessarily
  });
});

// GOOD — single RAF
requestAnimationFrame(() => {
  // Update here
});
```

#### Animating Too Many DOM Elements Simultaneously
Animating >100 DOM elements causes excessive paint cost.

```typescript
// BAD — animate all at once
gsap.to(".particle", { opacity: 0, duration: 1 }); // 500 elements

// GOOD — use Canvas or WebGL for particle systems
// Or use stagger to sequence and reduce simultaneous paint
gsap.to(".particle", { opacity: 0, duration: 1, stagger: 0.02 });
```

#### No `passive` Flag on Scroll Listeners
```typescript
// BAD
window.addEventListener("scroll", handler);

// GOOD
window.addEventListener("scroll", handler, { passive: true });
```

### Medium — Meaningful Improvement

#### Subpixel Rendering on Transforms
Avoid fractional pixel values in translations:
```typescript
// BAD — causes subpixel rendering
gsap.to(el, { x: 33.5, y: 22.7 });

// GOOD — round to whole pixels
gsap.to(el, { x: Math.round(x), y: Math.round(y) });
```

#### Unnecessary Repaints from Box Shadows / Filters
`box-shadow`, `filter`, `border-radius` on animated elements trigger expensive repaints.

**Fix:** Use `drop-shadow` filter on a pseudo-element, or avoid filters on animating elements.

#### Bundle Size Optimisation

| Library | Full Bundle | Optimised |
|---------|-------------|-----------|
| GSAP | ~27kb | Import only used plugins |
| Three.js | ~600kb | Use tree-shaking, import only needed modules |
| Motion for React | ~18kb | Already tree-shakeable |
| Lottie | ~40kb | Use `lottie-web` with renderer-specific build |
| Anime.js | ~7kb | Already small |

```typescript
// BAD — imports all of Three.js
import * as THREE from "three";

// GOOD — import only what you use
import { WebGLRenderer } from "three/src/renderers/WebGLRenderer.js";
import { Scene } from "three/src/scenes/Scene.js";
```

### Low — Nice to Have

#### Use `transform3d` to Force GPU Layer
```css
/* Force GPU compositing explicitly */
.animated-element {
  transform: translateZ(0); /* or translate3d(0,0,0) */
}
```

Use sparingly — only when you've measured a benefit.

#### Contain Layout and Style
```css
/* Prevent animation from causing parent reflows */
.animation-container {
  contain: layout style paint;
}
```

---

## DevTools Validation Guide

### Chrome DevTools — Performance Tab
1. Open DevTools → Performance tab
2. Click Record
3. Trigger the animation
4. Stop recording
5. Look for:
   - **Long frames** (>16ms) — indicates dropped frames
   - **Layout** blocks (purple) — indicates layout thrashing
   - **Paint** blocks (green) — indicates paint cost
   - **Composite Layers** — check which elements are on their own layer

### Chrome DevTools — Layers Panel
1. Open DevTools → More Tools → Layers
2. Identify elements with unnecessary compositor layers (caused by overuse of `will-change`)

### Chrome DevTools — Rendering Panel
1. Open DevTools → More Tools → Rendering
2. Enable **Paint Flashing** — red flashes show repaints
3. Enable **Layer Borders** — shows compositor layer boundaries
4. Enable **Frame Rendering Stats** — shows live FPS

### Lighthouse
Run Lighthouse with **Performance** mode to catch:
- Long animation tasks
- Layout shift during animations (CLS)
- Total Blocking Time from animation scripts
