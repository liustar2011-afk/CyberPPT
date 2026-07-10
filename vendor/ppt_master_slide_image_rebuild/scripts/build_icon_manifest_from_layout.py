#!/usr/bin/env python3
"""
PPT Master - Build Icon Manifest From Layout

Generate icon_manifest.json from layout_reference.json icon_reconstruction entries
and icon-slot zones.

Usage:
    python3 scripts/build_icon_manifest_from_layout.py <project_path> --write
    python3 scripts/build_icon_manifest_from_layout.py <project_path> --dry-run

Examples:
    python3 scripts/build_icon_manifest_from_layout.py projects/demo --write

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

from build_icon_manifest_lib import build_manifest, write_manifest  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build icon_manifest.json from layout_reference icon slots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--write", action="store_true", help="Write icon_manifest.json")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing icon_manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="Print manifest JSON without writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Project not found: {project}"]}, ensure_ascii=False, indent=2))
        return 1
    payload = build_manifest(project)
    payload["valid"] = bool(payload.get("summary", {}).get("icon_count", 0))
    payload["project"] = str(project)
    if args.write:
        try:
            out = write_manifest(project, payload, force=args.force)
            payload["written"] = True
            payload["manifest_path"] = str(out.relative_to(project))
        except FileExistsError as exc:
            payload["valid"] = False
            payload["written"] = False
            payload["errors"] = [str(exc)]
    elif args.dry_run:
        payload["written"] = False
    else:
        payload["written"] = False
        payload["hint"] = "Pass --write to create icon_manifest.json or --dry-run to preview only."
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("errors"):
        return 1
    return 0 if payload.get("valid") or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
