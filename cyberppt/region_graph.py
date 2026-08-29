"""Semantic macro-space contract for Stage 02 Region Graphs.

Region Graph sits between the semantic graph and pixel geometry. It records
where semantic evidence belongs at a normalized page-structure level without
turning Stage 02 into a fixed-layout/template engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


REGION_GRAPH_CANVAS_RATIO = "2:1"
REGION_GRAPH_PRIMARY_AXES = frozenset({
    "horizontal",
    "vertical",
    "radial",
    "bidirectional",
    "layered",
    "free_spatial",
})
REGION_GRAPH_ANCHORS = frozenset({
    "left",
    "center",
    "right",
    "top",
    "bottom",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
    "free",
})
REGION_GRAPH_SPANS = frozenset({"compact", "half", "full", "band", "free"})
REGION_GRAPH_PRIORITIES = frozenset({"primary", "secondary", "tertiary"})
REGION_GRAPH_RELATION_TYPES = frozenset({
    "peer",
    "flow",
    "converge",
    "dependency",
    "feedback",
    "boundary",
    "interface",
    "allocation",
    "support",
    "containment",
})


@dataclass(frozen=True)
class RegionSpec:
    id: str
    semantic_refs: tuple[str, ...]
    role: str
    anchor: str
    weight: float
    span: str
    priority: str
    text_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegionRelationSpec:
    source: str
    target: str
    type: str


@dataclass(frozen=True)
class RegionGraphSpec:
    canvas_ratio: str
    primary_axis: str
    regions: tuple[RegionSpec, ...]
    relations: tuple[RegionRelationSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas_ratio": self.canvas_ratio,
            "primary_axis": self.primary_axis,
            "regions": [
                {
                    "id": item.id,
                    "semantic_refs": list(item.semantic_refs),
                    "role": item.role,
                    "anchor": item.anchor,
                    "weight": item.weight,
                    "span": item.span,
                    "priority": item.priority,
                    **({"text_ids": list(item.text_ids)} if item.text_ids else {}),
                }
                for item in self.regions
            ],
            "relations": [
                {"from": item.source, "to": item.target, "type": item.type}
                for item in self.relations
            ],
        }


def _strings(value: object, *, field: str, required: bool = True) -> tuple[str, ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Region Graph {field} must be an array")
    values = tuple(str(item or "").strip() for item in value)
    if required and not values:
        raise ValueError(f"Region Graph {field} must not be empty")
    if any(not item for item in values) or len(values) != len(set(values)):
        raise ValueError(f"Region Graph {field} must contain unique non-empty values")
    return values


def _evidence_refs(value: object, *, field: str) -> tuple[str, ...]:
    refs = _strings(value, field=field)
    if any(not ref.startswith("E") or not ref[1:].isdigit() for ref in refs):
        raise ValueError(f"Region Graph {field} must contain E<number> semantic refs")
    return refs


def validate_region_graph(value: Mapping[str, object]) -> RegionGraphSpec:
    """Validate and normalize a Region Graph without inferring layout or topology.

    Cross-field reference integrity is enforced here because JSON Schema cannot
    reliably assert that relation endpoints exist in the same region-id set.
    """

    if not isinstance(value, Mapping):
        raise ValueError("Region Graph must be an object")
    canvas_ratio = str(value.get("canvas_ratio") or "").strip()
    if canvas_ratio != REGION_GRAPH_CANVAS_RATIO:
        raise ValueError(f"Region Graph canvas_ratio must be {REGION_GRAPH_CANVAS_RATIO}")
    primary_axis = str(value.get("primary_axis") or "").strip()
    if primary_axis not in REGION_GRAPH_PRIMARY_AXES:
        raise ValueError(f"unsupported Region Graph primary_axis: {primary_axis!r}")

    raw_regions = value.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise ValueError("Region Graph regions must be a non-empty array")
    regions: list[RegionSpec] = []
    region_ids: set[str] = set()
    for index, raw in enumerate(raw_regions, 1):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Region Graph regions[{index}] must be an object")
        region_id = str(raw.get("id") or "").strip()
        if not region_id.startswith("RG") or not region_id[2:].isdigit():
            raise ValueError(f"Region Graph regions[{index}].id must match RG<number>")
        if region_id in region_ids:
            raise ValueError(f"duplicate Region Graph region id: {region_id}")
        region_ids.add(region_id)
        role = str(raw.get("role") or "").strip()
        if not role:
            raise ValueError(f"Region Graph regions[{index}].role is required")
        anchor = str(raw.get("anchor") or "").strip()
        if anchor not in REGION_GRAPH_ANCHORS:
            raise ValueError(f"unsupported Region Graph anchor: {anchor!r}")
        span = str(raw.get("span") or "").strip()
        if span not in REGION_GRAPH_SPANS:
            raise ValueError(f"unsupported Region Graph span: {span!r}")
        priority = str(raw.get("priority") or "").strip()
        if priority not in REGION_GRAPH_PRIORITIES:
            raise ValueError(f"unsupported Region Graph priority: {priority!r}")
        try:
            weight = float(raw.get("weight"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Region Graph regions[{index}].weight must be numeric") from exc
        if not 0 < weight <= 1:
            raise ValueError(f"Region Graph regions[{index}].weight must be >0 and <=1")
        regions.append(
            RegionSpec(
                id=region_id,
                semantic_refs=_evidence_refs(raw.get("semantic_refs"), field=f"regions[{index}].semantic_refs"),
                role=role,
                anchor=anchor,
                weight=weight,
                span=span,
                priority=priority,
                text_ids=_strings(raw.get("text_ids"), field=f"regions[{index}].text_ids", required=False),
            )
        )

    raw_relations = value.get("relations")
    if not isinstance(raw_relations, list):
        raise ValueError("Region Graph relations must be an array")
    relations: list[RegionRelationSpec] = []
    seen_relations: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_relations, 1):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Region Graph relations[{index}] must be an object")
        source = str(raw.get("from") or "").strip()
        target = str(raw.get("to") or "").strip()
        relation_type = str(raw.get("type") or "").strip()
        if source not in region_ids or target not in region_ids:
            raise ValueError(f"Region Graph relations[{index}] references an unknown region")
        if source == target:
            raise ValueError(f"Region Graph relations[{index}] must connect distinct regions")
        if relation_type not in REGION_GRAPH_RELATION_TYPES:
            raise ValueError(f"unsupported Region Graph relation type: {relation_type!r}")
        signature = (source, target, relation_type)
        if signature in seen_relations:
            raise ValueError(f"duplicate Region Graph relation: {signature!r}")
        seen_relations.add(signature)
        relations.append(RegionRelationSpec(source=source, target=target, type=relation_type))

    return RegionGraphSpec(
        canvas_ratio=canvas_ratio,
        primary_axis=primary_axis,
        regions=tuple(regions),
        relations=tuple(relations),
    )


__all__ = [
    "REGION_GRAPH_ANCHORS",
    "REGION_GRAPH_CANVAS_RATIO",
    "REGION_GRAPH_PRIMARY_AXES",
    "REGION_GRAPH_PRIORITIES",
    "REGION_GRAPH_RELATION_TYPES",
    "REGION_GRAPH_SPANS",
    "RegionGraphSpec",
    "RegionRelationSpec",
    "RegionSpec",
    "validate_region_graph",
]
