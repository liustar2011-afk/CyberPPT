"""Validation for the mandatory text-free base in editable Stage 02 pages."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageChops, ImageDraw


SCHEMA = "cyberppt.stage02.clean_base.v2"
_REMOVAL_METHODS = {
    "flat-surface-rebuild",
    "local-background-reconstruction",
    "masked-inpainting",
    "reference-image-reconstruction",
}
_REQUIRED_VISUAL_CHECKS = {
    "text_removal",
    "background_continuity",
    "outside_mask_preserved",
}


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, *, parent: Path) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return (candidate if candidate.is_absolute() else parent / candidate).resolve()


def _image_hrefs(svg_path: Path) -> list[str]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    return [
        href
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "image"
        for href in [node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")]
        if href
    ]


def _region_bbox(value: Mapping[str, Any], *, width: int, height: int) -> tuple[int, int, int, int] | None:
    raw = value.get("bbox")
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    try:
        left, top, right, bottom = (int(round(float(item))) for item in raw)
    except (TypeError, ValueError):
        return None
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        return None
    return left, top, right, bottom


def _changed_pixels_within_regions(
    full_path: Path,
    base_path: Path,
    regions: list[tuple[int, int, int, int]],
    *,
    padding: int,
    max_outside_fraction: float,
) -> tuple[list[int], float]:
    """Return changed-pixel evidence without trusting a self-reported review."""

    with Image.open(full_path) as full_raw, Image.open(base_path) as base_raw:
        full = full_raw.convert("RGB")
        base = base_raw.convert("RGB")
    difference = ImageChops.difference(full, base)
    changed = difference.convert("L").point(lambda pixel: 255 if pixel > 2 else 0)
    changed_total = sum(1 for value in changed.get_flattened_data() if value)
    region_counts: list[int] = []
    mask = Image.new("L", full.size, 0)
    draw = ImageDraw.Draw(mask)
    for left, top, right, bottom in regions:
        draw.rectangle(
            (
                max(0, left - padding),
                max(0, top - padding),
                min(full.width, right + padding),
                min(full.height, bottom + padding),
            ),
            fill=255,
        )
        region_counts.append(sum(1 for value in changed.crop((left, top, right, bottom)).get_flattened_data() if value))
    outside = ImageChops.subtract(changed, mask)
    outside_changed = sum(1 for value in outside.get_flattened_data() if value)
    outside_fraction = outside_changed / changed_total if changed_total else 1.0
    if outside_fraction > max_outside_fraction:
        return region_counts, outside_fraction
    return region_counts, outside_fraction


def validate_clean_base(
    clean_base: Mapping[str, Any] | None,
    *,
    full_image: Path | str,
    authored_svg: Path | str,
    graphic_text_policy: Mapping[str, Any] | None,
    page_number: int,
    image_hrefs: list[str] | None = None,
) -> dict[str, Any]:
    """Require a distinct text-free base and native reconstruction of its text."""

    full_path = Path(full_image).expanduser().resolve()
    svg_path = Path(authored_svg).expanduser().resolve()
    value = dict(clean_base) if isinstance(clean_base, Mapping) else {}
    errors: list[dict[str, str]] = []
    if value.get("schema") != SCHEMA:
        errors.append({"code": "invalid_clean_base_schema", "message": f"expected {SCHEMA}"})
    if value.get("status") != "complete":
        errors.append({"code": "clean_base_not_complete", "message": "text-free base preparation is incomplete"})
    base_path = _path(value.get("path"), parent=svg_path.parent)
    if base_path is None or not base_path.is_file():
        errors.append({"code": "clean_base_missing", "message": "clean-base asset is missing"})
    if not full_path.is_file():
        errors.append({"code": "full_image_missing", "message": "audited full image is missing"})

    if full_path.is_file() and value.get("source_sha256") != _sha256(full_path):
        errors.append({"code": "clean_base_source_mismatch", "message": "clean base is not bound to the audited full image"})
    base_size: tuple[int, int] | None = None
    if base_path is not None and base_path.is_file():
        base_hash = _sha256(base_path)
        if value.get("sha256") != base_hash:
            errors.append({"code": "clean_base_hash_mismatch", "message": "clean-base hash does not match the asset"})
        if full_path.is_file() and (base_path == full_path or base_hash == _sha256(full_path)):
            errors.append({"code": "full_image_as_clean_base", "message": "audited full image cannot be the delivered base layer"})
        try:
            base_size = Image.open(base_path).size
            if full_path.is_file() and base_size != Image.open(full_path).size:
                errors.append({"code": "clean_base_canvas_mismatch", "message": "clean base must retain the full-image canvas"})
        except OSError as exc:
            errors.append({"code": "clean_base_unreadable", "message": str(exc)})

    if value.get("removal_scope") != "native_text_only":
        errors.append({"code": "invalid_removal_scope", "message": "clean base may remove only text declared native_text"})
    visual = value.get("visual_diff_report")
    if not isinstance(visual, Mapping) or visual.get("status") != "passed":
        errors.append({"code": "clean_base_visual_review_failed", "message": "clean-base visual-difference review must pass"})
    elif not _REQUIRED_VISUAL_CHECKS.issubset(
        {str(key) for key, result in visual.get("checks", {}).items() if result == "passed"}
        if isinstance(visual.get("checks"), Mapping)
        else set()
    ):
                errors.append({"code": "clean_base_visual_review_incomplete", "message": "review must pass text removal, continuity, and protected-area checks"})
    raw_regions = value.get("cleaned_text_regions")
    if not isinstance(raw_regions, list):
        errors.append({"code": "invalid_cleaned_text_regions", "message": "cleaned_text_regions must be a list"})
        raw_regions = []
    cleaned_items = [dict(item) for item in raw_regions if isinstance(item, Mapping)]
    cleaned = {_text(item.get("text")) for item in cleaned_items if _text(item.get("text"))}
    policy = dict(graphic_text_policy) if isinstance(graphic_text_policy, Mapping) else {}
    items = [dict(item) for item in policy.get("items", []) if isinstance(item, Mapping)]
    native = {
        _text(item.get("text"))
        for item in items
        if _text(item.get("treatment")) == "native_text"
        and item.get("source_visible") is not False
        and _text(item.get("text"))
    }
    native_by_id = {
        _text(item.get("id")): _text(item.get("text"))
        for item in items
        if _text(item.get("treatment")) == "native_text"
        and item.get("source_visible") is not False
        and _text(item.get("id"))
        and _text(item.get("text"))
    }
    policy_treatment_by_id = {
        _text(item.get("id")): _text(item.get("treatment"))
        for item in items
        if _text(item.get("id"))
    }
    full_size = Image.open(full_path).size if full_path.is_file() else None
    regions_by_policy_id: dict[str, dict[str, Any]] = {}
    region_boxes: list[tuple[int, int, int, int]] = []
    for region in cleaned_items:
        policy_id = _text(region.get("policy_id"))
        method = _text(region.get("method"))
        if policy_id in regions_by_policy_id:
            errors.append({"code": "duplicate_cleaned_text_region", "message": f"duplicate clean-base region for {policy_id}"})
        regions_by_policy_id[policy_id] = region
        if policy_treatment_by_id.get(policy_id) != "native_text":
            errors.append({"code": "non_native_text_removed", "message": f"{policy_id or _text(region.get('text'))}: only native_text may be removed from the clean base"})
        if method not in _REMOVAL_METHODS:
            errors.append({"code": "unsupported_text_removal_method", "message": f"{policy_id or _text(region.get('text'))}: use a local background repair method, not whiteout"})
        bbox = _region_bbox(region, width=full_size[0], height=full_size[1]) if full_size else None
        if bbox is None:
            errors.append({"code": "invalid_cleaned_text_bbox", "message": f"{policy_id or _text(region.get('text'))}: a bounded text-removal region is required"})
        else:
            region_boxes.append(bbox)
    missing = sorted(native - cleaned)
    if missing:
        errors.append({"code": "native_text_not_cleaned", "message": "native text absent from cleaned_text_regions: " + ", ".join(missing)})
    for policy_id, text in native_by_id.items():
        region = regions_by_policy_id.get(policy_id)
        if region is None or _text(region.get("text")) != text:
            errors.append({"code": "native_text_has_no_exact_clearance_region", "message": f"{policy_id}: native text requires one exact, bounded clearance region"})

    if full_path.is_file() and base_path is not None and base_path.is_file() and full_size and len(region_boxes) == len(cleaned_items):
        padding = value.get("clearance_padding_px", 6)
        max_outside = value.get("max_outside_mask_changed_fraction", 0.01)
        try:
            padding = int(padding)
            max_outside = float(max_outside)
            if padding < 0 or not 0 <= max_outside <= 1:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"code": "invalid_clean_base_diff_tolerance", "message": "clearance padding and outside-mask tolerance are invalid"})
        else:
            changed_counts, outside_fraction = _changed_pixels_within_regions(
                full_path, base_path, region_boxes, padding=padding, max_outside_fraction=max_outside
            )
            if any(count == 0 for count in changed_counts):
                errors.append({"code": "cleaned_region_has_no_pixel_change", "message": "every declared text-removal region must alter the full image"})
            if outside_fraction > max_outside:
                errors.append({"code": "clean_base_changes_outside_clearance_mask", "message": f"{outside_fraction:.4f} of changed pixels fall outside declared clearance regions"})
    for item in items:
        if _text(item.get("treatment")) != "preserved_in_image":
            continue
        if item.get("identity_integral") is not True:
            errors.append({"code": "preserved_text_not_identity_integral", "message": f"{_text(item.get('id')) or _text(item.get('text'))}: preserved image text requires identity_integral=true"})
        asset = _path(item.get("asset_ref"), parent=svg_path.parent)
        if asset is not None and (asset == full_path or asset == base_path):
            errors.append({"code": "preserved_text_uses_page_layer", "message": "preserved image text cannot use the full image or clean base"})

    if image_hrefs is None:
        try:
            hrefs = _image_hrefs(svg_path)
        except (OSError, ET.ParseError) as exc:
            errors.append({"code": "invalid_authored_svg", "message": str(exc)})
            hrefs = []
    else:
        hrefs = list(image_hrefs)
    if base_path is not None and base_path.is_file() and not any(
        not href.startswith(("data:", "http:", "https:")) and _path(href, parent=svg_path.parent) == base_path
        for href in hrefs
    ):
        errors.append({"code": "clean_base_not_referenced", "message": "authored SVG does not reference the declared clean base"})
    return {"schema": SCHEMA, "page_number": page_number, "valid": not errors, "errors": errors, "cleaned_text": sorted(cleaned), "native_text": sorted(native)}
