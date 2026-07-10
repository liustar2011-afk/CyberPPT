from __future__ import annotations

from typing import Any

from .schema import BINDING_TYPES, LOCATOR_ONLY_AUTHORITIES, GateIssue, PageSceneGraph


GATE_SCHEMA = "cyberppt.page_scene_graph_gate.v1"
TEXT_ZONE_TYPES = {"text_zone", "label_zone", "text_safe_zone"}
TARGET_REQUIRED_BINDINGS = {"container_text", "edge_label", "anchor_label", "legend_label"}
DEFAULT_CANVAS_WIDTH = 1672.0
DEFAULT_CANVAS_HEIGHT = 941.0


def _coordinate_context_dict(graph: PageSceneGraph) -> dict[str, Any]:
    context = graph.coordinate_context
    if hasattr(context, "to_dict"):
        return context.to_dict()
    return dict(context)


def _issue(code: str, node_id: str | None, evidence: dict[str, Any], action: str) -> GateIssue:
    return GateIssue(
        severity="error",
        code=code,
        node_id=node_id,
        source={"kind": "page_scene_graph_gate"},
        evidence=evidence,
        recommended_action=action,
        blocking=True,
    )


def _bbox_inside_canvas(bbox: list[float], width: float, height: float) -> bool:
    return bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= width and bbox[3] <= height and bbox[2] > bbox[0] and bbox[3] > bbox[1]


def build_scene_graph_gate(graph: PageSceneGraph) -> dict[str, Any]:
    issues: list[GateIssue] = []
    context = _coordinate_context_dict(graph)
    coordinate_space = context.get("coordinate_space")
    if not isinstance(coordinate_space, dict):
        coordinate_space = context.get("normalized_canvas") or {}
    canvas_width = float(coordinate_space.get("width") or DEFAULT_CANVAS_WIDTH)
    canvas_height = float(coordinate_space.get("height") or DEFAULT_CANVAS_HEIGHT)
    visual_ids = {node.node_id for node in graph.visual_nodes}

    for warning in context.get("warnings", []):
        if isinstance(warning, dict) and warning.get("code") == "coordinate_space_unresolved":
            issues.append(
                _issue(
                    "coordinate_space_unresolved",
                    None,
                    {"warning": warning},
                    "Record a transform that maps this source coordinate space into 1672x941.",
                )
            )

    for node in graph.visual_nodes:
        bbox = node.bbox.as_list()
        if not _bbox_inside_canvas(bbox, canvas_width, canvas_height):
            issues.append(
                _issue(
                    "coordinate_space_unresolved",
                    node.node_id,
                    {"bbox": bbox, "coordinate_space": coordinate_space},
                    "Normalize every visual node bbox to the 1672x941 scene graph coordinate space.",
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
        if text.binding is None:
            issues.append(
                _issue(
                    "missing_truth_binding",
                    text.node_id,
                    {"text": text.text},
                    "Bind the text node to a container, edge, anchor, free annotation region, title chrome, or legend.",
                )
            )
            continue
        if text.binding.type not in BINDING_TYPES:
            issues.append(
                _issue(
                    "missing_truth_binding",
                    text.node_id,
                    {"binding": text.binding.to_dict()},
                    "Use a supported binding type: container_text, edge_label, anchor_label, free_annotation, title_chrome, or legend_label.",
                )
            )
        if text.binding.type in TARGET_REQUIRED_BINDINGS and text.binding.target_id not in visual_ids:
            issues.append(
                _issue(
                    "missing_truth_binding",
                    text.node_id,
                    {"target_id": text.binding.target_id, "binding": text.binding.to_dict()},
                    "Bind the text node to an existing visual node or change the binding type to free_annotation/title_chrome with a page region.",
                )
            )
        if text.bbox_preferred is not None:
            bbox = text.bbox_preferred.as_list()
            if not _bbox_inside_canvas(bbox, canvas_width, canvas_height):
                issues.append(
                    _issue(
                        "coordinate_space_unresolved",
                        text.node_id,
                        {"bbox_preferred": bbox, "coordinate_space": coordinate_space},
                        "Normalize preferred text bbox to the 1672x941 scene graph coordinate space.",
                    )
                )

    bound_targets = {text.binding.target_id for text in graph.text_nodes if text.binding and text.binding.target_id}
    bound_targets.update(
        intent.target_id for intent in graph.layout_intents if intent.type == "honor_text_zone" and intent.target_id
    )
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
        "schema": GATE_SCHEMA,
        "valid": not any(issue.blocking for issue in issues),
        "blocking_count": sum(1 for issue in issues if issue.blocking),
        "warning_count": 0,
        "issues": issue_payloads,
    }
