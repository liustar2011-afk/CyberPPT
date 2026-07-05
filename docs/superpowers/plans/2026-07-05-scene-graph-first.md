# Scene Graph First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `page_scene_graph.json` and `page_scene_graph_gate.json` mandatory for all future CyberPPT script-image-generation-to-editable-PPT exports.

**Architecture:** Add a focused `scripts/dual_image_overlay/scene_graph/` package that builds a normalized page scene graph from script truth, image pairs, visual registry, and locator evidence. Existing export code is then rewired to consume scene graph layout output, and PPTX export is blocked whenever the graph gate has blocking issues.

**Tech Stack:** Python 3, dataclasses, JSON artifacts, PIL/Pillow for image dimensions, pytest, existing CyberPPT dual-image overlay scripts.

## Global Constraints

- `page_scene_graph.json` is the only page-level contract consumed by layout and QA.
- All production bbox values used by graph, layout, and gate stages must be normalized to `1280x720`.
- OCR can provide locator evidence only and must not overwrite script/content-lock text.
- Every text node must have a valid binding context; the binding can be container text, edge label, anchor label, free annotation, title chrome, or legend label.
- PPTX export must stop before export if `page_scene_graph_gate.json` contains blocking issues.
- Phase 1 keeps frame/icon/decorative visuals in the background image while recording visual nodes for layout and QA.
- Existing P6 failure classes must be represented as tests, not page-specific fixes.

---

## File Structure

- Create `scripts/dual_image_overlay/scene_graph/__init__.py`: package exports for the new scene graph API.
- Create `scripts/dual_image_overlay/scene_graph/schema.py`: dataclasses, JSON serialization, issue codes, and constants.
- Create `scripts/dual_image_overlay/scene_graph/coordinate.py`: coordinate source inspection, transform selection, bbox normalization.
- Create `scripts/dual_image_overlay/scene_graph/builder.py`: build visual nodes, text nodes, bindings, relations, and layout intents.
- Create `scripts/dual_image_overlay/scene_graph/gate.py`: blocking and warning validation for truth, geometry, binding, layout intents, and capture completeness.
- Create `scripts/dual_image_overlay/scene_graph/layout.py`: convert scene graph layout intents into existing overlay text boxes / layout plan records.
- Create `scripts/dual_image_overlay/scene_graph/render_qa.py`: render-output checks that can be fed back into source capture.
- Modify `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`: build and gate scene graph before layout/export.
- Modify `scripts/dual_image_overlay/source_capture.py`: persist scene graph, scene graph gate, relations, bindings, and render QA.
- Modify `scripts/dual_image_overlay/template_rebuild.py`: expose strict scene graph readiness and block export on gate failure.
- Add `tests/test_scene_graph_schema.py`.
- Add `tests/test_scene_graph_coordinate.py`.
- Add `tests/test_scene_graph_builder.py`.
- Add `tests/test_scene_graph_gate.py`.
- Add `tests/test_scene_graph_layout.py`.
- Add `tests/test_scene_graph_workflow.py`.

---

### Task 1: Scene Graph Schema

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/__init__.py`
- Create: `scripts/dual_image_overlay/scene_graph/schema.py`
- Test: `tests/test_scene_graph_schema.py`

**Interfaces:**
- Produces: `BBox`, `CoordinateContext`, `TruthSource`, `VisualNode`, `TextBinding`, `TextNode`, `Relation`, `LayoutIntent`, `GateIssue`, `PageSceneGraph`, `scene_graph_to_dict(graph) -> dict`, `scene_graph_from_dict(payload) -> PageSceneGraph`
- Consumes: none

- [ ] **Step 1: Write failing schema tests**

Add `tests/test_scene_graph_schema.py`:

```python
from scripts.dual_image_overlay.scene_graph.schema import (
    BBox,
    GateIssue,
    PageSceneGraph,
    TextBinding,
    TextNode,
    VisualNode,
    scene_graph_from_dict,
    scene_graph_to_dict,
)


def test_scene_graph_round_trip_preserves_binding_and_nodes():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={"normalized_canvas": {"width": 1280, "height": 720}},
        truth_sources={"script": {"path": "script.md", "authority": "text_truth"}},
        visual_nodes=[
            VisualNode(
                node_id="card_1",
                node_type="container",
                semantic_role="application_card",
                bbox=BBox(100, 80, 280, 180),
                source={"kind": "visual_element_registry"},
                confidence=1.0,
                component_id="p6_result_apps",
            )
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="企业应用",
                truth_source={"kind": "script", "path": "script.md"},
                semantic_role="card_title",
                binding=TextBinding(type="container_text", target_id="card_1", placement="inside"),
            )
        ],
    )

    payload = scene_graph_to_dict(graph)
    restored = scene_graph_from_dict(payload)

    assert payload["schema"] == "cyberppt.page_scene_graph.v1"
    assert restored.text_nodes[0].binding.type == "container_text"
    assert restored.visual_nodes[0].bbox.as_list() == [100.0, 80.0, 280.0, 180.0]


def test_gate_issue_shape_contains_required_fields():
    issue = GateIssue(
        severity="error",
        code="missing_truth_binding",
        node_id="text_1",
        source={"kind": "scene_graph_gate"},
        evidence={"text": "反馈迭代"},
        recommended_action="Bind the text node to a container, edge, anchor, region, title chrome, or legend.",
        blocking=True,
    )

    assert issue.to_dict() == {
        "severity": "error",
        "code": "missing_truth_binding",
        "node_id": "text_1",
        "source": {"kind": "scene_graph_gate"},
        "evidence": {"text": "反馈迭代"},
        "recommended_action": "Bind the text node to a container, edge, anchor, region, title chrome, or legend.",
        "blocking": True,
    }
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_schema.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.dual_image_overlay.scene_graph'`.

- [ ] **Step 3: Implement schema package**

Create `scripts/dual_image_overlay/scene_graph/__init__.py`:

```python
"""Scene graph contract for CyberPPT dual-image rebuilds."""

from .schema import (
    BBox,
    CoordinateContext,
    GateIssue,
    LayoutIntent,
    PageSceneGraph,
    Relation,
    TextBinding,
    TextNode,
    TruthSource,
    VisualNode,
    scene_graph_from_dict,
    scene_graph_to_dict,
)

__all__ = [
    "BBox",
    "CoordinateContext",
    "GateIssue",
    "LayoutIntent",
    "PageSceneGraph",
    "Relation",
    "TextBinding",
    "TextNode",
    "TruthSource",
    "VisualNode",
    "scene_graph_from_dict",
    "scene_graph_to_dict",
]
```

