#!/usr/bin/env python3
"""Read-only M32.3E3F2 provider market-price capability audit.

The default invocation uses only the checked-in/static declaration.  It does
not fetch a provider, inspect credentials, route traffic, or write a database.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.market_data.provider_price_capability import (
    audit_provider_market_price_capability,
    current_yahoo_chart_set_capability,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only provider market-price capability audit (M32.3E3F2)")
    parser.add_argument("--samples", type=Path, help="optional sanitized JSON list of field-availability samples")
    parser.add_argument("--output", type=Path, help="optional JSON report destination")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--network-probe", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.commit:
        raise SystemExit("--commit is unsupported; M32.3E3F2 capability audit is read-only")
    if args.network_probe:
        raise SystemExit("--network-probe is unsupported by default; supply reviewed sanitized samples instead")
    samples: list[dict[str, object]] = []
    if args.samples:
        try:
            raw = json.loads(args.samples.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid sanitized samples: {exc}") from exc
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise SystemExit("sanitized samples must be a JSON list of objects")
        samples = raw
    report = audit_provider_market_price_capability(
        current_yahoo_chart_set_capability(), samples=samples,
        provenance=((f"sanitized-samples:{args.samples.name}",) if args.samples else ("static-current-path-declaration",)),
    )
    rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
