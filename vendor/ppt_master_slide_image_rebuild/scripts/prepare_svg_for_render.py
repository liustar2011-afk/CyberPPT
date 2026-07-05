#!/usr/bin/env python3
"""
PPT Master - Prepare SVG for Preview Render

Build a render-ready SVG snapshot (inline data-icon, resolved hrefs) for Cairo preview rendering.

Usage:
    python3 scripts/prepare_svg_for_render.py <project_path> --svg svg_output/01.svg

Dependencies:
    None beyond svg_render_prepare_lib / embed_icons
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from svg_render_prepare_lib import prepare_svg_content, sha256_file, sha256_text
except ImportError:  # pragma: no cover
    raise

PREPARE_VERSION = "0.1.0"


@dataclass(frozen=True)
class PrepareResult:
    ok: bool
    svg_path: Path
    render_ready_path: Path
    svg_sha256: str
    render_input_hash: str
    icon_manifest_hash: str | None
    warnings: tuple[dict[str, str], ...]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "svg_path": str(self.svg_path),
            "render_ready_path": str(self.render_ready_path),
            "svg_sha256": self.svg_sha256,
            "render_input_hash": self.render_input_hash,
            "icon_manifest_hash": self.icon_manifest_hash,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "prepare_version": PREPARE_VERSION,
        }


def default_render_ready_path(project: Path, svg_path: Path) -> Path:
    return project / "exports" / "preview_qa" / f"{svg_path.stem}.render-ready.svg"


def icon_manifest_hash(project: Path) -> str | None:
    manifest = project / "icon_manifest.json"
    if manifest.is_file():
        return sha256_file(manifest)
    return None


def prepare_svg_for_render(
    project: Path,
    svg_path: Path,
    *,
    out_path: Path | None = None,
    write: bool = True,
) -> PrepareResult:
    errors: list[str] = []
    if not svg_path.is_file():
        return PrepareResult(
            ok=False,
            svg_path=svg_path,
            render_ready_path=out_path or default_render_ready_path(project, svg_path),
            svg_sha256="",
            render_input_hash="",
            icon_manifest_hash=None,
            warnings=(),
            errors=(f"SVG not found: {svg_path}",),
        )
    try:
        content, warnings = prepare_svg_content(svg_path)
    except OSError as exc:
        return PrepareResult(
            ok=False,
            svg_path=svg_path,
            render_ready_path=out_path or default_render_ready_path(project, svg_path),
            svg_sha256="",
            render_input_hash="",
            icon_manifest_hash=None,
            warnings=(),
            errors=(f"Failed to prepare SVG: {exc}",),
        )
    render_ready = out_path or default_render_ready_path(project, svg_path)
    if write:
        render_ready.parent.mkdir(parents=True, exist_ok=True)
        render_ready.write_text(content, encoding="utf-8")
    return PrepareResult(
        ok=True,
        svg_path=svg_path,
        render_ready_path=render_ready,
        svg_sha256=sha256_file(svg_path),
        render_input_hash=sha256_text(content),
        icon_manifest_hash=icon_manifest_hash(project),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare render-ready SVG for preview backends.")
    parser.add_argument("project_path", type=Path)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="Output render-ready SVG path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    svg = args.svg if args.svg.is_absolute() else project / args.svg
    out = args.out
    if out is not None and not out.is_absolute():
        out = project / out
    result = prepare_svg_for_render(project, svg, out_path=out)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
