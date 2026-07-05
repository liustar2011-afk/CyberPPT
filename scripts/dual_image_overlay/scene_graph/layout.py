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


def build_layout_plan_from_scene_graph(graph: PageSceneGraph) -> dict:
    nodes = _node_by_id(graph)
    items: list[dict[str, object]] = []
    for index, text in enumerate(graph.text_nodes):
        binding_type = text.binding.type if text.binding else "missing"
        if binding_type == "edge_label":
            bbox = _bbox_for_edge_label(text, nodes)
        else:
            bbox = _bbox_for_container_text(graph, text, nodes)
        intents = [intent.type for intent in graph.layout_intents if intent.node_id == text.node_id]
        items.append(
            {
                "index": index,
                "node_id": text.node_id,
                "text": text.text,
                "semantic_role": text.semantic_role,
                "binding_type": binding_type,
                "target_id": text.binding.target_id if text.binding else None,
                "bbox": bbox.as_list(),
                "font_size": _font_size_for(text.text, bbox),
                "font_weight": "700" if text.semantic_role.endswith("title") else "400",
                "align": "left",
                "word_wrap": True,
                "layout_intents": intents,
            }
        )
    return {
        "schema": LAYOUT_PLAN_SCHEMA,
        "page": graph.page,
        "source_scene_graph": "page_scene_graph.json",
        "items": items,
    }