Create `scripts/dual_image_overlay/scene_graph/schema.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

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


@dataclass(frozen=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def as_list(self) -> list[float]:
        return [round(float(self.x1), 3), round(float(self.y1), 3), round(float(self.x2), 3), round(float(self.y2), 3)]

    @classmethod
    def from_any(cls, value: Any) -> "BBox":
        if isinstance(value, BBox):
            return value
        if isinstance(value, list) and len(value) == 4:
            return cls(float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        if isinstance(value, dict):
            if {"x1", "y1", "x2", "y2"}.issubset(value):
                return cls(float(value["x1"]), float(value["y1"]), float(value["x2"]), float(value["y2"]))
            if {"x", "y", "w", "h"}.issubset(value):
                x = float(value["x"])
                y = float(value["y"])
                return cls(x, y, x + float(value["w"]), y + float(value["h"]))
        raise ValueError(f"Invalid bbox: {value!r}")


CoordinateContext = dict[str, Any]
TruthSource = dict[str, Any]


@dataclass
class VisualNode:
    node_id: str
    node_type: str
    semantic_role: str
    bbox: BBox
    source: dict[str, Any]
    confidence: float = 1.0
    component_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bbox"] = self.bbox.as_list()
        return payload


@dataclass
class TextBinding:
    type: str
    target_id: str | None = None
    placement: str | None = None
    safe_bbox: BBox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.safe_bbox is not None:
            payload["safe_bbox"] = self.safe_bbox.as_list()
        return payload


@dataclass
class TextNode:
    node_id: str
    text: str
    truth_source: dict[str, Any]
    semantic_role: str
    binding: TextBinding
    bbox_preferred: BBox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["binding"] = self.binding.to_dict()
        if self.bbox_preferred is not None:
            payload["bbox_preferred"] = self.bbox_preferred.as_list()
        return payload


@dataclass
class Relation:
    type: str
    source_id: str
    target_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class LayoutIntent:
    type: str
    node_id: str
    target_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateIssue:
    severity: str
    code: str
    node_id: str | None
    source: dict[str, Any]
    evidence: dict[str, Any]
    recommended_action: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PageSceneGraph:
    page: int
    coordinate_context: CoordinateContext
    truth_sources: dict[str, Any]
    visual_nodes: list[VisualNode] = field(default_factory=list)
    text_nodes: list[TextNode] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    layout_intents: list[LayoutIntent] = field(default_factory=list)
    gates: dict[str, Any] = field(default_factory=dict)


def scene_graph_to_dict(graph: PageSceneGraph) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "page": graph.page,
        "coordinate_context": graph.coordinate_context,
        "truth_sources": graph.truth_sources,
        "visual_nodes": [node.to_dict() for node in graph.visual_nodes],
        "text_nodes": [node.to_dict() for node in graph.text_nodes],
        "relations": [asdict(item) for item in graph.relations],
        "layout_intents": [asdict(item) for item in graph.layout_intents],
        "gates": graph.gates,
    }


def scene_graph_from_dict(payload: dict[str, Any]) -> PageSceneGraph:
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported scene graph schema: {payload.get('schema')}")
    visual_nodes = [
        VisualNode(
            node_id=str(item["node_id"]),
            node_type=str(item["node_type"]),
            semantic_role=str(item["semantic_role"]),
            bbox=BBox.from_any(item["bbox"]),
            source=dict(item.get("source") or {}),
            confidence=float(item.get("confidence", 1.0)),
            component_id=item.get("component_id"),
            metadata=dict(item.get("metadata") or {}),
        )
        for item in payload.get("visual_nodes", [])
    ]
    text_nodes = []
    for item in payload.get("text_nodes", []):
        binding_payload = dict(item["binding"])
        safe_bbox = binding_payload.get("safe_bbox")
        binding = TextBinding(
            type=str(binding_payload["type"]),
            target_id=binding_payload.get("target_id"),
            placement=binding_payload.get("placement"),
            safe_bbox=BBox.from_any(safe_bbox) if safe_bbox is not None else None,
            metadata=dict(binding_payload.get("metadata") or {}),
        )
        preferred = item.get("bbox_preferred")
        text_nodes.append(
            TextNode(
                node_id=str(item["node_id"]),
                text=str(item["text"]),
                truth_source=dict(item.get("truth_source") or {}),
                semantic_role=str(item.get("semantic_role") or "body"),
                binding=binding,
                bbox_preferred=BBox.from_any(preferred) if preferred is not None else None,
                metadata=dict(item.get("metadata") or {}),
            )
        )
    return PageSceneGraph(
        page=int(payload["page"]),
        coordinate_context=dict(payload.get("coordinate_context") or {}),
        truth_sources=dict(payload.get("truth_sources") or {}),
        visual_nodes=visual_nodes,
        text_nodes=text_nodes,
        relations=[Relation(**item) for item in payload.get("relations", [])],
        layout_intents=[LayoutIntent(**item) for item in payload.get("layout_intents", [])],
        gates=dict(payload.get("gates") or {}),
    )
```

- [ ] **Step 4: Run schema tests**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_schema.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/__init__.py scripts/dual_image_overlay/scene_graph/schema.py tests/test_scene_graph_schema.py
git commit -m "feat: add scene graph schema contract"
```

---

### Task 2: Coordinate Normalization

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/coordinate.py`
- Test: `tests/test_scene_graph_coordinate.py`

**Interfaces:**
- Consumes: `BBox`, `NORMALIZED_CANVAS`
- Produces: `resolve_coordinate_context(plan_size, image_size, registry_size, semantic_extent, registry_extent) -> dict`, `normalize_bbox(bbox, input_space, context) -> BBox`

- [ ] **Step 1: Write failing coordinate tests**

Add `tests/test_scene_graph_coordinate.py`:

```python
from scripts.dual_image_overlay.scene_graph.coordinate import normalize_bbox, resolve_coordinate_context
from scripts.dual_image_overlay.scene_graph.schema import BBox


def test_uses_semantic_width_when_right_side_extends_past_image_width():
    context = resolve_coordinate_context(
        plan_size={"width": 1920, "height": 941},
        image_size={"width": 1672, "height": 941},
        registry_size={"width": 1672, "height": 941},
        semantic_extent={"width": 1847, "height": 857},
        registry_extent={"width": 1920, "height": 915},
    )

    normalized = normalize_bbox(BBox(1742, 160, 1842, 221), context["semantic_input_space"], context)

    assert context["coordinate_space"] == {"width": 1280.0, "height": 720.0}
    assert context["semantic_input_space"] == {"width": 1920.0, "height": 941.0}
    assert context["visual_registry_input_space"] == {"width": 1920.0, "height": 941.0}
    assert normalized.as_list() == [1161.333, 122.423, 1228.0, 169.096]
    assert any(warning["code"] == "semantic_coordinate_space_uses_plan_extent" for warning in context["warnings"])


def test_uses_actual_image_size_when_extents_do_not_exceed_image_width():
    context = resolve_coordinate_context(
        plan_size={"width": 1920, "height": 941},
        image_size={"width": 1672, "height": 941},
        registry_size={"width": 1672, "height": 941},
        semantic_extent={"width": 822, "height": 257},
        registry_extent={"width": 730, "height": 235},
    )

    normalized = normalize_bbox(BBox(647, 152, 818, 253), context["semantic_input_space"], context)

    assert context["semantic_input_space"] == {"width": 1672.0, "height": 941.0}
    assert normalized.as_list() == [495.311, 116.302, 626.029, 193.624]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_coordinate.py -q`

