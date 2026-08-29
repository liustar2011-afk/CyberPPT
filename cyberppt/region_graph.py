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
REGION_GRAPH_TOPOLOGIES = frozenset({
    "parallel_set",
    "causal_convergence",
    "layered_architecture",
    "directed_flow",
    "lifecycle_loop",
    "governance_boundary",
    "ecosystem_map",
    "allocation_flow",
    "conclusion_anchor",
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


_AXIS_BY_TOPOLOGY = {
    "parallel_set": "free_spatial",
    "causal_convergence": "radial",
    "layered_architecture": "layered",
    "directed_flow": "horizontal",
    "lifecycle_loop": "radial",
    "governance_boundary": "horizontal",
    "ecosystem_map": "free_spatial",
    "allocation_flow": "horizontal",
    "conclusion_anchor": "horizontal",
}

_RELATION_TYPE_MAP = {
    "peer": "peer",
    "flow": "flow",
    "transform": "flow",
    "converge": "converge",
    "diverge": "allocation",
    "layer": "dependency",
    "dependency": "dependency",
    "boundary": "boundary",
    "control": "boundary",
    "interface": "interface",
    "exchange": "interface",
    "allocation": "allocation",
    "support": "support",
    "cause": "support",
    "evidence": "support",
    "responsibility": "support",
}


def _axis_anchor(axis: str, position: int, total: int) -> str:
    if total <= 1:
        return "center"
    if axis in {"horizontal", "bidirectional"}:
        if position == 0:
            return "left"
        if position == total - 1:
            return "right"
        return "center"
    if axis in {"vertical", "layered"}:
        if position == 0:
            return "top"
        if position == total - 1:
            return "bottom"
        return "center"
    return "free"


def _region_role(topology: str, evidence_id: str, focus_id: str, position: int) -> str:
    if topology == "parallel_set":
        return "peer"
    if topology == "causal_convergence":
        return "result" if evidence_id == focus_id else "source"
    if topology == "layered_architecture":
        return "layer"
    if topology == "directed_flow":
        return "result" if evidence_id == focus_id else "stage"
    if topology == "lifecycle_loop":
        return "lifecycle_stage"
    if topology == "governance_boundary":
        return "boundary_anchor" if evidence_id == focus_id else "boundary_participant"
    if topology == "ecosystem_map":
        return "actor"
    if topology == "allocation_flow":
        return "source" if position == 0 else "destination"
    if topology == "conclusion_anchor":
        return "conclusion" if evidence_id == focus_id else "evidence"
    raise ValueError(f"unsupported Region Graph topology: {topology!r}")


def _region_anchor(
    topology: str,
    evidence_id: str,
    focus_id: str,
    position: int,
    total: int,
    axis: str,
) -> str:
    if topology == "causal_convergence":
        return "center" if evidence_id == focus_id else "free"
    if topology in {"parallel_set", "ecosystem_map", "lifecycle_loop"}:
        return "free"
    if topology == "governance_boundary":
        if evidence_id == focus_id:
            return "center"
        focus_position = max(0, min(total - 1, position))
        return "left" if position < focus_position else "right"
    return _axis_anchor(axis, position, total)


def _region_weight(focus_policy: str, evidence_id: str, focus_id: str, total: int) -> float:
    if total <= 1:
        return 1.0
    if focus_policy == "single_anchor":
        if evidence_id == focus_id:
            return 0.4
        return round(0.6 / (total - 1), 4)
    return round(1.0 / total, 4)


def _region_span(topology: str, evidence_id: str, focus_id: str) -> str:
    if topology == "layered_architecture":
        return "band"
    if topology in {"parallel_set", "ecosystem_map", "lifecycle_loop"}:
        return "free"
    if evidence_id == focus_id and topology in {"causal_convergence", "conclusion_anchor"}:
        return "half"
    if topology == "governance_boundary":
        return "half"
    return "compact"


def _region_priority(focus_policy: str, evidence_id: str, focus_id: str) -> str:
    if focus_policy == "single_anchor" and evidence_id != focus_id:
        return "secondary"
    return "primary"


def _region_relation_type(edge: Mapping[str, object]) -> str:
    relation = str(edge.get("relation") or "").strip()
    if relation == "loop":
        return "feedback" if str(edge.get("direction") or "").strip() == "backward" else "flow"
    return _RELATION_TYPE_MAP.get(relation, "support")


def build_region_graph(
    *,
    topology: str,
    evidence_ids: list[str] | tuple[str, ...],
    focus_id: str,
    reading_sequence: list[str] | tuple[str, ...],
    semantic_edges: list[Mapping[str, object]] | tuple[Mapping[str, object], ...],
    focus_policy: str,
) -> dict[str, Any]:
    """Compile a topology-aware normalized Region Graph from audited semantics.

    The function chooses macro region roles, anchors and relative weights only.
    It never emits pixel coordinates and never invents new semantic evidence.
    """

    if topology not in REGION_GRAPH_TOPOLOGIES:
        raise ValueError(f"unsupported Region Graph topology: {topology!r}")
    ids = tuple(str(value).strip() for value in evidence_ids)
    reading = tuple(str(value).strip() for value in reading_sequence)
    if not ids or any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Region Graph compiler requires unique evidence ids")
    if focus_id not in ids:
        raise ValueError("Region Graph compiler focus_id must reference evidence")
    if len(reading) != len(ids) or set(reading) != set(ids):
        raise ValueError("Region Graph compiler reading_sequence must cover every evidence id once")

    axis = _AXIS_BY_TOPOLOGY[topology]
    region_by_evidence = {evidence_id: f"RG{index:02d}" for index, evidence_id in enumerate(reading, 1)}
    focus_position = reading.index(focus_id)
    regions: list[dict[str, Any]] = []
    for position, evidence_id in enumerate(reading):
        anchor = _region_anchor(topology, evidence_id, focus_id, position, len(reading), axis)
        if topology == "governance_boundary" and evidence_id != focus_id:
            anchor = "left" if position < focus_position else "right"
        regions.append({
            "id": region_by_evidence[evidence_id],
            "semantic_refs": [evidence_id],
            "role": _region_role(topology, evidence_id, focus_id, position),
            "anchor": anchor,
            "weight": _region_weight(focus_policy, evidence_id, focus_id, len(reading)),
            "span": _region_span(topology, evidence_id, focus_id),
            "priority": _region_priority(focus_policy, evidence_id, focus_id),
        })

    relations: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in semantic_edges:
        source = str(edge.get("from") or "").strip()
        target = str(edge.get("to") or "").strip()
        if source not in region_by_evidence or target not in region_by_evidence or source == target:
            continue
        relation_type = _region_relation_type(edge)
        signature = (region_by_evidence[source], region_by_evidence[target], relation_type)
        if signature in seen:
            continue
        seen.add(signature)
        relations.append({"from": signature[0], "to": signature[1], "type": signature[2]})

    payload = {
        "canvas_ratio": REGION_GRAPH_CANVAS_RATIO,
        "primary_axis": axis,
        "regions": regions,
        "relations": relations,
    }
    return validate_region_graph(payload).to_dict()


__all__ = [
    "REGION_GRAPH_ANCHORS",
    "REGION_GRAPH_CANVAS_RATIO",
    "REGION_GRAPH_PRIMARY_AXES",
    "REGION_GRAPH_PRIORITIES",
    "REGION_GRAPH_RELATION_TYPES",
    "REGION_GRAPH_SPANS",
    "REGION_GRAPH_TOPOLOGIES",
    "RegionGraphSpec",
    "RegionRelationSpec",
    "RegionSpec",
    "build_region_graph",
    "validate_region_graph",
]
