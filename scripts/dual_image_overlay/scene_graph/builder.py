from __future__ import annotations

import re
from typing import Any, Mapping

from .coordinate import normalize_bbox, resolve_coordinate_context
from .schema import BBox, LayoutIntent, PageSceneGraph, Relation, TextBinding, TextNode, VisualNode


TEXT_ZONE_TYPES = {"text_zone", "label_zone", "text_safe_zone"}
CONTAINER_TYPES = {
    "application_card",
    "source_card",
    "object_pool_cell",
    "service_segment",
    "governance_step",
    "container",
}
RESERVED_TYPES = {
    "icon",
    "flow_arrow",
    "arrow",
    "connector",
    "feedback_connector",
    "badge",
    "separator",
    "divider",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s\-·•,，.。:：;；、|｜/]+", "", value).lower()


def _split_items(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        for part in re.split(r"[、，,|｜]", str(line)):
            cleaned = part.strip(" -*•·")
            if cleaned:
                result.append(cleaned)
    return result


def _bbox_from_registry(raw: Mapping[str, Any]) -> BBox:
    return BBox.from_any(raw["blueprint_bbox_px"])


def _extent_from_bboxes(boxes: list[BBox]) -> dict[str, float] | None:
    if not boxes:
        return None
    return {"width": max(box.x2 for box in boxes), "height": max(box.y2 for box in boxes)}


def _intersects(a: BBox, b: BBox) -> bool:
    return max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1)) > 0 and max(
        0.0, min(a.y2, b.y2) - max(a.y1, b.y1)
    ) > 0


def _contains(container: BBox, child: BBox, tolerance: float = 3.0) -> bool:
    return (
        child.x1 >= container.x1 - tolerance
        and child.y1 >= container.y1 - tolerance
        and child.x2 <= container.x2 + tolerance
        and child.y2 <= container.y2 + tolerance
    )


def _visual_nodes(visual_registry: Mapping[str, Any], context: Mapping[str, Any]) -> list[VisualNode]:
    input_space = context["visual_registry_input_space"]
    nodes: list[VisualNode] = []
    elements = visual_registry.get("elements", [])
    if not isinstance(elements, list):
        return nodes
    for index, element in enumerate(elements, start=1):
        if not isinstance(element, dict) or "blueprint_bbox_px" not in element:
            continue
        node_id = str(element.get("element_id") or element.get("id") or f"visual_{index}")
        node_type = str(element.get("element_type") or "visual")
        nodes.append(
            VisualNode(
                node_id=node_id,
                node_type=node_type,
                semantic_role=str(element.get("semantic_role") or element.get("role") or node_type),
                bbox=normalize_bbox(_bbox_from_registry(element), input_space, context),
                source={"kind": "visual_element_registry"},
                confidence=float(element.get("confidence") or 1.0),
                component_id=element.get("source_component_id"),
                attributes={"raw": element},
            )
        )
    return nodes


def _semantic_container_nodes(semantic_plan: Mapping[str, Any], context: Mapping[str, Any]) -> list[VisualNode]:
    input_space = context["semantic_input_space"]
    nodes: list[VisualNode] = []
    containers = semantic_plan.get("containers", [])
    if not isinstance(containers, list):
        return nodes
    for index, container in enumerate(containers, start=1):
        if not isinstance(container, dict) or "bbox" not in container:
            continue
        nodes.append(
            VisualNode(
                node_id=str(container.get("id") or f"container_{index}"),
                node_type="container",
                semantic_role=str(container.get("role") or "container"),
                bbox=normalize_bbox(BBox.from_any(container["bbox"]), input_space, context),
                source={"kind": "semantic_plan"},
                confidence=float(container.get("confidence") or 1.0),
                component_id=container.get("component_id"),
                attributes={"raw": container},
            )
        )
    return nodes


def _find_node(nodes: list[VisualNode], node_id: str | None) -> VisualNode | None:
    for node in nodes:
        if node.node_id == node_id:
            return node
    return None


def _build_application_text(script_sections: Mapping[str, list[dict[str, Any]]]) -> list[str]:
    groups = script_sections.get("右侧｜结果应用方", [])
    texts: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or "").strip()
        lines = group.get("lines", [])
        items = _split_items([str(line) for line in lines]) if isinstance(lines, list) else []
        if title and items:
            texts.append(title + "\n" + "\n".join(f"• {item}" for item in items))
    return texts


