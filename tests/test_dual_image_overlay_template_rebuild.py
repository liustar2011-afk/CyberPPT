from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from cyberppt.commands.script_runner import script_path


ROOT = Path(__file__).resolve().parents[1]
REBUILD_ENGINE_DIR = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(REBUILD_ENGINE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REBUILD_ENGINE_DIR))

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import (  # noqa: E402
    OverlayTextBox,
    _editable_boxes_from_scene_graph_or_recognition,
    _prepare_page_images,
)
from scripts.dual_image_overlay.rebuild_engine.script_text_overlay import build_overlay_boxes  # noqa: E402


class DualImageOverlayTemplateRebuildTests(unittest.TestCase):
    def test_template_rebuild_is_exposed_as_cyberppt_script_alias(self) -> None:
        self.assertEqual("template_rebuild.py", script_path("template-rebuild").name)

    def test_vendor_rebuild_subprocess_receives_repo_pythonpath(self) -> None:
        from scripts.dual_image_overlay.template_rebuild import run_vendor_rebuild

        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "page_image_pairs.json"
            manifest.write_text('{"pairs": []}\n', encoding="utf-8")

            with patch("scripts.dual_image_overlay.template_rebuild.subprocess.run") as run:
                run_vendor_rebuild(
                    manifest,
                    ocr_backend="none",
                    force_ocr=False,
                    timeout=10,
                    export=False,
                )

            kwargs = run.call_args.kwargs

        self.assertEqual(ROOT, kwargs["cwd"])
        self.assertIn(str(ROOT), kwargs["env"]["PYTHONPATH"].split(":"))

    def test_template_rebuild_consumes_template_project_and_source_capture(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project)

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))
            source_capture = json.loads((project / "analysis/source_capture.json").read_text(encoding="utf-8"))
            template_gate = json.loads((project / "analysis/template_gate.json").read_text(encoding="utf-8"))
            page_quality = json.loads((project / "analysis/page_quality_report.json").read_text(encoding="utf-8"))
            container_workspace = json.loads(
                (project / "analysis/container_workspace/container_workspace_index.json").read_text(encoding="utf-8")
            )

        self.assertEqual("cyberppt.dual_image.template_rebuild_readiness.v1", readiness["schema"])
        self.assertTrue(readiness["checks"]["template_rebuild_consumed"])
        self.assertTrue(readiness["checks"]["source_capture_consumed"])
        self.assertTrue(readiness["checks"]["template_gate_pass"])
        self.assertFalse(readiness["checks"]["source_capture_gate_pass"])
        self.assertFalse(readiness["checks"]["scene_graph_gate_pass"])
        self.assertEqual(0, readiness["checks"]["scene_graph_gate_pages"])
        self.assertFalse(readiness["checks"]["page_quality_report_pass"])
        self.assertEqual("scene_graph_rework_required", readiness["status"])
        self.assertEqual("cyberppt.dual_image.source_capture.v1", source_capture["schema"])
        self.assertEqual([2], [page["page_number"] for page in source_capture["pages"]])
        self.assertTrue(template_gate["valid"])
        self.assertEqual("cyberppt.dual_image.page_quality_report.v1", page_quality["schema"])
        self.assertEqual("template", page_quality["stage"])
        self.assertFalse(page_quality["valid"])
        self.assertEqual("cyberppt.dual_image.container_workspace_set.v1", container_workspace["schema"])
        self.assertTrue(container_workspace["valid"])
        self.assertEqual(1, container_workspace["slot_count"])
        self.assertIn(
            "template.scene_graph_gate_pass",
            [item["id"] for item in page_quality["blocking_errors"]],
        )
        self.assertEqual(
            str((project / "analysis/page_quality_report.json").resolve()),
            readiness["artifacts"]["page_quality_report"],
        )
        self.assertEqual(
            str((project / "analysis/container_workspace/container_workspace_index.json").resolve()),
            readiness["artifacts"]["container_workspace"],
        )

    def test_template_rebuild_passes_visual_registry_dir_to_source_capture(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            registry_dir = root / "registry"
            _write_template_project(project)
            _write_visual_registry(registry_dir, page_number=2)
            manifest = _write_pair_manifest(root, project)

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                    "--visual-registry-dir",
                    str(registry_dir),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))
            source_capture = json.loads((project / "analysis/source_capture.json").read_text(encoding="utf-8"))
            source_capture_gate = json.loads((project / "analysis/source_capture_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(str(registry_dir.resolve()), readiness["visual_registry_dir"])
        self.assertEqual(str(registry_dir.resolve()), source_capture["inputs"]["visual_registry_dir"])
        self.assertEqual(1, source_capture["inputs"]["visual_registry_elements"])
        self.assertNotIn("non_text_visuals_not_individually_detected", source_capture_gate["gap_counts"])
        self.assertIn("render_delta_not_measured", source_capture_gate["gap_counts"])

    def test_rebuild_ingress_normalizes_full_and_background_to_1280_canvas(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            source_dir = root / "source"
            source_dir.mkdir()
            full = source_dir / "page_006_full.png"
            background = source_dir / "page_006_background.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(full)
            Image.new("RGB", (1672, 941), "#f8fafc").save(background)

            prepared_full, prepared_background, image_size_check = _prepare_page_images(
                full_image=full,
                background_image=background,
                project_path=project,
            )

            with Image.open(prepared_full) as full_image, Image.open(prepared_background) as background_image:
                self.assertEqual((1280, 720), full_image.size)
                self.assertEqual((1280, 720), background_image.size)

        self.assertEqual([1672, 941], image_size_check["source_full_size"])
        self.assertEqual([1672, 941], image_size_check["source_background_size"])
        self.assertEqual([1280, 720], image_size_check["output_size"])
        self.assertEqual("normalized_1280x720", image_size_check["status"])
        self.assertIn("/normalized/", str(prepared_full))
        self.assertIn("/normalized/", str(prepared_background))

    def test_svg_background_href_points_to_normalized_image_dir(self) -> None:
        from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _background_href_for_svg

        href = _background_href_for_svg(Path("/tmp/project/images/normalized/page_002_background_1280x720.png"))

        self.assertEqual("../images/normalized/page_002_background_1280x720.png", href)

    def test_empty_scene_graph_layout_keeps_dual_image_recognition_boxes(self) -> None:
        recognized = [
            OverlayTextBox(
                text="企业入库",
                x=100,
                y=120,
                w=160,
                h=32,
                font_size=18,
                source="script_matched",
            )
        ]

        boxes, source = _editable_boxes_from_scene_graph_or_recognition(
            {"schema": "cyberppt.page_layout_plan.v1", "items": []},
            {"x": 58, "y": 100, "width": 1164, "height": 554},
            recognized,
        )

        self.assertEqual(recognized, boxes)
        self.assertEqual("ocr_script_recognition", source)

    def test_main_flow_script_fallback_uses_card_space_not_ocr_text_bbox(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第7页：主链运行页",
                        "### 主链节点",
                        "1. 企业入库",
                        "明确企业类型、业务范围、目标区域、应用需求",
                        "2. 企业角色识别",
                        "投资运营、规划设计、EPC总包、装备制造、运维服务、供应链服务",
                        "3. 授权取证",
                        "基础评价授权 / 专项评价授权 / 对外传播授权",
                        "4. 数据治理",
                        "清洗、校验、去重、分类、口径统一、版本管理",
                        "5. 证据入库",
                        "按证据类型、能力维度、适用场景、授权边界组织入库",
                        "6. 能力评价",
                        "按评价模型、证据等级、场景适配规则形成评价结论",
                        "7. 专家复核",
                        "对重大结论、关键证据、风险提示、争议事项进行复核",
                        "8. 结果生成",
                        "画像报告、能力评价结果、证明材料、专题报告、风险提示",
                        "9. 场景调用",
                        "投标、融资、供应链、国别进入、行业监测、国际传播",
                        "10. 反馈更新",
                        "使用反馈、异议处理、补证修正、规则修订",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            ocr_items = []
            for index, center in enumerate([92, 220, 348, 476, 596, 716, 836, 964, 1084, 1202], start=1):
                ocr_items.append({"text": str(index), "bbox": [center - 8, 121, center + 8, 144], "confidence": 0.98})
                title = "企业入库" if index == 1 else f"节点{index}"
                ocr_items.append({"text": title, "bbox": [center - 35, 258, center + 35, 276], "confidence": 0.99})
                body = "明确企业类型、\n业务范围、\n目标区域、\n应用需求" if index == 1 else f"节点{index}说明"
                ocr_items.append({"text": body, "bbox": [center - 38, 300, center + 38, 411], "confidence": 0.98})
            layout = {"image_size": {"width": 1280, "height": 720}, "items": ocr_items}

            boxes = build_overlay_boxes(
                script,
                7,
                layout,
                {"x": 20, "y": 104, "width": 1240, "height": 592},
            )

        body = next(box for box in boxes if box.text.startswith("明确企业类型"))
        self.assertEqual("script_main_flow_fallback", body.source)
        self.assertGreater(body.w, 95)
        self.assertGreater(body.h, 110)
        self.assertGreaterEqual(body.font_size, 9.5)

    def test_template_body_region_uses_template_normalized_visual_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project, rebuild_mode="template_body_region")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))

        self.assertEqual("template_body_region", readiness["rebuild_mode"])
        self.assertEqual("template_normalized_reference", readiness["visual_reference_mode"])
        self.assertTrue(str(readiness["artifacts"]["visual_reference"]).endswith("template-normalized-reference.png"))

    def test_full_slide_uses_raw_full_visual_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project, rebuild_mode="full_slide")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))

        self.assertEqual("full_slide", readiness["rebuild_mode"])
        self.assertEqual("raw_full_image", readiness["visual_reference_mode"])
        self.assertTrue(str(readiness["artifacts"]["visual_reference"]).endswith("page_002_full.png"))

    def test_rebuild_mode_defaults_to_template_body_region(self) -> None:
        from scripts.dual_image_overlay.template_rebuild import _resolve_rebuild_mode

        self.assertEqual("template_body_region", _resolve_rebuild_mode({}))
        self.assertEqual("full_slide", _resolve_rebuild_mode({"rebuild_mode": "full_slide"}))
        self.assertEqual(
            "template_body_region",
            _resolve_rebuild_mode({"generation_contract": {"rebuild_mode": "template_body_region"}}),
        )


