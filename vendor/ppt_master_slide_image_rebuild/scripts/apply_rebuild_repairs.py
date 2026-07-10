#!/usr/bin/env python3
"""
PPT Master - Apply Rebuild Repairs

Apply auto-fix patches from exports/qa/repair_tasks.json to svg_output/.

Usage:
    python3 scripts/apply_rebuild_repairs.py <project_path> --write
    python3 scripts/apply_rebuild_repairs.py <project_path> --dry-run

Examples:
    python3 scripts/apply_rebuild_repairs.py projects/demo --write
    python3 scripts/apply_rebuild_repairs.py projects/demo --dry-run --task-id repair-001

Dependencies:
    Repository helpers: repair_tasks_lib, apply_rebuild_repairs_lib
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from apply_rebuild_repairs_lib import apply_from_project  # noqa: E402
from repair_tasks_lib import aggregate_repair_tasks, write_repair_tasks  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply repair_tasks.json patches to svg_output/ (UTF-8 safe).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--write", action="store_true", help="Write patched SVG and updated repair_tasks.json")
    parser.add_argument("--dry-run", action="store_true", help="Report patches without modifying files")
    parser.add_argument("--task-id", action="append", default=[], help="Limit to specific repair task id(s)")
    parser.add_argument("--max-tasks", type=int, default=None, help="Maximum auto-apply tasks per run")
    parser.add_argument(
        "--refresh-tasks",
        action="store_true",
        help="Re-aggregate repair_tasks.json from QA reports before applying",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.write and not args.dry_run:
        print(json.dumps({
            "valid": False,
            "errors": ["Specify --write or --dry-run"],
        }, ensure_ascii=False, indent=2))
        return 2
    project = args.project_path.resolve()
    if args.refresh_tasks:
        payload = aggregate_repair_tasks(project)
        write_repair_tasks(project, payload)
    task_ids = {str(item) for item in args.task_id if str(item).strip()} or None
    report = apply_from_project(
        project,
        dry_run=args.dry_run,
        write_tasks=args.write,
        task_ids=task_ids,
        max_tasks=args.max_tasks,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("valid", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
