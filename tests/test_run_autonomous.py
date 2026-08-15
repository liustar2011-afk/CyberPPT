from __future__ import annotations

import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import cyberppt.commands.run_autonomous as run_autonomous_module
from cyberppt.autonomous_contract import ContractError, load_contract, validate_source_boundary
from cyberppt.commands.run_autonomous import GateBlocked, _assert_page_authoring, run_autonomous


class AutonomousContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.source = self.project / "source" / "material.txt"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("唯一事实源", encoding="utf-8")
        self.denied = self.root / "old-project" / "workbench"
        self.denied.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _contract(self, **overrides: object) -> Path:
        payload: dict[str, object] = {
            "schema_version": 1,
            "mode": "autonomous_lightweight",
            "project": str(self.project),
            "source": {
                "allow": [str(self.source)],
                "deny_prefixes": [str(self.denied)],
            },
            "required": {
                "stage01": True,
                "stage02": True,
                "style_id": 9,
                "production_mode": "image-to-editable-svg",
                "images": True,
                "prompt_files": True,
                "image_qa": True,
            },
        }
        payload.update(overrides)
        path = self.root / "contract.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_contract_rejects_unregistered_source_file(self) -> None:
        extra = self.project / "source" / "extra.txt"
        extra.write_text("未经登记", encoding="utf-8")

        contract = load_contract(self._contract())

        with self.assertRaisesRegex(ContractError, "allowlist"):
            validate_source_boundary(contract)

    def test_contract_ignores_source_gitkeep_placeholder(self) -> None:
        (self.project / "source" / ".gitkeep").write_text("", encoding="utf-8")

        validate_source_boundary(load_contract(self._contract()))

    def test_contract_rejects_wrong_mode(self) -> None:
        with self.assertRaisesRegex(ContractError, "mode"):
            load_contract(self._contract(mode="interactive"))

    def test_contract_rejects_denied_provenance_in_workbench(self) -> None:
        artifact = self.project / "workbench" / "stages" / "01-analysis" / "outline.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text(str(self.denied.resolve()), encoding="utf-8")

        contract = load_contract(self._contract())

        with self.assertRaisesRegex(ContractError, "denied source provenance"):
            validate_source_boundary(contract)


