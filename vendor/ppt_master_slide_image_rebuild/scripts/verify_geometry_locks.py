#!/usr/bin/env python3
"""
PPT Master - Geometry Locks Verifier

Verify rebuilt SVG against geometry_locks[] export hard constraints in
layout_reference.json.

Usage:
    python3 scripts/verify_geometry_locks.py <project_path>
    python3 scripts/verify_geometry_locks.py <project_path> --write-report

Examples:
    python3 scripts/verify_geometry_locks.py projects/demo --write-report

Dependencies:
    None (only uses standard library plus repository helpers)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from geometry_locks_lib import Thresholds, verify_project  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify SVG geometry against layout_reference geometry_locks[].",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/geometry_locks_report.json")
    parser.add_argument("--report", type=Path, help="Custom report output path")
    parser.add_argument("--position-threshold", type=float, default=3.0, help="Position tolerance in px")
    parser.add_argument("--size-threshold", type=float, default=4.0, help="Size tolerance in px")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = Thresholds(position_px=args.position_threshold, size_px=args.size_threshold)
    payload = verify_project(
        args.project_path.resolve(),
        thresholds=thresholds,
        write_report=args.write_report,
        report_path=args.report,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
