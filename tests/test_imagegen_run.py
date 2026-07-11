from __future__ import annotations

import json
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from cyberppt.commands.blueprint_gate import (
    approve_blueprint_image_review,
    assert_controlled_imagegen_ready,
    stage_blueprint_image_review,
)
from cyberppt.commands.imagegen_run import run_imagegen_page
from cyberppt.commands.image_text_qa import run_project_image_text_qa


class ImagegenRunTests(unittest.TestCase):
    def _project_with_manifest(self) -> tuple[Path, dict[str, object]]:
        root = Path(tempfile.mkdtemp()) / "project"
        stage = root / "workbench/stages/02-blueprint-dual-image/pages_004_004"
        stage.mkdir(parents=True)
        output_path = stage / "page_004_full.png"
        prompt = "Use this approved prompt exactly."
        manifest = {
            "generation_contract": {"generation_size": {"width": 1672, "height": 941}},
            "pairs": [
                {
                    "page_number": 4,
                    "full": {"prompt": prompt, "path": str(output_path)},
                }
            ],
        }
        (stage / "page_image_pairs.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        return root, manifest

    def _write_approved_run_and_qa(
        self,
        project: Path,
        manifest: dict[str, object],
        *,
        run_manifest_sha256: str | None = None,
        run_prompt_sha256: str | None = None,
        qa_status: str = "passed",
    ) -> Path:
        stage = project / "workbench/stages/02-blueprint-dual-image/pages_004_004"
        manifest_path = stage / "page_image_pairs.json"
        full = manifest["pairs"][0]["full"]
        output_path = Path(str(full["path"]))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1672, 941), "white").save(output_path)
        qa_path = stage / "image_text_qa/page_004.json"
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        qa_path.write_text(
            json.dumps(
                {
                    "page": 4,
                    "image_path": str(output_path),
                    "image_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
                    "status": qa_status,
                    "deliverable_allowed": qa_status == "passed",
                }
            ),
            encoding="utf-8",
        )
        run_path = project / "imagegen_runs/page_4.json"
        run_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_text(
            json.dumps(
                {
                    "page": 4,
                    "manifest": str(manifest_path),
                    "manifest_sha256": run_manifest_sha256 or hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                    "prompt_sha256": run_prompt_sha256 or hashlib.sha256(str(full["prompt"]).encode("utf-8")).hexdigest(),
                    "output_path": str(output_path),
                    "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
                    "status": "passed",
                    "image_text_qa": str(qa_path),
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_approval_rejects_run_with_stale_prompt_hash(self) -> None:
        project, manifest = self._project_with_manifest()
        manifest_path = self._write_approved_run_and_qa(project, manifest, run_prompt_sha256="stale")
        stage_blueprint_image_review(project, manifest_path)

        with self.assertRaisesRegex(ValueError, "prompt hash"):
            approve_blueprint_image_review(project, "confirm_blueprint_images")

    def test_approval_rejects_run_with_stale_manifest_hash(self) -> None:
        project, manifest = self._project_with_manifest()
        manifest_path = self._write_approved_run_and_qa(project, manifest, run_manifest_sha256="stale")
        stage_blueprint_image_review(project, manifest_path)

        with self.assertRaisesRegex(ValueError, "manifest hash"):
            approve_blueprint_image_review(project, "confirm_blueprint_images")

    def test_approval_rejects_run_with_stale_output_hash(self) -> None:
        project, manifest = self._project_with_manifest()
        manifest_path = self._write_approved_run_and_qa(project, manifest)
        run_path = project / "imagegen_runs/page_4.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["output_sha256"] = "stale"
        run_path.write_text(json.dumps(run), encoding="utf-8")
        stage_blueprint_image_review(project, manifest_path)

        with self.assertRaisesRegex(ValueError, "output hash"):
            approve_blueprint_image_review(project, "confirm_blueprint_images")

    def test_approval_rejects_review_required_image_text_qa(self) -> None:
        project, manifest = self._project_with_manifest()
        manifest_path = self._write_approved_run_and_qa(project, manifest, qa_status="review_required")
        stage_blueprint_image_review(project, manifest_path)

        with self.assertRaisesRegex(ValueError, "image-text QA"):
            approve_blueprint_image_review(project, "confirm_blueprint_images")

    def test_controlled_readiness_accepts_current_passed_run_and_qa(self) -> None:
        project, manifest = self._project_with_manifest()
        manifest_path = self._write_approved_run_and_qa(project, manifest)

        assert_controlled_imagegen_ready(project, manifest_path)

    def test_image_text_qa_promotes_only_matching_run_to_passed(self) -> None:
        project, manifest = self._project_with_manifest()
        stage = project / "workbench/stages/02-blueprint-dual-image/pages_004_004"
        script = stage / "imagegen_script.md"
        script.write_text("## 第4页：测试\n\n【内容锁定】\n- 真实业务内容\n", encoding="utf-8")
        manifest["imagegen_script"] = str(script)
        manifest_path = stage / "page_image_pairs.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        def generator(**kwargs: object) -> Path:
            output_path = Path(str(kwargs["output_path"]))
            Image.new("RGB", (1672, 941), "white").save(output_path)
            return output_path

        run = run_imagegen_page(project, "4", generator=generator)
        run_path = Path(str(run["run_path"]))
        self.assertEqual("awaiting_image_text_qa", json.loads(run_path.read_text(encoding="utf-8"))["status"])
        with patch(
            "cyberppt.commands.image_text_qa.inspect_image_text",
            return_value={"page": 4, "status": "passed", "deliverable_allowed": True},
        ):
            run_project_image_text_qa(project, "4", ocr_json=self._write_ocr_fixture(project))

        self.assertEqual("passed", json.loads(run_path.read_text(encoding="utf-8"))["status"])

    def _write_ocr_fixture(self, project: Path) -> Path:
        fixture = project / "ocr.json"
        fixture.write_text(json.dumps({"4": "真实业务内容"}, ensure_ascii=False), encoding="utf-8")
        return fixture

    def test_page_uses_manifest_prompt_and_path_exactly(self) -> None:
        project, manifest = self._project_with_manifest()
        pair = manifest["pairs"][0]
        calls: list[dict[str, object]] = []

        def generator(**kwargs: object) -> Path:
            calls.append(kwargs)
            output_path = Path(str(kwargs["output_path"]))
            Image.new("RGB", (1672, 941), "white").save(output_path)
            return output_path

        result = run_imagegen_page(project, "4", generator=generator)

        self.assertEqual(pair["full"]["prompt"], calls[0]["prompt"])
        self.assertEqual(pair["full"]["path"], str(calls[0]["output_path"]))
        self.assertEqual(4, result["page"])
        self.assertEqual([1672, 941], result["actual_dimensions"])
        self.assertTrue(Path(str(result["run_path"])).is_file())

    def test_cover_page_is_rejected(self) -> None:
        project, _ = self._project_with_manifest()

        with self.assertRaises(ValueError):
            run_imagegen_page(project, "1", generator=lambda **_kwargs: Path("unused.png"))

    def test_multiple_pages_are_rejected(self) -> None:
        project, _ = self._project_with_manifest()

        with self.assertRaises(ValueError):
            run_imagegen_page(project, "4-5", generator=lambda **_kwargs: Path("unused.png"))
