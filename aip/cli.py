"""AIP command line interface.

Usage:
  aip check PATH [--fix] [--format human|json|sarif|github]
  aip run "request" [--project DIR] [--mode beginner|guided|expert]
  aip providers list | doctor

`aip check` requires no AI, no network, and no credentials.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass

from .check import check_path, format_report


def _jsonable(obj):
    if is_dataclass(obj):
        return asdict(obj)
    return str(obj)


def build_registry():
    from .gateway import ProviderRegistry, ProviderStatus
    from .backends.mock import MockAdapter, ReplayAdapter
    reg = ProviderRegistry()
    reg.register(MockAdapter(), status=ProviderStatus.AVAILABLE)
    reg.register(ReplayAdapter(fixture_path="docs/analysis/replay-fixtures.jsonl"),
                 status=ProviderStatus.CONFIGURED)
    return reg


def cmd_check(args) -> int:
    try:
        report = check_path(args.path, fix=args.fix)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    use_colour = args.format == "human" and sys.stdout.isatty()
    print(format_report(report, fmt=args.format, color=use_colour))
    return 1 if report.error_count else 0


def cmd_run(args) -> int:
    from .orchestrator import handle
    from .gateway import ModelGateway

    flag_map = {"model": "modular_context_with_model",
                "retrieval": "modular_context_with_retrieval",
                "compression": "modular_context_with_compression"}
    flags = {"modular_context": not args.legacy, "legacy_full_skill": args.legacy}
    for f in filter(None, args.flags.split(",")):
        if f not in flag_map:
            print(f"error: unknown flag '{f}'. Valid: {', '.join(flag_map)}",
                  file=sys.stderr)
            return 2
        flags[flag_map[f]] = True

    gateway = None
    if flags.get("modular_context_with_model"):
        gateway = ModelGateway(registry=build_registry())
    provider = None if args.provider == "auto" else args.provider

    result = handle(args.request, project_dir=args.project, user_mode=args.mode,
                    clarification_answer=args.answer, flags=flags,
                    gateway=gateway, provider=provider or "mock")
    out = {"status": result["status"],
           "explanation": result.get("explanation"),
           "clarification": (_jsonable(result["clarification"])
                             if result.get("clarification") else None),
           "selection": (_jsonable(result["selection"])
                         if result.get("selection") else None),
           "readiness": result["state"].implementation_readiness,
           "confidence": result["state"].confidence,
           "trace": result.get("trace")}
    print(json.dumps(out, indent=2, default=_jsonable))
    return 0


def cmd_providers(args) -> int:
    from .gateway import ProviderStatus
    reg = build_registry()
    if args.action == "list":
        rows = [{"provider": d.provider_id, "model": d.model,
                 "status": d.status.value,
                 "capabilities": {k: (v.value if hasattr(v, "value") else v)
                                  for k, v in asdict(d.capabilities).items()
                                  if v is not None}}
                for d in reg.list_available()]
        print(json.dumps(rows, indent=2))
        return 0

    problems = []
    for d in reg.list_available():
        if d.status == ProviderStatus.UNAVAILABLE:
            problems.append(f"{d.provider_id}: unavailable (no credentials)")
        if d.status == ProviderStatus.MISCONFIGURED:
            problems.append(f"{d.provider_id}: misconfigured")
    print(json.dumps({"ok": not problems, "problems": problems,
                      "note": "no billable request was made"}, indent=2))
    return 0 if not problems else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="aip", description="Animation Intelligence Platform")
    sub = ap.add_subparsers(dest="cmd", required=True)

    chk = sub.add_parser("check", help="Lint animation code. No AI required.")
    chk.add_argument("path", nargs="?", default=".")
    chk.add_argument("--fix", action="store_true",
                     help="Apply safe mechanical fixes.")
    chk.add_argument("--format", default="human",
                     choices=["human", "json", "sarif", "github"])
    chk.set_defaults(func=cmd_check)

    run_p = sub.add_parser("run", help="Route an animation request.")
    run_p.add_argument("request")
    run_p.add_argument("--project", default=None)
    run_p.add_argument("--mode", default="beginner",
                       choices=["beginner", "guided", "expert"])
    run_p.add_argument("--answer", default=None)
    run_p.add_argument("--provider", default="auto")
    run_p.add_argument("--flags", default="")
    run_p.add_argument("--legacy", action="store_true")
    run_p.set_defaults(func=cmd_run)

    prov = sub.add_parser("providers", help="Inspect model providers.")
    prov.add_argument("action", choices=["list", "doctor"])
    prov.set_defaults(func=cmd_providers)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(
        list(sys.argv[1:] if argv is None else argv))
    return args.func(args)
