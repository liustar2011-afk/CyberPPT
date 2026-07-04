#!/usr/bin/env python3
"""
PPT Master - Reference Object Similarity Gate

Compare reference image regions against preview PNG at object-level bboxes from
layout_reference.json, icon_manifest.json, and text_region_map.json.

Usage:
    python3 scripts/verify_reference_object_similarity.py <project_path>
    python3 scripts/verify_reference_object_similarity.py <project_path> --render --write-report

Examples:
    python3 scripts/verify_reference_object_similarity.py projects/demo --render --write-report

Dependencies:
    Pillow; cairosvg when --render refreshes preview PNGs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from reference_object_similarity_lib import Thresholds, verify_project  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Object-level reference vs preview similarity gate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--render", action="store_true", help="Render preview PNG when missing or stale")
    parser.add_argument(
        "--render-backend",
        choices=["cairo", "none"],
        default="cairo",
        help="Preview render backend (default: cairo)",
    )
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="Pass hard_gate to preview render backend",
    )
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/object_similarity_report.json")
    parser.add_argument("--report", type=Path, help="Custom report output path")
    parser.add_argument("--bbox-threshold", type=float, default=3.0, help="Reserved bbox position threshold metadata")
    parser.add_argument("--icon-threshold", type=float, default=4.0, help="Reserved icon threshold metadata")
    parser.add_argument(
        "--anchor-threshold",
        type=float,
        default=3.0,
        help="Max allowed anchor drift in pixels (default 3)",
    )
    parser.add_argument(
        "--zone-mean-threshold",
        type=float,
        default=None,
        help="Override all zone mean-diff thresholds with one value",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = Thresholds(
        bbox_position_px=args.bbox_threshold,
        icon_position_px=args.icon_threshold,
        icon_size_px=args.icon_threshold,
        anchor_drift_px=args.anchor_threshold,
        zone_mean_diff=args.zone_mean_threshold,
    )
    payload = verify_project(
        args.project_path.resolve(),
        render=args.render,
        render_backend=args.render_backend,
        hard_gate=args.hard_gate,
        thresholds=thresholds,
        write_report=args.write_report,
        report_path=args.report,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
