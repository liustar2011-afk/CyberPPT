from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"))

from scripts.dual_image_overlay.normalize import (  # noqa: E402
    CANVAS,
    normalize_image,
    relative_bbox,
    scale_bbox,
)
from scripts.dual_image_overlay.semantic_plan import load_semantic_plan  # noqa: E402
from script_text_overlay import (  # noqa: E402
    build_overlay_boxes_from_semantic_plan,
    build_semantic_layout_plan,
    build_semantic_layout_qa_report,
    enrich_semantic_plan_with_visual_registry,
    _load_vendored_ppt_master_core,
    normalize_semantic_plan_to_context,
    normalize_semantic_plan_to_canvas,
    reconcile_semantic_plan_with_script_truth,
    resolve_overlay_coordinate_context,
    validate_explicit_semantic_plan,
)


class DualImageOverlaySemanticPlanTests(unittest.TestCase):
    def test_scale_bbox_from_generated_image_to_canvas(self) -> None:
        self.assertEqual(CANVAS, (1280, 720))
        bbox = scale_bbox([167.2, 94.1, 334.4, 188.2], source_size=(1672, 941))
        self.assertEqual(bbox, [128.0, 72.0, 256.0, 144.0])

    def test_relative_bbox_uses_container_safe_area(self) -> None:
        bbox = relative_bbox([100, 50, 500, 250], [0.25, 0.1, 0.75, 0.9])
        self.assertEqual(bbox, [200.0, 70.0, 400.0, 230.0])

    def test_normalize_image_writes_1280x720(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            target = root / "target.png"
            Image.new("RGB", (1672, 941), "#FFFFFF").save(source)

            normalize_image(source, target)

            with Image.open(target) as image:
                self.assertEqual(image.size, (1280, 720))

    def test_load_semantic_plan_requires_explicit_containers_and_items(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "semantic_plan.json"

            path.write_text(
                json.dumps({"image_size": {"width": 1280, "height": 720}, "items": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "semantic_plan.containers"):
                load_semantic_plan(path)

            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "containers": [
                            {
                                "id": "title_bar",
                                "role": "title_container",
                                "bbox": [80, 40, 600, 160],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "semantic_plan.items"):
                load_semantic_plan(path)

    def test_load_semantic_plan_scales_boxes_and_relative_items(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "semantic_plan.json"
            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1672, "height": 941},
                        "containers": [
                            {
                                "id": "title_bar",
                                "role": "title_container",
                                "bbox": [80, 40, 1592, 160],
                                "text_safe_bbox": [100, 60, 1570, 140],
                            }
                        ],
                        "items": [
                            {
                                "source_text": "建议由中电联牵头",
                                "display_text": "建议由中电联牵头",
                                "role": "title",
                                "container_id": "title_bar",
                                "relative_bbox": [0, 0, 1, 1],
                                "font_size": 22,
                                "fill": "#FFFFFF",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            plan = load_semantic_plan(path)

            self.assertEqual(plan.image_size, {"width": 1280, "height": 720})
            self.assertEqual(plan.containers[0].bbox, [61.244, 30.606, 1218.756, 122.423])
            self.assertEqual(plan.containers[0].text_safe_bbox, [76.555, 45.909, 1201.914, 107.12])
            self.assertEqual(plan.items[0].bbox, [76.555, 45.909, 1201.914, 107.12])
            self.assertEqual(plan.items[0].container_id, "title_bar")

    def test_load_semantic_plan_rejects_unknown_container(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "semantic_plan.json"
            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "containers": [
                            {"id": "title_bar", "role": "title", "bbox": [80, 40, 600, 160]}
                        ],
                        "items": [
                            {
                                "display_text": "Missing container",
                                "container_id": "missing",
                                "relative_bbox": [0, 0, 1, 1],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown container_id"):
                load_semantic_plan(path)

    def test_rejects_ocr_as_production_geometry_truth(self) -> None:
        report = validate_explicit_semantic_plan(
            {
                "inputs": {"geometry_truth": "ocr_bbox"},
                "containers": [{"id": "card_1", "role": "ability_card", "bbox": [0, 0, 220, 150]}],
                "items": [
                    {
                        "display_text": "目录管理",
                        "source_text": "目录管理",
                        "role": "ability_title",
                        "container_id": "card_1",
                    }
                ],
            }
        )

        self.assertFalse(report["valid"])
        self.assertIn("ocr_geometry_truth_forbidden", {issue["code"] for issue in report["issues"]})

    def test_accepts_script_and_capture_grounded_semantic_plan(self) -> None:
        report = validate_explicit_semantic_plan(_ability_plan())

        self.assertTrue(report["valid"], report)
        self.assertEqual(0, report["error_count"])

    def test_loads_ppt_master_core_from_vendored_toolchain(self) -> None:
        core = _load_vendored_ppt_master_core()

        self.assertIsNotNone(core)
        self.assertEqual((1280, 720), core.CANVAS)
        self.assertIn("vendor/ppt_master_slide_image_rebuild/scripts/dual_image_rebuild_pptx.py", str(core.__file__))

    def test_ability_card_uses_container_slots_instead_of_item_bbox(self) -> None:
        plan = _ability_plan()
        layout = build_semantic_layout_plan(plan)
        by_text = {item["text"]: item for item in layout["items"]}

        self.assertEqual("semantic_container_safe_bbox_first", layout["layout_policy"])
        self.assertEqual("ability_card_slots", by_text["目录管理"]["layout_strategy"])
        self.assertLess(by_text["1"]["bbox"][0], by_text["目录管理"]["bbox"][0])
        self.assertGreater(by_text["• 指标/能力目录"]["bbox"][0], by_text["1"]["bbox"][0])
        self.assertGreater(by_text["• 目录版本管理"]["bbox"][1], by_text["• 指标/能力目录"]["bbox"][1])

    def test_builds_overlay_boxes_from_semantic_plan(self) -> None:
        boxes, layout, gate = build_overlay_boxes_from_semantic_plan(
            _ability_plan(),
            {"x": 20, "y": 104, "width": 1240, "height": 592},
        )

        self.assertTrue(gate["valid"])
        self.assertEqual(6, len(boxes))
        self.assertEqual("semantic_plan", boxes[0].source)
        self.assertEqual("ability_card_slots", layout["items"][0]["layout_strategy"])

    def test_semantic_overlay_uses_actual_background_size_for_dual_image_coordinates(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "ability_2",
                    "role": "ability_card",
                    "bbox": [643, 148, 822, 257],
                    "text_safe_bbox": [647, 152, 818, 253],
                    "align": "left",
                }
            ],
            "items": [
                {"display_text": "2", "role": "index", "container_id": "ability_2"},
                {"display_text": "身份认证", "role": "ability_title", "container_id": "ability_2"},
            ],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "p6_core_icon_2_identity",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 660, "y": 165, "w": 70, "h": 70},
                }
            ],
        }
        with TemporaryDirectory() as tmpdir:
            background = Path(tmpdir) / "background.png"
            Image.new("RGB", (1672, 941), "white").save(background)

            boxes, _layout, gate = build_overlay_boxes_from_semantic_plan(
                plan,
                {"x": 20, "y": 104, "width": 1240, "height": 592},
                visual_registry=registry,
                background_image=background,
            )

        by_text = {box.text: box for box in boxes}
        self.assertTrue(gate["valid"])
        self.assertGreater(by_text["身份认证"].x, 560)
        self.assertLess(by_text["身份认证"].x, 590)

    def test_explicit_semantic_plan_is_normalized_to_1280_canvas_before_persistence(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "ability_2",
                    "role": "ability_card",
                    "bbox": [643, 148, 822, 257],
                    "text_safe_bbox": [647, 152, 818, 253],
                }
            ],
            "items": [
                {
                    "display_text": "身份认证",
                    "role": "ability_title",
                    "container_id": "ability_2",
                    "bbox": [700, 180, 820, 210],
                }
            ],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "p6_core_icon_2_identity",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 660, "y": 165, "w": 70, "h": 70},
                }
            ],
        }
        with TemporaryDirectory() as tmpdir:
            background = Path(tmpdir) / "background.png"
            Image.new("RGB", (1672, 941), "white").save(background)

            context = resolve_overlay_coordinate_context(
                plan,
                visual_registry=registry,
                background_image=background,
            )
            normalized = normalize_semantic_plan_to_context(plan, context)

        self.assertEqual({"width": 1280.0, "height": 720.0}, normalized["image_size"])
        self.assertEqual([492.25, 113.24, 629.28, 196.64], normalized["containers"][0]["bbox"])
        self.assertEqual([535.89, 137.73, 627.75, 160.68], normalized["items"][0]["bbox"])
        self.assertEqual(
            {
                "input_space": {"width": 1672.0, "height": 941.0},
                "coordinate_space": {"width": 1280.0, "height": 720.0},
                "method": "scale_xyxy_to_normalized_canvas",
            },
            normalized["coordinate_normalization"],
        )

    def test_explicit_semantic_plan_normalization_uses_source_image_size_over_stale_plan_size(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "ability_2",
                    "role": "ability_card",
                    "bbox": [643, 148, 822, 257],
                    "text_safe_bbox": [647, 152, 818, 253],
                }
            ],
            "items": [
                {
                    "display_text": "身份认证",
                    "role": "ability_title",
                    "container_id": "ability_2",
                    "bbox": [700, 180, 820, 210],
                }
            ],
        }

        normalized = normalize_semantic_plan_to_canvas(
            plan,
            input_space={"width": 1672, "height": 941},
        )

        self.assertEqual({"width": 1280.0, "height": 720.0}, normalized["image_size"])
        self.assertEqual([492.25, 113.24, 629.28, 196.64], normalized["containers"][0]["bbox"])
        self.assertEqual(
            {
                "input_space": {"width": 1672.0, "height": 941.0},
                "coordinate_space": {"width": 1280.0, "height": 720.0},
                "method": "scale_xyxy_to_normalized_canvas",
            },
            normalized["coordinate_normalization"],
        )

    def test_normalized_semantic_plan_keeps_1280_input_space_on_reentry(self) -> None:
        plan = {
            "image_size": {"width": 1280, "height": 720},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "ability_2",
                    "role": "ability_card",
                    "bbox": [492.25, 113.24, 629.28, 196.64],
                    "text_safe_bbox": [495.31, 116.3, 626.22, 193.58],
                }
            ],
            "items": [
                {
                    "display_text": "身份认证",
                    "role": "ability_title",
                    "container_id": "ability_2",
                    "bbox": [535.89, 137.73, 627.75, 160.68],
                }
            ],
            "coordinate_normalization": {
                "input_space": {"width": 1672.0, "height": 941.0},
                "coordinate_space": {"width": 1280.0, "height": 720.0},
                "method": "scale_xyxy_to_normalized_canvas",
            },
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "p6_core_icon_2_identity",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 660, "y": 165, "w": 70, "h": 70},
                }
            ],
        }
        with TemporaryDirectory() as tmpdir:
            background = Path(tmpdir) / "background.png"
            Image.new("RGB", (1672, 941), "white").save(background)

            context = resolve_overlay_coordinate_context(
                plan,
                visual_registry=registry,
                background_image=background,
            )

        self.assertEqual({"width": 1280.0, "height": 720.0}, context["semantic_input_space"])
        self.assertEqual({"width": 1672.0, "height": 941.0}, context["visual_registry_input_space"])

    def test_visual_registry_creates_icon_aware_text_safe_area(self) -> None:
        plan = {
            "image_size": {"width": 400, "height": 220},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {"id": "source_1", "role": "source_card", "bbox": [20, 20, 220, 120]},
            ],
            "items": [
                {
                    "display_text": "企业/业务数据\n• 经营管理数据",
                    "source_text": "企业/业务数据\n• 经营管理数据",
                    "role": "list_item",
                    "container_id": "source_1",
                }
            ],
        }
        registry = {
            "blueprint_canvas_px": {"w": 400, "h": 220},
            "elements": [
                {
                    "element_id": "source_icon",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 35, "y": 45, "w": 42, "h": 42},
                },
                {
                    "element_id": "source_text_zone",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 92, "y": 42, "w": 112, "h": 58},
                },
            ],
        }

        enriched = enrich_semantic_plan_with_visual_registry(plan, registry)
        container = enriched["containers"][0]
        layout = build_semantic_layout_plan(plan, visual_registry=registry)
        item = layout["items"][0]

        self.assertEqual("visual_element_registry", container["text_zone_source"])
        self.assertEqual([290.4, 134.45, 656.8, 330.27], container["text_safe_bbox"])
        self.assertEqual("icon_zone", container["reserved_zones"][0]["name"])
        self.assertEqual([290.4, 134.45, 656.8, 330.27], item["bbox"])
        self.assertEqual("visual_element_registry", item["text_zone_source"])
        self.assertEqual("icon_zone", item["reserved_zones"][0]["name"])

    def test_ability_card_ignores_label_text_zone_as_full_safe_area(self) -> None:
        registry = {
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "ability_icon",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 310, "y": 120, "w": 55, "h": 55},
                },
                {
                    "element_id": "ability_label_zone",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 370, "y": 120, "w": 105, "h": 32},
                },
            ],
        }

        layout = build_semantic_layout_plan(_ability_plan(), visual_registry=registry)
        by_text = {item["text"]: item for item in layout["items"]}

        self.assertEqual("ability_card_slots", by_text["目录管理"]["layout_strategy"])
        self.assertLess(by_text["• 目录版本管理"]["bbox"][1], 220)
        self.assertGreater(by_text["• 目录版本管理"]["bbox"][1], by_text["目录管理"]["bbox"][1])

    def test_ability_card_text_avoids_registry_icon_zone(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "ability_2",
                    "role": "ability_card",
                    "bbox": [643, 148, 822, 257],
                    "text_safe_bbox": [647, 152, 818, 253],
                }
            ],
            "items": [
                {"display_text": "2", "role": "index", "container_id": "ability_2"},
                {"display_text": "身份认证", "role": "ability_title", "container_id": "ability_2", "align": "center"},
                {"display_text": "• 主体身份管理", "role": "bullet", "container_id": "ability_2"},
            ],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "stale_canvas_probe",
                    "element_type": "governance_spine",
                    "blueprint_bbox_px": {"x": 1630, "y": 85, "w": 290, "h": 750},
                },
                {
                    "element_id": "p6_core_icon_2_identity",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 660, "y": 165, "w": 70, "h": 70},
                },
                {
                    "element_id": "p6_core_label_2_identity",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 725, "y": 213, "w": 105, "h": 32},
                },
            ],
        }

        layout = build_semantic_layout_plan(plan, visual_registry=registry)
        by_text = {item["text"]: item for item in layout["items"]}

        icon_bbox = by_text["身份认证"]["reserved_zones"][0]["bbox"]
        self.assertGreaterEqual(by_text["身份认证"]["bbox"][0], icon_bbox[2] + 4)
        self.assertGreaterEqual(by_text["• 主体身份管理"]["bbox"][0], icon_bbox[2] + 4)
        self.assertEqual("left", by_text["身份认证"]["align"])
        self.assertIn("anchor_text_after_left_icon", by_text["身份认证"]["layout_hints"]["applied_rules"])
        self.assertIn("honor_registry_text_zone", by_text["身份认证"]["layout_hints"]["applied_rules"])

    def test_coordinate_context_prefers_actual_background_over_stale_plan_size(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "containers": [{"id": "ability_2", "role": "ability_card", "bbox": [640, 145, 825, 260]}],
            "items": [{"display_text": "身份认证", "role": "ability_title", "container_id": "ability_2"}],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "icon_identity",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 660, "y": 165, "w": 70, "h": 70},
                }
            ],
        }
        with TemporaryDirectory() as tmp:
            image = Path(tmp) / "background.png"
            Image.new("RGB", (1672, 941), "white").save(image)

            context = resolve_overlay_coordinate_context(plan, visual_registry=registry, background_image=image)
            layout = build_semantic_layout_plan(plan, visual_registry=registry, coordinate_context=context)

        self.assertEqual({"width": 1280.0, "height": 720.0}, context["coordinate_space"])
        self.assertEqual({"width": 1672.0, "height": 941.0}, context["source_coordinate_space"])
        self.assertEqual("normalized_1280x720", context["coordinate_space_source"])
        self.assertTrue(context["warnings"])
        self.assertEqual("coordinate_space_mismatch", context["warnings"][0]["code"])
        self.assertEqual(context, layout["coordinate_context"])

    def test_coordinate_context_uses_semantic_width_when_right_side_extends_past_background_width(self) -> None:
        plan = {
            "image_size": {"width": 1920, "height": 941},
            "containers": [
                {
                    "id": "governance_1",
                    "role": "governance_step",
                    "bbox": [1663, 148, 1847, 232],
                    "text_safe_bbox": [1742, 160, 1842, 221],
                }
            ],
            "items": [{"display_text": "分类分级", "role": "body", "container_id": "governance_1"}],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1672, "h": 941},
            "elements": [
                {
                    "element_id": "p6_compliance_icon_1",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 1685, "y": 165, "w": 55, "h": 50},
                }
            ],
        }
        with TemporaryDirectory() as tmp:
            image = Path(tmp) / "background.png"
            Image.new("RGB", (1672, 941), "white").save(image)

            context = resolve_overlay_coordinate_context(plan, visual_registry=registry, background_image=image)
            layout = build_semantic_layout_plan(plan, visual_registry=registry, coordinate_context=context)

        self.assertEqual({"width": 1920.0, "height": 941.0}, context["semantic_input_space"])
        self.assertEqual({"width": 1920.0, "height": 941.0}, context["visual_registry_input_space"])
        self.assertLessEqual(layout["items"][0]["bbox"][2], 1280)
        self.assertTrue(
            any(
                item["code"]
                in {"semantic_coordinate_space_uses_plan_extent", "semantic_coordinate_space_follows_registry_extent"}
                for item in context["warnings"]
            )
        )

    def test_reconcile_semantic_plan_uses_script_truth_for_result_apps_and_governance(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                """## 第6页：总体架构\n\n【内容锁定】\n- ### 右侧｜结果应用方\n- **企业应用**\n- 画像管理、投标预审、融资保险\n- **外部合作方应用**\n- 业主/总包方、采购方、金融保险机构\n- **行业组织应用**\n- 行业监测、能力地图、规则跟踪\n- ### 右侧竖条｜安全合规\n- 分类分级｜授权调用｜权限控制｜脱敏处理｜发布审核｜审计留痕\n---\n""",
                encoding="utf-8",
            )
            plan = {
                "image_size": {"width": 1280, "height": 720},
                "inputs": {"script_truth": str(script)},
                "containers": [
                    {"id": "application_1", "role": "application_card", "bbox": [100, 100, 260, 200]},
                    {"id": "application_2", "role": "application_card", "bbox": [100, 220, 260, 320]},
                    {"id": "application_3", "role": "application_card", "bbox": [100, 340, 260, 440]},
                    {"id": "governance_1", "role": "governance_step", "bbox": [300, 100, 380, 150]},
                ],
                "items": [
                    {
                        "display_text": "企业应用\n• 错误内容",
                        "source_text": "企业应用\n• 错误内容",
                        "role": "body",
                        "container_id": "application_1",
                    },
                    {"display_text": "错误扩写", "role": "body", "container_id": "governance_1"},
                ],
            }

            reconciled = reconcile_semantic_plan_with_script_truth(plan, script, 6)

        by_container = {item["container_id"]: item["display_text"] for item in reconciled["items"]}
        self.assertEqual("企业应用\n• 画像管理\n• 投标预审\n• 融资保险", by_container["application_1"])
        self.assertEqual("外部合作方应用\n• 业主/总包方\n• 采购方\n• 金融保险机构", by_container["application_2"])
        self.assertEqual("行业组织应用\n• 行业监测\n• 能力地图\n• 规则跟踪", by_container["application_3"])
        self.assertEqual("分类分级", by_container["governance_1"])
        self.assertEqual("script_truth_reconciled", reconciled["inputs"]["text_truth"])

    def test_semantic_layout_qa_flags_reserved_zone_overlap(self) -> None:
        layout = {
            "schema": "cyberppt.dual_image.semantic_layout_plan.v1",
            "items": [
                {
                    "text": "身份认证",
                    "bbox": [670, 170, 740, 220],
                    "container_safe_bbox": [640, 145, 825, 260],
                    "reserved_zones": [{"name": "icon_zone", "bbox": [660, 165, 730, 235]}],
                }
            ],
        }

        qa = build_semantic_layout_qa_report(layout)

        self.assertFalse(qa["valid"])
        self.assertEqual("text_intersects_reserved_zone", qa["issues"][0]["code"])

    def test_generic_body_text_avoids_left_icon_reserved_zone(self) -> None:
        plan = {
            "image_size": {"width": 1280, "height": 720},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "object_1",
                    "role": "object_pool_cell",
                    "bbox": [330, 470, 430, 520],
                    "text_safe_bbox": [370, 480, 420, 512],
                }
            ],
            "items": [{"display_text": "企业主体类", "role": "body", "container_id": "object_1"}],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "object_icon",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 345, "y": 482, "w": 30, "h": 30},
                }
            ],
        }

        layout = build_semantic_layout_plan(plan, visual_registry=registry)
        qa = build_semantic_layout_qa_report(layout)
        neighbor = layout["text_neighbors"][0]["nearest"]["left"]
        hints = layout["items"][0]["layout_hints"]

        self.assertGreaterEqual(layout["items"][0]["bbox"][0], 379)
        self.assertIn("avoid_left_reserved_zone", hints["applied_rules"])
        self.assertEqual("object_icon", hints["reserved_zone_drivers"][0]["source_element_id"])
        self.assertEqual("object_icon", neighbor["element_id"])
        self.assertEqual("icon", neighbor["element_type"])
        self.assertTrue(qa["valid"])

    def test_service_segment_records_nearby_icon_and_text_zone_hints(self) -> None:
        plan = {
            "image_size": {"width": 1280, "height": 720},
            "inputs": {"script_truth": "script.md", "visual_element_registry": "registry.json"},
            "containers": [
                {
                    "id": "service_5",
                    "role": "service_segment",
                    "bbox": [888, 629, 1053, 690],
                    "text_safe_bbox": [958, 639, 1043, 683],
                }
            ],
            "items": [
                {
                    "display_text": "生态协作服务\n• 合作生态对接\n• 能力开放共享",
                    "role": "service_item",
                    "container_id": "service_5",
                }
            ],
        }
        registry = {
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "service_icon",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 911, "y": 647, "w": 43, "h": 36},
                },
                {
                    "element_id": "service_text_zone",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 961, "y": 652, "w": 80, "h": 24},
                },
            ],
        }

        layout = build_semantic_layout_plan(plan, visual_registry=registry)
        item = layout["items"][0]
        neighbor = layout["text_neighbors"][0]["nearest"]["left"]

        self.assertEqual("service_segment", item["container_role"])
        self.assertIn("anchor_text_after_left_icon", item["layout_hints"]["applied_rules"])
        self.assertIn("honor_registry_text_zone", item["layout_hints"]["applied_rules"])
        self.assertEqual("service_icon", item["layout_hints"]["reserved_zone_drivers"][0]["source_element_id"])
        self.assertEqual("service_icon", neighbor["element_id"])
        self.assertEqual("service_text_zone", layout["text_neighbors"][0]["nearest"]["overlapping"][0]["element_id"])


