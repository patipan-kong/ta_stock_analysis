#!/usr/bin/env python3
"""M31.5 Registry execution coverage report and explicit remediation runner."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models.database import SessionLocal
from services.execution_registry_preflight import build_execution_registry_preflight
from services.execution_registry_remediation import (
    apply_registry_remediation,
    parse_registry_remediation_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report Registry execution readiness; read-only unless --commit is explicit"
    )
    parser.add_argument("--workspace-id", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None, help="optional JSON output path")
    parser.add_argument(
        "--remediation-manifest",
        type=Path,
        default=None,
        help="versioned explicit-evidence JSON manifest; dry-run unless --commit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="explicitly request rollback-only remediation preview (the default)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="commit only approved instructions from --remediation-manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.commit and args.dry_run:
        raise SystemExit("--commit and --dry-run are mutually exclusive")
    if args.commit and args.remediation_manifest is None:
        raise SystemExit("--commit requires --remediation-manifest")

    db = SessionLocal()
    try:
        payload = build_execution_registry_preflight(db, workspace_id=args.workspace_id).to_dict()
        if args.remediation_manifest is not None:
            manifest_payload = json.loads(args.remediation_manifest.read_text(encoding="utf-8"))
            instructions = parse_registry_remediation_manifest(manifest_payload)
            payload["remediation"] = apply_registry_remediation(
                db,
                instructions,
                commit=args.commit,
            ).to_dict()
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.output is not None:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
