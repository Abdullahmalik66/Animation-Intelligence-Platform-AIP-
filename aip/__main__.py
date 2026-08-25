"""CLI consumer (Workstream 14): the first real adapter over the modular
pipeline. Emits either a clarification, or the assembled specialist packet
(for host agents like Claude/Copilot to execute), or — when a live transport
is configured — the full validated result.

Usage:
  python3 -m aip "request text" [--project DIR] [--mode beginner|guided|expert]
          [--flags fable,retrieval,compression] [--legacy]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass

from .orchestrator import handle
from .backends.fable import FableBackend


def _jsonable(obj):
    if is_dataclass(obj):
        return asdict(obj)
    return str(obj)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aip")
    ap.add_argument("request")
    ap.add_argument("--project", default=None)
    ap.add_argument("--mode", default="beginner", choices=["beginner", "guided", "expert"])
    ap.add_argument("--answer", default=None, help="clarification answer")
    ap.add_argument("--flags", default="", help="comma list: fable,retrieval,compression")
    ap.add_argument("--legacy", action="store_true")
    args = ap.parse_args(argv)

    flag_map = {"fable": "modular_context_with_fable",
                "retrieval": "modular_context_with_retrieval",
                "compression": "modular_context_with_compression"}
    flags = {"modular_context": not args.legacy, "legacy_full_skill": args.legacy}
    for f in filter(None, args.flags.split(",")):
        flags[flag_map[f]] = True

    backend = FableBackend() if flags.get("modular_context_with_fable") else None
    result = handle(args.request, project_dir=args.project, user_mode=args.mode,
                    clarification_answer=args.answer, flags=flags, backend=backend)

    out = {"status": result["status"],
           "explanation": result.get("explanation"),
           "clarification": _jsonable(result.get("clarification")) if result.get("clarification") else None,
           "readiness": result["state"].implementation_readiness,
           "confidence": result["state"].confidence,
           "trace": result.get("trace")}
    print(json.dumps(out, indent=2, default=_jsonable))
    return 0


if __name__ == "__main__":
    sys.exit(main())