def _write_template_project(project: Path) -> None:
    (project / "templates").mkdir(parents=True)
    (project / "images").mkdir(parents=True)
    (project / "svg_output").mkdir(parents=True)
    (project / "analysis/ocr").mkdir(parents=True)
    (project / "analysis/semantic_containers").mkdir(parents=True)
    (project / "analysis/typography").mkdir(parents=True)

    (project / "spec_lock.md").write_text("# Spec Lock\n", encoding="utf-8")
    (project / "templates/brand_rules.json").write_text("{}\n", encoding="utf-8")
    (project / "templates/master_elements.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (project / "svg_output/page_002.svg").write_text(
        '<svg><text x="100" y="120">核心结论</text></svg>\n',
        encoding="utf-8",
    )
    (project / "analysis/ocr/page_002_text_mapping.json").write_text(
        json.dumps(
            {
                "page_number": 2,
                "boxes": [
                    {
                        "text": "核心结论",
                        "x": 100,
                        "y": 90,
                        "w": 180,
                        "h": 32,
                        "font_size": 18,
                        "font_family": "Microsoft YaHei",
                        "fill": "#123B66",
                        "font_weight": "700",
                        "align": "left",
                        "word_wrap": False,
                        "source": "script_matched",
                        "confidence": 1.0,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "analysis/semantic_containers/page_002_containers.json").write_text(
        json.dumps(
            {
                "page_number": 2,
                "containers": [
                    {
                        "id": "title",
                        "role": "title",
                        "x": 90,
                        "y": 80,
                        "w": 300,
                        "h": 60,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "analysis/typography/page_002_typography.json").write_text(
        json.dumps(
            {"decisions": [{"text": "核心结论", "rendered_text": "核心结论", "role": "T2", "applied_px": 18}]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_pair_manifest(root: Path, project: Path, *, rebuild_mode: str = "template_body_region") -> Path:
    image_dir = root / "images"
    image_dir.mkdir()
    full = image_dir / "page_002_full.png"
    background = image_dir / "page_002_background.png"
    full.write_bytes(b"fake-full")
    background.write_bytes(b"fake-background")
    manifest = {
        "mode": "cyberppt-dual-image-pair",
        "rebuild_mode": rebuild_mode,
        "project_path": str(project),
        "source_script": str(root / "script.md"),
        "generation_contract": {
            "mode": "template-content-region",
            "rebuild_mode": rebuild_mode,
            "rule": "Generate content-area images only; PPT title, subtitle and enterprise chrome are handled by template/export code.",
        },
        "pairs": [
            {
                "page_number": 2,
                "title": "核心结论",
                "full": {"filename": full.name, "path": str(full), "status": "Generated"},
                "background": {"filename": background.name, "path": str(background), "status": "Generated"},
            }
        ],
    }
    path = root / "page_image_pairs.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_visual_registry(registry_dir: Path, *, page_number: int) -> None:
    registry_dir.mkdir(parents=True)
    (registry_dir / f"slide-{page_number:02d}-visual-element-registry.json").write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_element_registry.v1",
                "elements": [
                    {
                        "element_id": "shape_title_marker",
                        "priority": "P1",
                        "element_type": "shape",
                        "source_component_id": "title_marker",
                        "blueprint_bbox_px": {"x": 88, "y": 74, "w": 12, "h": 58},
                        "ppt_target_bbox_in": {"x": 0.88, "y": 0.74, "w": 0.12, "h": 0.58},
                        "tolerance_px": 4,
                        "measurement_mode": "individual_bbox",
                        "render_bbox_px": None,
                        "delta_px": None,
                        "registration_status": "pending_render_measurement",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