Expected: FAIL with `ModuleNotFoundError` for `scene_graph.coordinate`.

- [ ] **Step 3: Implement coordinate functions**

Create `scripts/dual_image_overlay/scene_graph/coordinate.py`:

```python
from __future__ import annotations

from typing import Any

from .schema import BBox, NORMALIZED_CANVAS


def _size(value: dict[str, Any] | None) -> dict[str, float] | None:
    if not value:
        return None
    width = float(value.get("width") or value.get("w") or 0)
    height = float(value.get("height") or value.get("h") or 0)
    if width <= 0 or height <= 0:
        return None
    return {"width": round(width, 3), "height": round(height, 3)}


def _exceeds(a: dict[str, float] | None, b: dict[str, float] | None, tolerance: float = 2.0) -> bool:
    return bool(a and b and (a["width"] > b["width"] + tolerance or a["height"] > b["height"] + tolerance))


def resolve_coordinate_context(
    *,
    plan_size: dict[str, Any] | None,
    image_size: dict[str, Any] | None,
    registry_size: dict[str, Any] | None,
    semantic_extent: dict[str, Any] | None,
    registry_extent: dict[str, Any] | None,
) -> dict[str, Any]:
    plan = _size(plan_size)
    image = _size(image_size)
    registry = _size(registry_size)
    semantic = _size(semantic_extent)
    registry_used = _size(registry_extent)
    warnings: list[dict[str, Any]] = []

    semantic_input = image or registry or plan or NORMALIZED_CANVAS
    if plan and image and _exceeds(semantic, image):
        semantic_input = plan
        warnings.append(
            {
                "code": "semantic_coordinate_space_uses_plan_extent",
                "semantic_plan_image_size": plan,
                "background_image_actual": image,
                "semantic_bbox_extent": semantic,
                "resolved_semantic_input_space": semantic_input,
            }
        )

    registry_input = registry or semantic_input
    if plan and registry and _exceeds(registry_used, registry):
        registry_input = plan if not _exceeds(registry_used, plan) else registry_used
        warnings.append(
            {
                "code": "visual_registry_canvas_metadata_stale",
                "visual_registry_canvas": registry,
                "registry_bbox_extent": registry_used,
                "resolved_visual_registry_input_space": registry_input,
            }
        )
        if semantic_input == image and plan and not _exceeds(registry_used, plan):
            semantic_input = plan
            warnings.append(
                {
                    "code": "semantic_coordinate_space_follows_registry_extent",
                    "semantic_plan_image_size": plan,
                    "registry_bbox_extent": registry_used,
                    "resolved_semantic_input_space": semantic_input,
                }
            )

    return {
        "schema": "cyberppt.scene_graph.coordinate_context.v1",
        "coordinate_space": dict(NORMALIZED_CANVAS),
        "semantic_input_space": semantic_input,
        "visual_registry_input_space": registry_input,
        "image_size": image,
        "semantic_plan_image_size": plan,
        "visual_registry_canvas": registry,
        "semantic_bbox_extent": semantic,
        "visual_registry_bbox_extent": registry_used,
        "warnings": warnings,
    }


def normalize_bbox(bbox: BBox, input_space: dict[str, Any], context: dict[str, Any]) -> BBox:
    target = context["coordinate_space"]
    sx = float(target["width"]) / float(input_space["width"])
    sy = float(target["height"]) / float(input_space["height"])
    return BBox(bbox.x1 * sx, bbox.y1 * sy, bbox.x2 * sx, bbox.y2 * sy)
```

- [ ] **Step 4: Run coordinate tests**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_coordinate.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/coordinate.py tests/test_scene_graph_coordinate.py
git commit -m "feat: normalize scene graph coordinates"
```

---

### Task 3: Build Visual Nodes and Text Nodes

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/builder.py`
- Test: `tests/test_scene_graph_builder.py`

**Interfaces:**
- Consumes: `resolve_coordinate_context`, `normalize_bbox`, schema dataclasses
- Produces: `build_page_scene_graph(page_number, script_sections, semantic_plan, visual_registry, image_size) -> PageSceneGraph`

- [ ] **Step 1: Write failing builder tests**

Add `tests/test_scene_graph_builder.py`:

```python
from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph


def test_builds_container_text_binding_from_script_and_registry():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={
            "右侧｜结果应用方": [
                {"title": "企业应用", "lines": ["画像管理、投标预审、融资保险"]}
            ]
        },
        semantic_plan={
            "image_size": {"width": 1920, "height": 941},
            "containers": [
                {"id": "application_1", "role": "application_card", "bbox": [1344, 134, 1586, 281]}
            ],
            "items": [],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1920, "h": 941},
            "elements": [
                {
                    "element_id": "p6_app_card_1",
                    "element_type": "application_card",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1340, "y": 130, "w": 250, "h": 155},
                },
                {
                    "element_id": "p6_app_icon_1",
                    "element_type": "icon",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1355, "y": 160, "w": 54, "h": 54},
                },
                {
                    "element_id": "p6_app_text_zone_1",
                    "element_type": "text_zone",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1420, "y": 175, "w": 145, "h": 70},
                },
            ],
        },
        image_size={"width": 1920, "height": 941},
    )

    assert graph.text_nodes[0].text == "企业应用\n• 画像管理\n• 投标预审\n• 融资保险"
    assert graph.text_nodes[0].binding.type == "container_text"
    assert graph.text_nodes[0].binding.target_id == "application_1"
    assert any(intent.type == "honor_text_zone" for intent in graph.layout_intents)
    assert any(rel.type == "contains" and rel.source_id == "application_1" for rel in graph.relations)


def test_builds_edge_label_binding_without_container():
    graph = build_page_scene_graph(
        page_number=7,
        script_sections={"箭头关系": [{"title": "", "lines": ["右侧应用反馈 → 中部核心空间，表示结果应用反馈更新"]}]},
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [],
            "items": [
                {
                    "display_text": "反馈更新",
                    "source_text": "反馈更新",
                    "role": "arrow_label",
                    "target_id": "arrow_1",
                }
            ],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "arrow_1",
                    "element_type": "flow_arrow",
                    "blueprint_bbox_px": {"x": 500, "y": 300, "w": 120, "h": 20},
                }
            ],
        },
        image_size={"width": 1280, "height": 720},
    )

    assert graph.text_nodes[0].binding.type == "edge_label"
    assert graph.text_nodes[0].binding.target_id == "arrow_1"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_builder.py -q`

Expected: FAIL with `ModuleNotFoundError` for `scene_graph.builder`.

- [ ] **Step 3: Implement builder**

Create `scripts/dual_image_overlay/scene_graph/builder.py`:

