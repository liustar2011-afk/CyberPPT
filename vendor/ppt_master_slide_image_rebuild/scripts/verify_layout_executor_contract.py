#!/usr/bin/env python3
"""
PPT Master - Layout Executor Contract Verifier (复刻流程2)

Verify that generated SVG implements layout_reference.json and svg_build_plan.json
obligations: zone markers, icon ids, chain connectors, and structure primitives.

Usage:
    python3 scripts/verify_layout_executor_contract.py <project_path>
    python3 scripts/verify_layout_executor_contract.py <layout.json> --svg page.svg

Dependencies:
    layout_reference_rebuild2_lib.py (stdlib + same directory)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from layout_reference_rebuild2_lib import is_rebuild2, verify_executor_contract


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _svg_candidates(project: Path) -> list[Path]:
    final_files = sorted((project / "svg_final").glob("*.svg"))
    if final_files:
        return final_files
    return sorted((project / "svg_output").glob("*.svg"))


def verify_project(project: Path) -> dict[str, Any]:
    layout_path = project / "layout_reference.json"
    if not layout_path.exists():
        return {"valid": False, "errors": ["layout_reference.json missing"], "warnings": []}
    layout = load_json(layout_path)
    if not is_rebuild2(layout):
        return {
            "valid": False,
            "errors": ["Project is not 复刻流程2 — set workflow=layout-reference-rebuild-2 or version=2.0."],
            "warnings": [],
        }
    plan_path = project / "svg_build_plan.json"
    plan = load_json(plan_path) if plan_path.exists() else None
    svgs = _svg_candidates(project)
    if not svgs:
        return {"valid": False, "errors": ["No SVG in svg_final/ or svg_output/"], "warnings": []}

    errors: list[str] = []
    warnings: list[str] = []
    for svg in svgs:
        errs, warns = verify_executor_contract(layout, svg, plan=plan)
        for item in errs:
            errors.append(f"{svg.name}: {item}")
        for item in warns:
            warnings.append(f"{svg.name}: {item}")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Executor SVG against 复刻流程2 contract.")
    parser.add_argument("target", type=Path, help="Project directory or layout_reference.json")
    parser.add_argument("--svg", type=Path, help="SVG path when target is layout JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = args.target
    if target.is_dir():
        payload = verify_project(target)
    else:
        layout = load_json(target)
        if not args.svg:
            print(json.dumps({"valid": False, "errors": ["--svg required when target is a JSON file"]}, ensure_ascii=False))
            return 1
        errors, warnings = verify_executor_contract(layout, args.svg)
        payload = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
