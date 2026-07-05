#!/usr/bin/env python3
"""
PPT Master - Alignment Underlay Utility

Inject, strip, or check temporary reference-image underlays in
slide-image-rebuild SVG editing output.

Usage:
    python3 scripts/alignment_underlay.py <project> inject|strip|check [--opacity N]

Examples:
    python3 scripts/alignment_underlay.py projects/demo inject --opacity 0.28
    python3 scripts/alignment_underlay.py projects/demo strip
    python3 scripts/alignment_underlay.py projects/demo check

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
UNDERLAY_MARKER = "data-alignment-underlay"
UNDERLAY_MARKER_VALUE = "temporary"
EXPORT_POLICY_MARKER = "data-export-policy"
EXPORT_POLICY_VALUE = "strip-before-export"
UNDERLAY_IMAGE_MARKER = "data-alignment-underlay-image"
UNDERLAY_IMAGE_VALUE = "reference"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

ET.register_namespace("", SVG_NS)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _svg_tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _parse_length(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _canvas_rect(root: ET.Element) -> tuple[str, str, str, str]:
    view_box = root.get("viewBox")
    if view_box:
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", view_box)]
        if len(numbers) >= 4:
            x, y, width, height = numbers[:4]
            return (
                _format_number(x),
                _format_number(y),
                _format_number(width),
                _format_number(height),
            )

    width = _parse_length(root.get("width")) or 0.0
    height = _parse_length(root.get("height")) or 0.0
    return "0", "0", _format_number(width), _format_number(height)


def _discover_svg_dirs(project: Path) -> tuple[list[Path], list[str]]:
    warnings: list[str] = []
    dirs: list[Path] = []
    root_output = project / "svg_output"
    if root_output.is_dir():
        dirs.append(root_output)

    pages_dir = project / "pages"
    if pages_dir.is_dir():
        for svg_dir in sorted(pages_dir.glob("*/svg_output")):
            if svg_dir.is_dir():
                dirs.append(svg_dir)

    if not dirs:
        warnings.append("No svg_output directory found.")

    deduped: dict[str, Path] = {}
    for svg_dir in dirs:
        deduped[str(svg_dir.resolve())] = svg_dir
    return list(deduped.values()), warnings


def _find_svgs(project: Path) -> tuple[list[Path], list[str]]:
    dirs, warnings = _discover_svg_dirs(project)
    svgs: list[Path] = []
    for svg_dir in dirs:
        svgs.extend(sorted(svg_dir.glob("*.svg")))
    return svgs, warnings


def _manifest_references(project: Path) -> dict[str, Path]:
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return {}

    references: dict[str, Path] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id")
        reference = page.get("reference_image")
        if not isinstance(page_id, str) or not page_id.strip():
            continue
        if not isinstance(reference, str) or not reference.strip():
            continue
        path = Path(reference)
        if not path.is_absolute():
            path = project / path
        references[page_id.strip()] = path
    return references


def _single_reference_layout(project: Path) -> Path | None:
    matches = [
        path
        for path in sorted((project / "images").glob("reference_layout.*"))
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file()
    ]
    return matches[0] if len(matches) == 1 else None


def _resolve_reference(project: Path, stem: str, manifest_refs: dict[str, Path]) -> Path | None:
    manifest_ref = manifest_refs.get(stem)
    if manifest_ref is not None and manifest_ref.is_file():
        return manifest_ref

    reference_pages = project / "images" / "reference_pages"
    for suffix in IMAGE_EXTENSIONS:
        candidate = reference_pages / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate

    return _single_reference_layout(project)


def _relative_href(svg_path: Path, reference: Path) -> str:
    return os.path.relpath(reference.resolve(), start=svg_path.parent.resolve()).replace(os.sep, "/")


def _underlay_groups(root: ET.Element) -> list[ET.Element]:
    return [
        elem
        for elem in root.iter()
        if _local_name(elem.tag) == "g" and elem.get(UNDERLAY_MARKER) == UNDERLAY_MARKER_VALUE
    ]


def _temporary_underlay_elements(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter() if elem.get(UNDERLAY_MARKER) == UNDERLAY_MARKER_VALUE]


def _strip_temporary_groups(root: ET.Element) -> int:
    removed = 0

    def visit(parent: ET.Element) -> None:
        nonlocal removed
        for child in list(parent):
            if _local_name(child.tag) == "g" and child.get(UNDERLAY_MARKER) == UNDERLAY_MARKER_VALUE:
                parent.remove(child)
                removed += 1
                continue
            visit(child)

    visit(root)
    return removed


def _make_underlay_group(root: ET.Element, svg_path: Path, reference: Path, opacity: float) -> ET.Element:
    x, y, width, height = _canvas_rect(root)
    group = ET.Element(
        _svg_tag("g") if root.tag.startswith("{") else "g",
        {
            "id": "alignment-underlay",
            UNDERLAY_MARKER: UNDERLAY_MARKER_VALUE,
            EXPORT_POLICY_MARKER: EXPORT_POLICY_VALUE,
            "opacity": f"{opacity:g}",
            "pointer-events": "none",
        },
    )
    ET.SubElement(
        group,
        _svg_tag("image") if root.tag.startswith("{") else "image",
        {
            UNDERLAY_IMAGE_MARKER: UNDERLAY_IMAGE_VALUE,
            "href": _relative_href(svg_path, reference),
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "preserveAspectRatio": "none",
        },
    )
    return group


def _write_svg(tree: ET.ElementTree, svg_path: Path) -> None:
    tree.write(svg_path, encoding="unicode", xml_declaration=False)
    text = svg_path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        svg_path.write_text(text + "\n", encoding="utf-8")


def inject_underlays(project: Path, opacity: float = 0.28) -> dict[str, Any]:
    project = project.resolve()
    svgs, warnings = _find_svgs(project)
    manifest_refs = _manifest_references(project)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    injected = 0
    skipped = 0

    for svg_path in svgs:
        reference = _resolve_reference(project, svg_path.stem, manifest_refs)
        if reference is None:
            warnings.append(f"{svg_path}: no reference image found for stem {svg_path.stem!r}.")
            skipped += 1
            results.append({"path": str(svg_path), "status": "skipped", "reason": "missing_reference"})
            continue
        try:
            tree = ET.parse(svg_path)
        except ET.ParseError as exc:
            errors.append(f"{svg_path}: invalid SVG XML: {exc}")
            continue
        root = tree.getroot()
        removed = _strip_temporary_groups(root)
        group = _make_underlay_group(root, svg_path, reference, opacity)
        root.insert(0, group)
        _write_svg(tree, svg_path)
        injected += 1
        results.append(
            {
                "path": str(svg_path),
                "status": "injected",
                "removed_existing": removed,
                "reference_image": str(reference),
                "href": _relative_href(svg_path, reference),
            }
        )

    return {
        "valid": not errors,
        "action": "inject",
        "count": len(svgs),
        "injected": injected,
        "skipped": skipped,
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }


def strip_underlays(project: Path) -> dict[str, Any]:
    project = project.resolve()
    svgs, warnings = _find_svgs(project)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    removed_total = 0

    for svg_path in svgs:
        try:
            tree = ET.parse(svg_path)
        except ET.ParseError as exc:
            errors.append(f"{svg_path}: invalid SVG XML: {exc}")
            continue
        root = tree.getroot()
        removed = _strip_temporary_groups(root)
        if removed:
            _write_svg(tree, svg_path)
        removed_total += removed
        results.append({"path": str(svg_path), "removed": removed})

    return {
        "valid": not errors,
        "action": "strip",
        "count": len(svgs),
        "removed": removed_total,
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }


def check_no_underlays(project: Path) -> dict[str, Any]:
    project = project.resolve()
    svgs, warnings = _find_svgs(project)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    remaining_total = 0

    if not svgs:
        errors.append("No SVG files found to check.")

    for svg_path in svgs:
        try:
            root = ET.parse(svg_path).getroot()
        except ET.ParseError as exc:
            errors.append(f"{svg_path}: invalid SVG XML: {exc}")
            continue
        remaining = len(_temporary_underlay_elements(root))
        remaining_total += remaining
        results.append({"path": str(svg_path), "remaining": remaining})
        if remaining:
            errors.append(f"{svg_path}: temporary alignment underlay remains.")

    return {
        "valid": not errors,
        "action": "check",
        "count": len(svgs),
        "remaining": remaining_total,
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inject, strip, or check temporary SVG alignment underlays.")
    parser.add_argument("project", type=Path, help="slide-image-rebuild project directory")
    parser.add_argument("action", choices=("inject", "strip", "check"), help="Operation to run")
    parser.add_argument("--opacity", type=float, default=0.28, help="Injected underlay opacity, default: 0.28")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "inject":
        payload = inject_underlays(args.project, opacity=args.opacity)
    elif args.action == "strip":
        payload = strip_underlays(args.project)
    else:
        payload = check_no_underlays(args.project)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
