"""Semantic PowerPoint selection pane names for SVG-derived objects."""

from __future__ import annotations

import hashlib
import re
from xml.etree import ElementTree as ET


MAX_NAME_LEN = 80


def _tokenize(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    token = re.sub(r"_+", "_", token)
    return token.lower()


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def _page_token(page_id: str | None) -> str:
    token = _tokenize(page_id or "")
    if token:
        return token.upper()
    return "P"


def _fallback_name(fallback_kind: str, shape_id: int) -> str:
    labels = {
        "arc": "Arc",
        "crop": "Image",
        "ellipse": "Ellipse",
        "freeform": "Freeform",
        "group": "Group",
        "image": "Image",
        "line": "Line",
        "path": "Freeform",
        "polygon": "Polygon",
        "polyline": "Polyline",
        "rect": "Rectangle",
        "shape": "Shape",
        "text": "TextBox",
    }
    return f"{labels.get(fallback_kind, fallback_kind.title())} {shape_id}"


def _pick_semantic(elem: ET.Element, fallback_kind: str) -> tuple[str, str] | None:
    if elem.get("data-text-region-id"):
        return "text", elem.get("data-text-region-id", "")
    if elem.get("data-chain-connector"):
        return "connector", elem.get("data-chain-connector", "")
    if elem.get("data-icon-id"):
        return "icon", elem.get("data-icon-id", "")
    if elem.get("data-crop-id"):
        return "crop", elem.get("data-crop-id", "")
    if elem.get("data-crop-role"):
        return "crop", elem.get("data-crop-role", "")
    if elem.get("data-zone-id"):
        primitive = elem.get("data-primitive", "")
        zone = elem.get("data-zone-id", "")
        suffix = f"{zone}_{primitive}" if primitive else zone
        return "zone", suffix
    if elem.get("data-primitive"):
        return "shape", elem.get("data-primitive", "")
    if elem.get("id"):
        return fallback_kind, elem.get("id", "")
    return None


def has_semantic_name_source(elem: ET.Element) -> bool:
    """Return whether *elem* carries an attribute worth preserving as a group."""
    return any(
        elem.get(attr)
        for attr in (
            "data-text-region-id",
            "data-icon-id",
            "data-zone-id",
            "data-primitive",
            "data-chain-connector",
            "data-crop-id",
            "data-crop-role",
        )
    )


def semantic_shape_name(
    elem: ET.Element,
    fallback_kind: str,
    shape_id: int,
    *,
    page_id: str | None = None,
) -> str:
    """Build a stable, ASCII-safe PowerPoint selection pane name.

    Semantic SVG metadata wins; unannotated elements keep the historical
    PowerPoint-style fallback names to avoid noisy churn.
    """
    semantic = _pick_semantic(elem, fallback_kind)
    if semantic is None:
        return _fallback_name(fallback_kind, shape_id)

    object_kind, raw_value = semantic
    value_token = _tokenize(raw_value)
    if not value_token:
        value_token = _short_hash(raw_value or f"{fallback_kind}:{shape_id}")

    name = f"{_page_token(page_id)}_{object_kind}_{value_token}"
    if len(name) <= MAX_NAME_LEN:
        return name

    suffix = _short_hash(name)
    keep = MAX_NAME_LEN - len(suffix) - 1
    return f"{name[:keep].rstrip('_')}_{suffix}"


def uniquify_selection_name(name: str, counts: dict[str, int]) -> str:
    """Return *name* or a suffixed variant unique within the current slide."""
    current = counts.get(name, 0) + 1
    counts[name] = current
    if current == 1:
        return name

    suffix = f"_{current}"
    if len(name) + len(suffix) <= MAX_NAME_LEN:
        return f"{name}{suffix}"
    return f"{name[:MAX_NAME_LEN - len(suffix)].rstrip('_')}{suffix}"