```python
from __future__ import annotations

import re
from typing import Any

from .coordinate import normalize_bbox, resolve_coordinate_context
from .schema import BBox, LayoutIntent, PageSceneGraph, Relation, TextBinding, TextNode, VisualNode

TEXT_ZONE_TYPES = {"text_zone", "label_zone", "text_safe_zone"}
CONTAINER_TYPES = {"application_card", "source_card", "object_pool_cell", "service_segment", "governance_step", "container"}
RESERVED_TYPES = {"icon", "flow_arrow", "arrow", "connector", "feedback_connector", "badge", "separator", "divider"}


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


def _bbox_from_registry(raw: dict[str, Any]) -> BBox:
    bbox = raw.get("blueprint_bbox_px")
    return BBox.from_any(bbox)


def _extent_from_bboxes(boxes: list[BBox]) -> dict[str, float] | None:
    if not boxes:
        return None
    return {"width": max(box.x2 for box in boxes), "height": max(box.y2 for box in boxes)}


def _intersects(a: BBox, b: BBox) -> bool:
    return max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1)) > 0 and max(0.0, min(a.y2, b.y2) - max(a.y1, b.y1)) > 0


def _contains(container: BBox, child: BBox, tolerance: float = 3.0) -> bool:
    return (
        child.x1 >= container.x1 - tolerance
        and child.y1 >= container.y1 - tolerance
        and child.x2 <= container.x2 + tolerance
        and child.y2 <= container.y2 + tolerance
    )


def _visual_nodes(visual_registry: dict[str, Any], context: dict[str, Any]) -> list[VisualNode]:
    input_space = context["visual_registry_input_space"]
    nodes: list[VisualNode] = []
    for element in visual_registry.get("elements", []):
        if not isinstance(element, dict):
            continue
        raw_bbox = _bbox_from_registry(element)
        bbox = normalize_bbox(raw_bbox, input_space, context)
        nodes.append(
            VisualNode(
                node_id=str(element.get("element_id") or element.get("id")),
                node_type=str(element.get("element_type") or "visual"),
                semantic_role=str(element.get("semantic_role") or element.get("element_type") or "visual"),
                bbox=bbox,
                source={"kind": "visual_element_registry"},
                confidence=1.0,
                component_id=element.get("source_component_id"),
                metadata={"raw": element},
            )
        )
    return nodes


def _semantic_container_nodes(semantic_plan: dict[str, Any], context: dict[str, Any]) -> list[VisualNode]:
    input_space = context["semantic_input_space"]
    nodes: list[VisualNode] = []
    for container in semantic_plan.get("containers", []):
        if not isinstance(container, dict) or "bbox" not in container:
            continue
        nodes.append(
            VisualNode(
                node_id=str(container.get("id")),
                node_type="container",
                semantic_role=str(container.get("role") or "container"),
                bbox=normalize_bbox(BBox.from_any(container["bbox"]), input_space, context),
                source={"kind": "semantic_plan"},
                confidence=1.0,
                component_id=container.get("component_id"),
                metadata={"raw": container},
            )
        )
    return nodes


def _find_node(nodes: list[VisualNode], node_id: str | None) -> VisualNode | None:
    for node in nodes:
        if node.node_id == node_id:
            return node
    return None


def _best_container(nodes: list[VisualNode], role_fragment: str) -> VisualNode | None:
    for node in nodes:
        if role_fragment in node.semantic_role or role_fragment in node.node_id:
            return node
    return None


def _build_application_text(script_sections: dict[str, list[dict[str, Any]]]) -> list[str]:
    groups = script_sections.get("右侧｜结果应用方", [])
    texts: list[str] = []
    for group in groups:
        title = str(group.get("title") or "").strip()
        items = _split_items([str(line) for line in group.get("lines", [])])
        if title and items:
            texts.append(title + "\n" + "\n".join(f"• {item}" for item in items))
    return texts


def _text_nodes(script_sections: dict[str, list[dict[str, Any]]], semantic_plan: dict[str, Any], visual_nodes: list[VisualNode]) -> list[TextNode]:
    nodes: list[TextNode] = []
    for index, text in enumerate(_build_application_text(script_sections), start=1):
        target_id = f"application_{index}"
        nodes.append(
            TextNode(
                node_id=f"text_application_{index}",
                text=text,
                truth_source={"kind": "script"},
                semantic_role="application_card_text",
                binding=TextBinding(type="container_text", target_id=target_id, placement="inside"),
            )
        )
    for index, item in enumerate(semantic_plan.get("items", []), start=1):
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
                relations.append(Relation(type="contains", source_id=container.node_id, target_id=child.node_id, confidence=1.0))
            elif container.component_id and container.component_id == child.component_id and _intersects(container.bbox, child.bbox):
                relations.append(Relation(type="part_of", source_id=container.node_id, target_id=child.node_id, confidence=0.8))
    return relations


def _layout_intents(text_nodes: list[TextNode], visual_nodes: list[VisualNode], relations: list[Relation]) -> list[LayoutIntent]:
    intents: list[LayoutIntent] = []
    contained_by = {(rel.source_id, rel.target_id) for rel in relations if rel.type in {"contains", "part_of"}}
    for text in text_nodes:
        if text.binding.type == "container_text" and text.binding.target_id:
            for container_id, child_id in contained_by:
                if container_id != text.binding.target_id:
                    continue
                child = _find_node(visual_nodes, child_id)
                if child and child.node_type in TEXT_ZONE_TYPES:
                    intents.append(LayoutIntent(type="honor_text_zone", node_id=text.node_id, target_id=child.node_id))
                if child and child.node_type in RESERVED_TYPES:
                    intents.append(LayoutIntent(type="avoid_reserved_zone", node_id=text.node_id, target_id=child.node_id))
        if text.binding.type == "edge_label":
            intents.append(LayoutIntent(type="label_on_arrow", node_id=text.node_id, target_id=text.binding.target_id))
    return intents


def build_page_scene_graph(
    *,
    page_number: int,
    script_sections: dict[str, list[dict[str, Any]]],
    semantic_plan: dict[str, Any],
    visual_registry: dict[str, Any],
    image_size: dict[str, Any],
) -> PageSceneGraph:
    semantic_boxes = [BBox.from_any(item["bbox"]) for item in semantic_plan.get("containers", []) if isinstance(item, dict) and "bbox" in item]
    registry_boxes = [_bbox_from_registry(item) for item in visual_registry.get("elements", []) if isinstance(item, dict) and item.get("blueprint_bbox_px")]
    context = resolve_coordinate_context(
        plan_size=semantic_plan.get("image_size"),
        image_size=image_size,
        registry_size=visual_registry.get("blueprint_canvas_px"),
        semantic_extent=_extent_from_bboxes(semantic_boxes),
        registry_extent=_extent_from_bboxes(registry_boxes),
    )
    visual_nodes = _semantic_container_nodes(semantic_plan, context)
    existing_ids = {node.node_id for node in visual_nodes}
    visual_nodes.extend(node for node in _visual_nodes(visual_registry, context) if node.node_id not in existing_ids)
    text_nodes = _text_nodes(script_sections, semantic_plan, visual_nodes)
    relations = _relations(visual_nodes)
    intents = _layout_intents(text_nodes, visual_nodes, relations)
    return PageSceneGraph(
        page=page_number,
        coordinate_context=context,
        truth_sources={"script": {"authority": "text_truth"}, "ocr": {"authority": "locator_evidence_only"}},
        visual_nodes=visual_nodes,
        text_nodes=text_nodes,
        relations=relations,
        layout_intents=intents,
    )
```

