#!/usr/bin/env python3
"""
PPT Master - ChatGPT Precise Rebuild Lock

Verify the ChatGPT-only precise rebuild lock for slide-image rebuild projects.
The lock is intentionally narrow: it activates only when a project manifest sets
execution_profile or chatgpt_profile to `chatgpt_precise_rebuild`, or when this
script is called with --enforce.

Usage:
    python3 scripts/verify_chatgpt_precise_rebuild_lock.py <project_path>
    python3 scripts/verify_chatgpt_precise_rebuild_lock.py <project_path> --enforce

Examples:
    python3 scripts/verify_chatgpt_precise_rebuild_lock.py projects/rebuild_demo --enforce

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
DEFAULT_MIN_FONT_PT = 6.4
DEFAULT_MIN_BODY_FONT_PT = 7.0


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _manifest_path(project: Path) -> Path:
    return project / "slide_image_rebuild_manifest.json"


def _active(manifest: dict[str, Any], *, enforce: bool) -> bool:
    if enforce:
        return True
    profile = manifest.get("execution_profile") or manifest.get("chatgpt_profile")
    return profile == "chatgpt_precise_rebuild"


def _load_lock(project: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        project / "chatgpt_precise_rebuild_lock.json",
        repo_root / "presets" / "chatgpt_precise_rebuild_lock.json",
    ]
    for path in candidates:
        if path.is_file():
            data = _load_json(path)
            if data:
                return data
    return {}


def _find_svgs(project: Path) -> list[Path]:
    svgs: list[Path] = []
    for folder in ["svg_output", "svg_final"]:
        path = project / folder
        if path.is_dir():
            svgs.extend(sorted(path.glob("*.svg")))
    return svgs


def _font_role(elem: ET.Element) -> str:
    role = (
        elem.get("data-text-role")
        or elem.get("data-role")
        or elem.get("data-zone-role")
        or ""
    ).lower()
    if not role:
        zone_id = (elem.get("data-zone-id") or elem.get("id") or "").lower()
        if any(token in zone_id for token in ["body", "content", "desc", "caption", "paragraph"]):
            role = "body"
    return role


def _is_body_like(elem: ET.Element) -> bool:
    role = _font_role(elem)
    return any(token in role for token in ["body", "content", "desc", "paragraph", "caption"])


def _text_preview(elem: ET.Element) -> str:
    text = "".join(elem.itertext()).strip()
    return text[:30] or elem.get("id") or elem.get("data-zone-id") or "unnamed text"


def inspect_svg(
    svg: Path,
    *,
    min_font_pt: float,
    min_body_font_pt: float,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError as exc:
        return ([{"code": "invalid_svg", "message": str(exc), "path": str(svg)}], [])

    width = _float(root.get("width"))
    height = _float(root.get("height"))
    if width and abs(width - 1280) > 0.5:
        warnings.append({
            "code": "canvas_width_not_1280",
            "message": f"SVG width is {width}, expected 1280.",
            "path": str(svg),
        })
    if height and abs(height - 720) > 0.5:
        warnings.append({
            "code": "canvas_height_not_720",
            "message": f"SVG height is {height}, expected 720.",
            "path": str(svg),
        })

    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag == "image":
            x = _float(elem.get("x")) or 0
            y = _float(elem.get("y")) or 0
            w = _float(elem.get("width")) or 0
            h = _float(elem.get("height")) or 0
            if x <= 1 and y <= 1 and w >= 1278 and h >= 718:
                errors.append({
                    "code": "full_slide_image_forbidden",
                    "message": "Full-slide reference images are forbidden under chatgpt_precise_rebuild.",
                    "path": str(svg),
                })
        if tag != "text":
            continue
        font_pt = _float(elem.get("font-size"))
        if font_pt is None:
            continue
        label = _text_preview(elem)
        if font_pt < min_font_pt and elem.get("data-low-font-approved") != "true":
            errors.append({
                "code": "font_below_precise_lock_minimum",
                "message": f"{label}: font-size {font_pt:g}pt is below {min_font_pt:g}pt.",
                "path": str(svg),
            })
        if _is_body_like(elem) and font_pt < min_body_font_pt and elem.get("data-low-font-approved") != "true":
            errors.append({
                "code": "body_font_below_precise_lock_minimum",
                "message": f"{label}: body font-size {font_pt:g}pt is below {min_body_font_pt:g}pt.",
                "path": str(svg),
            })
        for key, value in elem.attrib.items():
            if "shrink" in str(value).lower() or "shrink" in key.lower():
                errors.append({
                    "code": "shrink_marker_forbidden",
                    "message": f"{label}: shrink-like marker `{key}={value}` is forbidden under chatgpt_precise_rebuild.",
                    "path": str(svg),
                })
    return errors, warnings


def verify(project: Path, *, enforce: bool = False) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    manifest = _load_json(_manifest_path(project))
    if not manifest:
        return {
            "valid": False,
            "active": enforce,
            "errors": [{
                "code": "missing_manifest",
                "message": "slide_image_rebuild_manifest.json is required.",
                "path": str(_manifest_path(project)),
            }],
            "warnings": [],
        }
    active = _active(manifest, enforce=enforce)
    if not active:
        return {"valid": True, "active": False, "errors": [], "warnings": []}

    lock = _load_lock(project)
    text_policy = lock.get("text_policy", {}) if isinstance(lock, dict) else {}
    min_font_pt = float(text_policy.get("minimum_font_pt", DEFAULT_MIN_FONT_PT))
    min_body_font_pt = float(text_policy.get("minimum_body_font_pt", DEFAULT_MIN_BODY_FONT_PT))

    if manifest.get("rebuild_mode") not in {"vector-hifi", "hifi", "wps-hifi"}:
        errors.append({
            "code": "precise_lock_requires_vector_hifi",
            "message": "chatgpt_precise_rebuild requires rebuild_mode vector-hifi/hifi/wps-hifi.",
            "path": str(_manifest_path(project)),
        })
    if _as_bool(manifest.get("allow_global_shrink")):
        errors.append({
            "code": "global_shrink_forbidden",
            "message": "allow_global_shrink must not be enabled under chatgpt_precise_rebuild.",
            "path": str(_manifest_path(project)),
        })
    if _as_bool(manifest.get("allow_content_deletion_for_fit")) or _as_bool(manifest.get("allow_page_split_for_fit")):
        errors.append({
            "code": "fit_by_content_change_forbidden",
            "message": "Do not delete content or split the page to make a precise reference rebuild fit.",
            "path": str(_manifest_path(project)),
        })

    svgs = _find_svgs(project)
    if not svgs:
        errors.append({
            "code": "missing_svg",
            "message": "No SVG found under svg_output/ or svg_final/.",
            "path": str(project),
        })
    for svg in svgs:
        svg_errors, svg_warnings = inspect_svg(
            svg,
            min_font_pt=min_font_pt,
            min_body_font_pt=min_body_font_pt,
        )
        errors.extend(svg_errors)
        warnings.extend(svg_warnings)

    return {
        "workflow": "slide-image-rebuild",
        "profile": "chatgpt_precise_rebuild",
        "active": True,
        "valid": not errors,
        "minimum_font_pt": min_font_pt,
        "minimum_body_font_pt": min_body_font_pt,
        "checked_svg_count": len(svgs),
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify ChatGPT precise image rebuild lock.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--enforce", action="store_true", help="Run even when manifest profile is not set")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = verify(args.project_path.resolve(), enforce=args.enforce)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
