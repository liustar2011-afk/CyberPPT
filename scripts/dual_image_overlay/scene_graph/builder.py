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


def _style_from_item(item: Mapping[str, Any]) -> dict[str, Any]:
    style: dict[str, Any] = {}
    for source_key, target_key in (
        ("font_size", "font_size"),
        ("fill", "fill"),
        ("font_family", "font_family"),
        ("font_weight", "font_weight"),
        ("bold", "bold"),
        ("align", "align"),
        ("word_wrap", "word_wrap"),
    ):
        if source_key in item:
            style[target_key] = item[source_key]
    return style


def _container_safe_bbox(semantic_plan: Mapping[str, Any], container_id: str, context: Mapping[str, Any]) -> BBox | None:
    containers = semantic_plan.get("containers", [])
    if not isinstance(containers, list):
        return None
    input_space = context["semantic_input_space"]
    for container in containers:
        if not isinstance(container, dict) or str(container.get("id") or "") != container_id:
            continue
        raw = container.get("text_safe_bbox") or container.get("bbox")
        if raw is None:
            return None
        return normalize_bbox(BBox.from_any(raw), input_space, context)
    return None


def _source_capture_style_by_text(source_capture_page: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not source_capture_page:
        return {}
    result: dict[str, dict[str, Any]] = {}
    text_objects = source_capture_page.get("text_objects", [])
    if not isinstance(text_objects, list):
        return result
    for item in text_objects:
        if not isinstance(item, dict):
            continue
        text = str(item.get("rendered_text") or item.get("text") or "").strip()
        style = item.get("style") if isinstance(item.get("style"), dict) else {}
        if text and style:
            result[_normalize_text(text)] = {
                "font_family": style.get("font_family"),
                "font_size": style.get("applied_font_size_px") or style.get("font_size_px"),
                "fill": style.get("fill"),
                "font_weight": style.get("font_weight"),
                "align": style.get("align"),
                "word_wrap": style.get("word_wrap"),
                "typography_role": style.get("typography_role"),
            }
    return {key: {k: v for k, v in value.items() if v is not None} for key, value in result.items()}


def _text_nodes(
    script_sections: Mapping[str, list[dict[str, Any]]],
    semantic_plan: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    source_capture_page: Mapping[str, Any] | None = None,
) -> list[TextNode]:
    nodes: list[TextNode] = []
    source_capture_style = _source_capture_style_by_text(source_capture_page)
    semantic_items = [item for item in semantic_plan.get("items", []) if isinstance(item, dict)] if isinstance(semantic_plan.get("items"), list) else []
    for index, text in enumerate(_build_application_text(script_sections), start=1):
        target_id = f"application_{index}"
        matching_item = next(
            (
                item
                for item in semantic_items
                if str(item.get("container_id") or "") == target_id
                or _normalize_text(str(item.get("display_text") or item.get("text") or "")) == _normalize_text(text)
            ),
            {},
        )
        style = {**_style_from_item(matching_item), **source_capture_style.get(_normalize_text(text), {})}
        nodes.append(
            TextNode(
                node_id=f"text_application_{index}",
                text=text,
                truth_source={"kind": "script"},
                semantic_role="application_card_text",
                binding=TextBinding(
                    type="container_text",
                    target_id=target_id,
                    placement="inside",
                    safe_bbox=_container_safe_bbox(semantic_plan, target_id, context),
                ),
                style=style,
            )
        )

    for index, item in enumerate(semantic_items, start=1):
        text = str(item.get("display_text") or item.get("text") or "").strip()
        if not text:
            continue
        role = str(item.get("role") or "body")
        style = {**_style_from_item(item), **source_capture_style.get(_normalize_text(text), {})}
        if role == "arrow_label" and item.get("target_id"):
            nodes.append(
                TextNode(
                    node_id=f"text_semantic_{index}",
                    text=text,
                    truth_source={"kind": "script"},
                    semantic_role=role,
                    binding=TextBinding(type="edge_label", target_id=str(item["target_id"]), placement="above"),
                    style=style,
                )
            )
        elif item.get("container_id") and not any(_normalize_text(text) == _normalize_text(existing.text) for existing in nodes):
            target_id = str(item["container_id"])
            nodes.append(
                TextNode(
                    node_id=f"text_semantic_{index}",
                    text=text,
                    truth_source={"kind": "script"},
                    semantic_role=role,
                    binding=TextBinding(
                        type="container_text",
                        target_id=target_id,
                        placement="inside",
                        safe_bbox=_container_safe_bbox(semantic_plan, target_id, context),
                    ),
                    style=style,
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


def _semantic_layout_relations(semantic_layout_plan: Mapping[str, Any] | None, visual_nodes: list[VisualNode]) -> list[Relation]:
    if not semantic_layout_plan:
        return []
    visual_ids = {node.node_id for node in visual_nodes}
    relations: list[Relation] = []
    raw_relations = semantic_layout_plan.get("container_relations", [])
    if not isinstance(raw_relations, list):
        return relations
    for relation in raw_relations:
        if not isinstance(relation, dict):
            continue
        source_id = str(relation.get("container_id") or "")
        target_id = str(relation.get("element_id") or "")
        if source_id not in visual_ids or target_id not in visual_ids:
            continue
        relation_type = str(relation.get("relation") or "contains")
        if relation_type == "contained_or_component_matched":
            relation_type = "contains"
        relations.append(
            Relation(
                type=relation_type,
                source_id=source_id,
                target_id=target_id,
                metrics={
                    key: relation.get(key)
                    for key in ("bbox", "element_type", "source_component_id", "container_role")
                    if key in relation
                },
                confidence=0.95,
            )
        )
    return relations


def _dedupe_relations(relations: list[Relation]) -> list[Relation]:
    result: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    for relation in relations:
        key = (relation.type, relation.source_id, relation.target_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(relation)
    return result


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


def _text_by_capture_key(text_nodes: list[TextNode]) -> dict[str, TextNode]:
    result: dict[str, TextNode] = {}
    for node in text_nodes:
        result[_normalize_text(node.text)] = node
        first_line = node.text.splitlines()[0] if node.text else ""
        if first_line:
            result.setdefault(_normalize_text(first_line), node)
    return result


def _neighbor_layout_intents(
    semantic_layout_plan: Mapping[str, Any] | None,
    text_nodes: list[TextNode],
    visual_nodes: list[VisualNode],
) -> list[LayoutIntent]:
    if not semantic_layout_plan:
        return []
    visual_by_id = {node.node_id: node for node in visual_nodes}
    text_by_key = _text_by_capture_key(text_nodes)
    neighbors = semantic_layout_plan.get("text_neighbors", [])
    if not isinstance(neighbors, list):
        return []
    intents: list[LayoutIntent] = []
    for neighbor in neighbors:
        if not isinstance(neighbor, dict):
            continue
        text = text_by_key.get(_normalize_text(str(neighbor.get("text") or "")))
        nearest = neighbor.get("nearest") if isinstance(neighbor.get("nearest"), dict) else {}
        if text is None or not nearest:
            continue
        for side, candidate in nearest.items():
            candidates = candidate if side == "overlapping" and isinstance(candidate, list) else [candidate]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                target_id = str(item.get("element_id") or "")
                target = visual_by_id.get(target_id)
                if target is None:
                    continue
                parameters = {
                    key: item.get(key)
                    for key in ("distance", "axis_overlap", "bbox", "element_type", "overlap_area")
                    if key in item
                }
                parameters["side"] = side
                intents.append(LayoutIntent(type="neighbor_context", node_id=text.node_id, target_id=target_id, parameters=parameters))
                if target.node_type in TEXT_ZONE_TYPES:
                    intents.append(LayoutIntent(type="honor_text_zone", node_id=text.node_id, target_id=target_id, parameters=parameters))
                elif target.node_type in RESERVED_TYPES:
                    intents.append(LayoutIntent(type="avoid_reserved_zone", node_id=text.node_id, target_id=target_id, parameters=parameters))
    return intents


def _dedupe_intents(intents: list[LayoutIntent]) -> list[LayoutIntent]:
    result: list[LayoutIntent] = []
    seen: set[tuple[str, str, str | None]] = set()
    for intent in intents:
        key = (intent.type, intent.node_id, intent.target_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(intent)
    return result


def build_page_scene_graph(
    *,
    page_number: int,
    script_sections: Mapping[str, list[dict[str, Any]]],
    semantic_plan: Mapping[str, Any],
    visual_registry: Mapping[str, Any],
    image_size: Mapping[str, Any],
    semantic_layout_plan: Mapping[str, Any] | None = None,
    source_capture_page: Mapping[str, Any] | None = None,
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
    text_nodes = _text_nodes(script_sections, semantic_plan, context, source_capture_page=source_capture_page)
    relations = _dedupe_relations([*_relations(visual_nodes), *_semantic_layout_relations(semantic_layout_plan, visual_nodes)])
    layout_intents = _dedupe_intents([*_layout_intents(text_nodes, visual_nodes, relations), *_neighbor_layout_intents(semantic_layout_plan, text_nodes, visual_nodes)])
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
        layout_intents=layout_intents,
        metadata={
            "builder": "scene_graph.builder.v1",
            "semantic_layout_plan_consumed": bool(semantic_layout_plan),
            "source_capture_page_consumed": bool(source_capture_page),
        },
    )
