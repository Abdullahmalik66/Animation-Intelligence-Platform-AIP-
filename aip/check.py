"""Animation linter — the zero-AI, zero-network, zero-config entry point.

`aip check ./src` finds accessibility violations, memory leaks, and layout
thrashing in animation code. Every rule traces back to a GOV-* governance rule
in shared/governance.md.

Design constraints:
  - Python stdlib only. No parser dependencies.
  - Never modifies files unless fix=True.
  - Never reads outside the requested path.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

SOURCE_SUFFIXES = {".css", ".scss", ".sass", ".less",
                   ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
                   ".vue", ".svelte", ".astro", ".html"}

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt",
             "out", "coverage", "__pycache__", ".venv", "venv", ".svelte-kit"}

Severity = str  # "error" | "warning"


@dataclass
class Finding:
    rule: str
    severity: Severity
    message: str
    file: str
    line: int
    column: int = 1
    governance: str = ""
    fix_hint: str = ""

    def location(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    fixed_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


# ---------------------------------------------------------------- helpers

def _strip_comments(text: str) -> str:
    """Blank out comments while preserving line numbering."""
    def _blank(m: re.Match) -> str:
        return re.sub(r"\S", " ", m.group(0))
    text = re.sub(r"/\*.*?\*/", _blank, text, flags=re.S)
    text = re.sub(r"(?<![:\w])//[^\n]*", _blank, text)
    return text


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _col_of(text: str, index: int) -> int:
    nl = text.rfind("\n", 0, index)
    return index - nl


def _has_reduced_motion(text: str) -> bool:
    return "prefers-reduced-motion" in text or "useReducedMotion" in text


def _duration_ms(value: str) -> Optional[float]:
    m = re.match(r"\s*([\d.]+)\s*(ms|s)\b", value)
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2) == "ms" else n * 1000


# ---------------------------------------------------------------- rules
# Each rule: (source_text, raw_text, relpath) -> Iterable[Finding]

LAYOUT_PROPS = ("width", "height", "top", "left", "right", "bottom",
                "margin", "margin-top", "margin-left", "padding")


def rule_layout_property(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-PERF: animating layout properties forces reflow every frame."""
    for m in re.finditer(r"transition(?:-property)?\s*:\s*([^;{}]+)[;}]", src):
        for prop in LAYOUT_PROPS:
            if re.search(rf"(?<![-\w]){re.escape(prop)}(?![-\w])", m.group(1)):
                yield Finding(
                    rule="perf/no-layout-property", severity="error",
                    message=(f"Transitioning `{prop}` forces layout recalculation "
                             f"on every frame. Use `transform` or `opacity`."),
                    file=path, line=_line_of(src, m.start(1)),
                    column=_col_of(src, m.start(1)),
                    governance="GOV-PERF",
                    fix_hint="Replace with transform: translate/scale, or opacity.")
                break

    # Inside @keyframes blocks
    for kf in re.finditer(r"@keyframes\s+[\w-]+\s*\{", src):
        depth, i, n = 0, kf.end() - 1, len(src)
        while i < n:
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body_start, body_end = kf.end(), i
        body = src[body_start:body_end]
        for pm in re.finditer(r"(?m)^\s*([a-z-]+)\s*:", body):
            if pm.group(1) in LAYOUT_PROPS:
                abs_i = body_start + pm.start(1)
                yield Finding(
                    rule="perf/no-layout-property", severity="error",
                    message=(f"Animating `{pm.group(1)}` in @keyframes forces "
                             f"layout on every frame. Use transform/opacity."),
                    file=path, line=_line_of(src, abs_i),
                    column=_col_of(src, abs_i), governance="GOV-PERF",
                    fix_hint="Use transform: scale()/translate() instead.")


