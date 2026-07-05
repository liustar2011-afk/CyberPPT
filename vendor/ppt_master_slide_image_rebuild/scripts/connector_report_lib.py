#!/usr/bin/env python3
"""
PPT Master - Connector Geometry Report (canonical schema)

Single source of truth for exports/qa/connector_geometry_report.json. Mirrors
text_fit_report_lib: the engine UPSERTs per-connector ``items`` and
verify_connector_geometry.py UPSERTs per-svg ``svg_checks`` into the SAME file
without clobbering; ``valid`` is recomputed from both each write.

Usage:
    from connector_report_lib import upsert_items, upsert_svg_checks, load_report

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_VERSION = "1.0"
REPORT_RELPATH = Path("exports") / "qa" / "connector_geometry_report.json"


def report_path_for(project: Path) -> Path:
    return project / REPORT_RELPATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": REPORT_VERSION, "items": [], "svg_checks": [], "cross_check": {}}


def recompute_valid(report: dict[str, Any]) -> bool:
    items_ok = all(not i.get("errors") for i in report.get("items", []))
    svg_ok = all(c.get("valid", True) for c in report.get("svg_checks", []))
    cross_ok = not report.get("cross_check", {}).get("errors")
    return items_ok and svg_ok and cross_ok


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    errors = sum(1 for i in items if i.get("errors") or i.get("status") in {"source_missing", "target_missing", "anchor_far_from_boundary", "invalid"})
    warnings = sum(1 for i in items if not i.get("errors") and i.get("status") not in {"ok", None})
    return {"total": total, "valid_count": total - errors, "warning_count": warnings, "error_count": errors}


def _write(path: Path, report: dict[str, Any]) -> Path:
    report["version"] = REPORT_VERSION
    report["generated_at"] = _utc_now()
    report["summary"] = _summary(report.get("items", []))
    report["valid"] = recompute_valid(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def upsert_items(project: Path, items: list[dict[str, Any]]) -> Path:
    """Set the per-connector items (engine producer); preserve svg_checks."""
    path = report_path_for(project)
    report = load_report(path)
    report["project"] = str(project.resolve())
    report["items"] = items
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
