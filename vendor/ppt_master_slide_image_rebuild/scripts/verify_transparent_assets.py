#!/usr/bin/env python3
"""Verify final transparent PNG assets used by slide-image-rebuild projects.

This gate is intentionally narrower than a generic PNG scanner: it checks only
asset directories and explicit transparent-asset manifests, not reference images,
rendered previews, or README/demo screenshots.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_ASSET_DIRS = (
    "assets",
    "generated_assets",
    "image_assets",
    "images/assets",
    "images/generated_assets",
)
SKIP_DIR_NAMES = {"source", "sources", "reference", "references", "preview", "previews", "qa", "tmp", "temp"}
MANIFEST_NAMES = ("transparent_assets.json", "asset_manifest.json", "image_asset_manifest.json")


def _project_asset_dirs(project: Path) -> list[Path]:
    dirs: list[Path] = []
    for rel in DEFAULT_ASSET_DIRS:
        candidate = project / rel
        if candidate.is_dir():
            dirs.append(candidate)
    return dirs


def _manifest_asset_paths(project: Path) -> list[Path]:
    paths: list[Path] = []
    for name in MANIFEST_NAMES:
        manifest = project / name
        if not manifest.is_file():
            continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        assets = payload.get("assets") if isinstance(payload, dict) else payload
        if not isinstance(assets, list):
            continue
        for item in assets:
            if isinstance(item, str):
                raw = item
            elif isinstance(item, dict):
                treatment = str(item.get("treatment") or item.get("source") or "").lower()
                if treatment and not any(key in treatment for key in ("transparent", "png", "imagegen")):
                    continue
                raw = item.get("path") or item.get("file") or item.get("final_png") or item.get("asset_path")
            else:
                continue
            if not isinstance(raw, str) or not raw.strip():
                continue
            path = Path(raw)
            if not path.is_absolute():
                path = project / path
            if path.suffix.lower() == ".png":
                paths.append(path)
    return paths


def _skip_asset_path(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = {part.lower() for part in rel.parts[:-1]}
        if parts & SKIP_DIR_NAMES:
            return True
        name = path.name.lower()
        return any(token in name for token in ("contact", "sheet", "preview", "reference", "source")) and len(rel.parts) == 1
    return False


def discover_assets(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".png" else []
    roots = _project_asset_dirs(target)
    assets: list[Path] = []
    for root in roots:
        for path in sorted(root.rglob("*.png")):
            if not _skip_asset_path(path, roots):
                assets.append(path)
    assets.extend(_manifest_asset_paths(target))
    unique: dict[Path, Path] = {}
    for path in assets:
        unique[path.resolve()] = path
    return [unique[key] for key in sorted(unique)]


def inspect_asset(path: Path, *, min_padding: int = 10) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return {"path": str(path), "valid": False, "errors": [f"missing asset file: {path}"], "warnings": []}

    try:
        with Image.open(path) as im:
            rgba = im.convert("RGBA")
    except Exception as exc:
        return {"path": str(path), "valid": False, "errors": [f"cannot open PNG: {exc}"], "warnings": []}

    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return {"path": str(path), "valid": False, "errors": ["empty alpha channel"], "warnings": []}

    left, top, right, bottom = bbox
    pads = (left, top, rgba.width - right, rgba.height - bottom)
    if min(pads) < min_padding:
        errors.append(f"unsafe transparent padding {pads}; expected all >= {min_padding}px")

    pix = rgba.load()
    edge_hits = 0
    for x in range(rgba.width):
        if pix[x, 0][3] or pix[x, rgba.height - 1][3]:
            edge_hits += 1
    for y in range(rgba.height):
        if pix[0, y][3] or pix[rgba.width - 1, y][3]:
            edge_hits += 1
    if edge_hits:
        errors.append(f"non-transparent pixels touch image edge ({edge_hits} hits)")

    alpha_extrema = alpha.getextrema()
    if alpha_extrema == (255, 255):
        errors.append("asset is fully opaque; expected transparent PNG with alpha padding")

    return {
        "path": str(path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "size": [rgba.width, rgba.height],
        "alpha_bbox": [left, top, right, bottom],
        "padding": list(pads),
    }


def inspect(target: Path, *, min_padding: int = 10) -> dict[str, Any]:
    assets = discover_assets(target)
    results = [inspect_asset(path, min_padding=min_padding) for path in assets]
    errors = [
        f"{Path(result['path']).name}: {error}"
        for result in results
        for error in result.get("errors", [])
    ]
    return {
        "valid": not errors,
        "count": len(results),
        "errors": errors,
        "warnings": [],
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify transparent PNG assets for image-to-PPTX rebuilds.")
    parser.add_argument("target", type=Path, help="Project directory or a PNG asset")
    parser.add_argument("--min-padding", type=int, default=10, help="Minimum transparent edge padding in pixels")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = inspect(args.target, min_padding=args.min_padding)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
