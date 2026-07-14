#!/usr/bin/env python3
"""Generate the read-only M31.6 Wave 1 evidence dossier/manifest."""
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
from services.execution_registry_wave1 import build_execution_registry_wave1_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the exact-match-only M31.6 Wave 1 Registry evidence manifest"
        )
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    db = SessionLocal()
    try:
        payload = build_execution_registry_wave1_manifest(db).to_dict()
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.write_text(rendered, encoding="utf-8")
        db.rollback()
        return 0
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
