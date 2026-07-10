#!/usr/bin/env python3
"""
PPT Master - SVG Rebuild Completeness Verifier

Ensure rebuilt SVG pages carry layout zones, icons, text regions, and connectors.

Usage:
    python3 scripts/verify_svg_rebuild_completeness.py <project_path>
    python3 scripts/verify_svg_rebuild_completeness.py <project_path> --strict --write-report

Examples:
    python3 scripts/verify_svg_rebuild_completeness.py projects/demo --strict --write-report

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from svg_rebuild_completeness_lib import verify_project  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SVG rebuild completeness for slide-image rebuild.")
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--strict", action="store_true", help="Also require chain connectors and minimum element count")
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/svg_completeness_report.json")
    parser.add_argument("--report", type=Path, help="Custom report output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Project not found: {project}"]}, ensure_ascii=False, indent=2))
        return 1
    payload = verify_project(
        project,
        strict=args.strict,
        write_report=args.write_report,
        report_path=args.report,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
