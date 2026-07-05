from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.script_runner import script_path
from scripts.dual_image_overlay.source_capture import (
    attach_render_delta_measurement,
    build_source_capture,
    build_source_capture_gate,
)


class DualImageOverlaySourceCaptureTests(unittest.TestCase):
    def test_source_capture_is_exposed_as_cyberppt_script_alias(self) -> None:
        self.assertEqual("source_capture.py", script_path("source-capture").name)

    def test_builds_unified_capture_from_existing_rebuild_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)

            capture = build_source_capture(project_dir)

        self.assertEqual(capture["schema"], "cyberppt.dual_image.source_capture.v1")
        self.assertEqual(capture["inputs"]["ocr_text_mappings"], 2)
        self.assertEqual(capture["capture_policy"]["text_wrap_before_shrink"], True)
        self.assertEqual(len(capture["pages"]), 1)

        page = capture["pages"][0]
        self.assertEqual(page["page_number"], 2)
        self.assertEqual(page["source_images"]["full"]["filename"], "page_002_full.png")
        self.assertEqual(page["image_regions"]["generation_contract"]["brand_body_region"]["x"], 58)
        self.assertEqual(page["containers"][0]["id"], "so_what_band")

        text_objects = page["text_objects"]
        self.assertEqual(text_objects[0]["style"]["typography_role"], "T8")
        self.assertEqual(text_objects[0]["rendered_text"], "建议按规则先行路径\n启动首阶段工作")
        self.assertTrue(text_objects[0]["layout"]["needs_wrapping"])
        self.assertEqual(text_objects[1]["source"]["kind"], "script_matched")
        self.assertEqual(text_objects[0]["style"]["font_size_px"], 14)
        self.assertEqual(text_objects[0]["style"]["font_size_pt"], 10.5)
        self.assertEqual(text_objects[0]["style"]["applied_font_size_px"], 16)
        self.assertEqual(text_objects[0]["style"]["applied_font_size_pt"], 12.0)

        inventory = page["visual_element_inventory"]
        self.assertTrue(any(item["element_id"] == "so_what_band" and item["element_type"] == "container" for item in inventory))
        self.assertTrue(any(item["element_id"] == "text_001" and item["priority"] == "P0" for item in inventory))
        self.assertTrue(
            any(gap["code"] == "non_text_visuals_not_individually_detected" for gap in page["capture_gaps"])
        )
        self.assertTrue(any(gap["code"] == "render_delta_not_measured" for gap in page["capture_gaps"]))

        rules = page["layout_rules"]
        self.assertTrue(rules["avoidance_policy"]["text_should_wrap_before_shrink"])
        self.assertEqual(rules["baseline_groups"][0]["candidate_y"], 621.45)

    def test_visual_registry_resolves_non_text_gap_but_keeps_render_delta_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            registry_dir = project_dir / "registry"
            _write_visual_registry(registry_dir, page_number=2)

            capture = build_source_capture(project_dir, visual_registry_dir=registry_dir)
            gate = build_source_capture_gate(capture)

        page = capture["pages"][0]
        inventory = page["visual_element_inventory"]
        registry_element = next(item for item in inventory if item["element_id"] == "icon_rule_path")
        self.assertEqual("visual_element_registry", registry_element["source"]["kind"])
        self.assertEqual("source_icon_rule", registry_element["source_component_id"])
        self.assertEqual({"x": 710, "y": 590, "w": 42, "h": 42}, registry_element["blueprint_bbox_px"])
        self.assertEqual({"x": 7.1, "y": 5.9, "w": 0.42, "h": 0.42}, registry_element["ppt_target_bbox_in"])
        self.assertIsNone(registry_element["render_bbox_px"])
        self.assertIsNone(registry_element["delta_px"])
        self.assertEqual("pending_render_measurement", registry_element["registration_status"])
        self.assertNotIn("non_text_visuals_not_individually_detected", gate["gap_counts"])
        self.assertIn("render_delta_not_measured", gate["gap_counts"])
        self.assertFalse(gate["valid"])

    def test_dual_image_editable_evidence_satisfies_missing_explicit_semantic_plan_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            registry_dir = project_dir / "registry"
            _write_visual_registry(registry_dir, page_number=2)
            (project_dir / "analysis/scene_graph_gate").mkdir(parents=True, exist_ok=True)
            _write_json(
                project_dir / "analysis/scene_graph_gate/page_002_scene_graph_gate.json",
                {"schema": "cyberppt.page_scene_graph_gate.v1", "valid": True, "blocking_count": 0},
            )
            (project_dir / "analysis/semantic_plan_gate").mkdir(parents=True, exist_ok=True)
            _write_json(
                project_dir / "analysis/semantic_plan_gate/page_002_semantic_plan_gate.json",
                {
                    "schema": "cyberppt.dual_image.semantic_plan_gate.v1",
                    "valid": False,
                    "issues": [{"code": "missing_semantic_plan"}],
                },
            )

            capture = build_source_capture(project_dir, visual_registry_dir=registry_dir)

        gaps = {gap["code"] for gap in capture["pages"][0]["capture_gaps"]}
        self.assertNotIn("semantic_plan_gate_failed", gaps)
        self.assertNotIn("non_text_visuals_not_individually_detected", gaps)

    def test_missing_semantic_plan_does_not_block_dual_image_source_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            (project_dir / "analysis/scene_graph_gate").mkdir(parents=True, exist_ok=True)
            _write_json(
                project_dir / "analysis/scene_graph_gate/page_002_scene_graph_gate.json",
                {"schema": "cyberppt.page_scene_graph_gate.v1", "valid": True, "blocking_count": 0},
            )
            (project_dir / "analysis/semantic_plan_gate").mkdir(parents=True, exist_ok=True)
            _write_json(
                project_dir / "analysis/semantic_plan_gate/page_002_semantic_plan_gate.json",
                {
                    "schema": "cyberppt.dual_image.semantic_plan_gate.v1",
                    "valid": False,
                    "issues": [{"code": "missing_semantic_plan"}],
                },
            )

            capture = build_source_capture(project_dir)
            gate = build_source_capture_gate(capture)

        gaps = {gap["code"] for gap in capture["pages"][0]["capture_gaps"]}
        self.assertNotIn("semantic_plan_gate_failed", gaps)
        self.assertNotIn("semantic_plan_gate_failed", gate["gap_counts"])
        self.assertIn("non_text_visuals_not_individually_detected", gate["gap_counts"])

    def test_source_capture_exposes_semantic_layout_container_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            layout_dir = project_dir / "analysis" / "semantic_layout_plan"
            layout_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                layout_dir / "page_002_layout_plan.json",
                {
                    "schema": "cyberppt.dual_image.semantic_layout_plan.v1",
                    "container_relations": [
                        {
                            "container_id": "ability_2",
                            "container_role": "ability_card",
                            "element_id": "icon_identity",
                            "element_type": "icon",
                            "relation": "contained_or_component_matched",
                            "bbox": [660, 165, 730, 235],
                        }
                    ],
                    "text_neighbors": [
                        {
                            "text": "身份认证",
                            "container_id": "ability_2",
                            "nearest": {
                                "left": {
                                    "element_id": "icon_identity",
                                    "element_type": "icon",
                                    "distance": 4,
                                }
                            },
                        }
                    ],
                    "items": [],
                },
            )

            capture = build_source_capture(project_dir)

        page = capture["pages"][0]
        self.assertEqual(
            [
                {
                    "container_id": "ability_2",
                    "container_role": "ability_card",
                    "element_id": "icon_identity",
                    "element_type": "icon",
                    "relation": "contained_or_component_matched",
                    "bbox": [660, 165, 730, 235],
                }
            ],
            page["semantic_relationships"],
        )
        self.assertEqual("身份认证", page["text_neighbor_relationships"][0]["text"])
        self.assertEqual("icon_identity", page["text_neighbor_relationships"][0]["nearest"]["left"]["element_id"])

    def test_source_capture_includes_scene_graph_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "analysis" / "scene_graph").mkdir(parents=True)
            (project_dir / "analysis" / "scene_graph_gate").mkdir(parents=True)
            (project_dir / "analysis" / "page_layout_plan").mkdir(parents=True)
            (project_dir / "analysis" / "render_qa").mkdir(parents=True)
            _write_json(
                project_dir / "analysis" / "scene_graph" / "page_006_scene_graph.json",
                {"schema": "cyberppt.page_scene_graph.v1", "page": 6, "text_nodes": []},
            )
            _write_json(
                project_dir / "analysis" / "scene_graph_gate" / "page_006_scene_graph_gate.json",
                {"schema": "cyberppt.page_scene_graph_gate.v1", "valid": True, "blocking_count": 0},
            )
            _write_json(
                project_dir / "analysis" / "page_layout_plan" / "page_006_layout_plan.json",
                {"schema": "cyberppt.page_layout_plan.v1", "page": 6, "items": []},
            )
            _write_json(
                project_dir / "analysis" / "render_qa" / "page_006_render_qa.json",
                {"schema": "cyberppt.scene_graph.render_qa.v1", "valid": True, "blocking_count": 0},
            )

            capture = build_source_capture(project_dir)

        page = capture["pages"][0]
        self.assertEqual("cyberppt.page_scene_graph.v1", page["scene_graph"]["schema"])
        self.assertTrue(page["scene_graph_gate"]["valid"])
        self.assertEqual("cyberppt.page_layout_plan.v1", page["page_layout_plan"]["schema"])
        self.assertEqual("cyberppt.scene_graph.render_qa.v1", page["render_qa"]["schema"])
        self.assertEqual(1, capture["inputs"]["scene_graph_pages"])
        self.assertEqual(1, capture["inputs"]["render_qa_pages"])

    def test_pair_manifest_scopes_visual_registry_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            registry_dir = project_dir / "registry"
            _write_visual_registry(registry_dir, page_number=2)
            _write_visual_registry(registry_dir, page_number=3, element_id="icon_other_page")

            capture = build_source_capture(
                project_dir,
                pair_manifest_path=project_dir / "images" / "page_image_pairs.json",
                visual_registry_dir=registry_dir,
            )

        self.assertEqual([2], [page["page_number"] for page in capture["pages"]])
        self.assertEqual(1, capture["inputs"]["visual_registry_elements"])
        inventory = capture["pages"][0]["visual_element_inventory"]
        self.assertTrue(any(item["element_id"] == "icon_rule_path" for item in inventory))
        self.assertFalse(any(item["element_id"] == "icon_other_page" for item in inventory))

    def test_render_delta_measurement_resolves_gate_gap_when_registry_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)
            registry_dir = project_dir / "registry"
            _write_visual_registry(registry_dir, page_number=2)
            capture = build_source_capture(project_dir, visual_registry_dir=registry_dir)

            measured = attach_render_delta_measurement(
                capture,
                rendered_preview="/tmp/page-render.png",
            )
            gate = build_source_capture_gate(measured)

        self.assertTrue(gate["valid"])
        self.assertEqual({}, gate["gap_counts"])
        self.assertTrue(gate["checks"]["capture_gaps_resolved"])
        page = measured["pages"][0]
        self.assertTrue(all(item["registration_status"] == "passed" for item in page["visual_element_inventory"]))
        self.assertEqual([], page["capture_gaps"])