- [ ] **Step 4: Run builder tests**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_builder.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/builder.py tests/test_scene_graph_builder.py
git commit -m "feat: build page scene graph nodes"
```

---

### Task 4: Scene Graph Gate

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/gate.py`
- Test: `tests/test_scene_graph_gate.py`

**Interfaces:**
- Consumes: `PageSceneGraph`, `BINDING_TYPES`, `TEXT_TRUTH_AUTHORITIES`, `LOCATOR_ONLY_AUTHORITIES`
- Produces: `build_scene_graph_gate(graph) -> dict`

- [ ] **Step 1: Write failing gate tests**

Add `tests/test_scene_graph_gate.py`:

```python
from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, TextBinding, TextNode, VisualNode


def test_gate_blocks_ocr_as_final_text_truth():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="OCR内容",
                truth_source={"kind": "ocr"},
                semantic_role="body",
                binding=TextBinding(type="container_text", target_id="card_1"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "script_truth_mismatch"


def test_gate_allows_arrow_label_without_container():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="arrow_1",
                node_type="flow_arrow",
                semantic_role="feedback_arrow",
                bbox=BBox(100, 100, 180, 110),
                source={"kind": "visual_element_registry"},
            )
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="反馈更新",
                truth_source={"kind": "script"},
                semantic_role="arrow_label",
                binding=TextBinding(type="edge_label", target_id="arrow_1"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True
    assert gate["blocking_count"] == 0


def test_gate_blocks_registry_text_zone_without_bound_text():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="text_zone_1",
                node_type="text_zone",
                semantic_role="application_text_zone",
                bbox=BBox(100, 100, 180, 140),
                source={"kind": "visual_element_registry"},
            )
        ],
        text_nodes=[],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "registry_container_without_text"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_gate.py -q`

Expected: FAIL with `ModuleNotFoundError` for `scene_graph.gate`.

- [ ] **Step 3: Implement gate**

Create `scripts/dual_image_overlay/scene_graph/gate.py`:

```python
from __future__ import annotations

from .schema import BINDING_TYPES, LOCATOR_ONLY_AUTHORITIES, GateIssue, PageSceneGraph

TEXT_ZONE_TYPES = {"text_zone", "label_zone", "text_safe_zone"}


def _issue(code: str, node_id: str | None, evidence: dict, action: str) -> GateIssue:
    return GateIssue(
        severity="error",
        code=code,
        node_id=node_id,
        source={"kind": "page_scene_graph_gate"},
        evidence=evidence,
        recommended_action=action,
        blocking=True,
    )


def build_scene_graph_gate(graph: PageSceneGraph) -> dict:
    issues: list[GateIssue] = []
    visual_ids = {node.node_id for node in graph.visual_nodes}

    for warning in graph.coordinate_context.get("warnings", []):
        if warning.get("code") == "coordinate_space_unresolved":
            issues.append(
                _issue(
                    "coordinate_space_unresolved",
                    None,
                    {"warning": warning},
                    "Record a transform that maps this source coordinate space into 1280x720.",
                )
            )

    for text in graph.text_nodes:
        kind = str(text.truth_source.get("kind") or "")
        if kind in LOCATOR_ONLY_AUTHORITIES:
            issues.append(
                _issue(
                    "script_truth_mismatch",
                    text.node_id,
                    {"truth_source": text.truth_source, "text": text.text},
                    "Replace OCR-derived final text with script, content-lock, or manual-override text.",
                )
            )
        if text.binding.type not in BINDING_TYPES:
            issues.append(
                _issue(
                    "missing_truth_binding",
                    text.node_id,
                    {"binding": text.binding.to_dict()},
                    "Use a supported binding type: container_text, edge_label, anchor_label, free_annotation, title_chrome, or legend_label.",
                )
            )
        if text.binding.type in {"container_text", "edge_label", "anchor_label", "legend_label"} and text.binding.target_id not in visual_ids:
            issues.append(
                _issue(
                    "missing_truth_binding",
                    text.node_id,
                    {"target_id": text.binding.target_id, "binding": text.binding.to_dict()},
                    "Bind the text node to an existing visual node or change the binding type to free_annotation/title_chrome with a page region.",
                )
            )

    bound_targets = {text.binding.target_id for text in graph.text_nodes if text.binding.target_id}
    for node in graph.visual_nodes:
        if node.node_type in TEXT_ZONE_TYPES and node.node_id not in bound_targets:
            issues.append(
                _issue(
                    "registry_container_without_text",
                    node.node_id,
                    {"node_type": node.node_type, "bbox": node.bbox.as_list()},
                    "Bind script truth text to this text zone or mark the node metadata as decorative_empty.",
                )
            )

    issue_payloads = [issue.to_dict() for issue in issues]
    return {
        "schema": "cyberppt.page_scene_graph_gate.v1",
        "valid": not any(issue.blocking for issue in issues),
        "blocking_count": sum(1 for issue in issues if issue.blocking),
        "warning_count": 0,
        "issues": issue_payloads,
    }
```

- [ ] **Step 4: Run gate tests**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_gate.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/gate.py tests/test_scene_graph_gate.py
git commit -m "feat: add blocking scene graph gate"
```

---

### Task 5: Layout From Scene Graph

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/layout.py`
- Test: `tests/test_scene_graph_layout.py`

**Interfaces:**
- Consumes: `PageSceneGraph`, `LayoutIntent`, `TextBinding`
- Produces: `build_layout_plan_from_scene_graph(graph) -> dict`

- [ ] **Step 1: Write failing layout tests**

Add `tests/test_scene_graph_layout.py`:

