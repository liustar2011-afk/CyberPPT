from __future__ import annotations

import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cyberppt.cli import build_parser, main
from cyberppt.commands.analysis_expression_gate import approve_analysis_artifact, stage_analysis_artifact
from cyberppt.commands.blueprint_gate import (
    approve_blueprint_image_review,
    approve_blueprint_input,
    approve_speaker_notes_review,
    approve_visual_style,
    stage_blueprint_image_review,
    stage_blueprint_input,
    stage_speaker_notes_review,
    stage_visual_style_options,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project
from cyberppt.commands.produce import (
    assemble_production,
    assert_image_text_qa_ready,
    get_production_status,
    prepare_production,
    verify_production,
)
from scripts.validate_pptx import validate_manifest, validate_manifest_slide


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
    {"id": "scenario_implementation", "label": "场景实施型"},
    {"id": "resource_risk", "label": "资源风险型"},
]

REPORTING_DIRECTION = """## 方向一：领导审定型
### 适用受众
分管领导
### 汇报目的
审定工作安排
### 内容重点
供需研判
### 证据
预测数据
### 优势
基础扎实
### 风险边界
不替代执行方案
## 方向二：执行对齐型
### 适用受众
业务处室
### 汇报目的
统一执行安排
### 内容重点
任务分工
### 证据
工作计划
### 优势
便于推进
### 风险边界
不扩大工作范围
## 方向三：场景实施型
### 适用受众
项目专班
### 汇报目的
明确实施路径
### 内容重点
首期场景
### 证据
实施路线
### 优势
行动性强
### 风险边界
远期场景待验证
## 方向四：资源风险型
### 适用受众
协调会议
### 汇报目的
明确资源保障
### 内容重点
预算、人员和安全
### 证据
资源测算
### 优势
边界清晰
### 风险边界
参考测算不等于批复
## 推荐方向
领导审定型
"""

CONTENT_PAGE = "4"
CONTENT_PAGE_NUMBER = int(CONTENT_PAGE)
CONTENT_PAGE_RANGE = "004_004"


def _approve_analysis(project: Path) -> None:
    artifacts = (
        (
            "source_analysis",
            "## 输入盘点\n年度供需预测报告\n## 证据表\n| ID | 论点 | 来源位置 |\n|---|---|---|\n| E01 | 供需总体平衡 | 年度供需预测报告第3页 |\n"
            "## 开放数据冲突\n无重大冲突\n## 内容脑暴\n领导审定型、执行对齐型\n## 页面物料池\n最大负荷、供需平衡\n",
            "evidence complete",
        ),
        (
            "reporting_direction",
            REPORTING_DIRECTION,
            "领导审定型",
        ),
        (
            "report_structure",
            "## 模块一\n形势研判\n## 模块二\n供需预测\n## 模块三\n风险提示\n## 模块四\n工作安排\n",
            "four modules",
        ),
        (
            "page_design",
            "## 封面\n项目名称\n## 目录\n章节导航\n## 过渡页\n进入供需预测\n## 内容页\n供需预测结论\n## 封底\n请审阅\n",
            "page design",
        ),
        (
            "business_script",
            "## 第4页：供需预测结论\n供需总体平衡\n### 非上屏：证据链\n- E-01\n"
            "### 来源位置\n- 年度供需预测报告第3页\n### 非上屏：完整性校核\n- 本页不承载业务内容。\n",
            "business script",
        ),
    )
    for gate, source, recommendation in artifacts:
        stage_analysis_artifact(project, gate, source, recommendation, OPTIONS)
        approve_analysis_artifact(project, gate, "leadership_review")


def _approved_project() -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temporary_directory = tempfile.TemporaryDirectory()
    root = Path(temporary_directory.name)
    project = root / "client-report"
    init_project(project)
    _approve_analysis(project)
    script = root / "script-final.md"
    script.write_text("## 第4页：测试\n组件A：内容\n", encoding="utf-8")
    stage_visual_style_options(project)
    approve_visual_style(project, "style_4")
    stage_blueprint_input(
        project,
        script.read_text(encoding="utf-8"),
        "confirm_blueprint_input",
        [
            {"id": "confirm_blueprint_input", "label": "确认蓝图输入"},
            {"id": "revise_blueprint_input", "label": "返回调整"},
        ],
    )
    approve_blueprint_input(project, "confirm_blueprint_input")
    return project, temporary_directory


