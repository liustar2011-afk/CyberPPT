from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


SCHEMA = "cyberppt.page_scene_graph.v1"
NORMALIZED_CANVAS = {"width": 1280.0, "height": 720.0}
TEXT_TRUTH_AUTHORITIES = {"script", "content_lock", "manual_override"}
LOCATOR_ONLY_AUTHORITIES = {"ocr", "text_layout"}
BINDING_TYPES = {
    "container_text",
    "edge_label",
    "anchor_label",
    "free_annotation",
    "title_chrome",
    "legend_label",
}
BLOCKING_ISSUE_CODES = {
    "missing_truth_binding",
    "coordinate_space_unresolved",
    "registry_container_without_text",
    "script_truth_mismatch",
    "safe_bbox_conflict",
    "render_text_missing",
    "render_overlap",
}


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError(f"Expected mapping-compatible value, got {type(value).__name__}")


@dataclass(frozen=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x1", float(self.x1))
        object.__setattr__(self, "y1", float(self.y1))
        object.__setattr__(self, "x2", float(self.x2))
        object.__setattr__(self, "y2", float(self.y2))

    def as_list(self) -> list[float]:
        return [float(round(value, 3)) for value in (self.x1, self.y1, self.x2, self.y2)]

    def to_dict(self) -> dict[str, float]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

    @classmethod
    def from_any(cls, value: Any) -> "BBox":
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return cls(value[0], value[1], value[2], value[3])
        if isinstance(value, Mapping):
            if {"x1", "y1", "x2", "y2"}.issubset(value):
                return cls(value["x1"], value["y1"], value["x2"], value["y2"])
            if {"x", "y", "w", "h"}.issubset(value):
                x = float(value["x"])
                y = float(value["y"])
                return cls(x, y, x + float(value["w"]), y + float(value["h"]))
        raise ValueError("BBox must be a BBox, [x1, y1, x2, y2], or bbox mapping")


@dataclass(frozen=True)
class CoordinateContext:
    normalized_canvas: dict[str, float] = field(default_factory=lambda: dict(NORMALIZED_CANVAS))
    coordinate_space: Any = "normalized_canvas"
    source: dict[str, Any] | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                **dict(self.details),
                "normalized_canvas": dict(self.normalized_canvas),
                "coordinate_space": self.coordinate_space,
                "source": self.source,
            }
        )

    @classmethod
    def from_any(cls, value: Any) -> "CoordinateContext":
        if isinstance(value, cls):
            return value
        payload = _as_dict(value)
        details = {
            key: payload[key]
            for key in payload
            if key not in {"normalized_canvas", "coordinate_space", "source"}
        }
        return cls(
            normalized_canvas=dict(payload.get("normalized_canvas", NORMALIZED_CANVAS)),
            coordinate_space=payload.get("coordinate_space", "normalized_canvas"),
            source=payload.get("source"),
            details=details,
        )


@dataclass(frozen=True)
class TruthSource:
    kind: str
    path: str | None = None
    authority: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "kind": self.kind,
                "path": self.path,
                "authority": self.authority,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_any(cls, value: Any) -> "TruthSource":
        if isinstance(value, cls):
            return value
        payload = _as_dict(value)
        return cls(
            kind=payload["kind"],
            path=payload.get("path"),
            authority=payload.get("authority"),
            metadata=payload.get("metadata"),
        )


