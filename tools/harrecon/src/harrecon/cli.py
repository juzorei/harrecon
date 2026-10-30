"""harrecon CLI: turn a HAR capture into the private API's shape, then a typed client."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .client import generate
from .diff import diff
from .har import api_calls, auth_markers, load, schema_for, schema_json


def _resolve(calls, spec: str):
    """Endpoint spec: 'GET /path' or '/path'."""
    for call in calls:
        method, _, path = spec.partition(" ")
        if not path:
            method, path = call.entries[0].method, spec
        if call.entries[0].path == path and (not method or call.entries[0].method == method.upper()):
            return call
    return None


def cmd_inventory(args) -> int:
    entries = load(args.har)
    calls = api_calls(entries, host=args.host)
    if args.json:
        print(json.dumps({
            "auth": auth_markers(entries),
            "endpoints": [{"endpoint": c.endpoint, "host": c.host, "samples": len(c.entries),
                           "statuses": sorted({e.status for e in c.entries}),
                           "query": bool(c.entries[0].query),
                           "request_body": c.entries[0].request_body is not None}
                          for c in calls],
        }, indent=2))
        return 0
    print(f"captured {len(entries)} entries, {len(calls)} JSON endpoints\n")
    markers = auth_markers(entries)
    if markers:
        print("auth mechanisms:")
        for kind, samples in markers.items():
            print(f"  {kind}: {samples[0]}")
        print()
    for c in calls:
        statuses = "/".join(str(e.status) for e in sorted(c.entries, key=lambda e: e.status)[:3])
        flags = []
        if c.entries[0].query:
            flags.append("query")
        if c.entries[0].request_body:
            flags.append("body")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        print(f"  {c.endpoint}  [{c.host}] {statuses}{flag_text}")
    if not calls:
        print("  (no JSON API calls found — recapture with the DevTools 'Preserve log' on, "
              "and make sure the request you care about returns JSON)")
        return 1
    return 0


def cmd_schema(args) -> int:
    entries = load(args.har)
    call = _resolve(api_calls(entries, host=args.host), args.endpoint)
    if call is None:
        print(f"harrecon: error: endpoint {args.endpoint!r} not found; run inventory", file=sys.stderr)
        return 2
    schema = schema_for(call)
    if args.json:
        print(json.dumps(schema, indent=2))
    else:
        print(f"{call.endpoint} — {len(call.entries)} sample(s)")
        print(schema_json(schema))
    return 0


def cmd_diff(args) -> int:
    a, b = load(args.har_a), load(args.har_b)
    d = diff(a, b, host=args.host)
    if args.json:
        print(json.dumps({
            "added": [c.endpoint for c in d.added],
            "removed": [c.endpoint for c in d.removed],
            "changed": [{"endpoint": c.endpoint, "before": sa, "after": sb} for c, sa, sb in d.changed],
        }, indent=2))
        return 0
    for c in d.added:
        print(f"  + {c.endpoint} [{c.host}]")
    for c in d.removed:
        print(f"  - {c.endpoint} [{c.host}]")
    for c, sa, sb in d.changed:
        print(f"  ~ {c.endpoint} [{c.host}] schema changed:")
        print(f"     before: {json.dumps(sa)[:160]}")
        print(f"     after:  {json.dumps(sb)[:160]}")
    if d.quiet:
        print("no API changes between the captures")
    return 0


def cmd_gen(args) -> int:
    entries = load(args.har)
    call = _resolve(api_calls(entries, host=args.host), args.endpoint)
    if call is None:
        print(f"harrecon: error: endpoint {args.endpoint!r} not found; run inventory", file=sys.stderr)
        return 2
    source = generate(call)
    if args.out:
        open(args.out, "w", encoding="utf-8", newline="\n").write(source)
        print(f"wrote {args.out}")
    else:
        print(source)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harrecon", description=__doc__)
    parser.add_argument("--version", action="version", version=f"harrecon {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inventory", help="what API does this capture contain")
    p.add_argument("har")
    p.add_argument("--host", help="filter to one host")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inventory)

    p = sub.add_parser("schema", help="merged response schema of one endpoint")
    p.add_argument("har")
    p.add_argument("endpoint", help="'GET /path' or '/path' (as inventory prints it)")
    p.add_argument("--host")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser("diff", help="what changed between two captures of the same API")
    p.add_argument("har_a")
    p.add_argument("har_b")
    p.add_argument("--host")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("gen", help="generate a typed client skeleton for one endpoint")
    p.add_argument("har")
    p.add_argument("endpoint")
    p.add_argument("--host")
    p.add_argument("--class-name")
    p.add_argument("--out", help="write to file instead of stdout")
    p.set_defaults(func=cmd_gen)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"harrecon: error: {exc.filename or exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"harrecon: error: not valid JSON/HAR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"harrecon: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
