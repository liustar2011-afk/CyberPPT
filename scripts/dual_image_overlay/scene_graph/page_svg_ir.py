"""Compile a validated page scene graph into the SVG/DrawingML handoff IR.

The IR deliberately separates the complex visual layer from the editable
information layer. It is JSON-serializable and does not draw or rasterize
anything; the existing PPT Master SVG runtime owns the eventual rendering.
"""

from __future__ import annotations

from typing import Any, Mapping

from .gate import build_scene_graph_gate
from .layout import build_layout_plan_from_scene_graph
from .schema import BBox, PageSceneGraph, Relation, VisualNode
from .text_metrics import avoid_reserved_zones, fit_text_to_safe_bbox


PAGE_SVG_IR_SCHEMA = "cyberppt.page_svg_ir.v1"
DEFAULT_BACKGROUND_ID = "page_background"


class PageSvgIRValidationError(ValueError):
    """Raised when a scene graph cannot produce a safe Page SVG IR."""


def _bbox_dict(bbox: BBox) -> dict[str, float]:
    return {"x": bbox.x1, "y": bbox.y1, "width": bbox.x2 - bbox.x1, "height": bbox.y2 - bbox.y1}


def _element_bbox(payload: Mapping[str, Any]) -> list[float] | None:
    bbox = payload.get("bbox")
    if not isinstance(bbox, Mapping):
        return None
    try:
        x = float(bbox["x"])
        y = float(bbox["y"])
        return [x, y, x + float(bbox["width"]), y + float(bbox["height"])]
    except (KeyError, TypeError, ValueError):
        return None


def _visual_kind(node: VisualNode) -> str:
    if node.node_type in {"flow_arrow", "arrow", "connector", "feedback_connector"}:
        return "connector"
    if node.node_type in {"icon", "image", "illustration", "photo"}:
        return "image"
    return "shape"


def _visual_element(node: VisualNode) -> dict[str, Any]:
    attrs = dict(node.attributes)
    geometry = attrs.get("geometry") or attrs.get("svg_geometry")
    return {
        "id": node.node_id,
        "kind": _visual_kind(node),
        "role": node.semantic_role,
        "bbox": _bbox_dict(node.bbox),
        "editable": bool(attrs.get("editable", False)),
        "source": dict(node.source),
        "confidence": node.confidence,
        "component_id": node.component_id,
        "geometry": geometry,
        "style": dict(attrs.get("style") or {}),
        "metadata": {
            "node_type": node.node_type,
            "attributes": attrs,
        },
    }


def _relation_element(relation: Relation, nodes: Mapping[str, VisualNode]) -> dict[str, Any]:
    source = nodes.get(relation.source_id)
    target = nodes.get(relation.target_id)
    if source is None or target is None:
        raise PageSvgIRValidationError(
            f"Relation {relation.type} references missing nodes: {relation.source_id}, {relation.target_id}"
        )
    start = {"x": (source.bbox.x1 + source.bbox.x2) / 2, "y": (source.bbox.y1 + source.bbox.y2) / 2}
    end = {"x": (target.bbox.x1 + target.bbox.x2) / 2, "y": (target.bbox.y1 + target.bbox.y2) / 2}
    return {
        "id": f"relation_{relation.source_id}_{relation.target_id}_{relation.type}",
        "kind": "connector",
        "role": relation.type,
        "editable": True,
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "start": start,
        "end": end,
        "metrics": dict(relation.metrics),
        "confidence": relation.confidence,
        "geometry_source": "scene_graph_relation",
    }


def _text_element(item: Mapping[str, Any], text_truth: Mapping[str, Any], *, safe_bbox: BBox | None = None, reserved_zones: list[Any] | None = None) -> dict[str, Any]:
    raw_bbox = item.get("bbox")
    if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
        raise PageSvgIRValidationError(f"Text item {item.get('node_id')} has no four-value bbox")
    bbox = BBox.from_any(raw_bbox)
    safe = safe_bbox or bbox
    metrics = fit_text_to_safe_bbox(str(item.get("text") or ""), safe, float(item.get("font_size") or 12), font_family=str(item.get("font_family") or "Microsoft YaHei"))
    avoidance = avoid_reserved_zones(bbox, safe, reserved_zones)
    if metrics["status"] == "blocked_overflow":
        raise PageSvgIRValidationError(f"Text item {item.get('node_id')} cannot fit its safe area")
    if avoidance["status"] == "blocked_reserved_zone":
        raise PageSvgIRValidationError(f"Text item {item.get('node_id')} collides with a reserved zone")
    final_bbox = BBox.from_any(avoidance["bbox"])
    return {
        "id": str(item["node_id"]),
        "kind": "text",
        "role": item.get("semantic_role"),
        "text": metrics["text"],
        "bbox": _bbox_dict(final_bbox),
        "editable": True,
        "truth_source": dict(text_truth),
        "binding": {
            "type": item.get("binding_type"),
            "target_id": item.get("target_id"),
        },
        "style": {
            "font_size": item.get("font_size"),
            "font_family": item.get("font_family"),
            "font_weight": item.get("font_weight"),
            "fill": item.get("fill"),
            "align": item.get("align"),
            "word_wrap": item.get("word_wrap"),
        },
        "layout": {
            "strategy": item.get("layout_strategy"),
            "source": item.get("layout_source"),
            "intents": list(item.get("layout_intents") or []),
        },
        "metrics": metrics,
        "avoidance": avoidance,
    }


