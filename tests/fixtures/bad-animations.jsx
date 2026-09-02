// Deliberately broken animation code — fixture for `aip check`.
// Do not "fix" this file.
import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import * as THREE from 'three';

export function Hero() {
  const ref = useRef(null);

  useEffect(() => {
    // leak/gsap-no-revert: never reverted
    ScrollTrigger.create({
      trigger: ref.current,
      start: 'top center',
      onEnter: () => gsap.to(ref.current, { opacity: 1 }),
    });

    // leak/observer-not-disconnected
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => e.target.classList.toggle('in', e.isIntersecting));
    });
    io.observe(ref.current);

    // leak/listener-not-removed + perf/no-layout-thrash
    window.addEventListener('scroll', () => {
      const h = ref.current.offsetHeight;
      ref.current.style.transform = `translateY(${h * 0.1}px)`;
    });

    // leak/raf-not-cancelled
    const loop = () => {
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);

    // leak/webgl-not-disposed
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    const mesh = new THREE.Mesh(geometry, material);

    // sec/untrusted-asset
    fetch('https://cdn.example.com/animations/hero.json')
      .then((r) => r.json())
      .then(console.log);
  }, []);

  return <div ref={ref} />;
}
