from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .schema import BBox, PageSceneGraph, TextBinding, TextNode, VisualNode


CONSTRAINED_REFLOW_SCHEMA = "cyberppt.recognized_constrained_reflow.v1"
TEXT_REGION_ROLES = {
    "editable_text",
    "title",
    "subtitle",
    "body",
    "label",
    "caption",
    "judgment",
    "evidence",
    "section_label",
    "diagram_label",
    "diagram_body",
}


def _is_recognized_text_region(node: VisualNode) -> bool:
    return bool(
        node.attributes.get("recognized_layout")
        and node.node_type not in {"image", "illustration", "photo"}
        and (
            node.node_type == "layout_zone"
            or node.semantic_role.lower() in TEXT_REGION_ROLES
        )
    )


def _role_score(text: TextNode, region: VisualNode) -> int:
    text_role = text.semantic_role.lower()
    region_role = region.semantic_role.lower()
    if text.binding and text.binding.target_id == region.node_id:
        return 120
    if text.attributes.get("recognized_region_id") == region.node_id:
        return 100
    if text_role == region_role:
        return 80
    if text_role.endswith("title") and "title" in region_role:
        return 60
    if text_role in {"body", "description", "bullet"} and region_role in {
        "body",
        "editable_text",
        "evidence",
        "diagram_body",
    }:
        return 40
    return 0


def _reading_key(node: VisualNode) -> tuple[float, float]:
    return node.bbox.y1, node.bbox.x1


def _assign_regions(text_nodes: list[TextNode], regions: list[VisualNode]) -> dict[str, VisualNode]:
    available = list(sorted(regions, key=_reading_key))
    result: dict[str, VisualNode] = {}
    for text in text_nodes:
        if not available:
            break
        ranked = sorted(
            enumerate(available),
            key=lambda item: (-_role_score(text, item[1]), _reading_key(item[1])),
        )
        index, selected = ranked[0]
        result[text.node_id] = selected
        available.pop(index)
    return result


def _illustration_safe_right(
    region: VisualNode,
    visual_nodes: list[VisualNode],
    *,
    canvas_width: float,
) -> float:
    """Keep text in a recognized left column out of adjacent image/diagram zones."""

    if region.bbox.x2 > canvas_width * 0.62:
        return region.bbox.x2
    candidates = [
        node.bbox.x1
        for node in visual_nodes
        if node.node_id != region.node_id
        and node.node_type in {"image", "illustration", "photo", "visual_anchor"}
        and node.bbox.x1 >= region.bbox.x1
        and node.bbox.y1 < region.bbox.y2
        and node.bbox.y2 > region.bbox.y1
    ]
    if not candidates:
        return region.bbox.x2
    gap = max(12.0, canvas_width * 0.012)
    return min(region.bbox.x2, min(candidates) - gap)


def _reflow_bbox(
    text: TextNode,
    region: VisualNode,
    canvas: dict[str, Any],
    visual_nodes: list[VisualNode],
) -> BBox:
    bbox = region.bbox
    canvas_width = float(canvas.get("width") or bbox.x2)
    safe_right = _illustration_safe_right(region, visual_nodes, canvas_width=canvas_width)
    width = max(1.0, safe_right - bbox.x1)
    height = max(1.0, bbox.y2 - bbox.y1)
    font_size = float(text.style.get("font_size") or 16.0)
    if width >= 160.0:
        desired_width = width
    else:
        max_region_width = max(width, canvas_width * 0.24)
        desired_width = min(
            max_region_width,
            max(width, min(len(text.text.replace("\n", "")), 24) * font_size * 0.72),
        )
    center_x = (bbox.x1 + safe_right) / 2.0
    x1 = max(0.0, center_x - desired_width / 2.0)
    x2 = min(canvas_width, x1 + desired_width)
    if x2 - x1 < desired_width:
        x1 = max(0.0, x2 - desired_width)
    is_left_text_column = width >= 160.0 and bbox.x2 <= canvas_width * 0.50
    padding_ratio = 0.10 if is_left_text_column else (0.05 if width >= 160.0 else 0.02)
    padding_x = max(6.0, desired_width * padding_ratio)
    usable_width = max(font_size * 4.0, desired_width - padding_x * 2.0)
    chars_per_line = max(4, int(usable_width / max(1.0, font_size * 0.92)))
    logical_lines = max(1, len(text.text.splitlines()))
    estimated_lines = max(logical_lines, math.ceil(len(text.text.replace("\n", "")) / chars_per_line))
    desired_height = max(font_size * 1.75 * estimated_lines, font_size * 1.9)
    paragraph_count = sum(1 for line in text.text.splitlines() if line.strip())
    minimum_height = height
    if paragraph_count >= 2 or estimated_lines >= 3:
        minimum_height = height * 1.5
    new_height = min(max(minimum_height, desired_height), max(height * 4.0, desired_height))
    growth = new_height - height
    max_height = float(canvas.get("height") or bbox.y2)
    y1 = max(0.0, bbox.y1 - growth * 0.35)
    y2 = min(max_height, y1 + new_height)
    if y2 - y1 < new_height:
        y1 = max(0.0, y2 - new_height)
    return BBox(x1 + padding_x, y1, x2 - padding_x, y2)


