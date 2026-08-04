"""Render Page SVG IR as the single SVG/DrawingML export input."""

from __future__ import annotations

import html
from typing import Any, Mapping


def _asset_sources(ir: Mapping[str, Any]) -> dict[str, str]:
    manifest = ir.get("image_assets")
    assets = manifest.get("assets", []) if isinstance(manifest, Mapping) else []
    return {
        str(item.get("asset_id")): str(item.get("source"))
        for item in assets
        if isinstance(item, Mapping) and item.get("asset_id") and item.get("source")
    }


def _bbox(element: Mapping[str, Any]) -> tuple[float, float, float, float]:
    raw = element.get("bbox")
    if not isinstance(raw, Mapping):
        raise ValueError(f"IR element {element.get('id')} has no bbox")
    return float(raw["x"]), float(raw["y"]), float(raw["width"]), float(raw["height"])


def _map_bbox(element, *, source_width, source_height, target):
    x, y, width, height = _bbox(element)
    sx = float(target["width"]) / source_width
    sy = float(target["height"]) / source_height
    return (
        float(target["x"]) + x * sx,
        float(target["y"]) + y * sy,
        width * sx,
        height * sy,
    )


def _image_href(element: Mapping[str, Any], assets: Mapping[str, str]) -> str | None:
    if element.get("href"):
        return str(element["href"])
    asset_id = str(element.get("asset_id") or "")
    if asset_id in assets:
        return assets[asset_id]
    source = element.get("source")
    if isinstance(source, Mapping):
        for key in ("path", "href", "source"):
            if source.get(key):
                return str(source[key])
    return None


def _text_svg(element, *, source_width, source_height, target, opacity):
    x, y, width, height = _map_bbox(
        element, source_width=source_width, source_height=source_height, target=target
    )
    style = element.get("style") if isinstance(element.get("style"), Mapping) else {}
    metrics = element.get("metrics") if isinstance(element.get("metrics"), Mapping) else {}
    font_size = float(metrics.get("font_size") or style.get("font_size") or 12)
    if str(style.get("font_size_space") or "") != "ppt_svg_px":
        font_size *= float(target["height"]) / source_height
    family = str(style.get("font_family") or "Microsoft YaHei")
    fill = str(style.get("fill") or "#0B1F3D")
    weight = str(style.get("font_weight") or "400")
    align = str(style.get("align") or "left")
    anchor = {"center": "middle", "right": "end"}.get(align, "start")
    text_x = x + (width / 2 if align == "center" else width if align == "right" else 0)
    lines = str(metrics.get("text") or element.get("text") or "").splitlines() or [""]
    line_height = font_size * 1.20
    total_height = font_size + max(0, len(lines) - 1) * line_height
    text_y = y + max(font_size, (height - total_height) / 2 + font_size * 0.88)
    tspans = "".join(
        f'<tspan x="{text_x:.2f}" dy="{0 if index == 0 else line_height:.2f}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text id="{html.escape(str(element.get("id") or ""))}" '
        f'data-ir-kind="text" data-ir-editable="1" '
        f'x="{text_x:.2f}" y="{text_y:.2f}" text-anchor="{anchor}" '
        f'font-family="{html.escape(family)}, Arial, sans-serif" '
        f'font-size="{font_size:.2f}" font-weight="{html.escape(weight)}" '
        f'fill="{html.escape(fill)}" fill-opacity="{opacity:.3f}">{tspans}</text>'
    )


