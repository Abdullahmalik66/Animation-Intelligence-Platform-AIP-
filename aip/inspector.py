"""Deterministic project inspector (Phase 6 support / Principle 4).

Extracts framework, package manager, and installed animation packages from a
target project's manifests and lockfiles. No LLM involvement. Read-only.
"""
from __future__ import annotations

import json
import re
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

    _resolve_versions(root, state, deps)
    _inspect_exports(root, state, deps)
    _discover_assets(root, state)
    _detect_toolchain(root, state, deps)
    return state


def _resolve_versions(root: Path, state: AnimationProjectState, deps: dict) -> None:
    """Exact versions from npm / pnpm / yarn lockfiles (static parsing only)."""
    npm_lock = root / "package-lock.json"
    if npm_lock.is_file():
        try:
            packages = json.loads(npm_lock.read_text(encoding="utf-8")).get("packages", {})
            for dep in deps:
                node = packages.get(f"node_modules/{dep}")
                if node and "version" in node:
                    state.resolved_versions[dep] = node["version"]
                    state.evidence.append(Evidence(f"{dep} version", "lockfile", "verified", node["version"]))
            return
        except (json.JSONDecodeError, OSError):
            state.unknowns.append("npm lockfile unreadable")

    pnpm_lock = root / "pnpm-lock.yaml"
    if pnpm_lock.is_file():
        try:
            text = pnpm_lock.read_text(encoding="utf-8")
            for dep in deps:
                # pnpm v9 format: "  /gsap@3.12.5:" or "  gsap@3.12.5:"; v6: "  /gsap/3.12.5:"
                m = re.search(rf"(?m)^\s+/?{re.escape(dep)}[@/](\d+\.\d+\.\d+[^:'\"\s(]*)", text)
                if m:
                    state.resolved_versions[dep] = m.group(1)
                    state.evidence.append(Evidence(f"{dep} version", "pnpm-lock.yaml", "verified", m.group(1)))
            return
        except OSError:
            state.unknowns.append("pnpm lockfile unreadable")

    yarn_lock = root / "yarn.lock"
    if yarn_lock.is_file():
        try:
            text = yarn_lock.read_text(encoding="utf-8")
            for dep in deps:
                # classic + berry: entry header containing "dep@..." then 'version "x"' / version: x
                m = re.search(rf'(?ms)^"?{re.escape(dep)}@[^\n]*:\n(?:[^\n]*\n)*?\s+version:?\s+"?([\d][^"\n]*)"?', text)
                if m:
                    state.resolved_versions[dep] = m.group(1)
                    state.evidence.append(Evidence(f"{dep} version", "yarn.lock", "verified", m.group(1)))
            return
        except OSError:
            state.unknowns.append("yarn lockfile unreadable")

    state.unknowns.append("No supported lockfile parsed — versions are declared ranges, not resolved")


def _inspect_exports(root: Path, state: AnimationProjectState, deps: dict) -> None:
    """Static export/declaration inspection: package.json 'exports' map and
    presence of .d.ts entrypoints. Never executes package code."""
    for dep, tech in ANIMATION_PACKAGES.items():
        if dep not in deps:
            continue
        pkg_dir = root / "node_modules" / dep
        meta = pkg_dir / "package.json"
        if not meta.is_file():
            state.unknowns.append(f"{dep}: node_modules not installed — exports unverified")
            continue
        try:
            pj = json.loads(meta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state.unknowns.append(f"{dep}: package.json unreadable")
            continue
        exports = pj.get("exports")
        export_keys = sorted(exports.keys()) if isinstance(exports, dict) else \
            [pj.get("main", "index.js")]
        types_entry = pj.get("types") or pj.get("typings")
        state.verified_exports[dep] = export_keys
        state.evidence.append(Evidence(f"{dep} exports", "node_modules/package.json",
                                       "verified", ",".join(export_keys[:10])))
        if types_entry and (pkg_dir / types_entry).is_file():
            state.evidence.append(Evidence(f"{dep} declarations", "node_modules",
                                           "verified", types_entry))
        else:
            state.unknowns.append(f"{dep}: TypeScript declarations not verified")


ASSET_FORMATS = {".riv": "rive", ".lottie": "dotlottie", ".glb": "gltf-binary",
                 ".gltf": "gltf", ".hdr": "hdr-texture"}


def _discover_assets(root: Path, state: AnimationProjectState) -> None:
    """Local asset discovery. Same-origin/local is a DELIVERY characteristic —
    trust stays 'unknown' until an approval source marks it approved."""
    approved_file = root / ".aip-approved-assets.json"
    approved: set[str] = set()
    if approved_file.is_file():
        try:
            approved = set(json.loads(approved_file.read_text(encoding="utf-8")).get("approved", []))
        except (json.JSONDecodeError, OSError):
            state.unknowns.append("Approved-asset config unreadable")
    for p in root.rglob("*"):
        if "node_modules" in p.parts or not p.is_file():
            continue
        fmt = ASSET_FORMATS.get(p.suffix.lower())
        is_lottie_json = p.suffix == ".json" and _looks_like_lottie(p)
        if not fmt and not is_lottie_json:
            continue
        rel = p.relative_to(root).as_posix()
        state.assets.append({
            "path": rel, "format": fmt or "lottie-json",
            "origin": "local", "delivery": "same-origin",
            "trust": "approved" if rel in approved else "unknown",
            "size_bytes": p.stat().st_size,
            "approval_source": ".aip-approved-assets.json" if rel in approved else None,
        })
        if rel not in approved:
            state.unknowns.append(f"Asset trust not established: {rel}")


def _looks_like_lottie(p: Path) -> bool:
    try:
        head = p.read_text(encoding="utf-8", errors="ignore")[:500]
        return '"layers"' in head and ('"v"' in head or '"fr"' in head)
    except OSError:
        return False


def _detect_toolchain(root: Path, state: AnimationProjectState, deps: dict) -> None:
    if (root / "tsconfig.json").is_file():
        state.evidence.append(Evidence("typescript", "tsconfig.json", "verified", "present"))
    for bundler in ("vite", "webpack", "esbuild", "rollup", "@rspack/core"):
        if bundler in deps:
            state.bundler = bundler
            break
    if "next" in deps:
        state.runtime = "nextjs-ssr"
    try:
        pj = json.loads((root / "package.json").read_text(encoding="utf-8"))
        if "browserslist" in pj:
            state.browser_support_policy = json.dumps(pj["browserslist"])
            state.evidence.append(Evidence("browser support", "package.json", "verified", "browserslist"))
    except (json.JSONDecodeError, OSError):
        pass


def installed_animation_technologies(state: AnimationProjectState) -> list[str]:
    return sorted({tech for pkg, tech in ANIMATION_PACKAGES.items()
                   if pkg in state.installed_packages})