class RunAutonomousTests(AutonomousContractTests):
    def _write_valid_source_foundation_handoff(self) -> Path:
        report = self.project / "integration" / "cyberppt-handoff-report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps({"projection_validation": {"status": "ok"}}),
            encoding="utf-8",
        )
        return report

    def _write_stage01_inputs(self) -> Path:
        analysis = self.project / "workbench" / "stages" / "01-analysis"
        analysis.mkdir(parents=True)
        (analysis / "outline.json").write_text(
            json.dumps({
                "editorial_authoring_mode": "author_driven",
                "editorial_authoring_status": "author_edited",
                "pages": [{"page_id": "p01", "page_type": "content"}],
            }),
            encoding="utf-8",
        )
        (analysis / "source-truth.json").write_text("{}", encoding="utf-8")
        drafts = self.project / "workbench" / "scripts" / "drafts"
        drafts.mkdir(parents=True)
        page = """## 第1页：测试页
- 页面类型：内容页
- 页面标题：测试页
- 主判断：测试判断
- 证据：ST001
- 完整文字稿：测试完整稿说明本页的业务关系与结论。
- 文字稿取舍说明：
  - 必留上屏：测试结论和关键业务关系。
  - 仅讲解：补充说明。
  - 仅追溯：ST001的原始出处。
- 上屏结论：测试结论
- 上屏文字：

  **01｜测试模块**
  - 测试内容
- 证据映射：ST001
- 视觉结构：以测试业务关系为唯一视觉中心，呈现输入、承接动作与结果的连续关系。

【演讲者备注】

说明测试判断如何承接上一页并交给下一页。
"""
        (drafts / "p01.md").write_text(page, encoding="utf-8")
        script = self.project / "workbench" / "scripts" / "final" / "script-final.md"
        script.parent.mkdir(parents=True)
        script.write_text("# final\n\n" + page, encoding="utf-8")
        self._write_valid_source_foundation_handoff()
        return script

    def test_failed_semantic_gate_short_circuits_before_stage02(self) -> None:
        self._write_stage01_inputs()
        with (
            patch("cyberppt.commands.run_autonomous.prepare_source_map"),
            patch("cyberppt.commands.run_autonomous.run_source_map_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_semantic_understanding_audit", return_value=(1, {"status": "rewrite_required"})),
            patch("cyberppt.commands.run_autonomous.prepare_stage02_handoff") as handoff,
        ):
            code, report = run_autonomous(self._contract())

        self.assertEqual(1, code)
        self.assertEqual("failed", report["status"])
        self.assertEqual("semantic-check", report["failed_gate"])
        handoff.assert_not_called()
        self.assertTrue(Path(str(report["report_path"])).is_file())

    def test_invalid_source_foundation_handoff_blocks_before_legacy_preparation(self) -> None:
        self._write_stage01_inputs()
        report = self._write_valid_source_foundation_handoff()
        report.write_text(
            json.dumps({"projection_validation": {"status": "error"}}),
            encoding="utf-8",
        )

        with patch("cyberppt.commands.run_autonomous.prepare_source_map") as prepare:
            code, result = run_autonomous(self._contract())

        self.assertEqual(1, code)
        self.assertEqual("source-foundation", result["failed_gate"])
        prepare.assert_not_called()

    def test_valid_source_foundation_handoff_does_not_recompile_source_truth(self) -> None:
        self._write_stage01_inputs()
        report = self._write_valid_source_foundation_handoff()
        with (
            patch("cyberppt.commands.run_autonomous.prepare_source_map"),
            patch(
                "cyberppt.commands.run_autonomous.run_source_map_audit",
                return_value=(0, {"status": "passed"}),
            ),
            patch(
                "cyberppt.commands.run_autonomous.run_semantic_understanding_audit",
                return_value=(0, {"status": "passed"}),
            ),
            patch(
                "cyberppt.commands.run_autonomous.run_source_truth_audit",
                return_value=(1, {"status": "rewrite_required"}),
            ),
            patch.object(run_autonomous_module, "compile_source_truth", create=True) as compile_truth,
        ):
            code, result = run_autonomous(self._contract())

        self.assertEqual(1, code)
        self.assertEqual("source-truth-audit", result["failed_gate"])
        source_foundation_gate = next(
            gate for gate in result["gates"] if gate["name"] == "source-foundation"
        )
        self.assertEqual(str(report.resolve()), source_foundation_gate["artifact"])
        compile_truth.assert_not_called()

    def test_candidate_outline_is_rejected_before_page_authoring(self) -> None:
        self._write_stage01_inputs()
        outline = self.project / "workbench" / "stages" / "01-analysis" / "outline.json"
        payload = json.loads(outline.read_text(encoding="utf-8"))
        payload["editorial_authoring_status"] = "mechanical_draft"
        outline.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaisesRegex(GateBlocked, "candidate Outline"):
            _assert_page_authoring(self.project)

    def test_completed_requires_actual_images_prompts_and_text_qa(self) -> None:
        script = self._write_stage01_inputs()
        visual = self.project / "visual"
        visual.mkdir()
        (visual / "generation-prompts.md").write_text("prompt", encoding="utf-8")
        output = self.project / "workbench" / "stages" / "02-imagegen" / "build"
        output.mkdir(parents=True)
        full = output / "full.png"
        full.write_bytes(b"full")
        attempts = output / "prompts" / "attempts"
        attempts.mkdir(parents=True)
        full_prompt = "actual full send prompt\n"
        for variant, prompt, inputs in (("full", full_prompt, []),):
            sent = attempts / f"page-001-{variant}-attempt-01-sent.txt"
            sent.write_text(prompt, encoding="utf-8", newline="")
            (attempts / f"page-001-{variant}-attempt-01-request.json").write_text(
                json.dumps({
                    "prompt_path": str(sent.resolve()),
                    "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
                    "base_prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
                    "model": "gpt-image-2",
                    "quality": "high",
                    "input_images": inputs,
                }),
                encoding="utf-8",
            )
        manifest = output / "page_image_pairs.json"
        manifest.write_text(json.dumps({"production_mode": "image-to-editable-svg", "pairs": [{"page_number": 1, "full": {"path": str(full), "status": "Generated", "prompt_sha256": sha256(full_prompt.encode("utf-8")).hexdigest(), "text_audit": {"valid": True}}}]}), encoding="utf-8")
        analysis = self.project / "analysis"
        analysis.mkdir()
        exported = analysis / "editable-deck.pptx"
        exported.write_bytes(b"pptx")
        delivery_readiness = analysis / "delivery_readiness.json"
        delivery_readiness.write_text(
            json.dumps({
                "status": "production_ready",
                "delivery_readiness": {"valid": True},
            }),
            encoding="utf-8",
        )
        production = {
            "status": "production_ready",
            "artifacts": {
                "page_image_pairs": str(manifest),
                "delivery_readiness": str(delivery_readiness),
                "exported_pptx": str(exported),
            },
            "production_readiness": {"valid": True, "status": "production_ready"},
        }
        (visual / "visual-design-decisions.json").write_text("{}", encoding="utf-8")
        receipt = visual / "execution-receipt.json"

        with (
            patch("cyberppt.commands.run_autonomous.prepare_source_map"),
            patch("cyberppt.commands.run_autonomous.run_source_map_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_semantic_understanding_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_source_truth_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_outline_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_script_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.prepare_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.audit_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.prepare_visual_structure_stage", return_value=visual / "skill-request.md"),
            patch("cyberppt.commands.run_autonomous.execute_visual_structure_stage", return_value={}),
            patch("cyberppt.commands.run_autonomous.record_visual_structure_execution", return_value=receipt),
            patch("cyberppt.commands.run_autonomous.run_visual_structure_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_final_script_pages", return_value=production) as pages,
        ):
            code, report = run_autonomous(self._contract())

        self.assertEqual(0, code)
        self.assertEqual("completed", report["status"])
        pages.assert_called_once()
        self.assertEqual("1-1", pages.call_args.kwargs["pages_raw"])
        self.assertEqual(self._contract().resolve(), pages.call_args.kwargs["autonomous_contract"])
        self.assertTrue(pages.call_args.kwargs["production_build"])
        self.assertEqual(str(script.resolve()), report["artifacts"]["final_script"])

    def test_missing_visual_decisions_stops_before_image_production(self) -> None:
        self._write_stage01_inputs()
        visual = self.project / "visual"
        visual.mkdir()

        with (
            patch("cyberppt.commands.run_autonomous.prepare_source_map"),
            patch("cyberppt.commands.run_autonomous.run_source_map_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_semantic_understanding_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_source_truth_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_outline_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_script_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.prepare_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.audit_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.prepare_visual_structure_stage", return_value=visual / "skill-request.md"),
            patch("cyberppt.commands.run_autonomous.run_final_script_pages") as pages,
        ):
            code, report = run_autonomous(self._contract())

        self.assertEqual(1, code)
        self.assertEqual("visual-structure-authoring", report["failed_gate"])
        pages.assert_not_called()

    def test_image_backend_runtime_error_is_reported_at_image_production(self) -> None:
        self._write_stage01_inputs()
        visual = self.project / "visual"
        visual.mkdir()
        (visual / "visual-design-decisions.json").write_text("{}", encoding="utf-8")

        with (
            patch("cyberppt.commands.run_autonomous.prepare_source_map"),
            patch("cyberppt.commands.run_autonomous.run_source_map_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_semantic_understanding_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_source_truth_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_outline_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_script_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.prepare_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.audit_stage02_handoff", return_value={"status": "passed"}),
            patch("cyberppt.commands.run_autonomous.prepare_visual_structure_stage", return_value=visual / "skill-invocation.md"),
            patch("cyberppt.commands.run_autonomous.execute_visual_structure_stage", return_value={}),
            patch("cyberppt.commands.run_autonomous.record_visual_structure_execution", return_value=visual / "execution-receipt.json"),
            patch("cyberppt.commands.run_autonomous.run_visual_structure_audit", return_value=(0, {"status": "passed"})),
            patch("cyberppt.commands.run_autonomous.run_final_script_pages", side_effect=RuntimeError("backend unavailable")),
        ):
            code, report = run_autonomous(self._contract())

        self.assertEqual(1, code)
        self.assertEqual("image-production", report["failed_gate"])
        self.assertEqual("backend unavailable", report["message"])
