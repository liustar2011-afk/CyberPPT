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
        and node.semantic_role.lower() in TEXT_REGION_ROLES
    )


def _role_score(text: TextNode, region: VisualNode) -> int:
    text_role = text.semantic_role.lower()
    region_role = region.semantic_role.lower()
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


def _reflow_bbox(text: TextNode, region: VisualNode, canvas: dict[str, Any]) -> BBox:
    bbox = region.bbox
    width = max(1.0, bbox.x2 - bbox.x1)
    height = max(1.0, bbox.y2 - bbox.y1)
    font_size = float(text.style.get("font_size") or 16.0)
    usable_width = max(font_size * 4.0, width - max(12.0, width * 0.04))
    chars_per_line = max(4, int(usable_width / max(1.0, font_size * 0.92)))
    logical_lines = max(1, len(text.text.splitlines()))
    estimated_lines = max(logical_lines, math.ceil(len(text.text.replace("\n", "")) / chars_per_line))
    desired_height = max(font_size * 1.45 * estimated_lines, font_size * 1.7)
    new_height = min(max(height, desired_height), height * 1.65)
    growth = new_height - height
    max_height = float(canvas.get("height") or bbox.y2)
    y1 = max(0.0, bbox.y1 - growth * 0.35)
    y2 = min(max_height, y1 + new_height)
    if y2 - y1 < new_height:
        y1 = max(0.0, y2 - new_height)
    padding_x = max(6.0, width * 0.02)
    return BBox(bbox.x1 + padding_x, y1, bbox.x2 - padding_x, y2)


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
        bbox = _reflow_bbox(text, region, canvas)
        style = {
            **text.style,
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
        updated_nodes.append(replace(text, style=style, binding=binding))
        records.append(
            {
                "node_id": text.node_id,
                "region_id": region.node_id,
                "source_bbox": region.bbox.as_list(),
                "reflow_bbox": bbox.as_list(),
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
    return replace(
        graph,
        text_nodes=updated_nodes,
        metadata={**graph.metadata, "constrained_reflow": report},
    ), report
