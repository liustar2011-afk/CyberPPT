#!/usr/bin/env python3
"""
PPT Master - Repair Tasks Aggregator

Aggregate QA failures into exports/qa/repair_tasks.json and block export when
open blocking repair tasks remain.

Usage:
    python3 scripts/aggregate_repair_tasks.py <project_path> --write-report
    python3 scripts/aggregate_repair_tasks.py <project_path> --write-report --enforce

Examples:
    python3 scripts/aggregate_repair_tasks.py projects/demo --write-report --enforce

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

from repair_tasks_lib import aggregate_repair_tasks, write_repair_tasks  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate slide-image-rebuild QA failures into repair_tasks.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/repair_tasks.json")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Exit non-zero when blocking open repair tasks remain",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    payload = aggregate_repair_tasks(project)
    if args.write_report:
        out = write_repair_tasks(project, payload)
        payload["report_path"] = str(out.relative_to(project))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.enforce and not payload.get("valid", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
