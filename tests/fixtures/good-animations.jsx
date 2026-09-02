// Correct animation code — `aip check` must report ZERO findings here.
// Guards against false positives.
import { useEffect, useRef } from 'react';
import gsap from 'gsap';

export function Reveal() {
  const ref = useRef(null);

  useEffect(() => {
    const prefersReduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;

    const ctx = gsap.context(() => {
      if (prefersReduced) return;
      gsap.to('.item', { opacity: 1, y: 0, stagger: 0.08 });
    }, ref);

    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => e.target.classList.toggle('in', e.isIntersecting));
    });
    io.observe(ref.current);

    const onScroll = () => {};
    window.addEventListener('scroll', onScroll, { passive: true });

    let frame = 0;
    const loop = () => {
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);

    return () => {
      ctx.revert();
      io.disconnect();
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  return <div ref={ref} />;
}
