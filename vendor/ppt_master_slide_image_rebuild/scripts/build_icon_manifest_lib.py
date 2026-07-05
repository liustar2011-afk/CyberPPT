#!/usr/bin/env python3
"""
Build icon_manifest.json drafts from layout_reference.json icon slots.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reference_object_similarity_lib import canvas_size, resolve_bbox_px

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
MANIFEST_VERSION = "1.0"
PROFILE = "chatgpt_precise_rebuild_icon_contract"

EXCLUDE_ID_KEYWORDS = (
    "page_number",
    "page_badge",
    "decorative_badge",
    "footer_page",
    "page_num",
)
EXCLUDE_ZONE_ROLES = (
    "page_number",
    "decorative_badge",
    "footer_page",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


def _should_exclude_id(value: str) -> bool:
    lowered = value.strip().lower()
    return any(token in lowered for token in EXCLUDE_ID_KEYWORDS)


def _slot_bbox(icon: dict[str, Any], canvas_w: int, canvas_h: int) -> list[float] | None:
    bbox = resolve_bbox_px(icon, canvas_w, canvas_h)
    if bbox is not None:
        return [round(value, 2) for value in bbox]
    slot = icon.get("slot")
    if not isinstance(slot, dict):
        return None
    try:
        cx = float(slot["cx_ratio"]) * canvas_w
        cy = float(slot["cy_ratio"]) * canvas_h
        size = float(slot.get("size_ratio") or slot.get("size_px") or 0.03) * min(canvas_w, canvas_h)
    except (KeyError, TypeError, ValueError):
        return None
    half = size / 2.0
    return [round(cx - half, 2), round(cy - half, 2), round(size, 2), round(size, 2)]


def _icon_from_layout_entry(icon: dict[str, Any], *, canvas_w: int, canvas_h: int) -> dict[str, Any] | None:
    icon_id = str(icon.get("id", "")).strip()
    if not icon_id or _should_exclude_id(icon_id):
        return None
    bbox = _slot_bbox(icon, canvas_w, canvas_h)
    if bbox is None:
        return None
    semantic = str(icon.get("semantic") or icon.get("description") or icon.get("label") or "functional icon").strip()
    return {
        "id": icon_id,
        "bbox_px": bbox,
        "semantic": semantic,
        "required": icon.get("required", True) is not False,
        "implementation": str(icon.get("implementation") or "asset_svg"),
        "fallback_allowed": icon.get("fallback_allowed", False) is True,
        "parent_zone": icon.get("parent_zone") or icon.get("parent_zone_id") or icon.get("zone_id") or "",
        "needs_review": bool(icon.get("needs_review", False)),
    }


def _icon_from_zone(zone: dict[str, Any], *, canvas_w: int, canvas_h: int) -> dict[str, Any] | None:
    zone_id = str(zone.get("id", "")).strip()
    if not zone_id or _should_exclude_id(zone_id):
        return None
    role = str(zone.get("role", "")).lower()
    component = str(zone.get("component", "")).lower()
    if role in EXCLUDE_ZONE_ROLES:
        return None
    if "icon" not in role and "icon_slot" not in component and "icon" not in component:
        return None
    bbox = resolve_bbox_px(zone, canvas_w, canvas_h)
    if bbox is None:
        return None
    x, y, width, height = bbox
    size = min(width, height)
    cx = x + width / 2.0
    cy = y + height / 2.0
    icon_id = str(zone.get("icon_id") or f"{zone_id}_icon")
    if _should_exclude_id(icon_id):
        return None
    semantic = str(zone.get("semantic") or zone.get("label") or f"icon in {zone_id}").strip()
    return {
        "id": icon_id,
        "bbox_px": [round(cx - size / 2, 2), round(cy - size / 2, 2), round(size, 2), round(size, 2)],
        "semantic": semantic,
        "required": zone.get("required", False) is True,
        "implementation": "asset_svg",
        "fallback_allowed": False,
        "parent_zone": zone_id,
        "needs_review": True,
    }


def collect_icons_for_layout(layout: dict[str, Any], *, page_id: str, svg_rel: str) -> list[dict[str, Any]]:
    canvas_w, canvas_h = canvas_size(layout, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
    seen: set[str] = set()
    icons: list[dict[str, Any]] = []

    icon_reconstruction = layout.get("icon_reconstruction", {})
    if isinstance(icon_reconstruction, dict):
        entries = icon_reconstruction.get("icons", [])
        if isinstance(entries, list):
            for item in entries:
                if not isinstance(item, dict):
                    continue
                manifest_icon = _icon_from_layout_entry(item, canvas_w=canvas_w, canvas_h=canvas_h)
                if manifest_icon is None or manifest_icon["id"] in seen:
                    continue
                seen.add(manifest_icon["id"])
                icons.append(manifest_icon)

    zones = layout.get("zones", [])
    if isinstance(zones, list):
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            manifest_icon = _icon_from_zone(zone, canvas_w=canvas_w, canvas_h=canvas_h)
            if manifest_icon is None or manifest_icon["id"] in seen:
                continue
            seen.add(manifest_icon["id"])
            icons.append(manifest_icon)

    return icons


def _svg_rel_for_page(project: Path, page_id: str, page_dir: Path) -> str:
    for folder in ("svg_output", "svg_final"):
        svg_dir = page_dir / folder
        if svg_dir.is_dir():
            matches = sorted(svg_dir.glob(f"{page_id}*.svg")) or sorted(svg_dir.glob("*.svg"))
            if matches:
                return str(matches[0].relative_to(project))
    for folder in ("svg_output", "svg_final"):
        svg_dir = project / folder
        if svg_dir.is_dir():
            matches = sorted(svg_dir.glob(f"{page_id}*.svg")) or sorted(svg_dir.glob("*.svg"))
            if matches:
                return str(matches[0].relative_to(project))
    return f"svg_output/{page_id}.svg"


def _layout_pages(project: Path) -> list[tuple[str, Path]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    out: list[tuple[str, Path]] = []
    if isinstance(pages, list) and pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id", "")).strip() or "01"
            page_dir = project / "pages" / page_id
            layout_path = page_dir / "layout_reference.json"
            if layout_path.is_file():
                out.append((page_id, layout_path))
                continue
            root_layout = project / "layout_reference.json"
            if root_layout.is_file():
                out.append((page_id, root_layout))
        if out:
            return out
    root_layout = project / "layout_reference.json"
    if root_layout.is_file():
        return [("01", root_layout)]
    pages_dir = project / "pages"
    if pages_dir.is_dir():
        for page_dir in sorted(pages_dir.iterdir()):
            layout_path = page_dir / "layout_reference.json"
            if layout_path.is_file():
                out.append((page_dir.name, layout_path))
    return out


def build_manifest(project: Path) -> dict[str, Any]:
    project = project.resolve()
    pages_payload: list[dict[str, Any]] = []
    warnings: list[str] = []
    for page_id, layout_path in _layout_pages(project):
        layout = load_json(layout_path)
        page_dir = layout_path.parent
        svg_rel = _svg_rel_for_page(project, page_id, page_dir)
        icons = collect_icons_for_layout(layout, page_id=page_id, svg_rel=svg_rel)
        if not icons:
            continue
        review_count = sum(1 for item in icons if item.get("needs_review"))
        if review_count:
            warnings.append(f"Page `{page_id}` has {review_count} icon(s) marked needs_review.")
        pages_payload.append({
            "page_id": page_id,
            "svg": svg_rel,
            "icons": icons,
        })

    return {
        "workflow": "slide-image-rebuild",
        "version": MANIFEST_VERSION,
        "profile": PROFILE,
        "generated_at": utc_now(),
        "source": "build_icon_manifest_from_layout.py",
        "policy": {
            "require_bbox": True,
            "bbox_position_tolerance_px": 3,
            "bbox_size_tolerance_px": 4,
            "min_visible_pixel_ratio": 0.015,
            "style_check": True,
            "max_stroke_width_px": 2.5,
            "min_bbox_fill_ratio": 0.12,
            "max_bbox_fill_ratio": 0.85,
            "min_padding_ratio": 0.08,
            "max_stroke_width_spread_px": 0.75,
        },
        "pages": pages_payload,
        "summary": {
            "page_count": len(pages_payload),
            "icon_count": sum(len(page.get("icons", [])) for page in pages_payload),
            "needs_review_count": sum(
                1
                for page in pages_payload
                for icon in page.get("icons", [])
                if isinstance(icon, dict) and icon.get("needs_review")
            ),
        },
        "warnings": warnings,
    }


def write_manifest(project: Path, payload: dict[str, Any], *, force: bool = False) -> Path:
    out = project / "icon_manifest.json"
    if out.is_file() and not force:
        raise FileExistsError(f"{out} already exists; pass --force to overwrite.")
    if out.is_file() and force:
        # Preserve hand-tuned policy overrides (e.g. style_check: false) across
        # regeneration; only icon entries are rebuilt from the layout.
        try:
            existing_policy = json.loads(out.read_text(encoding="utf-8")).get("policy")
        except (OSError, json.JSONDecodeError):
            existing_policy = None
        if isinstance(existing_policy, dict) and isinstance(payload.get("policy"), dict):
            payload["policy"] = {**payload["policy"], **existing_policy}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