def render_page_svg_ir(
    ir: Mapping[str, Any],
    *,
    canvas: Mapping[str, float],
    content_region: Mapping[str, float],
    slide_title: str,
    subtitle: str = "",
    text_opacity: float = 1.0,
) -> str:
    """Render Page SVG IR; legacy overlay boxes are intentionally not accepted."""
    ir_canvas = ir.get("canvas") if isinstance(ir.get("canvas"), Mapping) else {}
    source_width = float(ir_canvas.get("width") or 0)
    source_height = float(ir_canvas.get("height") or 0)
    if source_width <= 0 or source_height <= 0:
        raise ValueError("Page SVG IR canvas must have positive width and height")
    width = int(canvas["width"])
    height = int(canvas["height"])
    assets = _asset_sources(ir)
    opacity = max(0.0, min(1.0, float(text_opacity)))
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" data-pptx-bounds="0 0 {width} {height}" '
            f'data-export-source="page_svg_ir">'
        ),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#F7F6F0"/>',
        (
            f'<text x="{float(content_region["x"]):.2f}" y="46" '
            f'font-family="Microsoft YaHei, Arial, sans-serif" font-size="25" '
            f'font-weight="700" fill="#123B66">{html.escape(slide_title)}</text>'
        ),
    ]
    if subtitle:
        parts.append(
            f'<text x="{float(content_region["x"]):.2f}" y="72" '
            f'font-family="Microsoft YaHei, Arial, sans-serif" font-size="14" '
            f'fill="#60758A">{html.escape(subtitle)}</text>'
        )
    for layer in sorted(ir.get("layers", []), key=lambda item: int(item.get("z_index", 0))):
        layer_id = str(layer.get("id") or "")
        for element in layer.get("elements", []):
            if not isinstance(element, Mapping):
                continue
            kind = str(element.get("kind") or "")
            if kind == "image":
                href = _image_href(element, assets)
                if not href:
                    raise ValueError(f"Image element {element.get('id')} is absent from the asset registry")
                x, y, w, h = _map_bbox(
                    element,
                    source_width=source_width,
                    source_height=source_height,
                    target=content_region,
                )
                parts.append(
                    f'<image id="{html.escape(str(element.get("id") or ""))}" '
                    f'data-ir-layer="{html.escape(layer_id)}" '
                    f'data-ir-asset-id="{html.escape(str(element.get("asset_id") or ""))}" '
                    f'x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                    f'href="{html.escape(href)}" xlink:href="{html.escape(href)}" '
                    f'preserveAspectRatio="none"/>'
                )
            elif kind == "text":
                rendered_text = _text_svg(
                        element,
                        source_width=source_width,
                        source_height=source_height,
                        target=content_region,
                        opacity=opacity,
                    )
                parts.append(
                    rendered_text.replace(
                        'data-ir-kind="text"',
                        f'data-ir-kind="text" data-ir-layer="{html.escape(layer_id)}"',
                        1,
                    )
                )
            elif kind == "connector" and element.get("start") and element.get("end"):
                start, end = element["start"], element["end"]
                sx = float(content_region["width"]) / source_width
                sy = float(content_region["height"]) / source_height
                x1 = float(content_region["x"]) + float(start["x"]) * sx
                y1 = float(content_region["y"]) + float(start["y"]) * sy
                x2 = float(content_region["x"]) + float(end["x"]) * sx
                y2 = float(content_region["y"]) + float(end["y"]) * sy
                parts.append(
                    f'<line id="{html.escape(str(element.get("id") or ""))}" '
                    f'data-ir-layer="{html.escape(layer_id)}" '
                    f'x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    f'stroke="#8CA3B8" stroke-width="1"/>'
                )
            elif bool(element.get("editable")):
                x, y, w, h = _map_bbox(
                    element,
                    source_width=source_width,
                    source_height=source_height,
                    target=content_region,
                )
                style = element.get("style") if isinstance(element.get("style"), Mapping) else {}
                parts.append(
                    f'<rect id="{html.escape(str(element.get("id") or ""))}" '
                    f'data-ir-layer="{html.escape(layer_id)}" '
                    f'x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                    f'fill="{html.escape(str(style.get("fill") or "none"))}" '
                    f'stroke="{html.escape(str(style.get("stroke") or "#C9CDD1"))}"/>'
                )
    parts.append("</svg>\n")
    return "\n".join(parts)
