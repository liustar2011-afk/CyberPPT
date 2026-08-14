"""Inspectable, fail-closed reconstruction of one canonical page frame."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import NormalizedFrame, build_inventory, layer_record, page_gate


def _bbox(value: Any, *, canvas: tuple[int, int]) -> list[float]:
    if isinstance(value, Mapping):
        values = [value.get(key) for key in ("x", "y", "width", "height")]
    else:
        values = value if isinstance(value, (list, tuple)) else None
    if values is None or len(values) != 4:
        return [0.0, 0.0, float(canvas[0]), float(canvas[1])]
    try:
        return [float(item) for item in values]
    except (TypeError, ValueError):
        return [0.0, 0.0, float(canvas[0]), float(canvas[1])]


def _ocr_items(layout: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not layout:
        return []
    values = layout.get("items", layout.get("regions", []))
    return [dict(item) for item in values if isinstance(item, Mapping)] if isinstance(values, list) else []


def _normal_text(value: Any) -> str:
    return "".join(str(value or "").split()).casefold()


def _match_ocr(script_text: str, items: list[dict[str, Any]], used: set[int]) -> tuple[int | None, dict[str, Any] | None]:
    expected = _normal_text(script_text)
    for index, item in enumerate(items):
        if index in used:
            continue
        observed = _normal_text(item.get("text", item.get("content", "")))
        if expected and observed and (expected == observed or expected in observed or observed in expected):
            return index, item
    return None, None


def _classify_region(region: Mapping[str, Any]) -> str:
    family = str(region.get("family") or region.get("type") or "").strip().lower()
    aliases = {"shape": "simple_geometry", "geometry": "simple_geometry", "graphic": "source_graphic", "logo": "source_graphic", "chart": "data_graphic", "table": "data_graphic", "illustration": "scene", "image": "scene"}
    return aliases.get(family, family if family in {"text", "simple_geometry", "source_graphic", "data_graphic", "scene"} else "unknown")


def require_verified_region(region: dict[str, Any]) -> None:
    """Mark data/identity regions unresolved unless their exact source is verified."""
    family = region.get("family")
    verified = bool(region.get("identity_verified") or region.get("data_verified") or region.get("verified"))
    if family in {"data_graphic", "source_graphic"} and not verified:
        region.update(realization="manual_required", status="manual_required", reason="unverified_identity_or_data")


def inspect_page(
    frame: NormalizedFrame,
    *,
    script_text: Iterable[str] | None = None,
    ocr_layout: Mapping[str, Any] | None = None,
    regions: Iterable[Mapping[str, Any]] | None = None,
    visual_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind script text to OCR coordinates and inventory all supplied visual regions.

    OCR text is never copied into the reconstructed page: it provides a bbox
    only.  Callers must supply visual-registry regions (or explicit regions) to
    claim a graphic is safe to reproduce.
    """
    ocr = _ocr_items(ocr_layout)
    used: set[int] = set()
    observed_regions: list[dict[str, Any]] = []
    layers: list[dict[str, Any]] = []
    for index, truth in enumerate(script_text or []):
        ocr_index, item = _match_ocr(str(truth), ocr, used)
        if ocr_index is not None:
            used.add(ocr_index)
        bbox = _bbox((item or {}).get("bbox"), canvas=frame.pixel_size)
        region = {"id": f"text-{index:03d}", "family": "text", "bbox": bbox, "z_index": 1000 + index, "observed_text": (item or {}).get("text"), "truth_text": str(truth), "truth_source": "script", "locator_source": "ocr" if item else "none", "status": "verified" if item else "manual_required", "realization": "native_text" if item else "manual_required"}
        if item is None:
            region["reason"] = "missing_text_locator"
        observed_regions.append(region)
        layers.append(layer_record(region, frame=frame, index=len(layers)))

    supplied: list[Mapping[str, Any]] = list(regions or [])
    if visual_registry and isinstance(visual_registry.get("elements"), list):
        supplied.extend(item for item in visual_registry["elements"] if isinstance(item, Mapping))
    for index, raw in enumerate(supplied):
        family = _classify_region(raw)
        region = dict(raw)
        region.update({"id": str(raw.get("id") or f"visual-{index:03d}"), "family": family, "bbox": _bbox(raw.get("bbox", raw.get("blueprint_bbox_px")), canvas=frame.pixel_size), "z_index": int(raw.get("z_index", index + 10))})
        if family == "text":
            # Unapproved text in a visual registry cannot become slide copy.
            region.update(realization="manual_required", status="manual_required", reason="unbound_text_truth")
        elif family == "simple_geometry":
            region.update(realization="native_geometry", status="verified")
        elif family == "scene":
            region.setdefault("realization", "registered_layer")
            region.setdefault("status", "pending")
        else:
            require_verified_region(region)
            if region.get("realization") != "manual_required":
                if not (region.get("asset_path") or region.get("source_asset") or region.get("path")):
                    region.update(realization="manual_required", status="manual_required", reason="verified_graphic_asset_missing")
                else:
                    region.setdefault("realization", "exact_asset")
                    region.setdefault("status", "verified")
        region.setdefault("source_page", frame.page_number)
        region.setdefault("source_region", region["id"])
        observed_regions.append(region)
        layers.append(layer_record(region, frame=frame, index=len(layers)))

    layers = prepare_scene_layers(frame, layers)
    inventory = build_inventory(frame, observed_regions)
    gate = page_gate(layers, frame=frame)
    manual = [item for item in layers if item.get("status") == "manual_required" or item.get("realization") == "manual_required"]
    return {"schema": "cyberppt.image_to_editable_svg.inspection.v1", "frame": frame.to_dict(), "inventory": inventory, "layers": sorted(layers, key=lambda item: (int(item.get("z_index", 0)), str(item["id"]))), "page_gate": gate, "manual_required": manual}