def validate_page_svg_ir(ir: Mapping[str, Any]) -> dict[str, Any]:
    """Validate IDs, bounds, and editable text contracts without rendering."""
    issues: list[dict[str, Any]] = []
    canvas = ir.get("canvas") if isinstance(ir.get("canvas"), Mapping) else {}
    width = float(canvas.get("width") or 0)
    height = float(canvas.get("height") or 0)
    ids: set[str] = set()
    for layer in ir.get("layers", []):
        for element in layer.get("elements", []):
            element_id = str(element.get("id") or "")
            if not element_id or element_id in ids:
                issues.append({"code": "duplicate_or_missing_element_id", "element_id": element_id, "blocking": True})
            ids.add(element_id)
            bbox = _element_bbox(element)
            if bbox and not (bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= width and bbox[3] <= height):
                issues.append({"code": "element_outside_canvas", "element_id": element_id, "bbox": bbox, "blocking": True})
            if element.get("kind") == "text" and (not element.get("editable") or not element.get("truth_source")):
                issues.append({"code": "editable_text_contract_missing", "element_id": element_id, "blocking": True})
    return {
        "schema": "cyberppt.page_svg_ir_gate.v1",
        "valid": not any(issue["blocking"] for issue in issues),
        "blocking_count": sum(1 for issue in issues if issue["blocking"]),
        "issues": issues,
    }


def compile_scene_graph_to_page_svg_ir(
    graph: PageSceneGraph,
    *,
    background_href: str | None = None,
    layout_plan: Mapping[str, Any] | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Compile one page scene graph into a Page SVG IR document."""
    if not isinstance(graph, PageSceneGraph):
        raise TypeError("graph must be a PageSceneGraph")
    scene_gate = build_scene_graph_gate(graph)
    if strict and not scene_gate["valid"]:
        raise PageSvgIRValidationError(f"Scene graph gate failed with {scene_gate['blocking_count']} blocking issue(s)")

    context = graph.coordinate_context.to_dict()
    canvas = context.get("normalized_canvas") or {"width": 1672.0, "height": 941.0}
    nodes = {node.node_id: node for node in graph.visual_nodes}
    layout = dict(layout_plan or build_layout_plan_from_scene_graph(graph))
    text_by_id = {node.node_id: node for node in graph.text_nodes}

    background_elements: list[dict[str, Any]] = []
    if background_href:
        background_elements.append(
            {
                "id": DEFAULT_BACKGROUND_ID,
                "kind": "image",
                "role": "complex_visual_background",
                "href": str(background_href),
                "bbox": {"x": 0.0, "y": 0.0, "width": float(canvas["width"]), "height": float(canvas["height"])},
                "editable": False,
                "text_bearing": False,
                "source": {"kind": "dual_image_background"},
            }
        )

    visual_elements = [_visual_element(node) for node in graph.visual_nodes]
    relation_elements = [_relation_element(relation, nodes) for relation in graph.relations]
    text_elements = [
        _text_element(
            item,
            text_by_id[item["node_id"]].truth_source,
            safe_bbox=text_by_id[item["node_id"]].binding.safe_bbox if text_by_id[item["node_id"]].binding else None,
            reserved_zones=(text_by_id[item["node_id"]].binding.metadata.get("reserved_zones", []) if text_by_id[item["node_id"]].binding else []),
        )
        for item in layout.get("items", [])
        if item.get("node_id") in text_by_id
    ]
    ir = {
        "schema": PAGE_SVG_IR_SCHEMA,
        "page": graph.page,
        "canvas": {"width": float(canvas["width"]), "height": float(canvas["height"])},
        "coordinate_context": context,
        "root_attributes": {
            "data-pptx-bounds": f"0 0 {float(canvas['width'])} {float(canvas['height'])}",
            "data-scene-graph-schema": "cyberppt.page_scene_graph.v1",
        },
        "scene_graph_gate": scene_gate,
        "layers": [
            {"id": "background", "z_index": 0, "elements": background_elements},
            {"id": "visuals", "z_index": 10, "elements": visual_elements + relation_elements},
            {"id": "editable_information", "z_index": 20, "elements": text_elements},
        ],
        "metadata": {
            "source_scene_graph": "page_scene_graph.v1",
            "text_truth_policy": "scene_graph.text_nodes.truth_source",
            "background_policy": "background_is_complex_visual_only",
            "editable_text_count": len(text_elements),
            "visual_element_count": len(visual_elements),
            "relation_count": len(relation_elements),
        },
    }
    ir_gate = validate_page_svg_ir(ir)
    ir["page_svg_ir_gate"] = ir_gate
    if strict and not ir_gate["valid"]:
        raise PageSvgIRValidationError(f"Page SVG IR gate failed with {ir_gate['blocking_count']} blocking issue(s)")
    return ir
