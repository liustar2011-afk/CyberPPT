"""Fidelity gates specific to reconstructed, editable SVG pages."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from .contracts import NormalizedFrame, page_gate


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _frame(payload: Mapping[str, Any]) -> NormalizedFrame | None:
    candidate = payload.get("frame")
    if isinstance(candidate, Mapping):
        return NormalizedFrame(**candidate)
    inventory = payload.get("inventory")
    if isinstance(inventory, Mapping) and isinstance(inventory.get("frame"), Mapping):
        return NormalizedFrame(**inventory["frame"])
    return None


def check_page_svg(svg: Path | str, inspection: Mapping[str, Any]) -> dict[str, Any]:
    """Reject flattening, missing script truth, and bad registered-layer evidence."""
    path = Path(svg).expanduser().resolve()
    errors: list[dict[str, Any]] = []
    if not path.is_file():
        return {"schema": "cyberppt.image_to_editable_svg.svg_quality.v1", "valid": False, "blocking_errors": [{"code": "svg_missing", "message": str(path)}]}
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError as exc:
        return {"schema": "cyberppt.image_to_editable_svg.svg_quality.v1", "valid": False, "blocking_errors": [{"code": "svg_xml_invalid", "message": str(exc)}]}
    frame = _frame(inspection)
    layers = list(inspection.get("layers", []))
    gate = page_gate(layers, frame=frame)
    errors.extend(gate["blocking_errors"])
    source = str(frame.normalized_path) if frame else ""
    images = [element for element in root.iter() if _local(element.tag) == "image"]
    if source and any(source in " ".join(element.attrib.values()) for element in images):
        errors.append({"code": "canonical_full_source_embedded", "message": "the canonical full page cannot be delivered as an SVG image layer"})
    text_values = {"".join(element.itertext()).strip() for element in root.iter() if _local(element.tag) == "text"}
    for layer in layers:
        if layer.get("family") == "text":
            truth = str(layer.get("truth_text") or "").strip()
            if not truth or truth not in text_values:
                errors.append({"code": "native_text_truth_missing", "region_id": layer.get("id"), "message": "approved script text is absent from SVG native text"})
        if layer.get("family") in {"scene", "source_graphic", "data_graphic"} and layer.get("status") != "manual_required":
            if not any(item.attrib.get("id") == str(layer.get("id")) for item in images):
                errors.append({"code": "visual_layer_missing", "region_id": layer.get("id"), "message": "verified visual layer is absent from SVG"})
    return {"schema": "cyberppt.image_to_editable_svg.svg_quality.v1", "svg": str(path), "valid": not errors, "blocking_errors": errors, "blocking_count": len(errors), "native_text": sorted(value for value in text_values if value)}