def _write_artifacts(project_dir: Path) -> None:
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "analysis" / "ocr").mkdir(parents=True)
    (project_dir / "analysis" / "semantic_containers").mkdir(parents=True)
    (project_dir / "analysis" / "typography").mkdir(parents=True)
    (project_dir / "svg_output").mkdir(parents=True)

    _write_json(
        project_dir / "images" / "page_image_pairs.json",
        {
            "generation_contract": {
                "slide_canvas": {"width": 1280, "height": 720},
                "brand_body_region": {"x": 58, "y": 122, "width": 1164, "height": 554},
            },
            "pairs": [
                {
                    "page_number": 2,
                    "full": {"filename": "page_002_full.png", "path": "/tmp/page_002_full.png", "status": "ready"},
                    "background": {
                        "filename": "page_002_background.png",
                        "path": "/tmp/page_002_background.png",
                        "status": "ready",
                    },
                }
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "ocr" / "page_002_text_mapping.json",
        {
            "page_number": 2,
            "boxes": [
                _box("建议按规则先行路径启动首阶段工作", 166, 604, 460, 22, "ocr_unmatched"),
                _box("规则先行", 720, 621, 72, 22, "script_matched"),
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "semantic_containers" / "page_002_containers.json",
        {
            "page_number": 2,
            "containers": [
                {
                    "id": "so_what_band",
                    "role": "foundation_base",
                    "x": 58,
                    "y": 582,
                    "w": 1164,
                    "h": 91,
                    "background": "dark",
                    "fill": "#FFFFFF",
                }
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "typography" / "page_002_cyberppt_typography.json",
        {
            "decisions": [
                {
                    "text": "建议按规则先行路径启动首阶段工作",
                    "rendered_text": "建议按规则先行路径\n启动首阶段工作",
                    "role": "T8",
                    "applied_px": 16,
                },
                {"text": "规则先行", "rendered_text": "规则先行", "role": "T6", "applied_px": 14.67},
            ]
        },
    )
    _write_json(
        project_dir / "analysis" / "candidate_layout_rules.json",
        {
            "line_break": {
                "phrase_breaks": [
                    {
                        "compact_text": "建议按规则先行路径启动首阶段工作",
                        "break_text": "建议按规则先行路径\n启动首阶段工作",
                        "support": 1,
                    }
                ]
            },
            "baseline_groups": [
                {"page_number": 2, "candidate_y": 621.45, "labels": ["建议", "规则先行"], "support": 2}
            ],
            "alignment_issues": [],
        },
    )
    (project_dir / "svg_output" / "page_002.svg").write_text(
        '<svg><text x="166" y="616" font-size="16">建议按规则先行路径启动首阶段工作</text></svg>',
        encoding="utf-8",
    )


def _box(text: str, x: float, y: float, w: float, h: float, source: str) -> dict[str, object]:
    return {
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "font_size": 14,
        "font_family": "Microsoft YaHei",
        "fill": "#FFFFFF",
        "font_weight": "700",
        "align": "center",
        "word_wrap": True,
        "source": source,
        "confidence": 0.96,
    }


def _write_visual_registry(registry_dir: Path, *, page_number: int, element_id: str = "icon_rule_path") -> None:
    _write_json(
        registry_dir / f"slide-{page_number:02d}-visual-element-registry.json",
        {
            "schema": "cyberppt.visual_element_registry.v1",
            "elements": [
                {
                    "element_id": element_id,
                    "priority": "P0",
                    "element_type": "icon",
                    "source_component_id": "source_icon_rule",
                    "blueprint_bbox_px": {"x": 710, "y": 590, "w": 42, "h": 42},
                    "ppt_target_bbox_in": {"x": 7.1, "y": 5.9, "w": 0.42, "h": 0.42},
                    "tolerance_px": 3,
                    "measurement_mode": "individual_bbox",
                    "render_bbox_px": None,
                    "delta_px": None,
                    "registration_status": "pending_render_measurement",
                }
            ],
        },
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
