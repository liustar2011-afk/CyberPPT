"""Validation contract for text embedded in source graphics during Quick reconstruction."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "cyberppt.image_to_pptx.graphic_text_policy.v1"
EXACT_FIDELITY_MODE = "exact_source_image"
_TREATMENTS = {"native_text", "preserved_in_image", "decorative_glyph"}


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _svg_text_nodes(path: Path) -> list[tuple[str, str]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    texts: list[tuple[str, str]] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "text":
            continue
        value = _normalize_text("".join(node.itertext()))
        if value:
            texts.append((_normalize_text(node.get("data-cyberppt-text-id")), value))
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bbox_key(value: object) -> tuple[float, float, float, float] | None:
    if not _valid_glyph_bbox(value):
        return None
    assert isinstance(value, list)
    return tuple(round(float(item), 3) for item in value)


def _validate_exact_inventory(
    policy: Mapping[str, Any],
    *,
    source_image: Path | str | None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Require a frozen, source-bound inventory before editable reconstruction.

    The inventory is deliberately independent of OCR. OCR is useful location
    evidence but cannot be the textual authority because it may contain wrong
    Chinese characters. A reviewer freezes the exact visible text and regions;
    the policy and authored SVG must then reproduce that inventory verbatim.
    """

    errors: list[dict[str, str]] = []
    raw_inventory = policy.get("source_text_inventory")
    if not isinstance(raw_inventory, list) or not raw_inventory:
        return ([{
            "code": "missing_source_text_inventory",
            "message": "exact reconstruction requires a non-empty frozen source_text_inventory",
        }], [])
    inventory = [dict(item) for item in raw_inventory if isinstance(item, Mapping)]
    if len(inventory) != len(raw_inventory):
        errors.append({"code": "invalid_source_text_inventory", "message": "inventory entries must be objects"})

    image_path = Path(source_image).expanduser().resolve() if source_image is not None else None
    declared_hash = _normalize_text(policy.get("source_image_sha256"))
    if image_path is None or not image_path.is_file():
        errors.append({"code": "missing_exact_source_image", "message": "exact reconstruction requires the audited source image"})
    elif not declared_hash or declared_hash != _sha256(image_path):
        errors.append({"code": "source_image_hash_mismatch", "message": "source_text_inventory is not bound to the audited source image bytes"})

    inventory_ids: set[str] = set()
    inventory_keys: list[tuple[str, str, tuple[float, float, float, float] | None]] = []
    for index, item in enumerate(inventory):
        item_id = _normalize_text(item.get("id"))
        text = _normalize_text(item.get("text") or item.get("observed_text"))
        bbox = _bbox_key(item.get("bbox"))
        if not item_id or item_id in inventory_ids or not text or bbox is None:
            errors.append({
                "code": "invalid_source_text_inventory_item",
                "message": f"inventory item {index + 1} requires a unique id, exact text and bounded source bbox",
            })
        inventory_ids.add(item_id)
        inventory_keys.append((item_id, text, bbox))

    policy_items = [dict(item) for item in policy.get("items", []) if isinstance(item, Mapping)]
    policy_keys = [
        (
            _normalize_text(item.get("id")),
            _normalize_text(item.get("text") or item.get("observed_text")),
            _bbox_key(item.get("bbox")),
        )
        for item in policy_items
        if item.get("source_visible") is not False
    ]
    if policy_keys != inventory_keys:
        errors.append({
            "code": "source_inventory_policy_mismatch",
            "message": "graphic_text_policy items must reproduce the frozen source inventory exactly, including order, text and bbox",
        })
    return errors, inventory


def validate_graphic_text_policy(
    policy: Mapping[str, Any] | None,
    *,
    authored_svg: Path | str,
    page_number: int,
    svg_text_values: list[str] | None = None,
    image_href_values: list[str] | None = None,
    source_image: Path | str | None = None,
    require_exact_fidelity: bool = False,
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

    exact_inventory: list[dict[str, Any]] = []
    if require_exact_fidelity or policy_value.get("fidelity_mode") == EXACT_FIDELITY_MODE:
        if policy_value.get("fidelity_mode") != EXACT_FIDELITY_MODE:
            errors.append({
                "code": "exact_fidelity_mode_required",
                "message": f"editable reconstruction requires fidelity_mode={EXACT_FIDELITY_MODE}",
            })
        exact_errors, exact_inventory = _validate_exact_inventory(
            policy_value,
            source_image=source_image,
        )
        errors.extend(exact_errors)

    raw_items = policy_value.get("items")
    items = list(raw_items) if isinstance(raw_items, list) else []
    if not isinstance(raw_items, list):
        errors.append({"code": "invalid_items", "message": "items must be a list"})
    seen_ids: set[str] = set()
    try:
        # Node ids are part of the text-policy identity contract.  Callers may
        # provide pre-parsed text/image evidence, but a plain string list cannot
        # disambiguate repeated copy, so retain ids from the authored SVG.
        svg_text_nodes = _svg_text_nodes(svg_path)
        svg_texts = [text for _node_id, text in svg_text_nodes]
        image_hrefs = (
            list(image_href_values)
            if image_href_values is not None
            else _svg_image_hrefs(svg_path)
        )
    except (OSError, ET.ParseError) as exc:
        errors.append({"code": "invalid_authored_svg", "message": str(exc)})
        svg_text_nodes, svg_texts, image_hrefs = [], [], []

    checked: list[dict[str, Any]] = []
    consumed_svg_texts: set[int] = set()
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
        if treatment == "native_text":
            if not _valid_glyph_bbox(item.get("bbox")):
                item_errors.append("native text requires a bounded source bbox")
            if item.get("source_visible") is not False and text:
                id_matches = [
                    node_index for node_index, (node_id, _value) in enumerate(svg_text_nodes)
                    if item_id and node_id == item_id
                ]
                text_matches = [
                    node_index for node_index, (_node_id, value) in enumerate(svg_text_nodes)
                    if value == text
                ]
                matches = id_matches or text_matches
                if len(matches) != 1:
                    item_errors.append("native text must match exactly one authored SVG text node")
                elif matches[0] in consumed_svg_texts:
                    item_errors.append("authored SVG text node is classified more than once")
                else:
                    consumed_svg_texts.add(matches[0])
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

    unclassified = [
        {"id": node_id or None, "text": text}
        for node_index, (node_id, text) in enumerate(svg_text_nodes)
        if node_index not in consumed_svg_texts
    ]
    if unclassified:
        errors.append(
            {
                "code": "unclassified_svg_text",
                "message": f"{len(unclassified)} authored SVG text node(s) are missing from graphic_text_policy",
            }
        )

    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": not errors,
        "status": policy_value.get("status"),
        "items": checked,
        "native_svg_texts": svg_texts,
        "fidelity_mode": policy_value.get("fidelity_mode"),
        "source_text_inventory_count": len(exact_inventory),
        "unclassified_svg_texts": unclassified,
        "image_layer_count": len(image_hrefs),
        "errors": errors,
    }