def prepare_scene_layers(frame: NormalizedFrame, regions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Assign registered canvas evidence and deterministic shared-plate groups."""
    prepared: list[dict[str, Any]] = []
    for index, raw in enumerate(regions):
        layer = dict(raw)
        if layer.get("family") == "scene" and layer.get("status") != "manual_required":
            layer.setdefault("realization", "shared_plate" if layer.get("shared_plate") else "registered_layer")
            layer.setdefault("status", "verified" if layer.get("asset_path") or layer.get("source_asset") else "manual_required")
            if layer["status"] == "manual_required":
                layer.setdefault("reason", "scene_layer_asset_missing")
                layer["realization"] = "manual_required"
        if layer.get("realization") == "shared_plate":
            layer.setdefault("shared_plate", f"page-{frame.page_number:03d}-plate")
            layer.setdefault("plate_member", layer["id"])
            layer.setdefault("split_operation", "deterministic_bbox_split")
        prepared.append(layer_record(layer, frame=frame, index=index))
    return prepared


def _svg_image(layer: Mapping[str, Any]) -> str:
    asset = layer.get("asset_path") or layer.get("source_asset") or layer.get("path")
    if not asset:
        raise ValueError(f"layer {layer['id']} has no independently prepared asset")
    bbox = layer["bbox"]
    return f'<image id="{html.escape(str(layer["id"]))}" data-registration-group="{html.escape(str(layer["registration_group"]))}" x="{bbox[0]:.2f}" y="{bbox[1]:.2f}" width="{bbox[2]:.2f}" height="{bbox[3]:.2f}" href="{html.escape(str(asset))}" preserveAspectRatio="none"/>'


def author_page_svg(result: Mapping[str, Any], out_dir: Path | str) -> Path:
    """Write editable SVG without ever embedding the canonical complete page."""
    frame_data = result.get("frame", {})
    frame = NormalizedFrame(**frame_data) if isinstance(frame_data, Mapping) else None
    if frame is None:
        raise ValueError("inspection result lacks canonical frame")
    gate = result.get("page_gate") or page_gate(result.get("layers", []), frame=frame)
    if not gate.get("valid"):
        raise ValueError("cannot author SVG for a page with blocking reconstruction errors")
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{frame.pixel_size[0]}" height="{frame.pixel_size[1]}" viewBox="0 0 {frame.pixel_size[0]} {frame.pixel_size[1]}" data-reconstruction-schema="v1">']
    for layer in sorted(result.get("layers", []), key=lambda item: (int(item.get("z_index", 0)), str(item["id"]))):
        family, bbox = layer.get("family"), layer.get("bbox")
        if family == "text":
            text = html.escape(str(layer.get("truth_text", "")))
            if not text:
                raise ValueError(f"text layer {layer['id']} lacks script truth")
            x, y, width, height = bbox
            pieces.append(f'<text id="{html.escape(str(layer["id"]))}" data-truth-source="script" x="{x:.2f}" y="{y + height * .8:.2f}" font-family="Source Han Sans CN, PingFang SC, Microsoft YaHei, Arial, sans-serif" font-size="{max(12.0, height * .72):.2f}" fill="#0B1F3D">{text}</text>')
        elif family == "simple_geometry":
            x, y, width, height = bbox
            pieces.append(f'<rect id="{html.escape(str(layer["id"]))}" x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="{html.escape(str(layer.get("fill", "#D9E6F2")))}"/>')
        elif family in {"scene", "source_graphic", "data_graphic"}:
            asset = str(layer.get("asset_path") or layer.get("source_asset") or layer.get("path") or "")
            if asset in {frame.normalized_path, frame.source_path}:
                raise ValueError("canonical full page cannot be used as a delivered SVG layer")
            pieces.append(_svg_image(layer))
    pieces.append("</svg>")
    path = out / f"p{frame.page_number:02d}.svg"
    path.write_text("\n".join(pieces) + "\n", encoding="utf-8")
    return path


def write_inspection(result: Mapping[str, Any], path: Path | str) -> Path:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