def rule_reduced_motion(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-A11Y: motion must have a non-moving alternative."""
    if _has_reduced_motion(raw):
        return
    m = (re.search(r"@keyframes\s+([\w-]+)", src)
         or re.search(r"(?<![-\w])animation\s*:", src)
         or re.search(r"\.animate\s*\(", src)
         or re.search(r"(?<![-\w])(?:gsap|anime)\s*\.\s*(?:to|from|fromTo|timeline)\s*\(", src))
    if m:
        yield Finding(
            rule="a11y/no-reduced-motion-fallback", severity="error",
            message=("Animation defined with no `prefers-reduced-motion` "
                     "fallback. Users who request reduced motion will still "
                     "see movement."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-A11Y",
            fix_hint="Add @media (prefers-reduced-motion: reduce) { ... }")


def rule_rapid_flash(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-A11Y: >3Hz flashing can trigger photosensitive seizures."""
    for m in re.finditer(r"(?<![-\w])animation\s*:\s*([^;{}]+)[;}]", src):
        decl = m.group(1)
        if "infinite" not in decl:
            continue
        dm = re.search(r"([\d.]+)\s*(ms|s)\b", decl)
        if not dm:
            continue
        ms = _duration_ms(dm.group(0))
        if ms is not None and 0 < ms < 333:
            yield Finding(
                rule="a11y/no-rapid-flash", severity="error",
                message=(f"Infinite animation cycles every {ms:.0f}ms (>3Hz). "
                         f"This can trigger photosensitive seizures (WCAG 2.3.1)."),
                file=path, line=_line_of(src, m.start(1)),
                column=_col_of(src, m.start(1)), governance="GOV-A11Y",
                fix_hint="Slow the cycle to >=333ms, or remove the flash.")


def rule_infinite_no_pause(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-A11Y: indefinite motion needs a pause affordance."""
    if _has_reduced_motion(raw):
        return
    for m in re.finditer(r"animation-iteration-count\s*:\s*infinite", src):
        yield Finding(
            rule="a11y/infinite-no-pause", severity="warning",
            message=("Infinite animation with no pause control and no "
                     "reduced-motion fallback (WCAG 2.2.2)."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-A11Y",
            fix_hint="Provide a pause control or a reduced-motion fallback.")


def rule_gsap_cleanup(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-OWNERSHIP: GSAP contexts/ScrollTriggers leak without teardown."""
    has_cleanup = re.search(r"\.(revert|kill|killAll)\s*\(", src)
    if has_cleanup:
        return
    for pat, label in ((r"ScrollTrigger\s*\.\s*create\s*\(", "ScrollTrigger"),
                       (r"gsap\s*\.\s*context\s*\(", "gsap.context()"),
                       (r"gsap\s*\.\s*timeline\s*\(", "gsap.timeline()")):
        m = re.search(pat, src)
        if m:
            yield Finding(
                rule="leak/gsap-no-revert", severity="error",
                message=(f"{label} created but never reverted or killed. "
                         f"This leaks on unmount and duplicates on remount."),
                file=path, line=_line_of(src, m.start()),
                column=_col_of(src, m.start()), governance="GOV-OWNERSHIP",
                fix_hint="Return () => ctx.revert() from your effect.")
            return


def rule_observer_cleanup(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-OWNERSHIP: observers hold references to detached nodes."""
    if ".disconnect(" in src or ".unobserve(" in src:
        return
    m = re.search(r"new\s+(IntersectionObserver|ResizeObserver|MutationObserver)\s*\(", src)
    if m:
        yield Finding(
            rule="leak/observer-not-disconnected", severity="error",
            message=(f"{m.group(1)} created but never disconnected. It keeps "
                     f"detached DOM nodes alive."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-OWNERSHIP",
            fix_hint="Call observer.disconnect() in your cleanup function.")


def rule_raf_cleanup(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-OWNERSHIP: RAF loops run forever after unmount."""
    if "cancelAnimationFrame" in src:
        return
    m = re.search(r"requestAnimationFrame\s*\(", src)
    if m and len(re.findall(r"requestAnimationFrame\s*\(", src)) >= 2:
        yield Finding(
            rule="leak/raf-not-cancelled", severity="error",
            message=("requestAnimationFrame loop with no cancelAnimationFrame. "
                     "The loop keeps running after the component unmounts."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-OWNERSHIP",
            fix_hint="Store the frame id and cancelAnimationFrame(id) on cleanup.")


def rule_webgl_dispose(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-OWNERSHIP: GPU resources are not garbage collected."""
    if ".dispose(" in src:
        return
    m = re.search(r"new\s+THREE\s*\.\s*(\w*(?:Geometry|Material|Texture))\s*\(", src)
    if m:
        yield Finding(
            rule="leak/webgl-not-disposed", severity="error",
            message=(f"THREE.{m.group(1)} created but never disposed. GPU memory "
                     f"is not reclaimed by the garbage collector."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-OWNERSHIP",
            fix_hint="Call .dispose() on geometries, materials and textures.")


def rule_listener_cleanup(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-OWNERSHIP: scroll/resize listeners leak and cost performance."""
    adds = re.findall(r"addEventListener\s*\(\s*['\"](\w+)['\"]", src)
    removes = set(re.findall(r"removeEventListener\s*\(\s*['\"](\w+)['\"]", src))
    for ev in ("scroll", "resize", "mousemove", "pointermove", "wheel"):
        if ev in adds and ev not in removes:
            m = re.search(rf"addEventListener\s*\(\s*['\"]{ev}['\"]", src)
            if m:
                yield Finding(
                    rule="leak/listener-not-removed", severity="error",
                    message=(f"'{ev}' listener added but never removed. It leaks "
                             f"and keeps firing after unmount."),
                    file=path, line=_line_of(src, m.start()),
                    column=_col_of(src, m.start()), governance="GOV-OWNERSHIP",
                    fix_hint=f"removeEventListener('{ev}', handler) on cleanup.")


LAYOUT_READS = r"(offsetWidth|offsetHeight|offsetTop|offsetLeft|clientWidth|clientHeight|scrollWidth|scrollHeight|getBoundingClientRect)"


def rule_layout_thrash(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-PERF: interleaved layout reads and writes force sync reflow."""
    for hm in re.finditer(
            r"addEventListener\s*\(\s*['\"](?:scroll|resize)['\"]|requestAnimationFrame\s*\(", src):
        window = src[hm.start():hm.start() + 700]
        rm = re.search(LAYOUT_READS, window)
        if not rm:
            continue
        after = window[rm.end():]
        if re.search(r"\.style\s*\.\s*\w+\s*=|\.style\s*\.\s*setProperty\s*\(", after):
            abs_i = hm.start() + rm.start()
            yield Finding(
                rule="perf/no-layout-thrash", severity="warning",
                message=(f"Layout read (`{rm.group(1)}`) followed by a style write "
                         f"inside a scroll/RAF handler forces synchronous reflow."),
                file=path, line=_line_of(src, abs_i),
                column=_col_of(src, abs_i), governance="GOV-PERF",
                fix_hint="Batch all reads first, then all writes.")
            return


def rule_untrusted_asset(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-SECURITY: remote animation assets execute in your origin."""
    for m in re.finditer(r"['\"](https?://[^'\"]+\.(?:json|riv|glb|gltf|lottie))['\"]", src):
        yield Finding(
            rule="sec/untrusted-asset", severity="warning",
            message=(f"Remote animation asset loaded from {m.group(1)[:60]}… "
                     f"with no documented integrity or CSP policy."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-SECURITY",
            fix_hint="Self-host under /public, or document CSP + integrity.")


def rule_over_engineered(src: str, raw: str, path: str) -> Iterable[Finding]:
    """GOV-ROUTING: heavy library imported for something CSS can do."""
    m = re.search(r"(?m)^\s*import\s+[^;\n]*from\s+['\"](gsap|three)['\"]", src)
    if not m:
        return
    lib = m.group(1)
    calls = len(re.findall(rf"(?<![-\w]){lib}\s*\.", src, re.I))
    simple_only = bool(re.search(r":hover|onMouseEnter|onMouseOver", src))
    if calls <= 2 and simple_only:
        yield Finding(
            rule="arch/over-engineered", severity="warning",
            message=(f"`{lib}` imported but only used for a simple hover effect. "
                     f"A CSS transition would remove this dependency."),
            file=path, line=_line_of(src, m.start()),
            column=_col_of(src, m.start()), governance="GOV-ROUTING",
            fix_hint="Use `transition: transform .2s` instead.")


CSS_RULES: tuple[Callable, ...] = (
    rule_layout_property, rule_reduced_motion, rule_rapid_flash,
    rule_infinite_no_pause,
)
JS_RULES: tuple[Callable, ...] = (
    rule_layout_property, rule_reduced_motion, rule_gsap_cleanup,
    rule_observer_cleanup, rule_raf_cleanup, rule_webgl_dispose,
    rule_listener_cleanup, rule_layout_thrash, rule_untrusted_asset,
    rule_over_engineered,
)

CSS_SUFFIXES = {".css", ".scss", ".sass", ".less"}


# ---------------------------------------------------------------- engine

def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix in SOURCE_SUFFIXES:
            yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in SOURCE_SUFFIXES:
            if not any(part in SKIP_DIRS for part in p.parts):
                yield p


def _is_animation_related(text: str) -> bool:
    return bool(re.search(
        r"@keyframes|(?<![-\w])animation\s*:|(?<![-\w])transition\s*:|"
        r"requestAnimationFrame|IntersectionObserver|ResizeObserver|"
        r"MutationObserver|addEventListener|(?<![-\w])gsap|ScrollTrigger|"
        r"THREE\s*\.|framer-motion|\bmotion\b|\.animate\s*\(|anime\s*\(", text))


def check_path(path: str | Path, fix: bool = False) -> Report:
    root = Path(path).expanduser().resolve()
    report = Report()
    if not root.exists():
        raise FileNotFoundError(f"No such path: {root}")

    base = root if root.is_dir() else root.parent
    for file in _iter_files(root):
        try:
            raw = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        report.files_scanned += 1
        if not _is_animation_related(raw):
            continue
        src = _strip_comments(raw)
        try:
            rel = str(file.relative_to(base))
        except ValueError:
            rel = str(file)
        rules = CSS_RULES if file.suffix in CSS_SUFFIXES else JS_RULES
        for rule in rules:
            report.findings.extend(rule(src, raw, rel))

        if fix:
            report.fixed_count += _apply_fixes(file, raw, report.findings, rel)

    report.findings.sort(key=lambda f: (f.file, f.line, f.rule))
    return report


def _apply_fixes(file: Path, raw: str, findings: list[Finding], rel: str) -> int:
    """Only mechanical, provably-safe fixes. Currently: append a
    prefers-reduced-motion guard to CSS files that lack one."""
    mine = [f for f in findings if f.file == rel
            and f.rule == "a11y/no-reduced-motion-fallback"]
    if not mine or file.suffix not in CSS_SUFFIXES or _has_reduced_motion(raw):
        return 0
    guard = (
        "\n\n/* Added by `aip check --fix` (GOV-A11Y) */\n"
        "@media (prefers-reduced-motion: reduce) {\n"
        "  *, *::before, *::after {\n"
        "    animation-duration: 0.01ms !important;\n"
        "    animation-iteration-count: 1 !important;\n"
        "    transition-duration: 0.01ms !important;\n"
        "    scroll-behavior: auto !important;\n"
        "  }\n"
        "}\n")
    file.write_text(raw + guard, encoding="utf-8")
    for f in mine:
        findings.remove(f)
    return 1


# ---------------------------------------------------------------- output

_COLOR = {"error": "\033[31m", "warning": "\033[33m",
          "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m"}


def _c(key: str, text: str, enable: bool) -> str:
    return f"{_COLOR[key]}{text}{_COLOR['reset']}" if enable else text


def format_report(report: Report, fmt: str = "human", color: bool = True) -> str:
    if fmt == "json":
        return json.dumps({
            "files_scanned": report.files_scanned,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "fixed": report.fixed_count,
            "findings": [vars(f) for f in report.findings],
        }, indent=2)

    if fmt == "github":
        return "\n".join(
            f"::{f.severity} file={f.file},line={f.line},col={f.column},"
            f"title={f.rule}::{f.message}" for f in report.findings)

    if fmt == "sarif":
        rules = sorted({f.rule for f in report.findings})
        return json.dumps({
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {
                    "name": "aip", "informationUri": "https://github.com/aip",
                    "rules": [{"id": r} for r in rules]}},
                "results": [{
                    "ruleId": f.rule,
                    "level": "error" if f.severity == "error" else "warning",
                    "message": {"text": f.message},
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": f.file},
                        "region": {"startLine": f.line,
                                   "startColumn": f.column}}}],
                } for f in report.findings]}]}, indent=2)

    # human
    if not report.findings:
        return _c("dim", f"✔ No animation problems found "
                         f"({report.files_scanned} files scanned).", color)

    out: list[str] = []
    current = None
    width = max((len(f.message) for f in report.findings), default=0)
    for f in report.findings:
        if f.file != current:
            current = f.file
            out.append("")
            out.append(_c("bold", f.file, color))
        loc = f"{f.line}:{f.column}"
        out.append(f"  {_c('dim', loc.rjust(7), color)}  "
                   f"{_c(f.severity, f.severity.ljust(7), color)}  "
                   f"{f.message.ljust(width)}  {_c('dim', f.rule, color)}")
        if f.fix_hint:
            out.append(f"  {' ' * 7}  {_c('dim', '→ ' + f.fix_hint, color)}")

    n = len(report.findings)
    summary = (f"\n{n} problem{'s' if n != 1 else ''} "
               f"({report.error_count} error{'s' if report.error_count != 1 else ''}, "
               f"{report.warning_count} warning"
               f"{'s' if report.warning_count != 1 else ''})")
    out.append(_c("bold", summary, color))
    if report.fixed_count:
        out.append(_c("dim", f"{report.fixed_count} file(s) auto-fixed.", color))
    out.append(_c("dim", f"{report.files_scanned} files scanned.", color))
    return "\n".join(out)