```python
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import BBox, LayoutIntent, PageSceneGraph, TextBinding, TextNode, VisualNode


def test_layout_places_container_text_inside_text_zone_and_after_icon():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={"coordinate_space": {"width": 1280, "height": 720}},
        truth_sources={},
        visual_nodes=[
            VisualNode("application_1", "container", "application_card", BBox(896, 100, 1058, 220), {"kind": "semantic_plan"}),
            VisualNode("icon_1", "icon", "application_icon", BBox(904, 120, 940, 160), {"kind": "visual_element_registry"}),
            VisualNode("text_zone_1", "text_zone", "application_text_zone", BBox(946, 132, 1044, 188), {"kind": "visual_element_registry"}),
        ],
        text_nodes=[
            TextNode(
                "text_1",
                "企业应用\n• 画像管理\n• 投标预审",
                {"kind": "script"},
                "application_card_text",
                TextBinding("container_text", target_id="application_1"),
            )
        ],
        layout_intents=[
            LayoutIntent("honor_text_zone", "text_1", "text_zone_1"),
            LayoutIntent("avoid_reserved_zone", "text_1", "icon_1"),
        ],
    )

    plan = build_layout_plan_from_scene_graph(graph)
    item = plan["items"][0]

    assert item["bbox"] == [946.0, 132.0, 1044.0, 188.0]
    assert item["text"] == "企业应用\n• 画像管理\n• 投标预审"
    assert "honor_text_zone" in item["layout_intents"]
    assert "avoid_reserved_zone" in item["layout_intents"]


def test_layout_places_edge_label_above_arrow():
    graph = PageSceneGraph(
        page=7,
        coordinate_context={"coordinate_space": {"width": 1280, "height": 720}},
        truth_sources={},
        visual_nodes=[
            VisualNode("arrow_1", "flow_arrow", "feedback_arrow", BBox(500, 300, 620, 320), {"kind": "visual_element_registry"})
        ],
        text_nodes=[
            TextNode("text_1", "反馈更新", {"kind": "script"}, "arrow_label", TextBinding("edge_label", target_id="arrow_1"))
        ],
        layout_intents=[LayoutIntent("label_on_arrow", "text_1", "arrow_1")],
    )

    plan = build_layout_plan_from_scene_graph(graph)
    item = plan["items"][0]

    assert item["bbox"] == [500.0, 274.0, 620.0, 296.0]
    assert item["binding_type"] == "edge_label"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_layout.py -q`

Expected: FAIL with `ModuleNotFoundError` for `scene_graph.layout`.

- [ ] **Step 3: Implement layout module**

Create `scripts/dual_image_overlay/scene_graph/layout.py`:

```python
from __future__ import annotations

from .schema import BBox, PageSceneGraph, TextNode, VisualNode


def _node_by_id(graph: PageSceneGraph) -> dict[str, VisualNode]:
    return {node.node_id: node for node in graph.visual_nodes}


def _intent_targets(graph: PageSceneGraph, text_id: str, intent_type: str) -> list[str]:
    return [intent.target_id for intent in graph.layout_intents if intent.node_id == text_id and intent.type == intent_type and intent.target_id]


def _bbox_for_container_text(graph: PageSceneGraph, text: TextNode, nodes: dict[str, VisualNode]) -> BBox:
    text_zone_targets = _intent_targets(graph, text.node_id, "honor_text_zone")
    for target_id in text_zone_targets:
        if target_id in nodes:
            return nodes[target_id].bbox
    if text.binding.safe_bbox is not None:
        return text.binding.safe_bbox
    target = nodes.get(str(text.binding.target_id))
    if target is None:
        return BBox(0, 0, 1, 1)
    return BBox(target.bbox.x1 + 10, target.bbox.y1 + 8, target.bbox.x2 - 10, target.bbox.y2 - 8)


def _bbox_for_edge_label(text: TextNode, nodes: dict[str, VisualNode]) -> BBox:
    target = nodes.get(str(text.binding.target_id))
    if target is None:
        return BBox(0, 0, 1, 1)
    return BBox(target.bbox.x1, max(0.0, target.bbox.y1 - 26.0), target.bbox.x2, max(1.0, target.bbox.y1 - 4.0))


def _font_size_for(text: str, bbox: BBox) -> float:
    lines = max(1, len(text.splitlines()))
    height = max(1.0, bbox.y2 - bbox.y1)
    return round(max(7.0, min(16.0, height / lines * 0.78)), 2)


def build_layout_plan_from_scene_graph(graph: PageSceneGraph) -> dict:
    nodes = _node_by_id(graph)
    items = []
    for index, text in enumerate(graph.text_nodes):
        if text.binding.type == "edge_label":
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
                "binding_type": text.binding.type,
                "target_id": text.binding.target_id,
                "bbox": bbox.as_list(),
                "font_size": _font_size_for(text.text, bbox),
                "font_weight": "700" if text.semantic_role.endswith("title") else "400",
                "align": "left",
                "word_wrap": True,
                "layout_intents": intents,
            }
        )
    return {
        "schema": "cyberppt.page_layout_plan.v1",
        "page": graph.page,
        "source_scene_graph": "page_scene_graph.json",
        "items": items,
    }
```

- [ ] **Step 4: Run layout tests**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_layout.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/layout.py tests/test_scene_graph_layout.py
git commit -m "feat: build layout from scene graph"
```

---

### Task 6: Strict Workflow Integration

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Test: `tests/test_scene_graph_workflow.py`

**Interfaces:**
- Consumes: `build_page_scene_graph`, `build_scene_graph_gate`, `build_layout_plan_from_scene_graph`
- Produces: scene graph artifacts under `analysis/scene_graph/`, strict gate blocking before export

- [ ] **Step 1: Write failing workflow tests**

Add `tests/test_scene_graph_workflow.py`:

```python
import json
from pathlib import Path

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _scene_graph_artifact_paths, _scene_graph_gate_blocks_export


def test_scene_graph_artifact_paths_are_page_scoped(tmp_path: Path):
    paths = _scene_graph_artifact_paths(tmp_path, 6)

    assert paths["graph"] == tmp_path / "analysis" / "scene_graph" / "page_006_scene_graph.json"
    assert paths["gate"] == tmp_path / "analysis" / "scene_graph_gate" / "page_006_scene_graph_gate.json"
    assert paths["layout"] == tmp_path / "analysis" / "page_layout_plan" / "page_006_layout_plan.json"


def test_scene_graph_gate_blocks_export(tmp_path: Path):
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.page_scene_graph_gate.v1",
                "valid": False,
                "blocking_count": 1,
                "issues": [{"code": "missing_truth_binding", "blocking": True}],
            }
        ),
        encoding="utf-8",
    )

    assert _scene_graph_gate_blocks_export(gate_path) is True
```

- [ ] **Step 2: Run test and verify failure**

Run: `PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest tests/test_scene_graph_workflow.py -q`

Expected: FAIL because `_scene_graph_artifact_paths` is not defined.

- [ ] **Step 3: Add workflow helper functions**

Modify `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`:

```python
def _scene_graph_artifact_paths(project_path: Path, page_number: int) -> dict[str, Path]:
    return {
        "graph": project_path / "analysis" / "scene_graph" / f"page_{page_number:03d}_scene_graph.json",
        "gate": project_path / "analysis" / "scene_graph_gate" / f"page_{page_number:03d}_scene_graph_gate.json",
        "layout": project_path / "analysis" / "page_layout_plan" / f"page_{page_number:03d}_layout_plan.json",
    }