def _text_nodes(
    script_sections: Mapping[str, list[dict[str, Any]]],
    semantic_plan: Mapping[str, Any],
) -> list[TextNode]:
    nodes: list[TextNode] = []
    for index, text in enumerate(_build_application_text(script_sections), start=1):
        nodes.append(
            TextNode(
                node_id=f"text_application_{index}",
                text=text,
                truth_source={"kind": "script"},
                semantic_role="application_card_text",
                binding=TextBinding(type="container_text", target_id=f"application_{index}", placement="inside"),
            )
        )

    items = semantic_plan.get("items", [])
    if not isinstance(items, list):
        return nodes
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("display_text") or item.get("text") or "").strip()
        if not text:
            continue
        role = str(item.get("role") or "body")
        if role == "arrow_label" and item.get("target_id"):
            nodes.append(
                TextNode(
                    node_id=f"text_semantic_{index}",
                    text=text,
                    truth_source={"kind": "script"},
                    semantic_role=role,
                    binding=TextBinding(type="edge_label", target_id=str(item["target_id"]), placement="above"),
                )
            )
        elif item.get("container_id") and not any(_normalize_text(text) == _normalize_text(existing.text) for existing in nodes):
            nodes.append(
                TextNode(
                    node_id=f"text_semantic_{index}",
                    text=text,
                    truth_source={"kind": "script"},
                    semantic_role=role,
                    binding=TextBinding(type="container_text", target_id=str(item["container_id"]), placement="inside"),
                )
            )
    return nodes


def _relations(visual_nodes: list[VisualNode]) -> list[Relation]:
    relations: list[Relation] = []
    containers = [node for node in visual_nodes if node.node_type in CONTAINER_TYPES or node.node_type == "container"]
    for container in containers:
        for child in visual_nodes:
            if child.node_id == container.node_id:
                continue
            if _contains(container.bbox, child.bbox):
                relations.append(Relation(type="contains", source_id=container.node_id, target_id=child.node_id))
            elif container.component_id and container.component_id == child.component_id and _intersects(container.bbox, child.bbox):
                relations.append(Relation(type="part_of", source_id=container.node_id, target_id=child.node_id, confidence=0.8))
    return relations


def _layout_intents(text_nodes: list[TextNode], visual_nodes: list[VisualNode], relations: list[Relation]) -> list[LayoutIntent]:
    intents: list[LayoutIntent] = []
    contained_by = {(rel.source_id, rel.target_id) for rel in relations if rel.type in {"contains", "part_of"}}
    for text in text_nodes:
        binding = text.binding
        if binding is None:
            continue
        if binding.type == "container_text" and binding.target_id:
            for container_id, child_id in contained_by:
                if container_id != binding.target_id:
                    continue
                child = _find_node(visual_nodes, child_id)
                if child and child.node_type in TEXT_ZONE_TYPES:
                    intents.append(LayoutIntent(type="honor_text_zone", node_id=text.node_id, target_id=child.node_id))
                elif child and child.node_type in RESERVED_TYPES:
                    intents.append(LayoutIntent(type="avoid_reserved_zone", node_id=text.node_id, target_id=child.node_id))
        elif binding.type == "edge_label":
            intents.append(LayoutIntent(type="label_on_arrow", node_id=text.node_id, target_id=binding.target_id))
    return intents


def build_page_scene_graph(
    *,
    page_number: int,
    script_sections: Mapping[str, list[dict[str, Any]]],
    semantic_plan: Mapping[str, Any],
    visual_registry: Mapping[str, Any],
    image_size: Mapping[str, Any],
) -> PageSceneGraph:
    containers = semantic_plan.get("containers", [])
    semantic_boxes = [
        BBox.from_any(item["bbox"]) for item in containers if isinstance(item, dict) and "bbox" in item
    ] if isinstance(containers, list) else []
    elements = visual_registry.get("elements", [])
    registry_boxes = [
        _bbox_from_registry(item)
        for item in elements
        if isinstance(item, dict) and isinstance(item.get("blueprint_bbox_px"), (dict, list, tuple))
    ] if isinstance(elements, list) else []
    context = resolve_coordinate_context(
        plan_size=semantic_plan.get("image_size") if isinstance(semantic_plan.get("image_size"), dict) else None,
        image_size=image_size,
        registry_size=visual_registry.get("blueprint_canvas_px") if isinstance(visual_registry.get("blueprint_canvas_px"), dict) else None,
        semantic_extent=_extent_from_bboxes(semantic_boxes),
        registry_extent=_extent_from_bboxes(registry_boxes),
    )

    visual_nodes = _semantic_container_nodes(semantic_plan, context)
    existing_ids = {node.node_id for node in visual_nodes}
    visual_nodes.extend(node for node in _visual_nodes(visual_registry, context) if node.node_id not in existing_ids)
    text_nodes = _text_nodes(script_sections, semantic_plan)
    relations = _relations(visual_nodes)
    return PageSceneGraph(
        page=page_number,
        coordinate_context=context,
        truth_sources={
            "script": {"authority": "text_truth"},
            "ocr": {"authority": "locator_evidence_only"},
            "visual_registry": {"authority": "visual_geometry"},
            "semantic_plan": {"authority": "container_geometry"},
        },
        visual_nodes=visual_nodes,
        text_nodes=text_nodes,
        relations=relations,
        layout_intents=_layout_intents(text_nodes, visual_nodes, relations),
        metadata={"builder": "scene_graph.builder.v1"},
    )
