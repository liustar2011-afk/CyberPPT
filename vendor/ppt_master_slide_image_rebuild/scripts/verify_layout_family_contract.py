#!/usr/bin/env python3
"""
PPT Master - Layout Family Contract Verifier

Validate layout_reference.json against canonical page-family templates.

Usage:
    python3 scripts/verify_layout_family_contract.py <project_path>
    python3 scripts/verify_layout_family_contract.py <project_path> --strict --write-report

Examples:
    python3 scripts/verify_layout_family_contract.py projects/demo --write-report

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

from layout_family_lib import build_detected_layout_family, verify_layout_against_family  # noqa: E402


def _layout_files(project: Path) -> list[Path]:
    manifest_path = project / "slide_image_rebuild_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        pages = manifest.get("pages", [])
        paths: list[Path] = []
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                page_id = str(page.get("page_id", "")).strip()
                candidate = project / "pages" / page_id / "layout_reference.json"
                if candidate.is_file():
                    paths.append(candidate)
        if paths:
            return paths
    root = project / "layout_reference.json"
    return [root] if root.is_file() else []


def verify_project(project: Path, *, strict: bool = False, write_report: bool = False) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    for layout_path in _layout_files(project):
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        if not isinstance(layout.get("detected_layout_family"), dict):
            layout = dict(layout)
            layout["detected_layout_family"] = build_detected_layout_family(layout)
        page_result = verify_layout_against_family(layout, strict=strict)
        page_result["layout_reference"] = str(layout_path)
        pages.append(page_result)
        errors.extend(page_result.get("errors", []))
        warnings.extend(page_result.get("warnings", []))

    payload = {
        "workflow": "slide-image-rebuild",
        "check": "layout_family_contract",
        "project": str(project.resolve()),
        "valid": not errors,
        "strict": strict,
        "pages": pages,
        "errors": errors,
        "warnings": warnings,
    }
    if write_report:
        out = project / "exports" / "qa" / "layout_family_contract_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(out.relative_to(project))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify layout_reference against page-family templates.")
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--strict", action="store_true", help="Treat custom families as advisory only (still fail concrete mismatches)")
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/layout_family_contract_report.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Project not found: {project}"]}, ensure_ascii=False, indent=2))
        return 1
    payload = verify_project(project, strict=args.strict, write_report=args.write_report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
