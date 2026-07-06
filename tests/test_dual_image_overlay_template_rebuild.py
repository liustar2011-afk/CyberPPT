from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image, ImageDraw

from cyberppt.commands.script_runner import script_path


ROOT = Path(__file__).resolve().parents[1]
REBUILD_ENGINE_DIR = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(REBUILD_ENGINE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REBUILD_ENGINE_DIR))

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import (  # noqa: E402
    OverlayTextBox,
    _editable_boxes_from_scene_graph_or_recognition,
    _overlay_boxes_from_scene_graph_layout,
    _prepare_page_images,
    _write_page_understanding_artifact,
)
from scripts.dual_image_overlay.rebuild_engine.script_text_overlay import (  # noqa: E402
    MULTILINE_LINE_HEIGHT_FACTOR,
    OverlayTextBox as ScriptOverlayTextBox,
    _estimated_line_count,
    _fit_all_boxes,
    _wrap_svg_text,
    build_overlay_boxes,
    boxes_to_json,
    overlay_boxes_from_page_understanding,
)


class DualImageOverlayTemplateRebuildTests(unittest.TestCase):
    def test_template_rebuild_is_exposed_as_cyberppt_script_alias(self) -> None:
        self.assertEqual("template_rebuild.py", script_path("template-rebuild").name)

    def test_editable_overlay_rebuild_supports_module_help_execution(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "-m",
                "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild",
                "--help",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout)

    def test_script_text_overlay_supports_module_help_execution(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "-m",
                "scripts.dual_image_overlay.rebuild_engine.script_text_overlay",
                "--help",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout)

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
            _write_scene_graph_gate(project, page_number=2, valid=True)
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
            preflight_gate = json.loads((project / "analysis/preflight_gate.json").read_text(encoding="utf-8"))
            build_gate = json.loads((project / "analysis/build_gate.json").read_text(encoding="utf-8"))
            postflight_gate = json.loads((project / "analysis/postflight_gate.json").read_text(encoding="utf-8"))
            page_quality = json.loads((project / "analysis/page_quality_report.json").read_text(encoding="utf-8"))
            container_workspace = json.loads(
                (project / "analysis/container_workspace/container_workspace_index.json").read_text(encoding="utf-8")
            )
            workspace_assignment = json.loads(
                (project / "analysis/workspace_assignment/workspace_assignment_index.json").read_text(encoding="utf-8")
            )

        self.assertEqual("cyberppt.dual_image.template_rebuild_readiness.v1", readiness["schema"])
        self.assertTrue(readiness["checks"]["template_rebuild_consumed"])
        self.assertTrue(readiness["checks"]["source_capture_consumed"])
        self.assertTrue(readiness["checks"]["preflight_gate_pass"])
        self.assertTrue(readiness["checks"]["build_gate_pass"])
        self.assertFalse(readiness["checks"]["postflight_gate_pass"])
        self.assertTrue(readiness["checks"]["template_gate_pass"])
        self.assertFalse(readiness["checks"]["source_capture_gate_pass"])
        self.assertTrue(readiness["checks"]["scene_graph_gate_pass"])
        self.assertEqual(1, readiness["checks"]["scene_graph_gate_pages"])
        self.assertFalse(readiness["checks"]["page_quality_report_pass"])
        self.assertEqual("postflight_rework_required", readiness["status"])
        self.assertEqual("cyberppt.dual_image.source_capture.v1", source_capture["schema"])
        self.assertEqual([2], [page["page_number"] for page in source_capture["pages"]])
        self.assertTrue(template_gate["valid"])
        self.assertEqual("preflight", preflight_gate["stage"])
        self.assertTrue(preflight_gate["valid"], preflight_gate)
        self.assertEqual("build", build_gate["stage"])
        self.assertTrue(build_gate["valid"], build_gate)
        self.assertEqual("postflight", postflight_gate["stage"])
        self.assertFalse(postflight_gate["valid"])
        self.assertIn("postflight.visual_qa_gate_pass", [item["id"] for item in postflight_gate["blocking_errors"]])
        self.assertEqual("cyberppt.dual_image.page_quality_report.v1", page_quality["schema"])
        self.assertEqual("template", page_quality["stage"])
        self.assertFalse(page_quality["valid"])
        self.assertEqual("cyberppt.dual_image.container_workspace_set.v1", container_workspace["schema"])
        self.assertTrue(container_workspace["valid"])
        self.assertEqual(1, container_workspace["slot_count"])
        self.assertEqual("cyberppt.dual_image.workspace_assignment_set.v1", workspace_assignment["schema"])
        self.assertTrue(workspace_assignment["valid"])
        self.assertEqual(1, workspace_assignment["assignment_count"])
        self.assertNotIn(
            "template.scene_graph_gate_pass",
            [item["id"] for item in page_quality["blocking_errors"]],
        )
        self.assertIn(
            "template.visual_qa_gate_pass",
            [item["id"] for item in page_quality["blocking_errors"]],
        )
        self.assertFalse(readiness["checks"]["visual_qa_gate_pass"])
        self.assertEqual(
            str((project / "analysis/visual_qa_gate.json").resolve()),
            readiness["artifacts"]["visual_qa_gate"],
        )
        self.assertEqual(
            str((project / "analysis/page_quality_report.json").resolve()),
            readiness["artifacts"]["page_quality_report"],
        )
        self.assertEqual(
            str((project / "analysis/preflight_gate.json").resolve()),
            readiness["artifacts"]["preflight_gate"],
        )
        self.assertEqual(
            str((project / "analysis/build_gate.json").resolve()),
            readiness["artifacts"]["build_gate"],
        )
        self.assertEqual(
            str((project / "analysis/postflight_gate.json").resolve()),
            readiness["artifacts"]["postflight_gate"],
        )
        self.assertEqual(
            str((project / "analysis/container_workspace/container_workspace_index.json").resolve()),
            readiness["artifacts"]["container_workspace"],
        )
        self.assertEqual(
            str((project / "analysis/workspace_assignment/workspace_assignment_index.json").resolve()),
            readiness["artifacts"]["workspace_assignment"],
        )

    def test_template_workspace_infers_structure_when_capture_containers_are_too_coarse(self) -> None:
        from scripts.dual_image_overlay.template_rebuild import _build_template_container_workspaces

        with TemporaryDirectory() as directory:
            project = Path(directory)
            source_capture = {
                "pages": [
                    {
                        "page_number": 3,
                        "containers": [
                            {"id": "coarse_band", "role": "dark_band", "x": 40, "y": 230, "w": 1200, "h": 50}
                        ],
                        "text_objects": [
                            _capture_text("top_summary", 150, 140, 900, 24),
                            _capture_text("top_detail", 150, 176, 760, 24),
                            _capture_text("1", 70, 250, 14, 22),
                            _capture_text("A title", 114, 250, 130, 20),
                            _capture_text("A body", 110, 316, 180, 18),
                            _capture_text("2", 390, 250, 14, 22),
                            _capture_text("B title", 432, 250, 130, 20),
                            _capture_text("B body", 424, 316, 180, 18),
                            _capture_text("3", 696, 250, 14, 22),
                            _capture_text("C title", 730, 250, 130, 20),
                            _capture_text("C body", 728, 316, 180, 18),
                            _capture_text("4", 990, 250, 14, 22),
                            _capture_text("D title", 1034, 250, 130, 20),
                            _capture_text("D body", 1028, 316, 180, 18),
                            _capture_text("bottom 1", 194, 620, 162, 31),
                            _capture_text("bottom 2", 451, 620, 162, 31),
                            _capture_text("bottom 3", 714, 620, 162, 31),
                            _capture_text("bottom 4", 969, 620, 162, 31),
                        ],
                        "image_regions": {"canvas": {"width": 1280, "height": 720}},
                        "visual_element_inventory": [],
                    }
                ]
            }

            workspace, assignment = _build_template_container_workspaces(project, source_capture)
            structure_inference = json.loads(
                (project / "analysis/structure_inference/page_003_structure_inference.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertTrue(workspace["valid"], workspace)
        self.assertEqual("cyberppt.dual_image.structure_inference.v1", structure_inference["schema"])
        self.assertEqual(6, workspace["container_count"])
        self.assertGreaterEqual(workspace["slot_count"], 6)
        self.assertTrue(assignment["valid"], assignment)
        self.assertEqual(18, assignment["assignment_count"])

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

    def test_template_rebuild_generates_draft_visual_registry_from_source_capture(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project, with_visual_line=True)

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
            source_capture_gate = json.loads((project / "analysis/source_capture_gate.json").read_text(encoding="utf-8"))
            registry_dir = project / "analysis/visual_registry"
            self.assertTrue((registry_dir / "page_002_visual_element_registry.json").is_file())

        registry_dir = project / "analysis/visual_registry"
        self.assertTrue(readiness["draft_visual_registry_generated"])
        self.assertTrue(readiness["checks"]["draft_visual_registry_generated"])
        self.assertEqual(str(registry_dir.resolve()), readiness["visual_registry_dir"])
        self.assertEqual(str(registry_dir.resolve()), readiness["artifacts"]["draft_visual_registry"])
        self.assertEqual(str(registry_dir.resolve()), source_capture["inputs"]["visual_registry_dir"])
        self.assertGreater(source_capture["inputs"]["visual_registry_elements"], 0)
        self.assertNotIn("non_text_visuals_not_individually_detected", source_capture_gate["gap_counts"])
        self.assertIn("render_delta_not_measured", source_capture_gate["gap_counts"])

    def test_template_rebuild_generates_semantic_binding_when_explicit_plan_missing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            _write_scene_graph_gate(project, page_number=2, valid=True)
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
            self.assertTrue((project / "analysis/semantic_binding/page_002_semantic_binding.json").is_file())

    def test_rebuild_ingress_normalizes_full_and_background_to_1672_canvas(self) -> None:
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
                self.assertEqual((1672, 941), full_image.size)
                self.assertEqual((1672, 941), background_image.size)

        self.assertEqual([1672, 941], image_size_check["source_full_size"])
        self.assertEqual([1672, 941], image_size_check["source_background_size"])
        self.assertEqual([1672, 941], image_size_check["output_size"])
        self.assertEqual("normalized_1672x941", image_size_check["status"])
        self.assertIn("/normalized/", str(prepared_full))
        self.assertIn("/normalized/", str(prepared_background))

    def test_svg_background_href_points_to_normalized_image_dir(self) -> None:
        from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _background_href_for_svg

        href = _background_href_for_svg(Path("/tmp/project/images/normalized/page_002_background_1672x941.png"))

        self.assertEqual("../images/normalized/page_002_background_1672x941.png", href)

    def test_editable_overlay_rebuild_help_works_from_repo_root_and_script_dir(self) -> None:
        script = REBUILD_ENGINE_DIR / "editable_overlay_rebuild.py"

        from_root = subprocess.run(
            ["python3", str(script), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        from_script_dir = subprocess.run(
            ["python3", "editable_overlay_rebuild.py", "--help"],
            cwd=REBUILD_ENGINE_DIR,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, from_root.returncode, from_root.stdout + from_root.stderr)
        self.assertIn("Rebuild CyberPPT full/background image pairs", from_root.stdout)
        self.assertEqual(0, from_script_dir.returncode, from_script_dir.stdout + from_script_dir.stderr)
        self.assertIn("Rebuild CyberPPT full/background image pairs", from_script_dir.stdout)

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

    def test_overlay_boxes_drop_ocr_tail_duplicates_and_normalize_column_alignment(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第3页：当前形势与开展综合能力证明服务的必要性",
                        "### 能力维度扩展",
                        "项目履约：业绩、合同、质量安全",
                        "治理合规：反腐败、制裁、税务",
                        "E&S/HSE：环境、安全、劳工社区",
                        "国别适配：准入、属地、风险应对",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 1280, "height": 720},
                "items": [
                    {
                        "text": "对象来源：央企境外成员企业",
                        "bbox": [110, 303, 260, 321],
                        "confidence": 0.96,
                    },
                    {
                        "text": "项目履约：业绩、合同、质量安全",
                        "bbox": [424, 303, 581, 321],
                        "confidence": 0.96,
                    },
                    {"text": "质量安全", "bbox": [424, 329, 501, 347], "confidence": 0.96},
                    {
                        "text": "治理合规：反腐败、制裁、税务",
                        "bbox": [424, 371, 586, 390],
                        "confidence": 0.96,
                    },
                    {"text": "税务", "bbox": [424, 398, 465, 416], "confidence": 0.96},
                    {
                        "text": "E&S/HSE：环境、安全、劳工社区",
                        "bbox": [424, 440, 577, 459],
                        "confidence": 0.96,
                    },
                    {"text": "劳工社区", "bbox": [424, 468, 504, 485], "confidence": 0.96},
                    {
                        "text": "结果交付：报告、证书、档案",
                        "bbox": [728, 303, 882, 321],
                        "confidence": 0.96,
                    },
                    {
                        "text": "持续更新：规则、证据、状态",
                        "bbox": [1028, 303, 1188, 321],
                        "confidence": 0.96,
                    },
                ],
            }

            boxes = build_overlay_boxes(
                script,
                3,
                layout,
                {"x": 20, "y": 104, "width": 1240, "height": 592},
            )

        texts = [box.text for box in boxes]
        self.assertIn("项目履约：业绩、合同、质量安全", texts)
        self.assertNotIn("质量安全", texts)
        self.assertNotIn("税务", texts)
        self.assertNotIn("劳工社区", texts)
        self.assertEqual({"left"}, {box.align for box in boxes})
        self.assertGreaterEqual(min(box.font_size for box in boxes), 12.0)
        project_box = next(box for box in boxes if box.text.startswith("项目履约"))
        self.assertGreaterEqual(project_box.w, 190.0)
        self.assertEqual([project_box.text], _wrap_svg_text(project_box.text, project_box.w, project_box.font_size))

    def test_overlay_boxes_merge_stacked_arrow_flow_fragments(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第13页：科技金融赋能服务",
                        "### 投后链路",
                        "融资申请→风控审核→放款→还款，全流程线上化",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 1280, "height": 720},
                "items": [
                    {"text": "融资申请→风控审核", "bbox": [630, 449, 708, 460], "confidence": 0.94},
                    {"text": "→放款→还款", "bbox": [643, 464, 704, 475], "confidence": 0.94},
                    {"text": "全流程线上化", "bbox": [646, 480, 708, 491], "confidence": 0.95},
                ],
            }

            boxes = build_overlay_boxes(
                script,
                13,
                layout,
                {"x": 0, "y": 0, "width": 1280, "height": 720},
            )

        texts = [box.text for box in boxes]
        self.assertIn("融资申请→风控审核\n→放款→还款\n全流程线上化", texts)
        self.assertNotIn("融资申请→风控审核", texts)
        self.assertNotIn("→放款→还款", texts)
        self.assertNotIn("全流程线上化", texts)
        merged = next(box for box in boxes if box.text.startswith("融资申请"))
        self.assertEqual("ocr_unmatched_merged", merged.source)
        self.assertGreaterEqual(merged.h, 40.0)

    def test_template_rebuild_page_understanding_merges_ocr_fragments_with_script_truth(self) -> None:
        from scripts.dual_image_overlay.page_understanding import build_page_understanding
        from scripts.dual_image_overlay.text_truth import verify_text_blocks_against_script

        verified = verify_text_blocks_against_script(
            [
                {
                    "id": "stage_6_flow",
                    "ocr_text": "融资申请→风控审孩\n→放款→还款\n全流程线上化",
                    "bbox": [630.0, 464.0, 709.0, 506.0],
                    "line_boxes": [
                        [630.0, 464.0, 708.0, 475.0],
                        [643.0, 480.0, 704.0, 491.0],
                        [646.0, 496.0, 708.0, 506.0],
                    ],
                    "style": {"font_size": 8.5, "font_weight": "700"},
                }
            ],
            ["融资申请→风控审核→放款→还款，全流程线上化"],
        )
        payload = build_page_understanding(
            page_number=13,
            full_image=None,
            background_image=None,
            registration={"valid": True, "transform": "identity"},
            text_blocks=verified,
            explicit_containers=[
                {"id": "stage_6_card", "bbox": [624.0, 420.0, 714.0, 530.0], "source": "background_image"}
            ],
            implicit_containers=[],
            visual_elements=[],
        )

        self.assertEqual("融资申请→风控审核\n→放款→还款，\n全流程线上化", payload["text_blocks"][0]["final_text"])
        self.assertEqual("script_verified", payload["text_blocks"][0]["truth"]["status"])
        self.assertEqual("stage_6_card", payload["container_text_bindings"][0]["container_id"])

        boxes = overlay_boxes_from_page_understanding(payload, font_family="Microsoft YaHei", fill="#0B1F3D")

        self.assertEqual(1, len(boxes))
        self.assertEqual("page_understanding_script_verified", boxes[0].source)
        self.assertEqual((624.0, 420.0, 90.0, 110.0), (boxes[0].x, boxes[0].y, boxes[0].w, boxes[0].h))
        self.assertEqual("stage_6_flow", boxes[0].metadata["page_understanding"]["text_block_id"])
        self.assertEqual("stage_6_card", boxes[0].metadata["page_understanding"]["container_id"])

    def test_page_understanding_artifact_preserves_raw_ocr_text_before_script_truth(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            full_image = root / "full.png"
            background_image = root / "background.png"
            source_script = root / "script.md"
            Image.new("RGB", (1672, 941), "#ffffff").save(full_image)
            Image.new("RGB", (1672, 941), "#ffffff").save(background_image)
            source_script.write_text(
                "## 第13页：测试页\n\n融资申请→风控审核→放款→还款，全流程线上化\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 1672, "height": 941},
                "items": [
                    {
                        "text": "融资申请→风控审孩→放款→还款，全流程线上化",
                        "bbox": [823.0, 587.0, 926.0, 662.0],
                        "confidence": 0.91,
                        "source": "vision-json",
                    }
                ],
            }
            boxes = [
                OverlayTextBox(
                    text="融资申请→风控审核→放款→还款，全流程线上化",
                    x=823,
                    y=587,
                    w=103,
                    h=75,
                    font_size=8.5,
                    font_weight="700",
                    source="scene_graph_layout",
                )
            ]

            path = _write_page_understanding_artifact(
                project_path=project,
                page_number=13,
                full_image=full_image,
                background_image=background_image,
                source_script=source_script,
                boxes=boxes,
                layout=layout,
                body_region={"x": 0, "y": 0, "width": 1672, "height": 941},
                containers=[],
                visual_registry=None,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        text_block = payload["text_blocks"][0]
        self.assertEqual("融资申请→风控审孩→放款→还款，全流程线上化", text_block["ocr_text"])
        self.assertEqual("融资申请→风控审核→放款→还款，全流程线上化", text_block["final_text"])
        self.assertEqual("script_verified", text_block["truth"]["status"])
        self.assertEqual([823.0, 587.0, 926.0, 662.0], text_block["bbox"])
        self.assertEqual("overlay_export_context", text_block["source"])
        self.assertEqual("700", text_block["style"]["font_weight"])

    def test_pages_12_13_fixture_consumes_page_understanding_without_fragment_unique_match_gate(self) -> None:
        manifest = (
            ROOT
            / "projects/power-trusted-data-space-p12-p13/workbench/stages/02-blueprint-dual-image/pages_012_013/page_image_pairs.json"
        )
        if not manifest.exists():
            self.skipTest("pages 12/13 fixture is not present")

        result = subprocess.run(
            [
                "python3",
                "-m",
                "cyberppt",
                "template-rebuild",
                str(manifest),
                "--export",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertIn(result.returncode, {0, 3}, result.stdout + result.stderr)
        project = ROOT / "projects/power-trusted-data-space-p12-p13"
        source_gate = json.loads((project / "analysis/source_capture_gate.json").read_text(encoding="utf-8"))
        page_013 = json.loads(
            (project / "analysis/page_understanding/page_013_page_understanding.json").read_text(encoding="utf-8")
        )
        mapping = json.loads((project / "analysis/ocr/page_013_text_mapping.json").read_text(encoding="utf-8"))

        self.assertTrue(source_gate["checks"]["page_understanding_available"])
        self.assertTrue(source_gate["checks"]["page_understanding_consumed"])
        self.assertTrue(source_gate["checks"]["script_truth_verified"])
        self.assertTrue(source_gate["checks"]["fit_review_queue_clear"])
        self.assertGreater(
            next(page for page in json.loads((project / "analysis/source_capture.json").read_text(encoding="utf-8"))["pages"] if page["page_number"] == 13)[
                "page_understanding"
            ]["script_truth_evidence_only_count"],
            0,
        )
        flow_blocks = [
            block
            for block in page_013["text_blocks"]
            if str(block.get("final_text", "")).startswith("融资申请→风控审核")
        ]
        self.assertEqual(1, len(flow_blocks))
        self.assertIn("→放款→还款", flow_blocks[0]["final_text"])
        self.assertIn("全流程线上化", flow_blocks[0]["final_text"])
        self.assertEqual("auto_pass", flow_blocks[0]["fit"]["status"])
        self.assertFalse(flow_blocks[0]["fit"]["review_required"])
        self.assertEqual("move_and_scale_as_group", flow_blocks[0]["text_block_group"]["edit_behavior"])
        self.assertEqual(str((project / "analysis/page_understanding/page_013_page_understanding.json").resolve()), mapping["page_understanding"])

    def test_boxes_to_json_omits_absent_metadata_and_preserves_present_metadata(self) -> None:
        legacy_box = ScriptOverlayTextBox(
            text="核心结论",
            x=100,
            y=120,
            w=160,
            h=32,
            font_size=18,
        )
        metadata_box = ScriptOverlayTextBox(
            text="融资申请",
            x=200,
            y=220,
            w=120,
            h=28,
            font_size=14,
            metadata={"page_understanding": {"text_block_id": "ocr_item_001"}},
        )

        payload = boxes_to_json([legacy_box, metadata_box])

        self.assertNotIn("metadata", payload[0])
        self.assertEqual({"page_understanding": {"text_block_id": "ocr_item_001"}}, payload[1]["metadata"])

    def test_overlay_box_fit_can_shrink_below_preferred_minimum_for_crowded_slot(self) -> None:
        box = ScriptOverlayTextBox(
            text="投融匹配推荐清单（决策服务类）：为优质项目匹配适配金融机构",
            x=700,
            y=280,
            w=92,
            h=28,
            font_size=12.0,
            word_wrap=True,
            source="semantic_plan",
        )

        _fit_all_boxes([box])

        self.assertLess(box.font_size, 12.0)
        self.assertGreaterEqual(box.font_size, 6.5)
        line_count = _estimated_line_count(box.text, box.w * 0.96, box.font_size, word_wrap=True)
        self.assertLessEqual(line_count * box.font_size * MULTILINE_LINE_HEIGHT_FACTOR, box.h * 0.96)

    def test_overlay_box_fit_restores_preferred_font_when_workspace_allows_it(self) -> None:
        box = ScriptOverlayTextBox(
            text="获得可信风控依据的",
            x=1122,
            y=498,
            w=125,
            h=24,
            font_size=9.0,
            word_wrap=True,
            source="ocr_unmatched",
        )

        _fit_all_boxes([box])

        self.assertGreaterEqual(box.font_size, 11.5)

    def test_scene_graph_overlay_restores_preferred_font_when_workspace_allows_it(self) -> None:
        boxes = _overlay_boxes_from_scene_graph_layout(
            {
                "items": [
                    {
                        "text": "获得可信风控依据的",
                        "bbox": [1102, 480, 1230, 506],
                        "font_size": 9.0,
                        "word_wrap": True,
                    }
                ]
            },
            {"x": 0, "y": 0, "width": 1672, "height": 941},
        )

        self.assertGreaterEqual(boxes[0].font_size, 11.5)

    def test_recognition_overlay_restores_preferred_font_when_workspace_allows_it(self) -> None:
        box = OverlayTextBox(
            text="获得可信风控依据的",
            x=1122,
            y=498,
            w=125,
            h=24,
            font_size=9.0,
            word_wrap=True,
            source="ocr_unmatched",
        )

        boxes, source = _editable_boxes_from_scene_graph_or_recognition(
            {"items": []},
            {"x": 0, "y": 0, "width": 1280, "height": 720},
            [box],
        )

        self.assertEqual(source, "ocr_script_recognition")
        self.assertGreaterEqual(boxes[0].font_size, 11.5)

    def test_overlay_boxes_align_same_rank_body_rows_across_columns(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            rows = [
                ["采购预审：项目适配审查", "项目履约：业绩、合同、质量安全", "多部门留存：材料分散", "投标预审：能力与证据审查"],
                ["融资尽调：E&S风险管理", "治理合规：反腐败、制裁、税务", "口径不统一：标准不一", "融资保险：合规与风险沟通"],
                ["E&S/HSE：项目关键条件", "E&S/HSE：环境、安全、劳工社区", "版本难追溯：来源与时点不清", "供应链准入：质量与交付证明"],
                ["供应链尽责：合规责任管理", "国别适配：准入、属地、风险应对", "复用效率低：反复整理", "市场进入：国别适配证明"],
            ]
            script.write_text(
                "\n".join(["## 第3页：当前形势与开展综合能力证明服务的必要性"] + [text for row in rows for text in row])
                + "\n",
                encoding="utf-8",
            )
            x_positions = [110, 424, 728, 1028]
            y_rows = [303, 371, 468, 536]
            items = []
            for col_index, x in enumerate(x_positions):
                for row_index, y in enumerate(y_rows):
                    text = rows[row_index][col_index]
                    actual_y = 440 if (col_index, row_index) == (1, 2) else y
                    items.append({"text": text, "bbox": [x, actual_y, x + 170, actual_y + 18], "confidence": 0.96})
            layout = {"image_size": {"width": 1280, "height": 720}, "items": items}

            boxes = build_overlay_boxes(
                script,
                3,
                layout,
                {"x": 0, "y": 0, "width": 1280, "height": 720},
            )

        row_three = [
            next(box for box in boxes if box.text == "E&S/HSE：项目关键条件"),
            next(box for box in boxes if box.text == "E&S/HSE：环境、安全、劳工社区"),
            next(box for box in boxes if box.text == "版本难追溯：来源与时点不清"),
            next(box for box in boxes if box.text == "供应链准入：质量与交付证明"),
        ]
        self.assertLessEqual(max(box.y for box in row_three) - min(box.y for box in row_three), 0.01)

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


def _write_pair_manifest(
    root: Path,
    project: Path,
    *,
    rebuild_mode: str = "template_body_region",
    with_visual_line: bool = False,
) -> Path:
    image_dir = root / "images"
    image_dir.mkdir()
    full = image_dir / "page_002_full.png"
    background = image_dir / "page_002_background.png"
    if with_visual_line:
        Image.new("RGB", (1280, 720), "#ffffff").save(full)
        background_image = Image.new("RGB", (1280, 720), "#ffffff")
        ImageDraw.Draw(background_image).line((100, 120, 700, 120), fill="#123B66", width=8)
        background_image.save(background)
    else:
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
            "slide_canvas": {"width": 1280, "height": 720},
            "content_region": {"x": 20, "y": 104, "w": 1240, "h": 592},
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


def _capture_text(text: str, x: float, y: float, w: float, h: float) -> dict[str, object]:
    return {
        "text": text,
        "rendered_text": text,
        "bbox": {"x": x, "y": y, "w": w, "h": h},
        "style": {"typography_role": "body"},
    }


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


def _write_scene_graph_gate(project: Path, *, page_number: int, valid: bool) -> None:
    path = project / "analysis" / "scene_graph_gate" / f"page_{page_number:03d}_scene_graph_gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.scene_graph_gate.v1",
                "page_number": page_number,
                "valid": valid,
                "checks": {"scene_graph_exists": valid},
                "blocking_errors": [] if valid else [{"id": "scene_graph.missing"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
