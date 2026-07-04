#!/usr/bin/env python3
"""
PPT Master - Icon/Text Fit Verifier

Validate icon_reconstruction entries against text-block alignment rules in
layout_reference.json. This script checks planning geometry only; final visual
quality still requires rendered SVG/PPTX review.

Usage:
    python3 scripts/verify_icon_text_fit.py <layout_reference.json>

Examples:
    python3 scripts/verify_icon_text_fit.py projects/demo/layout_reference.json
    python3 scripts/verify_icon_text_fit.py projects/demo/layout_reference.json --tolerance 8

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def _slot_to_px(slot: dict[str, Any], canvas: dict[str, Any]) -> dict[str, float] | None:
    width = float(canvas.get("width_px") or 1280)
    height = float(canvas.get("height_px") or 720)
    if not all(isinstance(slot.get(key), (int, float)) for key in ["cx_ratio", "cy_ratio", "size_ratio"]):
        return None
    return {
        "cx": float(slot["cx_ratio"]) * width,
        "cy": float(slot["cy_ratio"]) * height,
        "size": float(slot["size_ratio"]) * min(width, height),
    }


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _actual_icon_positions(svg_path: Path) -> dict[str, dict[str, float]]:
    root = ET.parse(svg_path).getroot()
    out: dict[str, dict[str, float]] = {}
    for elem in root.iter():
        icon_id = elem.get("data-icon-id")
        if not icon_id:
            continue
        for child in elem.iter():
            if _strip_ns(child.tag) != "circle":
                continue
            cx = _float(child.get("cx"))
            cy = _float(child.get("cy"))
            r = _float(child.get("r"))
            if cx is not None and cy is not None and r is not None:
                out[icon_id] = {"cx": cx, "cy": cy, "size": r * 2}
                break
    return out


def verify(data: dict[str, Any], *, tolerance: float = 6.0) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    canvas = data.get("canvas", {})
    icon_reconstruction = data.get("icon_reconstruction", {})
    if not isinstance(icon_reconstruction, dict):
        return errors, ["No icon_reconstruction object found"]

    level_rules = icon_reconstruction.get("level_rules", {})
    icons = icon_reconstruction.get("icons", [])
    if not isinstance(level_rules, dict):
        errors.append("icon_reconstruction.level_rules must be an object")
        return errors, warnings
    if not isinstance(icons, list):
        errors.append("icon_reconstruction.icons must be a list")
        return errors, warnings

    for index, icon in enumerate(icons):
        if not isinstance(icon, dict):
            errors.append(f"icons[{index}] must be an object")
            continue
        icon_id = icon.get("id", f"#{index}")
        level = icon.get("level")
        text_anchor = icon.get("text_anchor", {})
        slot = icon.get("slot", {})
        rule = level_rules.get(level)
        if not rule:
            warnings.append(f"{icon_id}: no level rule for {level!r}; skipped formula check")
            continue
        if not isinstance(text_anchor, dict) or not text_anchor:
            warnings.append(f"{icon_id}: no text_anchor; skipped formula check")
            continue
        if not isinstance(slot, dict):
            errors.append(f"{icon_id}: slot must be an object")
            continue
        missing = [
            key for key in ["text_left_px", "text_top_px", "text_height_px"]
            if not isinstance(text_anchor.get(key), (int, float))
        ]
        if missing:
            errors.append(f"{icon_id}: text_anchor missing numeric field(s): {', '.join(missing)}")
            continue
        if not all(isinstance(rule.get(key), (int, float)) for key in ["circle_r_px", "text_gap_px", "icon_size_px"]):
            errors.append(f"{icon_id}: level rule must contain numeric circle_r_px/text_gap_px/icon_size_px")
            continue
        px_slot = _slot_to_px(slot, canvas)
        if px_slot is None:
            errors.append(f"{icon_id}: slot must contain numeric cx_ratio/cy_ratio/size_ratio")
            continue

        expected_cx = float(text_anchor["text_left_px"]) - float(rule["text_gap_px"]) - float(rule["circle_r_px"])
        expected_cy = float(text_anchor["text_top_px"]) + float(text_anchor["text_height_px"]) / 2
        alignment_model = icon.get("alignment_model") or rule.get("alignment_model")
        if alignment_model is None and level in {"title_aligned_icon", "card_section"}:
            alignment_model = "title_aligned_icon"
        elif alignment_model is None and level == "body_column_icon":
            alignment_model = "body_column_icon"
        elif alignment_model is None and level in {"action", "footer_action_icon"}:
            alignment_model = "footer_action_icon"
        if alignment_model not in {None, "title_aligned_icon", "body_column_icon", "footer_action_icon", "custom"}:
            errors.append(f"{icon_id}: unsupported alignment_model {alignment_model!r}")
        bare_linear_icon = float(rule["circle_r_px"]) == 0 and alignment_model in {
            "title_aligned_icon",
            "body_column_icon",
            "footer_action_icon",
            "custom",
        }
        expected_size = float(rule["circle_r_px"]) * 2

        if abs(px_slot["cx"] - expected_cx) > tolerance:
            errors.append(f"{icon_id}: cx {px_slot['cx']:.1f} differs from formula {expected_cx:.1f}")
        if abs(px_slot["cy"] - expected_cy) > tolerance:
            errors.append(f"{icon_id}: cy {px_slot['cy']:.1f} differs from formula {expected_cy:.1f}")
        if not bare_linear_icon and abs(px_slot["size"] - expected_size) > tolerance:
            warnings.append(f"{icon_id}: slot size {px_slot['size']:.1f} differs from circle diameter {expected_size:.1f}")

    return errors, warnings


def verify_svg_actual(
    data: dict[str, Any],
    svg_path: Path,
    *,
    tolerance: float = 6.0,
    strict: bool = False,
) -> tuple[list[str], list[str]]:
    if strict:
        errors: list[str] = []
        warnings: list[str] = []
    else:
        errors, warnings = verify(data, tolerance=tolerance)
    canvas = data.get("canvas", {})
    icons = data.get("icon_reconstruction", {}).get("icons", [])
    actual = _actual_icon_positions(svg_path)
    for icon in icons if isinstance(icons, list) else []:
        if not isinstance(icon, dict):
            continue
        icon_id = icon.get("id", "")
        if not icon_id:
            continue
        if icon_id not in actual:
            message = f"{icon_id}: no matching data-icon-id found in SVG"
            if strict:
                errors.append(message)
            else:
                warnings.append(message)
            continue
        if strict:
            continue
        slot = icon.get("slot", {})
        expected = _slot_to_px(slot, canvas) if isinstance(slot, dict) else None
        if expected is None:
            continue
        got = actual[icon_id]
        if abs(got["cx"] - expected["cx"]) > tolerance:
            errors.append(f"{icon_id}: actual cx {got['cx']:.1f} differs from planned {expected['cx']:.1f}")
        if abs(got["cy"] - expected["cy"]) > tolerance:
            errors.append(f"{icon_id}: actual cy {got['cy']:.1f} differs from planned {expected['cy']:.1f}")
        if abs(got["size"] - expected["size"]) > tolerance:
            warnings.append(f"{icon_id}: actual size {got['size']:.1f} differs from planned {expected['size']:.1f}")
    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify icon/text fit geometry in layout_reference.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to layout_reference.json")
    parser.add_argument("--svg", type=Path, help="Optional final SVG to compare actual icon positions")
    parser.add_argument("--tolerance", type=float, default=6.0, help="Allowed pixel delta for formula checks")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="复刻流程2: require every planned icon as data-icon-id in SVG (skip formula/slot delta checks)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data = load_json(args.path)
    if args.svg:
        errors, warnings = verify_svg_actual(
            data,
            args.svg,
            tolerance=args.tolerance,
            strict=args.strict,
        )
    else:
        errors, warnings = verify(data, tolerance=args.tolerance)
    payload = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