def _ability_plan() -> dict[str, object]:
    return {
        "image_size": {"width": 1280, "height": 720},
        "inputs": {
            "script_truth": "script-final.md",
            "source_capture": "source_capture.json",
            "visual_element_registry": "slide-06-visual-element-registry.json",
            "geometry_truth": "semantic_containers",
        },
        "containers": [
            {
                "id": "ability_1",
                "role": "ability_card",
                "bbox": [280, 80, 520, 230],
                "text_safe_bbox": [292, 88, 508, 220],
            }
        ],
        "items": [
            {"display_text": "1", "source_text": "1", "role": "index", "container_id": "ability_1"},
            {
                "display_text": "目录管理",
                "source_text": "目录管理",
                "role": "ability_title",
                "container_id": "ability_1",
            },
            {
                "display_text": "• 指标/能力目录",
                "source_text": "指标/能力目录",
                "role": "bullet",
                "container_id": "ability_1",
            },
            {
                "display_text": "• 评估维度管理",
                "source_text": "评估维度管理",
                "role": "bullet",
                "container_id": "ability_1",
            },
            {
                "display_text": "• 分类与标签管理",
                "source_text": "分类与标签管理",
                "role": "bullet",
                "container_id": "ability_1",
            },
            {
                "display_text": "• 目录版本管理",
                "source_text": "目录版本管理",
                "role": "bullet",
                "container_id": "ability_1",
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
