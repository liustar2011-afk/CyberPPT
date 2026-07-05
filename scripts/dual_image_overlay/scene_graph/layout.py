from __future__ import annotations

from .schema import BBox, PageSceneGraph, TextNode, VisualNode


LAYOUT_PLAN_SCHEMA = "cyberppt.page_layout_plan.v1"


def _node_by_id(graph: PageSceneGraph) -> dict[str, VisualNode]:
    return {node.node_id: node for node in graph.visual_nodes}


def _intent_targets(graph: PageSceneGraph, text_id: str, intent_type: str) -> list[str]:
    return [
        str(intent.target_id)
        for intent in graph.layout_intents
        if intent.node_id == text_id and intent.type == intent_type and intent.target_id
    ]


def _bbox_for_container_text(graph: PageSceneGraph, text: TextNode, nodes: dict[str, VisualNode]) -> BBox:
    for target_id in _intent_targets(graph, text.node_id, "honor_text_zone"):
        if target_id in nodes:
            return nodes[target_id].bbox
    if text.binding and text.binding.safe_bbox is not None:
        return text.binding.safe_bbox
    target = nodes.get(str(text.binding.target_id)) if text.binding else None
    if target is None:
        return BBox(0, 0, 1, 1)
    return BBox(target.bbox.x1 + 10, target.bbox.y1 + 8, target.bbox.x2 - 10, target.bbox.y2 - 8)


def _bbox_for_edge_label(text: TextNode, nodes: dict[str, VisualNode]) -> BBox:
    target = nodes.get(str(text.binding.target_id)) if text.binding else None
    if target is None:
        return BBox(0, 0, 1, 1)
    return BBox(target.bbox.x1, max(0.0, target.bbox.y1 - 26.0), target.bbox.x2, max(1.0, target.bbox.y1 - 4.0))


def _font_size_for(text: str, bbox: BBox) -> float:
    lines = max(1, len(text.splitlines()))
    height = max(1.0, bbox.y2 - bbox.y1)
    return round(max(7.0, min(16.0, height / lines * 0.78)), 2)


def _style_number(style: dict[str, object], key: str) -> float | None:
    value = style.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _style_bbox(style: dict[str, object], key: str) -> BBox | None:
    value = style.get(key)
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        x1, y1, x2, y2 = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return BBox(x1, y1, x2, y2)


def _font_weight_for(text: TextNode) -> str:
    style = text.style
    if style.get("font_weight") is not None:
        return str(style["font_weight"])
    if style.get("bold") is True:
        return "700"
    return "700" if text.semantic_role.endswith("title") else "400"


def build_layout_plan_from_scene_graph(graph: PageSceneGraph) -> dict:
    nodes = _node_by_id(graph)
    items: list[dict[str, object]] = []
    for index, text in enumerate(graph.text_nodes):
        binding_type = text.binding.type if text.binding else "missing"
        style = text.style
        explicit_bbox = _style_bbox(style, "layout_bbox")
        if explicit_bbox is not None:
            bbox = explicit_bbox
        elif binding_type == "edge_label":
            bbox = _bbox_for_edge_label(text, nodes)
        else:
            bbox = _bbox_for_container_text(graph, text, nodes)
        intents = [intent.type for intent in graph.layout_intents if intent.node_id == text.node_id]
        font_size = _style_number(style, "font_size") or _font_size_for(text.text, bbox)
        items.append(
            {
                "index": index,
                "node_id": text.node_id,
                "text": text.text,
                "semantic_role": text.semantic_role,
                "binding_type": binding_type,
                "target_id": text.binding.target_id if text.binding else None,
                "bbox": bbox.as_list(),
                "font_size": round(font_size, 2),
                "font_family": str(style.get("font_family") or "Microsoft YaHei"),
                "fill": str(style.get("fill") or "#0B1F3D"),
                "font_weight": _font_weight_for(text),
                "align": str(style.get("align") or "left"),
                "word_wrap": bool(style.get("word_wrap", True)),
                "layout_intents": intents,
                "layout_strategy": style.get("layout_strategy"),
                "layout_source": style.get("layout_source") or "scene_graph_fallback",
            }
        )
    return {
        "schema": LAYOUT_PLAN_SCHEMA,
        "page": graph.page,
        "source_scene_graph": "page_scene_graph.json",
        "items": items,
    }
