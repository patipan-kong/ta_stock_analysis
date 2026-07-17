#!/usr/bin/env python3
"""Read-only M32.3E3R2 Registry lot-capability evidence preflight."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models.database import SessionLocal
from services.execution_lot_capability import (
    LotCapabilityManifestError,
    build_lot_capability_preflight,
    parse_lot_capability_manifest,
)


def _parse_timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--generated-at must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise argparse.ArgumentTypeError("--generated-at must include a timezone offset")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Registry lot-capability evidence preflight (M32.3E3R2)"
    )
    parser.add_argument("--manifest", type=Path, default=None, help="strict future-review evidence manifest")
    parser.add_argument("--output", type=Path, default=None, help="optional deterministic JSON artifact path")
    parser.add_argument("--generated-at", type=_parse_timestamp, default=None, help="explicit ISO-8601 report time")
    parser.add_argument("--environment-reference", default="cli", help="non-secret environment label recorded in the report")
    # Deliberately present only to issue an explicit, safe refusal instead of
    # letting argparse silently imply that an R2 write mode exists.
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.commit:
        raise SystemExit("--commit is unsupported in M32.3E3R2; this CLI is read-only")
    manifest = None
    source_references: tuple[str, ...] = ()
    if args.manifest is not None:
        try:
            manifest = parse_lot_capability_manifest(
                json.loads(args.manifest.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, LotCapabilityManifestError) as exc:
            raise SystemExit(f"invalid lot-capability manifest: {exc}") from exc
        source_references = (f"manifest:{args.manifest.name}",)
    generated_at = args.generated_at or datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        report = build_lot_capability_preflight(
            db,
            generated_at=generated_at,
            environment_reference=args.environment_reference,
            source_references=source_references,
            manifest=manifest,
        )
        rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.write_text(rendered, encoding="utf-8")
        return 0
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
