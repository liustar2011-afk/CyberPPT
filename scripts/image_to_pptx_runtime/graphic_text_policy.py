"""Validation contract for text embedded in source graphics during Quick reconstruction."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "cyberppt.image_to_pptx.graphic_text_policy.v1"
_TREATMENTS = {"native_text", "preserved_in_image", "decorative_glyph"}


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _svg_texts(path: Path) -> list[str]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    texts: list[str] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "text":
            continue
        value = _normalize_text("".join(node.itertext()))
        if value:
            texts.append(value)
    return texts


def _svg_image_hrefs(path: Path) -> list[str]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    hrefs: list[str] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "image":
            continue
        href = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")
        if href:
            hrefs.append(href)
    return hrefs


def _has_image_evidence(authored_svg: Path, hrefs: list[str], asset_ref: object) -> bool:
    reference = str(asset_ref or "").strip()
    if not reference:
        return False
    if reference.startswith("data:"):
        return reference in hrefs
    candidate = (authored_svg.parent / reference).resolve()
    if not candidate.is_file():
        return False
    return any(
        href == reference or (authored_svg.parent / href).resolve() == candidate
        for href in hrefs
        if not href.startswith(("data:", "http:", "https:"))
    )


def _valid_glyph_bbox(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    try:
        left, top, right, bottom = (float(item) for item in value)
    except (TypeError, ValueError):
        return False
    return 0 <= left < right and 0 <= top < bottom


def validate_graphic_text_policy(
    policy: Mapping[str, Any] | None,
    *,
    authored_svg: Path | str,
    page_number: int,
) -> dict[str, Any]:
    """Validate the page-level embedded-graphic text treatment contract."""
    svg_path = Path(authored_svg).expanduser().resolve()
    errors: list[dict[str, str]] = []
    policy_value = dict(policy) if isinstance(policy, Mapping) else {}
    if policy_value.get("schema") != SCHEMA:
        errors.append({"code": "missing_or_invalid_schema", "message": f"expected {SCHEMA}"})
    if policy_value.get("status") != "complete":
        errors.append({"code": "policy_not_complete", "message": "graphic text classification is not complete"})
    if policy_value.get("empty_container_check") != "passed":
        errors.append({"code": "empty_container_check_failed", "message": "unresolved or empty text containers block delivery"})
    unresolved = policy_value.get("unresolved_empty_containers")
    if unresolved:
        errors.append({"code": "unresolved_empty_containers", "message": "policy lists unresolved empty containers"})

    raw_items = policy_value.get("items")
    items = list(raw_items) if isinstance(raw_items, list) else []
    if not isinstance(raw_items, list):
        errors.append({"code": "invalid_items", "message": "items must be a list"})
    seen_ids: set[str] = set()
    try:
        svg_texts = _svg_texts(svg_path)
        image_hrefs = _svg_image_hrefs(svg_path)
    except (OSError, ET.ParseError) as exc:
        errors.append({"code": "invalid_authored_svg", "message": str(exc)})
        svg_texts, image_hrefs = [], []

    checked: list[dict[str, Any]] = []
    for index, raw_item in enumerate(items):
        item = dict(raw_item) if isinstance(raw_item, Mapping) else {}
        item_id = _normalize_text(item.get("id")) or f"item-{index + 1:03d}"
        text = _normalize_text(item.get("text"))
        treatment = _normalize_text(item.get("treatment"))
        item_errors: list[str] = []
        if item_id in seen_ids:
            item_errors.append("duplicate item id")
        seen_ids.add(item_id)
        if not text and treatment != "decorative_glyph":
            item_errors.append("text is required")
        if treatment not in _TREATMENTS:
            item_errors.append("treatment must be native_text, preserved_in_image, or decorative_glyph")
        if treatment == "native_text" and text and not any(text in value for value in svg_texts):
            item_errors.append("exact text is missing from authored SVG")
        if treatment == "preserved_in_image" and not _has_image_evidence(svg_path, image_hrefs, item.get("asset_ref")):
            item_errors.append("preserved image text has no referenced local image layer")
        if treatment == "decorative_glyph":
            observed = _normalize_text(item.get("observed_text") or item.get("text"))
            review = item.get("visual_review")
            if not observed:
                item_errors.append("decorative glyph requires the OCR or visual observation")
            if not _valid_glyph_bbox(item.get("bbox")):
                item_errors.append("decorative glyph requires a bounded local region")
            if not isinstance(review, Mapping) or review.get("status") != "passed" or review.get("classification") != "non_semantic_glyph":
                item_errors.append("decorative glyph requires passed non_semantic_glyph visual review")
            if observed and any(observed in value for value in svg_texts):
                item_errors.append("decorative glyph must not be rebuilt as editable text")
        if item_errors:
            errors.append({"code": "invalid_item", "message": f"{item_id}: {'; '.join(item_errors)}"})
        checked.append({"id": item_id, "text": text, "treatment": treatment, "valid": not item_errors})

    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": not errors,
        "status": policy_value.get("status"),
        "items": checked,
        "native_svg_texts": svg_texts,
        "image_layer_count": len(image_hrefs),
        "errors": errors,
    }
