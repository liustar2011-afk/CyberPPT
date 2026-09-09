from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tests._final_script_pages_base import FinalScriptPagesTests as _FinalScriptPagesTestsBase


# Pytest's unittest collector can collect an imported TestCase even when the
# alias begins with an underscore. Keep the historical base available for
# inheritance but make only the modern wrapper class collectable.
_FinalScriptPagesTestsBase.__test__ = False


class FinalScriptPagesTests(_FinalScriptPagesTestsBase):
    __test__ = True

    def test_external_script_full_copy_is_nonvisible_prompt_context(self) -> None:
        from cyberppt.commands.final_script_pages import run_final_script_pages
        from cyberppt.commands.init_project import init_project

        full_copy = "平台提供数据服务。\n\n补充条件仅用于理解业务边界。"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "external-stage02"
            init_project(project)
            script = root / "external.md"
            script.write_text(
                "## P01 数据服务\n\n- 页面类型：内容页\n\n"
                f"### 完整文字稿\n\n{full_copy}\n\n"
                "### 上屏文字\n\n平台提供数据服务。\n",
                encoding="utf-8",
            )
            original = script.read_bytes()
            summary = run_final_script_pages(
                project=project, script=script, pages_raw="1",
                style_id=9, external_script=True,
            )
            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text())
            prompt = manifest["pairs"][0]["full"]["prompt"]
            self.assertEqual("external_script", manifest["source_mode"])
            self.assertIn("--external-script", summary["resume_command"])
            self.assertEqual(original, script.read_bytes())
            self.assertIn("【完整文字稿（不上屏）】", prompt)
            self.assertEqual(1, prompt.count(full_copy))
            visible = prompt.split("【页面内容素材｜允许提炼、改写、重组】", 1)[1]
            self.assertIn("平台提供数据服务。", visible)
            self.assertNotIn("补充条件仅用于理解业务边界", visible)

    def test_typo_audit_regenerates_before_enhancement(self) -> None:
        """Correction retry must operate on real image bytes before enhancement."""

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "page-004.png"
            reference = Path(tmp) / "palette-09.png"
            reference.write_bytes(b"reference")
            manifest = {
                "production_mode": "image-to-editable-svg",
                "pairs": [
                    {
                        "page_number": 4,
                        "reference_images": [{"path": str(reference)}],
                        "image_text_truth": {
                            "script_text": "数据产品\n数据服务",
                            "scope": "typo_and_gibberish_only",
                        },
                        "full": {
                            "path": str(output),
                            "prompt": "prompt",
                            "canvas": "2048x1024",
                        },
                    }
                ],
            }
            failed = {
                "valid": False,
                "issues": [
                    {
                        "type": "typo",
                        "expected": "数据服务",
                        "observed": "数据服努",
                        "bbox": [10, 20, 30, 40],
                    }
                ],
            }
            passed = {"valid": True, "issues": []}

            def generate_image(**kwargs: object) -> None:
                target = Path(str(kwargs["output_path"]))
                Image.new("RGB", (2048, 1024), "white").save(target)

            with (
                patch(
                    "cyberppt.commands.final_script_pages.run_codex_image",
                    side_effect=generate_image,
                ) as generate,
                patch(
                    "cyberppt.image_text_gate.audit_generated_image_text",
                    side_effect=[failed, passed],
                ),
                patch("cyberppt.commands.final_script_pages.ensure_output_size") as enhance,
            ):
                from cyberppt.commands.final_script_pages import _generate_manifest_images

                summary = _generate_manifest_images(
                    manifest,
                    model="gpt-image-2",
                    quality="high",
                    timeout=600,
                    force=True,
                    dry_run=False,
                )

            failed_image = Path(tmp) / "page-004.attempt-01-text-audit-failed.png"
            error_crop = Path(tmp) / (
                "page-004.attempt-01-text-audit-failed-text-audit-region-01.png"
            )
            self.assertEqual(2, generate.call_count)
            first_call, second_call = generate.call_args_list
            self.assertEqual([reference], first_call.kwargs["image_paths"])
            self.assertEqual(
                [failed_image, error_crop, reference],
                second_call.kwargs["image_paths"],
            )
            self.assertIn("第一张输入图片是上一轮生成", second_call.kwargs["prompt"])
            self.assertIn('"expected": "数据服务"', second_call.kwargs["prompt"])
            self.assertIn('"observed": "数据服努"', second_call.kwargs["prompt"])

            attempt_records = summary["imagegen_attempts"]
            self.assertEqual(2, len(attempt_records))
            first_sent = Path(attempt_records[0]["prompt_path"])
            second_sent = Path(attempt_records[1]["prompt_path"])
            second_record = json.loads(
                Path(attempt_records[1]["request_record_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(first_call.kwargs["prompt"], first_sent.read_text(encoding="utf-8"))
            self.assertEqual(second_call.kwargs["prompt"], second_sent.read_text(encoding="utf-8"))
            self.assertEqual(
                second_record["prompt_sha256"],
                hashlib.sha256(second_sent.read_bytes()).hexdigest(),
            )
            self.assertTrue(second_record["correction_retry"])
            self.assertEqual("gpt-image-2", second_record["model"])
            self.assertEqual("high", second_record["quality"])
            self.assertEqual("2048x1024", second_record["size"])
            self.assertEqual(str(failed_image), second_record["failed_image"])
            self.assertEqual(
                [
                    str(failed_image.resolve()),
                    str(error_crop.resolve()),
                    str(reference.resolve()),
                ],
                second_record["input_images"],
            )

            self.assertTrue(failed_image.is_file())
            self.assertTrue(error_crop.is_file())
            self.assertEqual(str(failed_image), summary["text_audits"][0]["image"])
            enhance.assert_called_once_with(output, "2048x1024")
            self.assertTrue(manifest["pairs"][0]["full"]["text_audit"]["valid"])
            self.assertEqual(2, len(summary["text_audits"]))
