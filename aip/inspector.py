"""Deterministic project inspector (Phase 6 support / Principle 4).

Extracts framework, package manager, and installed animation packages from a
target project's manifests and lockfiles. No LLM involvement. Read-only.
"""
from __future__ import annotations

import json
from pathlib import Path

from .state import AnimationProjectState, Evidence

ANIMATION_PACKAGES = {
    "gsap": "gsap", "animejs": "animejs", "motion": "motion",
    "framer-motion": "motion-react", "three": "threejs",
    "lottie-web": "lottie", "@lottiefiles/dotlottie-web": "lottie",
    "@rive-app/react-canvas": "rive", "@rive-app/react-webgl2": "rive",
    "@rive-app/canvas": "rive", "@rive-app/webgl2": "rive",
}
FRAMEWORK_PACKAGES = {"react": "react", "vue": "vue", "svelte": "svelte",
                      "@angular/core": "angular", "next": "nextjs"}


def inspect_project(project_dir: str | Path, state: AnimationProjectState) -> AnimationProjectState:
    root = Path(project_dir)
    pkg_path = root / "package.json"
    if not pkg_path.is_file():
        state.unknowns.append("No package.json found — framework and packages unverified")
        return state

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        state.unknowns.append(f"package.json unreadable: {exc}")
        return state

    deps: dict[str, str] = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    state.installed_packages = deps

    for name, fw in FRAMEWORK_PACKAGES.items():
        if name in deps:
            state.framework = fw
            state.framework_version = deps[name]
            state.evidence.append(Evidence(f"framework={fw}", "package.json", "verified", deps[name]))
            if fw == "nextjs":
                break  # next implies react but nextjs is more specific

    for lock, mgr in [("package-lock.json", "npm"), ("pnpm-lock.yaml", "pnpm"),
                      ("yarn.lock", "yarn"), ("bun.lockb", "bun")]:
        if (root / lock).is_file():
            state.package_manager = mgr
            break

    # Resolve exact versions from npm lockfile when present (declared ranges otherwise).
    lockfile = root / "package-lock.json"
    if lockfile.is_file():
        try:
            lock_data = json.loads(lockfile.read_text(encoding="utf-8"))
            packages = lock_data.get("packages", {})
            for dep in deps:
                node = packages.get(f"node_modules/{dep}")
                if node and "version" in node:
                    state.resolved_versions[dep] = node["version"]
                    state.evidence.append(Evidence(f"{dep} version", "lockfile", "verified", node["version"]))
        except (json.JSONDecodeError, OSError):
            state.unknowns.append("Lockfile unreadable — versions are declared ranges only")
    else:
        state.unknowns.append("No supported lockfile parsed — versions are declared ranges, not resolved")

    return state


def installed_animation_technologies(state: AnimationProjectState) -> list[str]:
    return sorted({tech for pkg, tech in ANIMATION_PACKAGES.items()
                   if pkg in state.installed_packages})