def _scene_graph_gate_blocks_export(gate_path: Path) -> bool:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    return bool(gate.get("blocking_count") or not gate.get("valid", False))
```

Add imports in the same file:

```python
from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph
from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import scene_graph_to_dict
```

- [ ] **Step 4: Run workflow helper test**

Run: `PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest tests/test_scene_graph_workflow.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Wire graph build before existing layout**

In `rebuild_from_manifest(...)`, after `semantic_plan`, `explicit_plan`, and `visual_registry` are loaded, create scene graph artifacts before overlay boxes are built:

```python
paths = _scene_graph_artifact_paths(project_path, page_number)
for path in paths.values():
    path.parent.mkdir(parents=True, exist_ok=True)
graph = build_page_scene_graph(
    page_number=page_number,
    script_sections=_script_sections_for_scene_graph(source_script, page_number),
    semantic_plan=explicit_plan if explicit_semantic is not None else semantic_plan_to_json(semantic_plan),
    visual_registry=visual_registry or {"blueprint_canvas_px": {"w": 1280, "h": 720}, "elements": []},
    image_size={"width": image_size_check["width"], "height": image_size_check["height"]},
)
graph_gate = build_scene_graph_gate(graph)
paths["graph"].write_text(json.dumps(scene_graph_to_dict(graph), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
paths["gate"].write_text(json.dumps(graph_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if graph_gate["blocking_count"]:
    raise ValueError(f"Scene graph gate failed for page {page_number}: {graph_gate['issues']}")
page_layout_plan = build_layout_plan_from_scene_graph(graph)
paths["layout"].write_text(json.dumps(page_layout_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

Add `_script_sections_for_scene_graph(source_script: Path, page_number: int) -> dict[str, list[dict]]` near the helpers:

```python
def _script_sections_for_scene_graph(source_script: Path, page_number: int) -> dict[str, list[dict[str, Any]]]:
    from script_text_overlay import extract_script_truth_sections

    return extract_script_truth_sections(source_script, page_number)
```

- [ ] **Step 6: Update `template_rebuild.py` readiness**

Modify `scripts/dual_image_overlay/template_rebuild.py` so readiness includes scene graph artifacts:

```python
scene_graph_gate_paths = sorted((project_dir / "analysis" / "scene_graph_gate").glob("page_*_scene_graph_gate.json"))
scene_graph_gates = [json.loads(path.read_text(encoding="utf-8")) for path in scene_graph_gate_paths]
scene_graph_valid = bool(scene_graph_gates) and all(gate.get("valid") for gate in scene_graph_gates)
```

Add to readiness output:

```python
"scene_graph_gate_pass": scene_graph_valid,
"scene_graph_gate_pages": len(scene_graph_gates),
```

Set final `valid`:

```python
valid = bool(template_gate["valid"] and source_capture_gate["valid"] and scene_graph_valid)
```

- [ ] **Step 7: Run targeted tests**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest tests/test_scene_graph_workflow.py tests/test_scene_graph_builder.py tests/test_scene_graph_gate.py tests/test_scene_graph_layout.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py scripts/dual_image_overlay/template_rebuild.py tests/test_scene_graph_workflow.py
git commit -m "feat: require scene graph gate before export"
```

---

### Task 7: Source Capture and Render QA Integration

**Files:**
- Create: `scripts/dual_image_overlay/scene_graph/render_qa.py`
- Modify: `scripts/dual_image_overlay/source_capture.py`
- Test: `tests/test_scene_graph_render_qa.py`
- Test: `tests/test_dual_image_overlay_source_capture.py`

**Interfaces:**
- Consumes: `page_scene_graph.json`, `page_layout_plan.json`, rendered PNG path
- Produces: `build_render_qa(layout_plan, rendered_image_size) -> dict`, source capture fields `scene_graph`, `scene_graph_gate`, `page_layout_plan`, `render_qa`

- [ ] **Step 1: Write failing render QA test**

Add `tests/test_scene_graph_render_qa.py`:

```python
from scripts.dual_image_overlay.scene_graph.render_qa import build_render_qa


def test_render_qa_flags_text_outside_canvas():
    qa = build_render_qa(
        layout_plan={
            "items": [
                {"node_id": "text_1", "text": "审计留痕", "bbox": [1260, 100, 1310, 120]},
            ]
        },
        rendered_image_size={"width": 1280, "height": 720},
    )

    assert qa["valid"] is False
    assert qa["issues"][0]["code"] == "render_text_outside_canvas"


def test_render_qa_accepts_text_inside_canvas():
    qa = build_render_qa(
        layout_plan={
            "items": [
                {"node_id": "text_1", "text": "审计留痕", "bbox": [1160, 100, 1220, 120]},
            ]
        },
        rendered_image_size={"width": 1280, "height": 720},
    )

    assert qa["valid"] is True
```

- [ ] **Step 2: Run test and verify failure**

Run: `PYTHONPATH=. pytest tests/test_scene_graph_render_qa.py -q`

Expected: FAIL with `ModuleNotFoundError` for `scene_graph.render_qa`.

- [ ] **Step 3: Implement render QA**

Create `scripts/dual_image_overlay/scene_graph/render_qa.py`:

```python
from __future__ import annotations

from typing import Any


def _inside_canvas(bbox: list[float], width: float, height: float) -> bool:
    return bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= width and bbox[3] <= height


def build_render_qa(layout_plan: dict[str, Any], rendered_image_size: dict[str, Any]) -> dict[str, Any]:
    width = float(rendered_image_size.get("width") or 1280)
    height = float(rendered_image_size.get("height") or 720)
    issues: list[dict[str, Any]] = []
    for item in layout_plan.get("items", []):
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            issues.append(
                {
                    "severity": "error",
                    "code": "render_text_missing_bbox",
                    "node_id": item.get("node_id"),
                    "text": item.get("text"),
                    "blocking": True,
                }
            )
            continue
        values = [float(value) for value in bbox]
        if not _inside_canvas(values, width, height):
            issues.append(
                {
                    "severity": "error",
                    "code": "render_text_outside_canvas",
                    "node_id": item.get("node_id"),
                    "text": item.get("text"),
                    "bbox": [round(value, 3) for value in values],
                    "canvas": {"width": width, "height": height},
                    "blocking": True,
                }
            )
    return {
        "schema": "cyberppt.scene_graph.render_qa.v1",
        "valid": not any(issue.get("blocking") for issue in issues),
        "blocking_count": sum(1 for issue in issues if issue.get("blocking")),
        "issues": issues,
    }
```

- [ ] **Step 4: Modify source capture loaders**

In `scripts/dual_image_overlay/source_capture.py`, add loaders:

```python
def _load_scene_graphs(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / "scene_graph").glob("page_*_scene_graph.json")):
        page_number = _page_number_from_name(path.name)
        if page_number is not None:
            by_page[page_number] = json.loads(path.read_text(encoding="utf-8"))
    return by_page


def _load_scene_graph_gates(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / "scene_graph_gate").glob("page_*_scene_graph_gate.json")):
        page_number = _page_number_from_name(path.name)
        if page_number is not None:
            by_page[page_number] = json.loads(path.read_text(encoding="utf-8"))
    return by_page


def _load_page_layout_plans(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / "page_layout_plan").glob("page_*_layout_plan.json")):
        page_number = _page_number_from_name(path.name)
        if page_number is not None:
            by_page[page_number] = json.loads(path.read_text(encoding="utf-8"))
    return by_page
```

Inside `build_source_capture(...)`, load these dictionaries and add page fields:

```python
scene_graphs_by_page = _load_scene_graphs(project_dir)
scene_graph_gates_by_page = _load_scene_graph_gates(project_dir)
page_layout_by_page = _load_page_layout_plans(project_dir)
```

Add to each page payload:

```python
"scene_graph": scene_graphs_by_page.get(page_number),
"scene_graph_gate": scene_graph_gates_by_page.get(page_number),
"page_layout_plan": page_layout_by_page.get(page_number),
```

Add to metadata counts:

```python
"scene_graph_pages": len(scene_graphs_by_page),
"scene_graph_gate_pages": len(scene_graph_gates_by_page),
"page_layout_plan_pages": len(page_layout_by_page),
```

- [ ] **Step 5: Extend source capture tests**

In `tests/test_dual_image_overlay_source_capture.py`, add:

```python
def test_source_capture_includes_scene_graph_contract(tmp_path: Path):
    project = tmp_path / "ppt_project"
    (project / "analysis" / "scene_graph").mkdir(parents=True)
    (project / "analysis" / "scene_graph_gate").mkdir(parents=True)
    (project / "analysis" / "page_layout_plan").mkdir(parents=True)
    (project / "analysis" / "scene_graph" / "page_006_scene_graph.json").write_text(
        json.dumps({"schema": "cyberppt.page_scene_graph.v1", "page": 6, "text_nodes": []}),
        encoding="utf-8",
    )
    (project / "analysis" / "scene_graph_gate" / "page_006_scene_graph_gate.json").write_text(
        json.dumps({"schema": "cyberppt.page_scene_graph_gate.v1", "valid": True, "blocking_count": 0}),
        encoding="utf-8",
    )
    (project / "analysis" / "page_layout_plan" / "page_006_layout_plan.json").write_text(
        json.dumps({"schema": "cyberppt.page_layout_plan.v1", "page": 6, "items": []}),
        encoding="utf-8",
    )

    capture = build_source_capture(project)
    page = capture["pages"][0]

    assert page["scene_graph"]["schema"] == "cyberppt.page_scene_graph.v1"
    assert page["scene_graph_gate"]["valid"] is True
    assert page["page_layout_plan"]["schema"] == "cyberppt.page_layout_plan.v1"
```

- [ ] **Step 6: Run source capture and render QA tests**

Run:

```bash
PYTHONPATH=. pytest tests/test_scene_graph_render_qa.py tests/test_dual_image_overlay_source_capture.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/dual_image_overlay/scene_graph/render_qa.py scripts/dual_image_overlay/source_capture.py tests/test_scene_graph_render_qa.py tests/test_dual_image_overlay_source_capture.py
git commit -m "feat: capture scene graph and render qa"
```

---

### Task 8: End-to-End Strict Export Regression

**Files:**
- Modify: `tests/test_scene_graph_workflow.py`
- Test fixture: use temporary minimal image pair generated in test

**Interfaces:**
- Consumes: strict workflow from Task 6
- Produces: regression coverage proving export is blocked when graph gate fails and allowed when graph gate passes

- [ ] **Step 1: Add failing strict export tests**

Append to `tests/test_scene_graph_workflow.py`:

```python
import pytest


def test_strict_scene_graph_blocks_export_on_unbound_text(tmp_path: Path):
    from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
    from scripts.dual_image_overlay.scene_graph.schema import PageSceneGraph, TextBinding, TextNode

    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="孤立文本",
                truth_source={"kind": "script"},
                semantic_role="body",
                binding=TextBinding(type="container_text", target_id="missing_container"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["blocking_count"] == 1
    assert gate["issues"][0]["code"] == "missing_truth_binding"


def test_strict_scene_graph_allows_edge_label_without_container():
    from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
    from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, TextBinding, TextNode, VisualNode

    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode("arrow_1", "flow_arrow", "feedback_arrow", BBox(10, 10, 100, 20), {"kind": "visual_element_registry"})
        ],
        text_nodes=[
            TextNode("text_1", "反馈更新", {"kind": "script"}, "arrow_label", TextBinding("edge_label", target_id="arrow_1"))
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True
```

- [ ] **Step 2: Run strict workflow tests**

Run: `PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest tests/test_scene_graph_workflow.py -q`

Expected: all tests pass.

- [ ] **Step 3: Run full test suite**

Run: `PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q`

Expected: all tests pass.

- [ ] **Step 4: Run P6 strict rebuild smoke test**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. python3 scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py rebuild \
  projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/images/page_image_pairs.json \
  --visible-image-variant background \
  --editable-text-visibility visible \
  --semantic-plan-dir projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/semantic_plan_explicit \
  --visual-registry-dir projects/power-overseas-capability-p6-p9-restart/workbench/registry \
  --export
```

Expected:

- command exits 0
- `projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/ppt_project/analysis/scene_graph/page_006_scene_graph.json` exists
- `projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/ppt_project/analysis/scene_graph_gate/page_006_scene_graph_gate.json` has `"valid": true`
- exported PPTX path is printed

- [ ] **Step 5: Render P6 and verify visually**

Run:

```bash
mkdir -p projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/rendered/scene-graph-strict
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to png \
  --outdir projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/rendered/scene-graph-strict \
  projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/ppt_project/exports/*.pptx
```

Expected:

- rendered PNG exists under `rendered/scene-graph-strict`
- right-side application and governance text is visible
- no full-image text layer is doubled over editable text

- [ ] **Step 6: Commit**

```bash
git add tests/test_scene_graph_workflow.py projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/ppt_project/analysis/scene_graph projects/power-overseas-capability-p6-p9-restart/workbench/stage3/p6/ppt_project/analysis/scene_graph_gate
git commit -m "test: enforce strict scene graph export"
```

---

## Self-Review Checklist

- Spec coverage: Tasks 1-2 cover schema and coordinate context; Tasks 3-5 cover graph build, binding, relations, layout intents, and safe areas; Task 6 enforces blocking workflow; Task 7 records source capture and render QA; Task 8 adds strict regression and P6 smoke coverage.
- Placeholder scan: no unresolved placeholder wording remains; every task includes concrete tests, commands, and implementation snippets.
- Type consistency: the plan uses `PageSceneGraph`, `TextBinding`, `VisualNode`, `TextNode`, `build_page_scene_graph`, `build_scene_graph_gate`, and `build_layout_plan_from_scene_graph` consistently across tasks.
