#!/usr/bin/env python3
"""Verify optional CxR grid contracts for slide-image-rebuild assets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT_NAMES = ("grid_contract.json", "asset_grid_contract.json")


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


def _box(raw: Any, label: str, errors: list[str]) -> Box | None:
    if not isinstance(raw, list) or len(raw) != 4:
        errors.append(f"{label}: expected [x, y, w, h]")
        return None
    if not all(isinstance(value, (int, float)) for value in raw):
        errors.append(f"{label}: bbox values must be numeric")
        return None
    x, y, w, h = [float(value) for value in raw]
    if w <= 0 or h <= 0:
        errors.append(f"{label}: bbox width/height must be positive")
        return None
    return Box(x, y, w, h)


def _load_contract(target: Path) -> tuple[dict[str, Any] | None, Path | None]:
    if target.is_file():
        return json.loads(target.read_text(encoding="utf-8")), target
    for name in CONTRACT_NAMES:
        path = target / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), path
    return None, None


def _policy(grid: dict[str, Any], key: str, default: float) -> float:
    policy = grid.get("policy") if isinstance(grid.get("policy"), dict) else {}
    value = policy.get(key, default)
    return float(value) if isinstance(value, (int, float)) else default


def _cell_box(grid_box: Box, rows: int, cols: int, row: int, col: int) -> Box:
    cell_w = grid_box.w / cols
    cell_h = grid_box.h / rows
    return Box(grid_box.x + col * cell_w, grid_box.y + row * cell_h, cell_w, cell_h)


def _inspect_grid(page_id: str, grid: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    grid_id = str(grid.get("id") or "grid")
    prefix = f"page {page_id} grid {grid_id}"

    rows = grid.get("rows")
    cols = grid.get("columns")
    if not isinstance(rows, int) or rows <= 0:
        errors.append(f"{prefix}: rows must be a positive integer")
    if not isinstance(cols, int) or cols <= 0:
        errors.append(f"{prefix}: columns must be a positive integer")
    grid_box = _box(grid.get("bbox_px"), f"{prefix}.bbox_px", errors)
    if errors or grid_box is None:
        return {"id": grid_id, "valid": False, "errors": errors, "warnings": warnings}

    aspect_tolerance = _policy(grid, "aspect_tolerance_ratio", 0.03)
    actual_aspect = grid_box.w / grid_box.h
    expected_aspect = cols / rows
    if abs(actual_aspect - expected_aspect) / expected_aspect > aspect_tolerance:
        errors.append(
            f"{prefix}: grid bbox aspect {actual_aspect:.3f} does not match "
            f"C:R {cols}:{rows} ({expected_aspect:.3f}) within {aspect_tolerance:.1%}"
        )

    if rows == cols and abs(actual_aspect - 1.0) > aspect_tolerance:
        errors.append(f"{prefix}: {rows}x{cols} grid must use a square bbox")

    center_tolerance = _policy(grid, "center_tolerance_px", 4.0)
    hard_min_padding = _policy(grid, "hard_min_padding_ratio", 0.10)
    warn_min_padding = _policy(grid, "warning_min_padding_ratio", 0.15)
    preferred_min = _policy(grid, "preferred_fill_ratio_min", 0.55)
    preferred_max = _policy(grid, "preferred_fill_ratio_max", 0.70)

    items = grid.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{prefix}: items must be a non-empty list")
        return {"id": grid_id, "valid": False, "errors": errors, "warnings": warnings}

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{prefix}.items[{index}]: expected object")
            continue
        item_id = str(item.get("id") or f"item_{index + 1}")
        cell = item.get("cell")
        if not isinstance(cell, list) or len(cell) != 2 or not all(isinstance(value, int) for value in cell):
            errors.append(f"{prefix}.{item_id}: cell must be [row, column] using zero-based indexes")
            continue
        row, col = cell
        if row < 0 or row >= rows or col < 0 or col >= cols:
            errors.append(f"{prefix}.{item_id}: cell {cell} is outside {rows}x{cols} grid")
            continue
        item_box = _box(item.get("bbox_px"), f"{prefix}.{item_id}.bbox_px", errors)
        if item_box is None:
            continue
        cell_box = _cell_box(grid_box, rows, cols, row, col)
        dx = item_box.cx - cell_box.cx
        dy = item_box.cy - cell_box.cy
        if abs(dx) > center_tolerance or abs(dy) > center_tolerance:
            errors.append(
                f"{prefix}.{item_id}: center offset ({dx:+.1f}, {dy:+.1f})px from "
                f"cell center exceeds {center_tolerance:.1f}px"
            )
        pads = (
            item_box.x - cell_box.x,
            item_box.y - cell_box.y,
            cell_box.right - item_box.right,
            cell_box.bottom - item_box.bottom,
        )
        min_padding_ratio = min(pads) / min(cell_box.w, cell_box.h)
        if min_padding_ratio < hard_min_padding:
            errors.append(
                f"{prefix}.{item_id}: cell padding ratio {min_padding_ratio:.3f} "
                f"is below hard minimum {hard_min_padding:.3f}"
            )
        elif min_padding_ratio < warn_min_padding:
            warnings.append(
                f"{prefix}.{item_id}: cell padding ratio {min_padding_ratio:.3f} "
                f"is below preferred warning minimum {warn_min_padding:.3f}"
            )
        fill_ratio = max(item_box.w, item_box.h) / min(cell_box.w, cell_box.h)
        if fill_ratio < preferred_min or fill_ratio > preferred_max:
            warnings.append(
                f"{prefix}.{item_id}: fill ratio {fill_ratio:.3f} is outside "
                f"preferred {preferred_min:.2f}-{preferred_max:.2f} safe zone"
            )

    return {
        "id": grid_id,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "rows": rows,
            "columns": cols,
            "aspect": round(actual_aspect, 5),
            "expected_aspect": round(expected_aspect, 5),
            "items": len(items),
        },
    }


def inspect(target: Path) -> dict[str, Any]:
    contract, contract_path = _load_contract(target)
    if contract is None:
        return {
            "valid": True,
            "skipped": True,
            "errors": [],
            "warnings": ["grid contract skipped: no grid_contract.json found"],
            "results": [],
        }
    pages = contract.get("pages")
    if not isinstance(pages, list):
        return {
            "valid": False,
            "skipped": False,
            "errors": ["grid contract requires pages[]"],
            "warnings": [],
            "contract": str(contract_path),
            "results": [],
        }
    results: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            results.append({"valid": False, "errors": ["page entry must be an object"], "warnings": []})
            continue
        page_id = str(page.get("page_id") or "unknown")
        grids = page.get("grids")
        if not isinstance(grids, list) or not grids:
            results.append({"page_id": page_id, "valid": False, "errors": [f"page {page_id}: grids must be non-empty"], "warnings": []})
            continue
        for grid in grids:
            if isinstance(grid, dict):
                result = _inspect_grid(page_id, grid)
            else:
                result = {"valid": False, "errors": [f"page {page_id}: grid entry must be an object"], "warnings": []}
            result["page_id"] = page_id
            results.append(result)
    errors = [error for result in results for error in result.get("errors", [])]
    warnings = [warning for result in results for warning in result.get("warnings", [])]
    return {
        "valid": not errors,
        "skipped": False,
        "contract": str(contract_path),
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify optional CxR grid contracts.")
    parser.add_argument("target", type=Path, help="Project directory or grid_contract.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = inspect(args.target)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
