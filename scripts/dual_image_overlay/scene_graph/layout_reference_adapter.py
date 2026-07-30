from __future__ import annotations

from typing import Any, Mapping

from .coordinate import normalize_bbox
from .schema import BBox, Relation, VisualNode


LAYOUT_REFERENCE_ADAPTER_SCHEMA = "cyberppt.layout_reference_adapter.v1"


def _bbox_xywh(value: Any) -> BBox | None:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            x, y, width, height = (float(item) for item in value)
        except (TypeError, ValueError):
            return None
        if width <= 0 or height <= 0:
            return None
        return BBox(x, y, x + width, y + height)
    if isinstance(value, Mapping):
        try:
            return BBox.from_any(value)
        except ValueError:
            return None
    return None


def _reference_bbox(raw: Mapping[str, Any]) -> BBox | None:
    bbox = _bbox_xywh(raw.get("bbox_px"))
    if bbox is not None:
        return bbox
    value = raw.get("bbox")
    if isinstance(value, Mapping):
        try:
            return BBox.from_any(value)
        except ValueError:
            return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return BBox.from_any(value)
        except ValueError:
            return None
    return None


def _iter_reference_items(layout_reference: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    result: list[tuple[str, Mapping[str, Any]]] = []
    for key in ("zones", "visual_anchors"):
        values = layout_reference.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, Mapping):
                result.append((key, value))
    return result


def adapt_layout_reference(
    layout_reference: Mapping[str, Any] | None,
    *,
    coordinate_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert slide-image-rebuild layout evidence into Scene Graph inputs.

    The adapter preserves detected expression structure and geometry evidence.
    It does not select a template or create a new layout.
    """

    if not layout_reference:
        return {
            "schema": LAYOUT_REFERENCE_ADAPTER_SCHEMA,
            "visual_nodes": [],
            "relations": [],
            "metadata": {"consumed": False},
        }

    input_space = (
        coordinate_context.get("image_size")
        or coordinate_context.get("semantic_input_space")
        or coordinate_context.get("coordinate_space")
    )
    if not isinstance(input_space, Mapping):
        raise ValueError("coordinate_context must provide an image or coordinate input space")
    visual_nodes: list[VisualNode] = []
    seen_ids: set[str] = set()
    for index, (collection, raw) in enumerate(_iter_reference_items(layout_reference), start=1):
        bbox = _reference_bbox(raw)
        if bbox is None:
            continue
        node_id = str(raw.get("id") or raw.get("zone_id") or raw.get("anchor_id") or f"recognized_{index}")
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        role = str(raw.get("role") or raw.get("semantic_role") or raw.get("type") or "recognized_region")
        node_type = str(raw.get("node_type") or ("layout_zone" if collection == "zones" else "visual_anchor"))
        visual_nodes.append(
            VisualNode(
                node_id=node_id,
                node_type=node_type,
                semantic_role=role,
                bbox=normalize_bbox(bbox, input_space, coordinate_context),
                source={"kind": "layout_reference", "collection": collection},
                confidence=float(raw.get("confidence") or 1.0),
                component_id=raw.get("component_id"),
                attributes={
                    "recognized_layout": True,
                    "reference_payload": dict(raw),
                },
            )
        )

    node_ids = {node.node_id for node in visual_nodes}
    relations: list[Relation] = []
    contract = layout_reference.get("structure_contract")
    raw_relations = contract.get("relations", []) if isinstance(contract, Mapping) else []
    if isinstance(raw_relations, list):
        for raw in raw_relations:
            if not isinstance(raw, Mapping):
                continue
            source_id = str(raw.get("source_id") or raw.get("from") or "")
            target_id = str(raw.get("target_id") or raw.get("to") or "")
            if source_id not in node_ids or target_id not in node_ids:
                continue
            relations.append(
                Relation(
                    type=str(raw.get("type") or raw.get("relation") or "related_to"),
                    source_id=source_id,
                    target_id=target_id,
                    metrics={"source": "layout_reference.structure_contract"},
                    confidence=float(raw.get("confidence") or 1.0),
                )
            )

    return {
        "schema": LAYOUT_REFERENCE_ADAPTER_SCHEMA,
        "visual_nodes": visual_nodes,
        "relations": relations,
        "metadata": {
            "consumed": True,
            "source_version": layout_reference.get("version"),
            "layout_grammar": layout_reference.get("layout_grammar"),
            "structure_contract": contract,
            "geometry_locks": layout_reference.get("geometry_locks", []),
            "recognized_node_count": len(visual_nodes),
        },
    }
