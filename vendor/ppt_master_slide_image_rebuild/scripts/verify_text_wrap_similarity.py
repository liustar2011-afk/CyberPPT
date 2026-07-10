#!/usr/bin/env python3
"""
PPT Master - Text Wrap Similarity Gate

Compare declared text_region_map regions against SVG text blocks for line count,
bbox drift, baseline drift, and edge margins.

Usage:
    python3 scripts/verify_text_wrap_similarity.py <project_path> --write-report

Examples:
    python3 scripts/verify_text_wrap_similarity.py projects/demo --write-report

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

from text_wrap_similarity_lib import Thresholds, verify_project  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify SVG text wrap similarity against text_region_map.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/text_wrap_similarity_report.json")
    parser.add_argument("--report", type=Path, help="Custom report output path")
    parser.add_argument("--bbox-threshold", type=float, default=3.0, help="Max bbox position drift in px")
    parser.add_argument("--baseline-threshold", type=float, default=2.0, help="Max first-line baseline drift in px")
    parser.add_argument("--edge-margin", type=float, default=4.0, help="Minimum inset from region bbox edges in px")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = Thresholds(
        bbox_position_px=args.bbox_threshold,
        baseline_px=args.baseline_threshold,
        edge_margin_px=args.edge_margin,
    )
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
