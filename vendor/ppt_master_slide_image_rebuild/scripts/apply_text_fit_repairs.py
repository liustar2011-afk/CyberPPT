#!/usr/bin/env python3
"""
PPT Master - Text Fit Repair Suggestions

Reads the canonical text_fit_report.json (items, fit_id level) and proposes
parameter repairs for every text box whose fit status is not clean. v1 only
emits suggestions to exports/qa/text_fit_repair_suggestions.json; with
--write-overrides it also merges actionable repairs into the project's
text_fit_overrides.json (修订版 §十二, second-phase write-back).

Usage:
    python3 scripts/apply_text_fit_repairs.py projects/<name>
    python3 scripts/apply_text_fit_repairs.py projects/<name> --write-overrides

Dependencies:
    None (only uses standard library + sibling text_fit_report_lib)
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

from text_fit_report_lib import load_report, report_path_for  # noqa: E402

SUGGESTIONS_RELPATH = Path("exports") / "qa" / "text_fit_repair_suggestions.json"
OVERRIDES_RELPATH = Path("text_fit_overrides.json")

# Statuses that warrant a repair, and whether they are mechanically actionable.
_ACTIONABLE = {"overflow", "truncated", "fit_at_min_font", "compressed_line_height"}
_MANUAL_ONLY = {"protected_term_split", "punctuation_violation"}


def suggest_for_item(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Return repair actions for one report item (empty if status is clean).

    Note: actionable statuses (overflow/truncated/fit_at_min_font/compressed)
    all occur AT minimum font, so lowering the font cap never helps — the real
    levers are more lines, tighter line height, or shorter text.
    """
    status = str(item.get("status", ""))
    fit_id = str(item.get("fit_id", ""))
    line_count = int(item.get("line_count", 0) or 0)
    repairs: list[dict[str, Any]] = []

    if status in _ACTIONABLE:
        repairs.append({
            "fit_id": fit_id,
            "action": "increase_max_lines",
            "value": line_count + 1,
            "reason": f"status={status}: allow one more line than the current {line_count}",
        })
        repairs.append({
            "fit_id": fit_id,
            "action": "reduce_line_height_ratio",
            "value": 1.25,
            "reason": f"status={status}: tighten line height to recover vertical space",
        })
        repairs.append({
            "fit_id": fit_id,
            "action": "prompt_manual_shorten",
            "value": None,
            "reason": f"status={status}: shorten text or widen box if it still overflows",
        })

    if status in _MANUAL_ONLY:
        repairs.append({
            "fit_id": fit_id,
            "action": "prompt_manual_shorten",
            "value": None,
            "reason": f"status={status}: needs human edit (shorten text or widen box)",
        })

    return repairs


def build_suggestions(report: dict[str, Any]) -> dict[str, Any]:
    items = report.get("items", [])
    repairs: list[dict[str, Any]] = []
    for item in items:
        repairs.extend(suggest_for_item(item))
    return {
        "version": "1.0",
        "source_items": len(items),
        "repaired_items": len({r["fit_id"] for r in repairs}),
        "repairs": repairs,
    }


def _overrides_from_repairs(repairs: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold actionable repairs into a {fit_id: {param: value}} override map."""
    action_to_param = {
        "increase_max_lines": "max_lines",
        "reduce_line_height_ratio": "line_height_ratio",
    }
    overrides: dict[str, Any] = {}
    for r in repairs:
        param = action_to_param.get(r["action"])
        if param is None or r.get("value") is None:
            continue
        overrides.setdefault(r["fit_id"], {})[param] = r["value"]
    return overrides


def write_overrides(project: Path, repairs: list[dict[str, Any]]) -> Path:
    """Merge repairs into the project's text_fit_overrides.json (preserve existing)."""
    path = project / OVERRIDES_RELPATH
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = {}
    bucket = existing.setdefault("overrides", {})
    for fit_id, params in _overrides_from_repairs(repairs).items():
        bucket.setdefault(fit_id, {}).update(params)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate text-fit repair suggestions from text_fit_report.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project", type=Path, help="Project directory")
    parser.add_argument("--report", type=Path, default=None, help="Override report path")
    parser.add_argument(
        "--write-overrides",
        action="store_true",
        help="Also merge actionable repairs into <project>/text_fit_overrides.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project.resolve()
    report_path = args.report or report_path_for(project)
    if not report_path.is_file():
        print(json.dumps({"valid": False, "errors": [f"report not found: {report_path}"]}, ensure_ascii=False))
        return 1

    report = load_report(report_path)
    suggestions = build_suggestions(report)

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
