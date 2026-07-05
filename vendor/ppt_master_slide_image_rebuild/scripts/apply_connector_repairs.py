#!/usr/bin/env python3
"""
PPT Master - Connector Repair Suggestions

Reads connector_geometry_report.json (items) and proposes repairs for every
connector whose status is not clean. v1 emits suggestions to
exports/qa/connector_repair_suggestions.json; --write-overrides merges
actionable repairs into the project's connector_overrides.json. Mirrors
apply_text_fit_repairs.py.

Usage:
    python3 scripts/apply_connector_repairs.py projects/<name>
    python3 scripts/apply_connector_repairs.py projects/<name> --write-overrides

Dependencies:
    None (only uses standard library + sibling connector_report_lib)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from connector_report_lib import load_report, report_path_for  # noqa: E402

SUGGESTIONS_RELPATH = Path("exports") / "qa" / "connector_repair_suggestions.json"
OVERRIDES_RELPATH = Path("connector_overrides.json")


def suggest_for_item(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Return repair actions for one report item (empty if status is clean)."""
    status = str(item.get("status", ""))
    cid = str(item.get("connector_id", ""))
    repairs: list[dict[str, Any]] = []

    if status == "crossed_avoid_zone":
        repairs.append({"connector_id": cid, "action": "switch_route", "value": "orthogonal",
                        "reason": "path crosses an avoid_zone; reroute around it"})
    elif status == "anchor_far_from_boundary":
        repairs.append({"connector_id": cid, "action": "change_source_side", "value": item.get("source_side"),
                        "reason": "anchor sits too far from the object boundary"})
        repairs.append({"connector_id": cid, "action": "increase_target_padding", "value": 14,
                        "reason": "pull the endpoint back from the target"})
    elif status in ("source_missing", "target_missing", "unsupported_shape"):
        repairs.append({"connector_id": cid, "action": "prompt_manual_fix", "value": None,
                        "reason": f"status={status}: needs a model/spec fix, not a geometry tweak"})

    return repairs


def build_suggestions(report: dict[str, Any]) -> dict[str, Any]:
    items = report.get("items", [])
    repairs: list[dict[str, Any]] = []
    for item in items:
        repairs.extend(suggest_for_item(item))
    return {
        "version": "1.0",
        "source_items": len(items),
        "repaired_items": len({r["connector_id"] for r in repairs}),
        "repairs": repairs,
    }


def _overrides_from_repairs(repairs: list[dict[str, Any]]) -> dict[str, Any]:
    action_to_param = {
        "switch_route": "route",
        "change_source_side": "source_side",
        "increase_target_padding": "target_padding",
    }
    overrides: dict[str, Any] = {}
    for r in repairs:
        param = action_to_param.get(r["action"])
        if param is None or r.get("value") is None:
            continue
        overrides.setdefault(r["connector_id"], {})[param] = r["value"]
    return overrides


def write_overrides(project: Path, repairs: list[dict[str, Any]]) -> Path:
    path = project / OVERRIDES_RELPATH
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = {}
    bucket = existing.setdefault("overrides", {})
    for cid, params in _overrides_from_repairs(repairs).items():
        bucket.setdefault(cid, {}).update(params)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate connector repair suggestions from connector_geometry_report.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project", type=Path, help="Project directory")
    parser.add_argument("--report", type=Path, default=None, help="Override report path")
    parser.add_argument("--write-overrides", action="store_true",
                        help="Merge actionable repairs into <project>/connector_overrides.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project.resolve()
    report_path = args.report or report_path_for(project)
    if not report_path.is_file():
        print(json.dumps({"valid": False, "errors": [f"report not found: {report_path}"]}, ensure_ascii=False))
        return 1

    suggestions = build_suggestions(load_report(report_path))
    out = project / SUGGESTIONS_RELPATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(suggestions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suggestions["suggestions_path"] = str(out.relative_to(project))

    if args.write_overrides:
        ov = write_overrides(project, suggestions["repairs"])
        suggestions["overrides_path"] = str(ov.relative_to(project))

    print(json.dumps(suggestions, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
