---
mode: agent
description: Generate a production-ready animation implementation
---

# Animate

Generate a complete, production-ready animation implementation based on the confirmed approach.

## Requirements for Every Implementation

### 1. Code Quality
- TypeScript preferred
- Named constants for all durations, delays, and easing values
- No magic numbers
- No `any` types
- No `console.log`
- Comments explain *why*, not *what*

### 2. Accessibility (Required)
- Handle `prefers-reduced-motion` in every implementation
- Provide static/visible fallback when motion is disabled
- Animated content >5s needs pause/stop controls (WCAG 2.2.2)

### 3. Cleanup (Required)
Every implementation must include cleanup:
- GSAP: `gsap.context().revert()`
- Motion for React: cancel manual RAF, let library handle the rest
- Three.js: dispose geometry, material, texture, renderer; cancel RAF
- Rive: `rive.cleanup()`
- Lottie: `lottie.destroy()`
- Anime.js: `anime.remove(targets)`
- Motion: `animation.cancel()`

### 4. Performance
- Only animate `transform` and `opacity` by default
- No layout-triggering properties
- `will-change` only if measured benefit exists

---

## Output Format

````
## Implementation: [Animation Name]

**Library:** [Library used]
**Framework:** [React / Vue / Vanilla / etc.]

### Dependencies

```bash
npm install [package]
```

### Code

```tsx
// Full implementation here
```

### CSS (if needed)

```css
/* Supporting styles */
```

### Usage

```tsx
// How to use the component
```

### Notes

- [Any important implementation decisions]
- [Browser compatibility notes]
- [Known limitations]
````

---

## Library-Specific Patterns

### CSS Pattern
```css
/* Always guard with prefers-reduced-motion */
@media (prefers-reduced-motion: no-preference) {
  .element {
    animation: fadeIn 0.6s ease-out both;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### GSAP Pattern (React)
```tsx
import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const DURATION = 0.6;
const EASE = "power2.out";

export function AnimatedComponent() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from(".card", {
          opacity: 0,
          y: 40,
          duration: DURATION,
          ease: EASE,
          stagger: 0.1,
        });
      });

      mm.add("(prefers-reduced-motion: reduce)", () => {
        // No animation — elements visible immediately
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return <div ref={containerRef}>{/* ... */}</div>;
}
```

### Motion for React Pattern
```tsx
import { motion, useReducedMotion, AnimatePresence } from "motion/react";

const VARIANTS = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

const REDUCED_VARIANTS = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

export function AnimatedComponent({ isVisible }: { isVisible: boolean }) {
  const prefersReducedMotion = useReducedMotion();
  const variants = prefersReducedMotion ? REDUCED_VARIANTS : VARIANTS;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          variants={variants}
          initial="hidden"
          animate="visible"
          exit="exit"
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      )}
    </AnimatePresence>
  );
}
```

### Three.js Pattern (React)
```tsx
import { useEffect, useRef } from "react";
import * as THREE from "three";

export function ThreeScene() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current!;
    let rafId: number;

    // Setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, mount.clientWidth / mount.clientHeight, 0.1, 1000);
    const geometry = new THREE.BoxGeometry();
    const material = new THREE.MeshStandardMaterial({ color: 0x6366f1 });
    const mesh = new THREE.Mesh(geometry, material);

    scene.add(mesh);
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    // Reduced motion check
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const animate = () => {
      rafId = requestAnimationFrame(animate);
      if (!prefersReduced) {
        mesh.rotation.x += 0.01;
        mesh.rotation.y += 0.01;
      }
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(rafId);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={mountRef} style={{ width: "100%", height: "400px" }} />;
}
```

### Lottie Pattern (React)
```tsx
import { useEffect, useRef } from "react";
import lottie, { AnimationItem } from "lottie-web";

const ANIMATION_PATH = "/animations/my-animation.json"; // trusted origin only

export function LottieAnimation() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let animation: AnimationItem;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    animation = lottie.loadAnimation({
      container: containerRef.current!,
      renderer: "svg",
      loop: !prefersReduced,
      autoplay: !prefersReduced,
      path: ANIMATION_PATH,
      rendererSettings: {
        preserveAspectRatio: "xMidYMid slice",
      },
    });

    if (prefersReduced) {
      animation.goToAndStop(0, true); // show first frame only
    }

    return () => animation.destroy();
  }, []);

  return <div ref={containerRef} aria-hidden="true" />;
}
```