@dataclass(frozen=True)
class VisualNode:
    node_id: str
    node_type: str
    semantic_role: str
    bbox: BBox
    source: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    component_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "bbox", BBox.from_any(self.bbox))
        object.__setattr__(self, "confidence", float(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "node_id": self.node_id,
                "node_type": self.node_type,
                "semantic_role": self.semantic_role,
                "bbox": self.bbox.as_list(),
                "source": dict(self.source),
                "confidence": self.confidence,
                "component_id": self.component_id,
                "attributes": dict(self.attributes) if self.attributes else None,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VisualNode":
        return cls(
            node_id=payload["node_id"],
            node_type=payload["node_type"],
            semantic_role=payload["semantic_role"],
            bbox=BBox.from_any(payload["bbox"]),
            source=dict(payload.get("source", {})),
            confidence=payload.get("confidence", 1.0),
            component_id=payload.get("component_id"),
            attributes=dict(payload.get("attributes", {})),
        )


@dataclass(frozen=True)
class TextBinding:
    type: str
    target_id: str | None = None
    placement: str | None = None
    safe_bbox: BBox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.safe_bbox is not None:
            object.__setattr__(self, "safe_bbox", BBox.from_any(self.safe_bbox))

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "type": self.type,
                "target_id": self.target_id,
                "placement": self.placement,
                "safe_bbox": self.safe_bbox.as_list() if self.safe_bbox else None,
                "metadata": dict(self.metadata) if self.metadata else None,
            }
        )

    @classmethod
    def from_any(cls, value: Any) -> "TextBinding":
        if isinstance(value, cls):
            return value
        payload = _as_dict(value)
        return cls(
            type=payload["type"],
            target_id=payload.get("target_id"),
            placement=payload.get("placement"),
            safe_bbox=BBox.from_any(payload["safe_bbox"]) if payload.get("safe_bbox") else None,
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class TextNode:
    node_id: str
    text: str
    truth_source: dict[str, Any]
    semantic_role: str
    binding: TextBinding | None = None
    bbox_preferred: BBox | None = None
    style: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.binding is not None:
            object.__setattr__(self, "binding", TextBinding.from_any(self.binding))
        if self.bbox_preferred is not None:
            object.__setattr__(self, "bbox_preferred", BBox.from_any(self.bbox_preferred))

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "node_id": self.node_id,
                "text": self.text,
                "truth_source": dict(self.truth_source),
                "semantic_role": self.semantic_role,
                "binding": self.binding.to_dict() if self.binding else None,
                "bbox_preferred": self.bbox_preferred.as_list() if self.bbox_preferred else None,
                "style": dict(self.style) if self.style else None,
                "attributes": dict(self.attributes) if self.attributes else None,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TextNode":
        if "bbox" in payload:
            raise ValueError("TextNode payload must use bbox_preferred, not bbox")
        return cls(
            node_id=payload["node_id"],
            text=payload["text"],
            truth_source=dict(payload.get("truth_source", {})),
            semantic_role=payload["semantic_role"],
            binding=TextBinding.from_any(payload["binding"]) if payload.get("binding") else None,
            bbox_preferred=BBox.from_any(payload["bbox_preferred"]) if payload.get("bbox_preferred") else None,
            style=dict(payload.get("style", {})),
            attributes=dict(payload.get("attributes", {})),
        )


@dataclass(frozen=True)
class Relation:
    type: str
    source_id: str
    target_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", float(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "type": self.type,
                "source_id": self.source_id,
                "target_id": self.target_id,
                "metrics": dict(self.metrics),
                "confidence": self.confidence,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Relation":
        if "relation_type" in payload:
            raise ValueError("Relation payload must use type, not relation_type")
        return cls(
            type=payload["type"],
            source_id=payload["source_id"],
            target_id=payload["target_id"],
            metrics=dict(payload.get("metrics", {})),
            confidence=payload.get("confidence", 1.0),
        )


@dataclass(frozen=True)
class LayoutIntent:
    type: str
    node_id: str
    target_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "type": self.type,
                "node_id": self.node_id,
                "target_id": self.target_id,
                "parameters": dict(self.parameters),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LayoutIntent":
        if "intent_type" in payload:
            raise ValueError("LayoutIntent payload must use type, not intent_type")
        return cls(
            type=payload["type"],
            node_id=payload["node_id"],
            target_id=payload.get("target_id"),
            parameters=dict(payload.get("parameters", {})),
        )


@dataclass(frozen=True)
class GateIssue:
    severity: str
    code: str
    node_id: str | None
    source: dict[str, Any]
    evidence: dict[str, Any]
    recommended_action: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        if not isinstance(self.blocking, bool):
            raise ValueError("GateIssue blocking must be a bool")
        return {
            "severity": self.severity,
            "code": self.code,
            "node_id": self.node_id,
            "source": dict(self.source),
            "evidence": dict(self.evidence),
            "recommended_action": self.recommended_action,
            "blocking": self.blocking,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GateIssue":
        blocking = payload["blocking"]
        if not isinstance(blocking, bool):
            raise ValueError("GateIssue blocking must be a bool")
        return cls(
            severity=payload["severity"],
            code=payload["code"],
            node_id=payload.get("node_id"),
            source=dict(payload.get("source", {})),
            evidence=dict(payload.get("evidence", {})),
            recommended_action=payload["recommended_action"],
            blocking=blocking,
        )


@dataclass(frozen=True)
class PageSceneGraph:
    page: int
    coordinate_context: CoordinateContext | dict[str, Any] = field(default_factory=CoordinateContext)
    truth_sources: dict[str, Any] = field(default_factory=dict)
    visual_nodes: list[VisualNode] = field(default_factory=list)
    text_nodes: list[TextNode] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    layout_intents: list[LayoutIntent] = field(default_factory=list)
    gates: dict[str, Any] = field(default_factory=dict)
    gate_issues: list[GateIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "coordinate_context", CoordinateContext.from_any(self.coordinate_context))
        object.__setattr__(self, "visual_nodes", [node if isinstance(node, VisualNode) else VisualNode.from_dict(node) for node in self.visual_nodes])
        object.__setattr__(self, "text_nodes", [node if isinstance(node, TextNode) else TextNode.from_dict(node) for node in self.text_nodes])
        object.__setattr__(self, "relations", [rel if isinstance(rel, Relation) else Relation.from_dict(rel) for rel in self.relations])
        object.__setattr__(
            self,
            "layout_intents",
            [intent if isinstance(intent, LayoutIntent) else LayoutIntent.from_dict(intent) for intent in self.layout_intents],
        )
        object.__setattr__(self, "gates", dict(self.gates))
        object.__setattr__(
            self,
            "gate_issues",
            [issue if isinstance(issue, GateIssue) else GateIssue.from_dict(issue) for issue in self.gate_issues],
        )

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(
            {
                "schema": SCHEMA,
                "page": self.page,
                "coordinate_context": self.coordinate_context.to_dict(),
                "truth_sources": dict(self.truth_sources),
                "visual_nodes": [node.to_dict() for node in self.visual_nodes],
                "text_nodes": [node.to_dict() for node in self.text_nodes],
                "relations": [relation.to_dict() for relation in self.relations],
                "layout_intents": [intent.to_dict() for intent in self.layout_intents],
                "gates": dict(self.gates),
                "gate_issues": [issue.to_dict() for issue in self.gate_issues],
                "metadata": dict(self.metadata) if self.metadata else None,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PageSceneGraph":
        schema = payload.get("schema")
        if schema != SCHEMA:
            raise ValueError(f"Unsupported scene graph schema: {schema}")
        return cls(
            page=payload["page"],
            coordinate_context=payload.get("coordinate_context", {}),
            truth_sources=dict(payload.get("truth_sources", {})),
            visual_nodes=[VisualNode.from_dict(node) for node in payload.get("visual_nodes", [])],
            text_nodes=[TextNode.from_dict(node) for node in payload.get("text_nodes", [])],
            relations=[Relation.from_dict(relation) for relation in payload.get("relations", [])],
            layout_intents=[LayoutIntent.from_dict(intent) for intent in payload.get("layout_intents", [])],
            gates=dict(payload.get("gates") or {}),
            gate_issues=[GateIssue.from_dict(issue) for issue in payload.get("gate_issues", [])],
            metadata=dict(payload.get("metadata", {})),
        )


def scene_graph_to_dict(graph: PageSceneGraph) -> dict[str, Any]:
    if not isinstance(graph, PageSceneGraph):
        raise ValueError("scene_graph_to_dict expects a PageSceneGraph")
    return graph.to_dict()


def scene_graph_from_dict(payload: Mapping[str, Any]) -> PageSceneGraph:
    return PageSceneGraph.from_dict(payload)
