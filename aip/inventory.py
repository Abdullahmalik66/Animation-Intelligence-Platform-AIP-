"""Deterministic repository inventory and token baseline.

Stdlib-only. Token counts are ESTIMATES (chars/4 heuristic) because no model
tokenizer dependency is installed; every figure is labelled "estimated".
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_EXT = {".md", ".txt", ".yml", ".yaml", ".json", ".css", ".tsx", ".ts", ".js", ".py", ""}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SENSITIVE_RE = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*\S", re.I)


def estimate_tokens(text: str) -> int:
    """Estimated tokens: chars/4 heuristic. NOT an exact model count."""
    return max(1, len(text) // 4)


def classify_role(rel: str) -> str:
    if rel.startswith("skills/"):
        return "canonical-skill"
    if rel.startswith("references/"):
        return "canonical-reference"
    if rel.startswith("shared/"):
        return "shared-governance"
    if rel.startswith(("manifests/", "schemas/")):
        return "platform-metadata"
    if rel.startswith("aip/"):
        return "platform-code"
    if rel.startswith("examples/"):
        return "example"
    if rel.startswith(("adapters/", ".github/prompts")):
        return "adapter"
    if rel.startswith(("docs/", "evals/", "tests/")):
        return "docs-or-tests"
    return "meta"


def build_inventory() -> dict:
    files = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        entry: dict = {"path": rel, "size_bytes": p.stat().st_size,
                       "role": classify_role(rel),
                       "generated": rel.startswith("docs/analysis/"),
                       "context_eligible": p.suffix in {".md", ".css", ".tsx"} and
                                            not rel.endswith(".bak")}
        try:
            text = p.read_text(encoding="utf-8")
            entry["estimated_tokens"] = estimate_tokens(text)
            entry["sha256"] = hashlib.sha256(text.encode()).hexdigest()[:16]
            entry["possible_sensitive"] = bool(SENSITIVE_RE.search(text))
        except (UnicodeDecodeError, OSError):
            entry["estimated_tokens"] = None
            entry["context_eligible"] = False
        files.append(entry)
    skills = [f for f in files if f["role"] == "canonical-skill" and f["estimated_tokens"]]
    return {
        "note": "All token figures are estimates (chars/4). No exact tokenizer installed.",
        "total_files": len(files),
        "estimated_tokens_all_skills": sum(f["estimated_tokens"] for f in skills),
        "files": files,
    }


def main() -> None:
    inv = build_inventory()
    out = ROOT / "docs" / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(inv, indent=2))
    print(f"Files: {inv['total_files']}; estimated skill tokens: "
          f"{inv['estimated_tokens_all_skills']}")


if __name__ == "__main__":
    sys.exit(main())
