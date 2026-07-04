#!/usr/bin/env python3
"""
PPT Master - Connector Geometry Verifier

Checks connector SVG elements (data-chain-connector) for required markers and,
when an engine report exists, cross-checks that every rendered connector is
reported and gates by its geometry status. Mirrors verify_text_fit.py.

Usage:
    python3 scripts/verify_connector_geometry.py <project_or_svg>
    python3 scripts/verify_connector_geometry.py <project> --write-report

Dependencies:
    None (only uses standard library + sibling connector_report_lib)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from connector_report_lib import report_path_for, upsert_svg_checks  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"

# Connector status severity, mirrors connector_geometry.DEFAULT_GATE_SEVERITY.
STATUS_SEVERITY: dict[str, str] = {
    "ok": "ok",
    "source_missing": "error",
    "target_missing": "error",
    "unsupported_shape": "warning",
    "anchor_far_from_boundary": "error",
    "crossed_avoid_zone": "warning",
    "invalid": "error",
}

REQUIRED_MARKERS = ("data-connector-id", "data-source-id", "data-target-id", "data-route-type")


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    for sub in ("svg_final", "svg_output"):
        if (target / sub).is_dir():
            return sorted((target / sub).glob("*.svg"))
    return sorted(target.glob("*.svg"))


def inspect(svg_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    root = ET.parse(svg_path).getroot()
    connector_ids: list[str] = []
    checked = 0
    for elem in root.iter():
        cid = elem.get("data-chain-connector")
        if cid is None:
            continue
        checked += 1
        connector_ids.append(cid)
        missing = [m for m in REQUIRED_MARKERS if elem.get(m) is None]
        if missing:
            warnings.append(f"{cid}: missing marker(s) {', '.join(missing)}")
    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "connectors": checked,
        "connector_ids": connector_ids,
    }


def cross_check_report(report_path: Path, svg_ids: set[str]) -> dict[str, Any]:
    """Cross-check engine report items against connector ids found in SVGs."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"errors": [], "warnings": [f"report unreadable: {report_path}"], "checked": False}
    items = payload.get("items")
    if not isinstance(items, list):
        return {"errors": [], "warnings": [], "checked": False}

    reported = {str(i.get("connector_id")) for i in items if i.get("connector_id")}
    for cid in sorted(svg_ids - reported):
        errors.append(f"{cid}: present in SVG but missing from connector_geometry_report.json")
    for item in items:
        cid = str(item.get("connector_id", ""))
        status = str(item.get("status", ""))
        severity = STATUS_SEVERITY.get(status, "warning")
        if severity == "error":
            errors.append(f"{cid}: report status '{status}'")
        elif severity == "warning" and status and status != "ok":
            warnings.append(f"{cid}: report status '{status}'")
    return {"errors": errors, "warnings": warnings, "checked": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify connector SVG geometry + markers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    parser.add_argument("--report", type=Path, default=None, help="Engine report to cross-check")
    parser.add_argument("--write-report", action="store_true", help="Merge svg_checks into the canonical report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        print(json.dumps({"valid": False, "errors": ["No SVG files found"]}, ensure_ascii=False, indent=2))
        return 1

    results = [inspect(svg) for svg in svgs]
    payload: dict[str, Any] = {"valid": all(r["valid"] for r in results), "count": len(results), "results": results}

    project = args.target if args.target.is_dir() else args.target.parent
    report_path = args.report or report_path_for(project)
    cross: dict[str, Any] | None = None
    if report_path.is_file():
        svg_ids = {cid for r in results for cid in r.get("connector_ids", [])}
        cross = cross_check_report(report_path, svg_ids)
        if cross["checked"]:
            payload["cross_check"] = cross
            if cross["errors"]:
                payload["valid"] = False

    if args.write_report and args.target.is_dir():
        written = upsert_svg_checks(args.target.resolve(), results, cross if cross and cross.get("checked") else None)
        payload["report_path"] = str(written.relative_to(args.target.resolve()))

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
