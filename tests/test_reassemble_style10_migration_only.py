"""Task 6 regression: a production manifest is self-describing.

reassemble_style10_prompts.py used to be a shadow prompt-assembly path,
independent from scripts/imagegen_pipeline/artifact_prompt.py's single
renderer, and its output directories were the closest thing to "the real
prompt" for Style 10 projects. This test locks the replacement guarantee: a
real production manifest (built through build_manifest / compile_page_prompt)
carries enough self-describing provenance (compiler, prompt_ir_version,
prompt_sha256) that nobody needs to trust a hand-copied prompts/ directory to
know where a prompt came from.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, stage_script
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt
from scripts.imagegen_pipeline.page_manifest import build_manifest
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from tests.test_artifact_prompt import _spec


class ProductionManifestCarriesSelfDescribingProvenanceTests(unittest.TestCase):
    def test_manifest_prompt_traces_back_without_a_reassembled_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text(
                "## 第2页：治理结果\n\n- 页面类型：内容页\n- 页面标题：治理结果\n"
                "- 主判断：治理结果可追溯。\n- 上屏文字：\n\n  Governed input\n  Traceable result\n",
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(project=project, style_id=10, source_script=script)
            spec = replace(_spec(), page_id="P02", page_number=2)
            expected_prompt = render_final_prompt(
                build_final_prompt_ir(spec), style_id=spec.art_direction.style_id, style_lock=style_lock
            )
            approved = root / "approved.md"
            approved.write_text(expected_prompt, encoding="utf-8")
            stage_script(project, 2, "imagegen", "final", approved)
            approve_script(project, 2, "imagegen")

            with patch(
                "scripts.imagegen_pipeline.page_manifest.load_project_page_artifact_specs",
                return_value={2: spec},
            ):
                manifest, _, _, _ = build_manifest(
                    script=script,
                    pages_raw="2",
                    output_dir=root / "images",
                    project_path=project,
                    style_lock=style_lock,
                    require_approved_prompts=True,
                    prompt_compiler="artifact-spec-v2",
                )

        self.assertEqual("artifact-spec-v2", manifest["prompt_contract"]["compiler"])
        pair = manifest["pairs"][0]
        self.assertEqual(expected_prompt, pair["full"]["prompt"])
        self.assertIn("prompt_sha256", pair["full"])
        self.assertTrue(pair["full"]["prompt_sha256"])


if __name__ == "__main__":
    unittest.main()