def _reflow_font_size(text: TextNode) -> float:
    current = float(text.style.get("font_size") or 16.0)
    role = text.semantic_role.lower()
    if role in {"body", "description", "evidence"}:
        return max(current, 14.5)
    if "title" in role or role in {"section_label", "judgment"}:
        return max(current, 18.0)
    if role == "diagram_body":
        return max(current, 11.0)
    if role in {"label", "caption"}:
        return max(current, 10.0)
    return max(current, 12.0)


def _wrap_text_to_bbox(text: str, bbox: BBox, font_size: float) -> str:
    """Insert semantic-neutral line breaks because SVG text does not auto-wrap."""

    if "\u00a0" in text:
        # Explicit non-breaking spacing is a layout contract for distributed
        # short labels (for example, one label per recognized gateway cell).
        return text
    usable_width = max(1.0, bbox.x2 - bbox.x1)
    # CJK glyphs render close to one em wide. The additional safety factor
    # absorbs DrawingML/SVG font metric drift and keeps text visibly inside.
    chars_per_line = max(4, int(usable_width / max(1.0, font_size * 1.45)))
    wrapped: list[str] = []
    for raw_line in text.splitlines() or [text]:
        if not raw_line:
            wrapped.append("")
            continue
        indent = ""
        content = raw_line
        if raw_line.startswith(("• ", "· ")):
            indent, content = raw_line[:2], raw_line[2:]
        elif raw_line.startswith("  "):
            indent, content = "  ", raw_line[2:]
        first_capacity = max(1, chars_per_line - len(indent))
        wrapped.append(indent + content[:first_capacity])
        content = content[first_capacity:]
        continuation_indent = "  " if indent else ""
        continuation_capacity = max(1, chars_per_line - len(continuation_indent))
        while content:
            wrapped.append(continuation_indent + content[:continuation_capacity])
            content = content[continuation_capacity:]
    return "\n".join(wrapped)


def apply_recognized_constrained_reflow(
    graph: PageSceneGraph,
    *,
    strict: bool = False,
) -> tuple[PageSceneGraph, dict[str, Any]]:
    """Reflow reliable text inside the expression structure recognized from the image."""

    regions = [node for node in graph.visual_nodes if _is_recognized_text_region(node)]
    assignments = _assign_regions(graph.text_nodes, regions)
    canvas = graph.coordinate_context.to_dict().get("coordinate_space") or {}
    updated_nodes: list[TextNode] = []
    records: list[dict[str, Any]] = []
    for text in graph.text_nodes:
        region = assignments.get(text.node_id)
        if region is None:
            updated_nodes.append(text)
            records.append(
                {
                    "node_id": text.node_id,
                    "status": "unassigned",
                    "blocking": strict,
                }
            )
            continue
        reflow_font_size = _reflow_font_size(text)
        bbox = _reflow_bbox(
            replace(text, style={**text.style, "font_size": reflow_font_size}),
            region,
            canvas,
            graph.visual_nodes,
        )
        reflow_text = _wrap_text_to_bbox(text.text, bbox, reflow_font_size)
        style = {
            **text.style,
            "font_size": reflow_font_size,
            "recognized_reflow_bbox": bbox.as_list(),
            "layout_strategy": "recognized_expression_constrained_reflow",
            "layout_source": "recognized_layout_reflow",
        }
        binding = text.binding or TextBinding(type="container_text")
        binding = replace(
            binding,
            target_id=region.node_id,
            safe_bbox=bbox,
            metadata={
                **binding.metadata,
                "recognized_region_id": region.node_id,
                "expression_pattern_preserved": True,
            },
        )
        updated_nodes.append(replace(text, text=reflow_text, style=style, binding=binding))
        records.append(
            {
                "node_id": text.node_id,
                "region_id": region.node_id,
                "source_bbox": region.bbox.as_list(),
                "reflow_bbox": bbox.as_list(),
                "line_count": len(reflow_text.splitlines()),
                "status": "assigned",
                "blocking": False,
            }
        )

    layout_meta = graph.metadata.get("layout_reference") if isinstance(graph.metadata, dict) else {}
    grammar = layout_meta.get("layout_grammar") if isinstance(layout_meta, dict) else None
    report = {
        "schema": CONSTRAINED_REFLOW_SCHEMA,
        "page": graph.page,
        "valid": not any(record["blocking"] for record in records),
        "expression_pattern": grammar,
        "expression_pattern_preserved": True,
        "assigned_count": sum(record["status"] == "assigned" for record in records),
        "unassigned_count": sum(record["status"] == "unassigned" for record in records),
        "items": records,
    }
    if strict and not graph.text_nodes:
        report["valid"] = False
        report["issues"] = [
            {
                "code": "missing_text_nodes",
                "blocking": True,
                "reason": "recognized reflow requires reliable script-backed text nodes",
            }
        ]
    return replace(
        graph,
        text_nodes=updated_nodes,
        metadata={**graph.metadata, "constrained_reflow": report},
    ), report
