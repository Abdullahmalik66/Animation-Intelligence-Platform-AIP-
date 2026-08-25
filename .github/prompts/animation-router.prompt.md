---
mode: agent
description: Analyze animation requirements and recommend the best solution
---

# Animation Router

Analyze the following animation requirement and recommend the best implementation approach.

## Your Task

1. Read the user's animation requirement carefully.
2. Evaluate against the decision matrix below.
3. Output a structured recommendation — do NOT write any code yet.
4. Wait for confirmation before implementing.

## Decision Matrix

### Step 1 — Can CSS solve it?

Ask: Is this a simple transition, hover state, entrance animation, or keyframe loop?

CSS can handle:
- Hover and focus transitions
- Fade in/out on page load
- Simple slide, scale, rotate entrances
- Looping decorative animations
- Scroll-reveal with `@keyframes` + Intersection Observer
- Scroll-driven animations (Chrome 115+, with fallback)

If CSS can solve it → recommend CSS. Do not proceed to library selection.

### Step 2 — 3D or WebGL?

If the requirement involves: 3D scenes, WebGL rendering, shaders, particle systems, 3D models → **Three.js**

### Step 3 — Designer-Created Asset?

If the requirement involves a file from After Effects, Rive, or a design tool:
- `.riv` file with states/interactions → **Rive**
- `.json` Lottie file, static playback → **Lottie**

### Step 4 — Scroll-Driven or Complex Timeline?

If the requirement involves:
- Pinned scroll sections
- Multi-element choreographed timelines
- Scroll-triggered sequences
- Staggered complex timelines
→ **GSAP**

### Step 5 — React State or Gesture?

If the requirement involves:
- Animating on React state change
- Drag, pan, or gesture interactions
- Shared layout transitions between routes
- Exit animations tied to component unmount
→ **Motion for React**

### Step 6 — Lightweight or Vanilla?

If the requirement is:
- Vanilla JS or simple DOM animation
- No React/Vue/framework
- Lightweight bundle is critical
→ **Anime.js** or **Motion (vanilla)**

### Step 7 — Default Complex

If none of the above fit → **GSAP**

---

## Output Format

```
## Animation Analysis

**Requirement Summary:** [One-line summary of what was asked]

**Recommendation:** [CSS / GSAP / Motion for React / Three.js / Rive / Lottie / Anime.js / Motion]

**Reason:** [One clear sentence explaining why]

**Alternatives Considered:**
- [Alternative 1]: [Why not chosen]
- [Alternative 2]: [Why not chosen]

**Bundle Cost:** [Approx gzipped size of recommended library]

**Accessibility Requirements:**
- [What needs `prefers-reduced-motion` handling]
- [Any WCAG 2.2 concerns]

**Performance Notes:**
- [GPU compositing eligibility]
- [Any layout triggers to avoid]

**Ready to Implement?** Confirm to proceed with `/animate`.
```

---

## Examples

### Example Input
> I need to fade in a hero section when the page loads in React.

### Example Output
```
## Animation Analysis

**Requirement Summary:** Fade-in entrance animation for a hero section on page load.

**Recommendation:** CSS

**Reason:** A single fade-in on load is a simple entrance that CSS handles perfectly with `@keyframes` or a `transition`, with zero bundle cost.

**Alternatives Considered:**
- Motion for React: Overkill for a single static fade-in
- GSAP: Unnecessary dependency for this use case

**Bundle Cost:** 0kb — no library needed

**Accessibility Requirements:**
- Wrap animation in `@media (prefers-reduced-motion: no-preference)` block
- Element must be visible without animation as fallback

**Performance Notes:**
- Use `opacity` and `transform` only — both GPU composited
- Do not animate `height` or `margin`

**Ready to Implement?** Confirm to proceed with `/animate`.
```

---

### Example Input
> I need a scroll-driven animation that pins a section, reveals 5 cards with stagger, and parallaxes a background image.

### Example Output
```
## Animation Analysis

**Requirement Summary:** Scroll-pinned section with staggered card reveals and parallax background.

**Recommendation:** GSAP (with ScrollTrigger)

**Reason:** Pinned scroll sections, multi-element stagger, and parallax together constitute a complex timeline that is GSAP ScrollTrigger's primary use case.

**Alternatives Considered:**
- CSS scroll-timeline: Cannot handle pinning or cross-element choreography reliably yet
- Motion for React: No native scroll-pin support

**Bundle Cost:** ~27kb gzipped (GSAP core + ScrollTrigger)

**Accessibility Requirements:**
- Use `gsap.matchMedia()` to disable pin and parallax for `prefers-reduced-motion: reduce`
- Cards must be readable without animation

**Performance Notes:**
- Animate only `transform` and `opacity` — do not animate `width` or `background-position`
- Use `scrub: true` carefully — high scrub values reduce performance

**Ready to Implement?** Confirm to proceed with `/animate`.
```
