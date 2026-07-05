import json
from pathlib import Path

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import (
    _overlay_boxes_from_scene_graph_layout,
    _scene_graph_artifact_paths,
    _scene_graph_gate_blocks_export,
)
from scripts.dual_image_overlay.template_rebuild import build_template_rebuild_readiness


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


def test_scene_graph_layout_replaces_legacy_overlay_boxes():
    boxes = _overlay_boxes_from_scene_graph_layout(
        {
            "schema": "cyberppt.page_layout_plan.v1",
            "items": [
                {
                    "node_id": "text_1",
                    "text": "企业应用",
                    "bbox": [640, 180, 960, 360],
                    "font_size": 16,
                    "font_weight": "700",
                    "align": "left",
                    "word_wrap": True,
                }
            ],
        },
        {"x": 58, "y": 100, "width": 1164, "height": 554},
    )

    assert len(boxes) == 1
    assert boxes[0].source == "scene_graph_layout"
    assert boxes[0].text == "企业应用"
    assert boxes[0].x == 640.0
    assert boxes[0].y == 238.5
    assert boxes[0].w == 291.0
    assert boxes[0].h == 138.5
    assert boxes[0].font_size == 12.31


def test_template_readiness_requires_scene_graph_gate(tmp_path: Path):
    project = tmp_path / "project"
    _write_minimal_project(project)
    manifest = _write_pair_manifest(tmp_path, project)

    readiness = build_template_rebuild_readiness(manifest, export_requested=False)

    assert readiness["valid"] is False
    assert readiness["status"] == "scene_graph_rework_required"
    assert readiness["checks"]["scene_graph_gate_pass"] is False
    assert readiness["checks"]["scene_graph_gate_pages"] == 0


def test_template_readiness_reports_scene_graph_gate_pass(tmp_path: Path):
    project = tmp_path / "project"
    _write_minimal_project(project)
    _write_scene_graph_gate(project, page_number=6, valid=True)
    manifest = _write_pair_manifest(tmp_path, project)

    readiness = build_template_rebuild_readiness(manifest, export_requested=False)

    assert readiness["checks"]["scene_graph_gate_pass"] is True
    assert readiness["checks"]["scene_graph_gate_pages"] == 1


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


def _write_minimal_project(project: Path) -> None:
    (project / "templates").mkdir(parents=True)
    (project / "images").mkdir(parents=True)
    (project / "svg_output").mkdir(parents=True)
    (project / "analysis/ocr").mkdir(parents=True)
    (project / "analysis/semantic_containers").mkdir(parents=True)
    (project / "analysis/typography").mkdir(parents=True)
    (project / "spec_lock.md").write_text("# Spec Lock\n", encoding="utf-8")
    (project / "templates/brand_rules.json").write_text("{}\n", encoding="utf-8")
    (project / "templates/master_elements.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (project / "svg_output/page_006.svg").write_text(
        '<svg><text x="100" y="120">核心结论</text></svg>\n',
        encoding="utf-8",
    )
    (project / "analysis/ocr/page_006_text_mapping.json").write_text(
        json.dumps(
            {
                "page_number": 6,
                "boxes": [
                    {
                        "text": "核心结论",
                        "x": 100,
                        "y": 90,
                        "w": 180,
                        "h": 32,
                        "source": "script_matched",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "analysis/semantic_containers/page_006_containers.json").write_text(
        json.dumps({"page_number": 6, "containers": []}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_scene_graph_gate(project: Path, *, page_number: int, valid: bool) -> None:
    path = project / "analysis" / "scene_graph_gate" / f"page_{page_number:03d}_scene_graph_gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.page_scene_graph_gate.v1",
                "valid": valid,
                "blocking_count": 0 if valid else 1,
                "issues": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_pair_manifest(root: Path, project: Path) -> Path:
    manifest = root / "page_image_pairs.json"
    manifest.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "pairs": [{"page_number": 6}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
