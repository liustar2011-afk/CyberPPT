#!/usr/bin/env python3
"""
PPT Master - SVG Preview Verifier

Render SVG pages to PNG and run lightweight visual QA checks: nonblank preview,
viewBox bounds, basic element overflow, suspicious edge text, and CJK font
availability. This is a heuristic preview gate, not a replacement for visual review.

Usage:
    python3 scripts/verify_svg_preview.py <project_path_or_svg> [--render]

Examples:
    python3 scripts/verify_svg_preview.py projects/demo --render
    python3 scripts/verify_svg_preview.py projects/demo/svg_output/01_cover.svg

Dependencies:
    cairosvg, Pillow
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    from PIL import Image, ImageStat
except ImportError as exc:  # pragma: no cover - environment setup
    raise SystemExit("Pillow is required.") from exc

try:
    from render_preview_backend import ensure_preview_for_svg
except ImportError:  # pragma: no cover
    from scripts.render_preview_backend import ensure_preview_for_svg  # type: ignore


SVG_NS = "{http://www.w3.org/2000/svg}"
CJK_RE = re.compile(r"[\u3400-\u9fff]")
TOFU_RE = re.compile(r"[□�]")


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    if not match:
        return None
    return float(match.group(1))


def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox") or root.get("viewbox")
    if raw:
        parts = [float(part) for part in re.split(r"[\s,]+", raw.strip()) if part]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    width = _float(root.get("width")) or 1280
    height = _float(root.get("height")) or 720
    return 0, 0, width, height


def _text_content(elem: ET.Element) -> str:
    return "".join(elem.itertext())


def _font_families(root: ET.Element) -> list[str]:
    families: list[str] = []
    for elem in root.iter():
        font = elem.get("font-family")
        if font:
            families.append(font)
    return families


def _font_available(name: str) -> bool:
    clean = name.strip().strip("\"'")
    if not clean or clean.lower() in {"serif", "sans-serif", "monospace"}:
        return False
    try:
        result = subprocess.run(
            ["fc-match", clean],
            check=False,
            text=True,
            capture_output=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    return result.returncode == 0 and bool(result.stdout.strip()) and "LastResort" not in result.stdout


def _has_cjk_font(families: list[str]) -> bool:
    preferred = [
        "PingFang SC",
        "Microsoft YaHei",
        "Hiragino Sans GB",
        "Heiti SC",
        "STHeiti",
        "Source Han Sans",
        "Noto Sans CJK",
        "Arial Unicode MS",
        "SimHei",
        "SimSun",
    ]
    family_blob = "\n".join(families)
    if any(name in family_blob for name in preferred):
        return any(_font_available(name) for name in preferred if name in family_blob)
    return False


def _element_bounds(elem: ET.Element) -> tuple[float, float, float, float] | None:
    tag = _strip_ns(elem.tag)
    if tag in {"rect", "image", "svg"}:
        x = _float(elem.get("x")) or 0
        y = _float(elem.get("y")) or 0
        w = _float(elem.get("width"))
        h = _float(elem.get("height"))
        if w is not None and h is not None:
            return x, y, x + w, y + h
    if tag == "circle":
        cx = _float(elem.get("cx"))
        cy = _float(elem.get("cy"))
        r = _float(elem.get("r"))
        if cx is not None and cy is not None and r is not None:
            return cx - r, cy - r, cx + r, cy + r
    if tag == "line":
        values = [_float(elem.get(key)) for key in ["x1", "y1", "x2", "y2"]]
        if all(value is not None for value in values):
            x1, y1, x2, y2 = values  # type: ignore[misc]
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    if tag == "text":
        x = _float(elem.get("x"))
        y = _float(elem.get("y"))
        if x is not None and y is not None:
            size = _float(elem.get("font-size")) or 16
            content = _text_content(elem)
            approx_w = len(content) * size * 0.58
            return x, y - size, x + approx_w, y + size * 0.3
    return None



def _image_nonblank(path: Path) -> bool:
    image = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(image)
    return max(stat.stddev) > 1.0


def inspect_svg(
    svg_path: Path,
    *,
    render: bool = False,
    output_dir: Path | None = None,
    project: Path | None = None,
    render_backend: str = "cairo",
    force_render: bool = False,
    hard_gate: bool = False,
    server_url: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vx, vy, vw, vh = _viewbox(root)
    max_x = vx + vw
    max_y = vy + vh

    all_text = "\n".join(_text_content(elem) for elem in root.iter() if _strip_ns(elem.tag) == "text")
    if TOFU_RE.search(all_text):
        errors.append("SVG text contains tofu/replacement characters")
    if CJK_RE.search(all_text) and not _has_cjk_font(_font_families(root)):
        warnings.append("CJK text detected but no available CJK font was found in font-family stacks")

    overflow_count = 0
    edge_text_count = 0
    for elem in root.iter():
        bounds = _element_bounds(elem)
        if bounds is None:
            continue
        x1, y1, x2, y2 = bounds
        if x2 < vx - 2 or y2 < vy - 2 or x1 > max_x + 2 or y1 > max_y + 2:
            overflow_count += 1
        if _strip_ns(elem.tag) == "text":
            if x1 < vx + 4 or x2 > max_x - 4 or y1 < vy + 4 or y2 > max_y - 4:
                edge_text_count += 1

    if overflow_count:
        warnings.append(f"{overflow_count} basic element(s) appear completely outside the viewBox")
    if edge_text_count:
        warnings.append(f"{edge_text_count} text element(s) sit very close to the canvas edge")

    preview_path = None
    render_meta: str | None = None
    resolved_backend: str | None = None
    if render:
        out_dir = output_dir or svg_path.parent
        preview_path = out_dir / f"{svg_path.stem}.preview.png"
        proj = project or _project_root_for_svg(svg_path)
        render_result = ensure_preview_for_svg(
            proj,
            svg_path,
            preview_path,
            render=True,
            render_backend=render_backend,
            force_render=force_render,
            hard_gate=hard_gate,
            server_url=server_url,
        )
        resolved_backend = render_result.backend
        render_meta = str(render_result.meta_path)
        if not render_result.ok:
            errors.extend(render_result.errors)
        elif preview_path.is_file() and not _image_nonblank(preview_path):
            errors.append("Rendered preview appears blank")
        warnings.extend(render_result.warnings)

    payload = {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "viewBox": [vx, vy, vw, vh],
        "text_elements": sum(1 for elem in root.iter() if _strip_ns(elem.tag) == "text"),
        "preview": str(preview_path) if preview_path else None,
    }
    if resolved_backend:
        payload["render_backend"] = resolved_backend
    if render_meta:
        payload["render_meta"] = render_meta
    return payload


def _project_root_for_svg(svg_path: Path) -> Path:
    for parent in [svg_path.parent, *svg_path.parents]:
        if (parent / "svg_output").is_dir() and svg_path.parent.name in {"svg_output", "svg_final"}:
            return parent
        if (parent / "layout_reference.json").is_file() or (parent / "slide_image_rebuild_manifest.json").is_file():
            return parent
    return svg_path.parent


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    if (target / "svg_output").is_dir():
        return sorted((target / "svg_output").glob("*.svg"))
    return sorted(target.glob("*.svg"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render SVG previews and run lightweight visual QA checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    parser.add_argument("--render", action="store_true", help="Render PNG previews")
    parser.add_argument("--output-dir", type=Path, help="Preview output directory")
    parser.add_argument(
        "--render-backend",
        choices=["auto", "cairo", "none"],
        default="cairo",
    )
    parser.add_argument("--force-render", action="store_true")
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="Reject --render-backend auto (for CI / pre-export)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        print(json.dumps({"valid": False, "errors": ["No SVG files found"]}, ensure_ascii=False, indent=2))
        return 1
    output_dir = args.output_dir
    project = args.target if args.target.is_dir() else args.target.parent
    if output_dir is None and args.target.is_dir():
        output_dir = args.target / "exports" / "preview_qa"
    results = [
        inspect_svg(
            svg,
            render=args.render,
            output_dir=output_dir,
            project=project,
            render_backend=args.render_backend,
            force_render=args.force_render,
            hard_gate=args.hard_gate,
            server_url=getattr(args, "server_url", None),
        )
        for svg in svgs
    ]
    valid = all(result["valid"] for result in results)
    payload = {"valid": valid, "count": len(results), "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