def _write_passed_image_text_qa(project: Path, pages_raw: str, pairs_path: Path) -> Path:
    page_number = int(pages_raw)
    prepare_paths = sorted((project / "workbench/stages/02-blueprint-dual-image").glob("*/production_prepare.json"))
    matching_prepare = next(
        (
            path
            for path in prepare_paths
            if json.loads(path.read_text(encoding="utf-8")).get("pages_raw") == pages_raw
        ),
        None,
    )
    stage_dir = matching_prepare.parent if matching_prepare else pairs_path.parent.parent
    script = stage_dir / "imagegen_script.md"
    script.write_text(
        f"""## 第{page_number}页：测试

【页面类型】
本页类型：内容页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 真实业务内容

【构图指令】
生成正文内容区。

【结构密度】
- 正文区
""",
        encoding="utf-8",
    )
    pair_manifest = json.loads(pairs_path.read_text(encoding="utf-8"))
    full = pair_manifest["pairs"][0]["full"]
    full["prompt"] = full.get("prompt") or "Generate the approved page 4 content exactly."
    pairs_path.write_text(json.dumps(pair_manifest, ensure_ascii=False), encoding="utf-8")
    image_path = Path(full["path"])
    qa_dir = stage_dir / "image_text_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report_path = qa_dir / f"page_{page_number:03d}.json"
    report_path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.image_text_qa.v1",
                "page": page_number,
                "image_path": str(image_path),
                "image_sha256": _sha256_for_test(image_path),
                "status": "passed",
                "deliverable_allowed": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary_path = qa_dir / "image_text_qa_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.image_text_qa_summary.v1",
                "pages_raw": pages_raw,
                "pages": [page_number],
                "status": "passed",
                "deliverable_allowed": True,
                "imagegen_script": str(script),
                "imagegen_script_sha256": _sha256_for_test(script),
                "page_image_manifest": str(pairs_path),
                "page_image_manifest_sha256": _sha256_for_test(pairs_path),
                "reports": [{"page": page_number, "path": str(report_path), "status": "passed"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    run_path = project / "imagegen_runs" / f"page_{page_number}.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.imagegen_run.v1",
                "page": page_number,
                "manifest": str(pairs_path),
                "manifest_sha256": _sha256_for_test(pairs_path),
                "prompt_sha256": _sha256_for_test_text(full["prompt"]),
                "output_path": str(image_path),
                "output_sha256": _sha256_for_test(image_path),
                "status": "passed",
                "image_text_qa": str(report_path),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return summary_path


class ProduceTests(unittest.TestCase):
    def test_editable_text_delivery_manifest_is_a_strict_known_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "template_text_lock.json"
            visual = root / "visual.json"
            lock.write_text("{}", encoding="utf-8")
            visual.write_text("{}", encoding="utf-8")
            manifest = {
                "delivery_mode": "editable_text_three_image",
                "body_content_editable": True,
                "template_text_editable": True,
                "speaker_notes_required": True,
                "template_text_lock": {"path": str(lock), "sha256": _sha256_for_test(lock)},
                "production_visual_report": {"path": str(visual), "passed": True},
                "slides": [],
            }
            self.assertEqual([], validate_manifest(manifest))
            self.assertEqual(
                [],
                validate_manifest_slide(
                    {
                        "delivery_mode": "editable_text_three_image",
                        "body_image_required": True,
                        "image_assets": [{"role": "approved_background", "path": str(lock)}],
                    },
                    {"pictures": 1, "native_text_shapes": 2, "text_content": "正文"},
                    1,
                ),
            )

    def test_editable_text_mode_stops_after_speaker_notes_for_vendor_assets(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            manifest = project / "manifest.yml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "production_mode: full_image_ppt", "production_mode: editable_text_three_image"
                ),
                encoding="utf-8",
            )
            prepare_production(project, CONTENT_PAGE)
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            status = get_production_status(project, CONTENT_PAGE)

            self.assertEqual("editable_text_assets_required", status["next_gate"])
            self.assertIn("produce editable-text", status["next_command"])

    def test_produce_editable_text_command_is_registered(self) -> None:
        args = build_parser().parse_args(["produce", "editable-text", "/tmp/project", "--pages", "1"])
        self.assertEqual("editable-text", args.produce_command)
        self.assertEqual("two-image", args.input_mode)

    def test_produce_editable_text_command_accepts_three_image_input_mode(self) -> None:
        args = build_parser().parse_args(
            ["produce", "editable-text", "/tmp/project", "--pages", "1", "--input-mode", "three-image"]
        )
        self.assertEqual("three-image", args.input_mode)

    def test_image_text_qa_readiness_blocks_without_current_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "image-text QA"):
                assert_image_text_qa_ready(Path(tmp), "1")

    def test_prepare_production_stages_inputs_and_speaker_notes_confirmation(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            summary = prepare_production(project, CONTENT_PAGE)

            self.assertEqual("production_inputs_prepared", summary["status"])
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).is_file())
            self.assertTrue(Path(summary["artifacts"]["speaker_notes_pending_confirmation"]).is_file())
            self.assertTrue(Path(summary["artifacts"]["production_prepare"]).is_file())
            self.assertEqual(
                "speaker_notes_approval_required",
                get_production_status(project, CONTENT_PAGE)["next_gate"],
            )

    def test_status_json_and_prepare_commands_are_available(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepare_output = io.StringIO()
            with redirect_stdout(prepare_output):
                prepare_code = main(["produce", "prepare", str(project), "--pages", CONTENT_PAGE])

            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_code = main(["produce", "status", str(project), "--pages", CONTENT_PAGE, "--json"])

            self.assertEqual(0, prepare_code)
            self.assertEqual(0, status_code)
            self.assertEqual("production_inputs_prepared", json.loads(prepare_output.getvalue())["status"])
            self.assertEqual("speaker_notes_approval_required", json.loads(status_output.getvalue())["next_gate"])

    def test_final_script_pages_rejects_production_build_with_produce_assemble_recovery(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            approved_input = project / "workbench/stages/02-blueprint-dual-image/blueprint_input.md"
            with self.assertRaisesRegex(ValueError, "produce assemble"):
                run_final_script_pages(project=project, script=approved_input, pages_raw="1", production_build=True)

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(
                    [
                        "final-script-pages",
                        str(project),
                        "--script",
                        str(approved_input),
                        "--pages",
                        "1",
                        "--production-build",
                    ]
                )

            self.assertEqual(2, code)
            self.assertIn("produce assemble", stderr.getvalue())

    def test_assemble_rejects_zero_return_code_without_required_artifacts(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, CONTENT_PAGE)
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            manifest = json.loads(pairs.read_text(encoding="utf-8"))
            for pair in manifest["pairs"]:
                Path(pair["full"]["path"]).write_bytes(b"approved-image")
            _write_passed_image_text_qa(project, CONTENT_PAGE, pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            notes = Path(prepared["artifacts"]["speaker_notes_manifest"])
            stage_speaker_notes_review(project, notes, CONTENT_PAGE)
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            with patch("cyberppt.commands.produce.subprocess.run", return_value=Mock(returncode=0)):
                with self.assertRaisesRegex(RuntimeError, "assembly_artifact_missing"):
                    assemble_production(project, CONTENT_PAGE)

    def test_verify_promotes_valid_assembly_to_delivery(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            stage_dir = project / "workbench/stages/02-blueprint-dual-image/pages_001"
            image_ppt = stage_dir / "image_ppt"
            approved = image_ppt / "approved.png"
            exported = image_ppt / "assembled.pptx"
            pairs = image_ppt / "page_image_pairs.json"
            template_lock = image_ppt / "template_text_lock.json"
            manifest = image_ppt / "template_image_manifest.json"
            assembly = image_ppt / "assembly_report.json"
            approved.parent.mkdir(parents=True)
            approved.write_bytes(b"approved-image")
            template_lock.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.template_text_lock.v1",
                        "pages": [1],
                        "records": [{"page": 1, "approved": True}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pairs.write_text(
                json.dumps(
                    {"pairs": [{"page_number": 1, "full": {"path": str(approved)}}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            _write_passed_image_text_qa(project, "1", pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            manifest.write_text(
                json.dumps(
                    {
                        "canvas": {"width": 1280, "height": 720},
                        "body_region": {"x": 0, "y": 0, "width": 1280, "height": 720},
                        "page_image_manifest": str(pairs),
                        "template_text_lock": str(template_lock),
                        "tasks": [{"page_number": 1, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            exported.write_bytes(b"pptx")
            assembly.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.assembly_report.v1",
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {"1": str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                        "failures": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            stage_speaker_notes_review(project, manifest, "1")
            approve_speaker_notes_review(project, "confirm_speaker_notes")
            with patch(
                "cyberppt.commands.produce.render_and_compare",
                return_value={"schema": "cyberppt.production_visual_report.v1", "passed": True, "slides": []},
            ), patch("cyberppt.commands.produce.validate_pptx", return_value={"errors": [], "warnings": []}):
                report = verify_production(project, "1")

            self.assertEqual("deliverable_ready", report["status"])
            self.assertTrue(Path(report["delivery_pptx"]).is_file())

    def test_verify_requires_current_blueprint_image_approval(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            stage_dir = project / "workbench/stages/02-blueprint-dual-image/pages_001"
            image_ppt = stage_dir / "image_ppt"
            image_ppt.mkdir(parents=True)
            approved = image_ppt / "approved.png"
            exported = image_ppt / "assembled.pptx"
            pairs = image_ppt / "page_image_pairs.json"
            manifest = image_ppt / "template_image_manifest.json"
            approved.write_bytes(b"approved-image")
            exported.write_bytes(b"pptx")
            pairs.write_text(
                json.dumps({"pairs": [{"page_number": 1, "full": {"path": str(approved)}}]}),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": 1, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (image_ppt / "assembly_report.json").write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {"1": str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            stage_speaker_notes_review(project, manifest, "1")
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            with self.assertRaisesRegex(ValueError, "blueprint image review approval is required"):
                verify_production(project, "1")

    def test_verify_requires_template_text_lock(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            stage_dir = project / "workbench/stages/02-blueprint-dual-image/pages_001"
            image_ppt = stage_dir / "image_ppt"
            image_ppt.mkdir(parents=True)
            approved = image_ppt / "approved.png"
            exported = image_ppt / "assembled.pptx"
            pairs = image_ppt / "page_image_pairs.json"
            manifest = image_ppt / "template_image_manifest.json"
            approved.write_bytes(b"approved-image")
            exported.write_bytes(b"pptx")
            pairs.write_text(
                json.dumps({"pairs": [{"page_number": 1, "full": {"path": str(approved)}}]}),
                encoding="utf-8",
            )
            _write_passed_image_text_qa(project, "1", pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": str(manifest),
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": 1, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (image_ppt / "assembly_report.json").write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {"1": str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            stage_speaker_notes_review(project, manifest, "1")
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            with patch(
                "cyberppt.commands.produce.render_and_compare",
                return_value={"schema": "cyberppt.production_visual_report.v1", "passed": True, "slides": []},
            ), patch("cyberppt.commands.produce.validate_pptx", return_value={"errors": [], "warnings": []}):
                with self.assertRaisesRegex(RuntimeError, "template text lock is required"):
                    verify_production(project, "1")

    def test_verify_requires_current_speaker_notes_approval(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            stage_dir = project / "workbench/stages/02-blueprint-dual-image/pages_001/image_ppt"
            stage_dir.mkdir(parents=True)
            approved = stage_dir / "approved.png"
            exported = stage_dir / "assembled.pptx"
            manifest = stage_dir / "template_image_manifest.json"
            approved.write_bytes(b"approved-image")
            exported.write_bytes(b"pptx")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": str(stage_dir / "speaker_notes_manifest.json"),
                        "tasks": [{"page_number": 1, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (stage_dir / "assembly_report.json").write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {"1": str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "speaker notes approval is required"):
                verify_production(project, "1")

    def test_verify_rejects_stale_assembly_hash(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            stage_dir = project / "workbench/stages/02-blueprint-dual-image/pages_001/image_ppt"
            stage_dir.mkdir(parents=True)
            exported = stage_dir / "assembled.pptx"
            manifest = stage_dir / "template_image_manifest.json"
            exported.write_bytes(b"pptx")
            manifest.write_text('{"tasks":[]}', encoding="utf-8")
            (stage_dir / "assembly_report.json").write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {},
                        "artifacts_sha256": {"exported_pptx": "stale", "template_image_manifest": _sha256_for_test(manifest)},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "stale assembly"):
                verify_production(project, "1")

    def test_status_invalidates_deliverable_when_dependency_changes(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, CONTENT_PAGE)
            image_ppt = Path(prepared["artifacts"]["production_prepare"]).parent / "image_ppt"
            image_ppt.mkdir(parents=True)
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            pair_manifest = json.loads(pairs.read_text(encoding="utf-8"))
            approved = Path(pair_manifest["pairs"][0]["full"]["path"])
            exported = image_ppt / "assembled.pptx"
            manifest = image_ppt / "template_image_manifest.json"
            approved.parent.mkdir(parents=True, exist_ok=True)
            approved.write_bytes(b"approved-image")
            _write_passed_image_text_qa(project, CONTENT_PAGE, pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            exported.write_bytes(b"pptx")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": prepared["artifacts"]["speaker_notes_manifest"],
                        "template_text_lock": prepared["artifacts"]["template_text_lock"],
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": CONTENT_PAGE_NUMBER, "image_path": str(approved), "notes_text": "approved notes", "slide_title": "测试"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            approve_speaker_notes_review(project, "confirm_speaker_notes")
            assembly = image_ppt / "assembly_report.json"
            assembly.write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {CONTENT_PAGE: str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "cyberppt.commands.produce.render_and_compare",
                return_value={"schema": "cyberppt.production_visual_report.v1", "passed": True, "slides": []},
            ), patch("cyberppt.commands.produce.validate_pptx", return_value={"errors": [], "warnings": []}):
                verify_production(project, CONTENT_PAGE)

            visual_report = project / f"workbench/stages/05-qa-delivery/pages_{CONTENT_PAGE_RANGE}/production_visual_report.json"
            visual_report.write_text('{"passed": false}\n', encoding="utf-8")

            self.assertNotEqual("deliverable_ready", get_production_status(project, CONTENT_PAGE)["status"])

    def test_status_rejects_readiness_with_incomplete_dependency_hashes(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, CONTENT_PAGE)
            image_ppt = Path(prepared["artifacts"]["production_prepare"]).parent / "image_ppt"
            image_ppt.mkdir(parents=True)
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            pair_manifest = json.loads(pairs.read_text(encoding="utf-8"))
            approved = Path(pair_manifest["pairs"][0]["full"]["path"])
            exported = image_ppt / "assembled.pptx"
            manifest = image_ppt / "template_image_manifest.json"
            approved.parent.mkdir(parents=True, exist_ok=True)
            approved.write_bytes(b"approved-image")
            _write_passed_image_text_qa(project, CONTENT_PAGE, pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            exported.write_bytes(b"pptx")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": prepared["artifacts"]["speaker_notes_manifest"],
                        "template_text_lock": prepared["artifacts"]["template_text_lock"],
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": CONTENT_PAGE_NUMBER, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            approve_speaker_notes_review(project, "confirm_speaker_notes")
            assembly = image_ppt / "assembly_report.json"
            assembly.write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {CONTENT_PAGE: str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "cyberppt.commands.produce.render_and_compare",
                return_value={"schema": "cyberppt.production_visual_report.v1", "passed": True, "slides": []},
            ), patch("cyberppt.commands.produce.validate_pptx", return_value={"errors": [], "warnings": []}):
                report = verify_production(project, CONTENT_PAGE)

            readiness = Path(report["production_readiness"])
            payload = json.loads(readiness.read_text(encoding="utf-8"))
            delivery_pptx = Path(payload["delivery_pptx"])
            payload["dependency_hashes"] = {str(delivery_pptx.resolve()): _sha256_for_test(delivery_pptx)}
            readiness.write_text(json.dumps(payload), encoding="utf-8")

            self.assertNotEqual("deliverable_ready", get_production_status(project, CONTENT_PAGE)["status"])

    def test_status_rejects_readiness_without_template_text_lock(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, CONTENT_PAGE)
            image_ppt = Path(prepared["artifacts"]["production_prepare"]).parent / "image_ppt"
            image_ppt.mkdir(parents=True)
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            pair_manifest = json.loads(pairs.read_text(encoding="utf-8"))
            approved = Path(pair_manifest["pairs"][0]["full"]["path"])
            exported = image_ppt / "assembled.pptx"
            manifest = image_ppt / "template_image_manifest.json"
            approved.parent.mkdir(parents=True, exist_ok=True)
            approved.write_bytes(b"approved-image")
            _write_passed_image_text_qa(project, CONTENT_PAGE, pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            exported.write_bytes(b"pptx")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": prepared["artifacts"]["speaker_notes_manifest"],
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": CONTENT_PAGE_NUMBER, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            approve_speaker_notes_review(project, "confirm_speaker_notes")
            assembly = image_ppt / "assembly_report.json"
            assembly.write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {CONTENT_PAGE: str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            readiness_dir = project / f"workbench/stages/05-qa-delivery/pages_{CONTENT_PAGE_RANGE}"
            readiness_dir.mkdir(parents=True)
            visual = readiness_dir / "production_visual_report.json"
            strict = readiness_dir / "strict_validation_report.json"
            delivery_manifest = readiness_dir / "full_image_delivery_manifest.json"
            delivery = project / "delivery/client-report_pages_001_001.pptx"
            delivery.parent.mkdir(parents=True, exist_ok=True)
            for path, content in (
                (visual, '{"passed": true}\n'),
                (strict, '{"errors": []}\n'),
                (delivery_manifest, '{"delivery_mode": "full_image_ppt"}\n'),
            ):
                path.write_text(content, encoding="utf-8")
            delivery.write_bytes(b"pptx")
            dependencies = [
                assembly,
                exported,
                manifest,
                pairs,
                Path(prepared["artifacts"]["speaker_notes_manifest"]),
                visual,
                strict,
                delivery_manifest,
                delivery,
                approved,
            ]
            (readiness_dir / "production_readiness.json").write_text(
                json.dumps(
                    {
                        "status": "deliverable_ready",
                        "delivery_pptx": str(delivery),
                        "delivery_pptx_sha256": _sha256_for_test(delivery),
                        "dependency_hashes": {str(path.resolve()): _sha256_for_test(path) for path in dependencies},
                        "artifacts": {
                            "production_visual_report": str(visual),
                            "strict_validation_report": str(strict),
                            "full_image_delivery_manifest": str(delivery_manifest),
                            "delivery_pptx": str(delivery),
                        },
                    }
                ),
                encoding="utf-8",
            )

            self.assertNotEqual("deliverable_ready", get_production_status(project, CONTENT_PAGE)["status"])

    def test_status_rejects_legacy_readiness_without_dependency_hashes(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, CONTENT_PAGE)
            image_ppt = Path(prepared["artifacts"]["production_prepare"]).parent / "image_ppt"
            image_ppt.mkdir(parents=True)
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            pair_manifest = json.loads(pairs.read_text(encoding="utf-8"))
            approved = Path(pair_manifest["pairs"][0]["full"]["path"])
            exported = image_ppt / "assembled.pptx"
            manifest = image_ppt / "template_image_manifest.json"
            approved.parent.mkdir(parents=True, exist_ok=True)
            approved.write_bytes(b"approved-image")
            _write_passed_image_text_qa(project, CONTENT_PAGE, pairs)
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            exported.write_bytes(b"pptx")
            manifest.write_text(
                json.dumps(
                    {
                        "speaker_notes_manifest": prepared["artifacts"]["speaker_notes_manifest"],
                        "template_text_lock": prepared["artifacts"]["template_text_lock"],
                        "page_image_manifest": str(pairs),
                        "tasks": [{"page_number": CONTENT_PAGE_NUMBER, "image_path": str(approved), "notes_text": "approved notes"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            approve_speaker_notes_review(project, "confirm_speaker_notes")
            (image_ppt / "assembly_report.json").write_text(
                json.dumps(
                    {
                        "valid": True,
                        "artifacts": {"exported_pptx": str(exported), "template_image_manifest": str(manifest)},
                        "approved_images": {CONTENT_PAGE: str(approved)},
                        "artifacts_sha256": {
                            "exported_pptx": _sha256_for_test(exported),
                            "template_image_manifest": _sha256_for_test(manifest),
                        },
                    }
                ),
                encoding="utf-8",
            )
            delivery = project / f"delivery/client-report_pages_{CONTENT_PAGE_RANGE}.pptx"
            delivery.parent.mkdir(parents=True, exist_ok=True)
            delivery.write_bytes(b"pptx")
            readiness_dir = project / f"workbench/stages/05-qa-delivery/pages_{CONTENT_PAGE_RANGE}"
            readiness_dir.mkdir(parents=True)
            (readiness_dir / "production_readiness.json").write_text(
                json.dumps(
                    {
                        "status": "deliverable_ready",
                        "delivery_pptx": str(delivery),
                        "delivery_pptx_sha256": _sha256_for_test(delivery),
                        "artifacts": {"delivery_pptx": str(delivery)},
                    }
                ),
                encoding="utf-8",
            )

            self.assertNotEqual("deliverable_ready", get_production_status(project, CONTENT_PAGE)["status"])


def _sha256_for_test(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_for_test_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
