"""Validation for the mandatory text-free base in editable Stage 02 pages."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageChops, ImageDraw


SCHEMA = "cyberppt.stage02.clean_base.v3"
ALGORITHM_VERSION = "masked-text-clearance-v3"
VISUAL_DIFF_SCHEMA = "cyberppt.stage02.clean_base.visual_diff.v2"
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
    "no_abnormal_solid_blocks",
}
_PIXEL_DIFF_THRESHOLD = 2


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


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def graphic_text_policy_sha256(policy: Mapping[str, Any] | None) -> str:
    """Hash the complete graphic-text policy used to declare the masks."""

    return _json_sha256(dict(policy) if isinstance(policy, Mapping) else {})


def _count_pixels(mask: Image.Image) -> int:
    return sum(1 for value in mask.get_flattened_data() if value)


def _clearance_box(
    region: Mapping[str, Any],
    *,
    width: int,
    height: int,
    padding: int,
) -> tuple[int, int, int, int] | None:
    explicit = _region_bbox(
        {"bbox": region.get("clearance_bbox")}, width=width, height=height
    )
    if explicit is not None:
        return explicit
    bbox = _region_bbox(region, width=width, height=height)
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    return (
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    )


def _changed_components(
    changed: Image.Image,
    box: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    """Describe connected changed regions inside one declared clearance mask."""

    crop = changed.crop(box)
    width, height = crop.size
    if width <= 0 or height <= 0:
        return []
    binary = bytearray(1 if value else 0 for value in crop.get_flattened_data())
    seen = bytearray(len(binary))
    components: list[dict[str, Any]] = []
    for start, value in enumerate(binary):
        if not value or seen[start]:
            continue
        seen[start] = 1
        queue = [start]
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width
        while queue:
            current = queue.pop()
            x, y = current % width, current // width
            count += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            neighbours = (
                current - 1 if x else -1,
                current + 1 if x + 1 < width else -1,
                current - width if y else -1,
                current + width if y + 1 < height else -1,
            )
            for neighbour in neighbours:
                if neighbour >= 0 and binary[neighbour] and not seen[neighbour]:
                    seen[neighbour] = 1
                    queue.append(neighbour)
        component_width = max_x - min_x + 1
        component_height = max_y - min_y + 1
        components.append(
            {
                "pixels": count,
                "bbox": [
                    box[0] + min_x,
                    box[1] + min_y,
                    box[0] + max_x + 1,
                    box[1] + max_y + 1,
                ],
                "fill_ratio": round(count / (component_width * component_height), 4),
            }
        )
    return components


def compute_visual_diff_report(
    full_path: Path | str,
    base_path: Path | str,
    regions: list[Mapping[str, Any]],
    *,
    padding: int = 0,
    max_outside_fraction: float = 0.0,
    source_sha256: str | None = None,
    clean_base_sha256: str | None = None,
    policy_sha256: str | None = None,
) -> dict[str, Any]:
    """Recompute clean-base integrity from pixels and declared masks.

    The manifest receipt is evidence about the run, never the source of truth.
    This function intentionally treats a large solid connected change as a
    likely container whiteout, even when its manifest claims that the page
    passed.
    """

    full_file = Path(full_path).expanduser().resolve()
    base_file = Path(base_path).expanduser().resolve()
    report: dict[str, Any] = {
        "schema": VISUAL_DIFF_SCHEMA,
        "qa_origin": "computed",
        "algorithm_version": ALGORITHM_VERSION,
        "source_sha256": source_sha256 or (_sha256(full_file) if full_file.is_file() else ""),
        "clean_base_sha256": clean_base_sha256 or (_sha256(base_file) if base_file.is_file() else ""),
        "graphic_text_policy_sha256": policy_sha256 or "",
        "checks": {
            "text_removal": "failed",
            "background_continuity": "failed",
            "outside_mask_preserved": "failed",
            "no_abnormal_solid_blocks": "failed",
        },
        "metrics": {},
    }
    if not full_file.is_file() or not base_file.is_file():
        report["status"] = "failed"
        report["error"] = "full image or clean base is missing"
        return report
    try:
        with Image.open(full_file) as full_raw, Image.open(base_file) as base_raw:
            full = full_raw.convert("RGB")
            base = base_raw.convert("RGB")
    except OSError as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        return report
    if full.size != base.size:
        report["status"] = "failed"
        report["error"] = "full image and clean base must share a canvas"
        return report

    boxes: list[tuple[int, int, int, int]] = []
    invalid_regions = 0
    mask = Image.new("L", full.size, 0)
    draw = ImageDraw.Draw(mask)
    for region in regions:
        box = _clearance_box(region, width=full.width, height=full.height, padding=padding)
        if box is None:
            invalid_regions += 1
            continue
        boxes.append(box)
        draw.rectangle(box, fill=255)

    difference = ImageChops.difference(full, base)
    changed = difference.convert("L").point(
        lambda pixel: 255 if pixel > _PIXEL_DIFF_THRESHOLD else 0
    )
    changed_total = _count_pixels(changed)
    changed_inside = _count_pixels(ImageChops.multiply(changed, mask))
    outside_changed = _count_pixels(ImageChops.subtract(changed, mask))
    outside_fraction = outside_changed / changed_total if changed_total else 0.0
    region_metrics: list[dict[str, Any]] = []
    abnormal_blocks: list[dict[str, Any]] = []
    changed_region_count = 0
    for index, box in enumerate(boxes):
        left, top, right, bottom = box
        region_area = (right - left) * (bottom - top)
        region_changed = _count_pixels(changed.crop(box))
        changed_region_count += int(region_changed > 0)
        components = _changed_components(changed, box)
        large_components = [
            component
            for component in components
            if component["pixels"] >= max(64, int(region_area * 0.15))
            and component["fill_ratio"] >= 0.78
        ]
        for component in large_components:
            abnormal_blocks.append({"region_index": index, **component})
        region_metrics.append(
            {
                "index": index,
                "clearance_bbox": list(box),
                "area": region_area,
                "changed_pixels": region_changed,
                "changed_fraction": round(region_changed / region_area, 6) if region_area else 1.0,
                "component_count": len(components),
                "abnormal_solid_blocks": large_components,
            }
        )

    text_removal = bool(boxes) and invalid_regions == 0 and changed_region_count == len(boxes)
    outside_ok = outside_fraction <= max_outside_fraction
    no_blocks = not abnormal_blocks
    report["checks"] = {
        "text_removal": "passed" if text_removal else "failed",
        "background_continuity": "passed" if text_removal and no_blocks else "failed",
        "outside_mask_preserved": "passed" if outside_ok else "failed",
        "no_abnormal_solid_blocks": "passed" if no_blocks else "failed",
    }
    report["metrics"] = {
        "canvas": list(full.size),
        "declared_region_count": len(regions),
        "valid_clearance_region_count": len(boxes),
        "changed_pixels": changed_total,
        "changed_pixels_inside_mask": changed_inside,
        "changed_pixels_outside_mask": outside_changed,
        "outside_changed_fraction": round(outside_fraction, 8),
        "max_outside_changed_fraction": max_outside_fraction,
        "changed_regions": changed_region_count,
        "abnormal_solid_block_count": len(abnormal_blocks),
        "regions": region_metrics,
    }
    report["status"] = "passed" if all(
        value == "passed" for value in report["checks"].values()
    ) else "failed"
    return report


def _valid_visual_receipt(
    report: object,
    *,
    source_sha256: str,
    clean_base_sha256: str,
    policy_sha256: str,
) -> bool:
    """Accept only a computed, fully bound visual and OCR receipt.

    A manifest receipt is useful evidence for recovery, but its claims must
    retain the provenance and input bindings produced by this runtime.  The
    pixel report is still recomputed by callers; this helper prevents a
    hand-written ``status=passed`` receipt from becoming a reusable
    checkpoint.
    """

    if not isinstance(report, Mapping):
        return False
    if (
        report.get("schema") != VISUAL_DIFF_SCHEMA
        or report.get("qa_origin") != "computed"
        or report.get("algorithm_version") != ALGORITHM_VERSION
        or report.get("status") != "passed"
        or report.get("source_sha256") != source_sha256
        or report.get("clean_base_sha256") != clean_base_sha256
        or report.get("graphic_text_policy_sha256") != policy_sha256
    ):
        return False
    checks = report.get("checks")
    if not isinstance(checks, Mapping) or any(
        checks.get(name) != "passed" for name in _REQUIRED_VISUAL_CHECKS
    ):
        return False
    post_ocr = report.get("post_clean_ocr")
    return (
        isinstance(post_ocr, Mapping)
        and post_ocr.get("executed") is True
        and post_ocr.get("status") == "passed"
        and post_ocr.get("residual") == []
    )


def is_reusable_clean_base(
    clean_base: Mapping[str, Any] | None,
    *,
    full_image: Path | str,
    graphic_text_policy: Mapping[str, Any] | None,
) -> bool:
    """Allow reuse only after current-pixel and binding checks pass."""

    if not isinstance(clean_base, Mapping):
        return False
    base_path = Path(str(clean_base.get("path") or "")).expanduser().resolve()
    full_path = Path(full_image).expanduser().resolve()
    if (
        clean_base.get("schema") != SCHEMA
        or clean_base.get("status") != "complete"
        or clean_base.get("algorithm_version") != ALGORITHM_VERSION
        or not base_path.is_file()
        or not full_path.is_file()
    ):
        return False
    full_hash = _sha256(full_path)
    base_hash = _sha256(base_path)
    policy_hash = graphic_text_policy_sha256(graphic_text_policy)
    if (
        clean_base.get("source_sha256") != full_hash
        or clean_base.get("sha256") != base_hash
        or clean_base.get("graphic_text_policy_sha256") != policy_hash
    ):
        return False
    regions = [
        dict(item)
        for item in clean_base.get("cleaned_text_regions", [])
        if isinstance(item, Mapping)
    ]
    try:
        padding = int(clean_base.get("clearance_padding_px") or 0)
        max_outside = float(clean_base.get("max_outside_mask_changed_fraction") or 0)
    except (TypeError, ValueError):
        return False
    if padding < 0 or not 0 <= max_outside <= 1:
        return False
    actual = compute_visual_diff_report(
        full_path,
        base_path,
        regions,
        padding=padding,
        max_outside_fraction=max_outside,
        source_sha256=full_hash,
        clean_base_sha256=base_hash,
        policy_sha256=policy_hash,
    )
    receipt = clean_base.get("visual_diff_report")
    return (
        actual["status"] == "passed"
        and _valid_visual_receipt(
            receipt,
            source_sha256=full_hash,
            clean_base_sha256=base_hash,
            policy_sha256=policy_hash,
        )
        and isinstance(receipt, Mapping)
        and isinstance(receipt.get("checks"), Mapping)
        and {
            name: receipt["checks"].get(name)
            for name in _REQUIRED_VISUAL_CHECKS
        }
        == actual.get("checks")
        and receipt.get("metrics") == actual.get("metrics")
    )


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

    if value.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append({"code": "invalid_clean_base_algorithm", "message": f"expected {ALGORITHM_VERSION}"})
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
        errors.append({"code": "clean_base_visual_review_incomplete", "message": "review must pass text removal, continuity, protected-area and solid-block checks"})
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
    try:
        declared_padding = int(value.get("clearance_padding_px", 6))
    except (TypeError, ValueError):
        declared_padding = 0
        errors.append({"code": "invalid_clean_base_diff_tolerance", "message": "clearance padding and outside-mask tolerance are invalid"})
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
            clearance = _clearance_box(
                region,
                width=full_size[0],
                height=full_size[1],
                padding=declared_padding,
            ) if full_size else None
            if clearance is None:
                errors.append({"code": "invalid_clearance_mask", "message": f"{policy_id or _text(region.get('text'))}: an explicit bounded clearance mask is required"})
            else:
                if not (
                    clearance[0] <= bbox[0]
                    and clearance[1] <= bbox[1]
                    and clearance[2] >= bbox[2]
                    and clearance[3] >= bbox[3]
                ):
                    errors.append({"code": "clearance_mask_does_not_cover_text", "message": f"{policy_id or _text(region.get('text'))}: clearance mask must contain the declared text bbox"})
                region_boxes.append(clearance)
    missing = sorted(native - cleaned)
    if missing:
        errors.append({"code": "native_text_not_cleaned", "message": "native text absent from cleaned_text_regions: " + ", ".join(missing)})
    for policy_id, text in native_by_id.items():
        region = regions_by_policy_id.get(policy_id)
        if region is None or _text(region.get("text")) != text:
            errors.append({"code": "native_text_has_no_exact_clearance_region", "message": f"{policy_id}: native text requires one exact, bounded clearance region"})

    expected_policy_hash = graphic_text_policy_sha256(policy)
    if value.get("graphic_text_policy_sha256") != expected_policy_hash:
        errors.append({"code": "clean_base_policy_mismatch", "message": "clean base is not bound to the current graphic-text policy"})
    if isinstance(visual, Mapping):
        if visual.get("schema") != VISUAL_DIFF_SCHEMA:
            errors.append({"code": "clean_base_visual_receipt_schema_invalid", "message": f"expected {VISUAL_DIFF_SCHEMA}"})
        if visual.get("qa_origin") != "computed":
            errors.append({"code": "clean_base_visual_receipt_not_computed", "message": "visual-difference receipt must be produced by the runtime computation"})
        expected_full_hash = _sha256(full_path) if full_path.is_file() else ""
        expected_base_hash = _sha256(base_path) if base_path is not None and base_path.is_file() else ""
        for field, expected in (
            ("algorithm_version", ALGORITHM_VERSION),
            ("source_sha256", expected_full_hash),
            ("clean_base_sha256", expected_base_hash),
            ("graphic_text_policy_sha256", expected_policy_hash),
        ):
            if visual.get(field) != expected:
                errors.append({"code": "clean_base_visual_receipt_mismatch", "message": f"visual-difference receipt field {field} does not match current inputs"})
        post_ocr = visual.get("post_clean_ocr")
        if not isinstance(post_ocr, Mapping) or post_ocr.get("executed") is not True:
            errors.append({"code": "post_clean_ocr_not_executed", "message": "post-clean OCR must be executed and recorded"})
        elif post_ocr.get("status") != "passed" or post_ocr.get("residual") != []:
            errors.append({"code": "post_clean_ocr_failed", "message": "post-clean OCR detected residual text or did not pass"})

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
            actual_visual = compute_visual_diff_report(
                full_path,
                base_path,
                cleaned_items,
                padding=padding,
                max_outside_fraction=max_outside,
                source_sha256=_sha256(full_path),
                clean_base_sha256=_sha256(base_path),
                policy_sha256=expected_policy_hash,
            )
            receipt_checks = (
                {
                    name: visual.get("checks", {}).get(name)
                    for name in _REQUIRED_VISUAL_CHECKS
                }
                if isinstance(visual, Mapping) and isinstance(visual.get("checks"), Mapping)
                else None
            )
            if isinstance(visual, Mapping) and (
                receipt_checks != actual_visual.get("checks")
                or visual.get("metrics") != actual_visual.get("metrics")
            ):
                errors.append({"code": "clean_base_visual_receipt_stale", "message": "visual-difference receipt does not match the current pixel computation"})
            if actual_visual["status"] != "passed":
                failed_checks = [
                    key for key, result in actual_visual.get("checks", {}).items()
                    if result != "passed"
                ]
                if "text_removal" in failed_checks:
                    errors.append({"code": "cleaned_region_has_no_pixel_change", "message": "every declared text-removal region must alter the full image"})
                if "outside_mask_preserved" in failed_checks:
                    fraction = actual_visual.get("metrics", {}).get("outside_changed_fraction", "unknown")
                    errors.append({"code": "clean_base_changes_outside_clearance_mask", "message": f"{fraction} of changed pixels fall outside declared clearance regions"})
                if "no_abnormal_solid_blocks" in failed_checks:
                    errors.append({"code": "clean_base_abnormal_solid_block", "message": "clean base contains a large solid changed block inside a text mask"})
                if "background_continuity" in failed_checks:
                    errors.append({"code": "clean_base_background_continuity_failed", "message": "clean-base background continuity check failed"})
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
