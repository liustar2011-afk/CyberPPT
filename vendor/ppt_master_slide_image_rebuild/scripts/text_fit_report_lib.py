#!/usr/bin/env python3
"""
PPT Master - Text Fit Report (canonical schema)

Single source of truth for exports/qa/text_fit_report.json. Resolves the
historical schema collision where the engine wrote per-fit_id ``items`` and
verify_text_fit.py wrote per-svg ``results`` to the SAME path, clobbering each
other. The unified v2 report keeps both under distinct keys and both producers
UPSERT (merge) rather than overwrite:

    {
      "version": "2.0",
      "generated_at": "...Z",
      "project": "/abs/path",
      "valid": true,
      "items": [ ...fit_id level, written by the engine... ],
      "svg_checks": [ ...per-svg, written by verify_text_fit.py... ],
      "cross_check": { "errors": [], "warnings": [], "checked": true }
    }

``valid`` is always recomputed from items + svg_checks + cross_check, so either
producer running last leaves a consistent file.

Usage:
    from text_fit_report_lib import upsert_items, upsert_svg_checks, load_report

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_VERSION = "2.0"
REPORT_RELPATH = Path("exports") / "qa" / "text_fit_report.json"


def report_path_for(project: Path) -> Path:
    return project / REPORT_RELPATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_report(path: Path) -> dict[str, Any]:
    """Load an existing report, or return a fresh skeleton on miss/parse error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": REPORT_VERSION, "items": [], "svg_checks": [], "cross_check": {}}


def _item_ok(item: dict[str, Any]) -> bool:
    return not item.get("errors")


def recompute_valid(report: dict[str, Any]) -> bool:
    """valid = no item errors AND no svg_check errors AND no cross_check errors."""
    items_ok = all(_item_ok(i) for i in report.get("items", []))
    svg_ok = all(c.get("valid", True) for c in report.get("svg_checks", []))
    cross_ok = not report.get("cross_check", {}).get("errors")
    return items_ok and svg_ok and cross_ok


def _write(path: Path, report: dict[str, Any]) -> Path:
    report["version"] = REPORT_VERSION
    report["generated_at"] = _utc_now()
    report["valid"] = recompute_valid(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def upsert_items(project: Path, items: list[dict[str, Any]]) -> Path:
    """Set the fit_id-level items (engine producer); preserve svg_checks."""
    path = report_path_for(project)
    report = load_report(path)
    report["project"] = str(project.resolve())
    report["items"] = items
    report["count"] = len(items)
    return _write(path, report)


def upsert_svg_checks(
    project: Path,
    svg_checks: list[dict[str, Any]],
    cross_check: dict[str, Any] | None = None,
) -> Path:
    """Set the per-svg checks (verify producer); preserve engine items."""
    path = report_path_for(project)
    report = load_report(path)
    report["project"] = str(project.resolve())
    report["svg_checks"] = svg_checks
    if cross_check is not None:
        report["cross_check"] = cross_check
    return _write(path, report)
