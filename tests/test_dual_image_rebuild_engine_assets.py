from __future__ import annotations

import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

import template_image_ppt_export as exporter  # noqa: E402


TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAF/gL+fAS+wwAAAABJRU5ErkJggg=="
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_project_production_fixture(root: Path) -> dict[str, Path]:
    _write_json(
        root / "workbench/analysis_expression/contract.json",
        {"schema": "cyberppt.analysis_expression.contract.v1"},
    )
    script = root / "script-final.md"
    script.write_text(
        "## \u7b2c2\u9875\uff1aScript title\n"
        "\u3010\u5185\u5bb9\u9501\u5b9a\u3011\n"
        "\u6807\u9898\uff1aScript title\n"
        "\u526f\u6807\u9898\uff1aScript subtitle\n"
        "Script body\n",
        encoding="utf-8",
    )
    full_image = root / "page_002_full.png"
    full_image.write_bytes(TINY_PNG)
    template_lock = _write_json(
        root / "template_text_lock.json",
        {
            "schema": "cyberppt.template_text_lock.v1",
            "pages": [2],
            "records": [
                {
                    "page": 2,
                    "title": "Locked title",
                    "subtitle": "Locked subtitle",
                    "section": "Locked section",
                    "template_variant": "locked-variant",
                    "page_badge_enabled": True,
                    "footer_enabled": False,
                    "approved": True,
                }
            ],
        },
    )
    pair_manifest = _write_json(
        root / "page_image_pairs.json",
        {
            "mode": "cyberppt-full-image-only",
            "pairs": [
                {
                    "page_number": 2,
                    "title": "Script title",
                    "full": {
                        "path": str(full_image),
                        "status": "Generated",
                    },
                }
            ],
        },
    )
    notes_manifest = _write_json(
        root / "speaker_notes_manifest.json",
        {
            "schema": "cyberppt.speaker_notes_manifest.v1",
            "pages": [2],
            "notes": [
                {
                    "page_number": 2,
                    "title": "Approved note title",
                    "notes_text": "Approved note body",
                    "source": "business_rule_draft",
                }
            ],
        },
    )
    stage = root / "workbench/stages/02-blueprint-dual-image"
    image_review = _write_json(
        stage / "blueprint_image_review.json",
        {
            "schema": "cyberppt.blueprint_image_review.v1",
            "page_image_manifest": str(pair_manifest.resolve()),
            "page_image_manifest_sha256": _sha256(pair_manifest),
            "images": [
                {
                    "page": 2,
                    "path": str(full_image.resolve()),
                    "sha256": _sha256(full_image),
                }
            ],
        },
    )
    image_approval = _write_json(
        stage / "blueprint_image_review.approved.json",
        {"approved": True, "artifact": str(image_review.resolve())},
    )
    notes_approval = _write_json(
        stage / "speaker_notes_review.approved.json",
        {
            "approved": True,
            "manifest": str(notes_manifest.resolve()),
            "manifest_sha256": _sha256(notes_manifest),
        },
    )
    return {
        "script": script,
        "full_image": full_image,
        "template_lock": template_lock,
        "pair_manifest": pair_manifest,
        "notes_manifest": notes_manifest,
        "image_review": image_review,
        "image_approval": image_approval,
        "notes_approval": notes_approval,
        "output": root / "output",
    }


def _build_project_production_manifest(paths: dict[str, Path], **overrides: object) -> dict:
    kwargs: dict[str, object] = {
        "script_path": paths["script"],
        "selected_pages": [2],
        "output_dir": paths["output"],
        "template_text_lock": paths["template_lock"],
        "page_image_manifest": paths["pair_manifest"],
        "speaker_notes_manifest": paths["notes_manifest"],
        "project_production": True,
    }
    kwargs.update(overrides)
    return exporter.build_manifest(**kwargs)


class DualImageRebuildEngineAssetsTest(unittest.TestCase):
    def test_project_production_uses_locked_text_approved_images_and_notes(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))

            locks = exporter.load_template_text_lock(paths["template_lock"], [2])
            images = exporter.load_approved_full_images(paths["pair_manifest"], [2])
            manifest = _build_project_production_manifest(paths)

        task = manifest["tasks"][0]
        self.assertEqual("Locked title", locks[2]["title"])
        self.assertEqual(paths["full_image"].resolve(), images[2])
        self.assertEqual("Locked title", task["title"])
        self.assertEqual("Locked title", task["slide_title"])
        self.assertEqual("Locked subtitle", task["subtitle"])
        self.assertEqual("Locked section", task["section"])
        self.assertEqual("locked-variant", task["template_variant"])
        self.assertTrue(task["page_badge_enabled"])
        self.assertFalse(task["footer_enabled"])
        self.assertEqual(str(paths["full_image"].resolve()), task["image_path"])
        self.assertEqual("approved_speaker_notes", task["notes_source"])
        self.assertEqual("Approved note body", task["notes_text"])

    def test_project_production_requires_all_approved_inputs(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            cases = (
                ("template_text_lock", None, "metadata_required: --template-text-lock is required"),
                ("page_image_manifest", None, "approved page image manifest is required"),
                ("speaker_notes_manifest", None, "approved speaker notes manifest is required"),
            )
            for key, value, message in cases:
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                    _build_project_production_manifest(paths, **{key: value})

    def test_project_production_rejects_missing_page_lock(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["template_lock"].read_text(encoding="utf-8"))
            payload["records"] = []
            _write_json(paths["template_lock"], payload)

            with self.assertRaisesRegex(ValueError, "missing template text lock record for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_unapproved_page_lock(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["template_lock"].read_text(encoding="utf-8"))
            payload["records"][0]["approved"] = False
            _write_json(paths["template_lock"], payload)

            with self.assertRaisesRegex(ValueError, "template text lock is not approved for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_page_set_mismatch(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["pair_manifest"].read_text(encoding="utf-8"))
            payload["pairs"][0]["page_number"] = 1
            _write_json(paths["pair_manifest"], payload)

            with self.assertRaisesRegex(ValueError, "approved page image manifest page set mismatch"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_missing_full_image(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            paths["full_image"].unlink()

            with self.assertRaisesRegex(FileNotFoundError, "approved full image is missing for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_unapproved_image_review(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            _write_json(
                paths["image_approval"],
                {"approved": False, "artifact": str(paths["image_review"].resolve())},
            )

            with self.assertRaisesRegex(ValueError, "blueprint image review approval is required"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_tampered_approved_image(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            paths["full_image"].write_bytes(TINY_PNG + b"tampered")

            with self.assertRaisesRegex(ValueError, "approved blueprint image hash mismatch for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_tampered_page_image_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["pair_manifest"].read_text(encoding="utf-8"))
            payload["pairs"][0]["title"] = "Tampered title"
            _write_json(paths["pair_manifest"], payload)

            with self.assertRaisesRegex(ValueError, "approved page image manifest has changed"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_duplicate_page_image_records(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["pair_manifest"].read_text(encoding="utf-8"))
            payload["pairs"].append(dict(payload["pairs"][0]))
            _write_json(paths["pair_manifest"], payload)

            with self.assertRaisesRegex(ValueError, "duplicate approved page image manifest record for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_duplicate_requested_pages(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))

            with self.assertRaisesRegex(ValueError, "duplicate requested page 2"):
                _build_project_production_manifest(paths, selected_pages=[2, 2])

    def test_project_production_rejects_duplicate_template_lock_declared_pages(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["template_lock"].read_text(encoding="utf-8"))
            payload["pages"] = [2, 2]
            _write_json(paths["template_lock"], payload)

            with self.assertRaisesRegex(ValueError, "duplicate template text lock declared page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_duplicate_speaker_notes_declared_pages(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["notes_manifest"].read_text(encoding="utf-8"))
            payload["pages"] = [2, 2]
            _write_json(paths["notes_manifest"], payload)
            approval = json.loads(paths["notes_approval"].read_text(encoding="utf-8"))
            approval["manifest_sha256"] = _sha256(paths["notes_manifest"])
            _write_json(paths["notes_approval"], approval)

            with self.assertRaisesRegex(ValueError, "duplicate approved speaker notes declared page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_locates_project_from_every_approved_input(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = _write_project_production_fixture(root / "project")
            external_lock = _write_json(
                root / "external" / "template_text_lock.json",
                json.loads(paths["template_lock"].read_text(encoding="utf-8")),
            )

            with self.assertRaisesRegex(
                ValueError,
                "project production requires approved inputs under a project containing",
            ):
                _build_project_production_manifest(paths, template_text_lock=external_lock)

    def test_project_production_rejects_duplicate_blueprint_review_images(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["image_review"].read_text(encoding="utf-8"))
            payload["images"].append(dict(payload["images"][0]))
            _write_json(paths["image_review"], payload)

            with self.assertRaisesRegex(ValueError, "duplicate approved blueprint image review record for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_tampered_speaker_notes_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            payload = json.loads(paths["notes_manifest"].read_text(encoding="utf-8"))
            payload["notes"][0]["notes_text"] = "Tampered notes"
            _write_json(paths["notes_manifest"], payload)

            with self.assertRaisesRegex(ValueError, "approved speaker notes manifest has changed"):
                _build_project_production_manifest(paths)

    def test_project_production_rejects_unapproved_and_duplicate_speaker_notes(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            _write_json(
                paths["notes_approval"],
                {
                    "approved": False,
                    "manifest": str(paths["notes_manifest"].resolve()),
                    "manifest_sha256": _sha256(paths["notes_manifest"]),
                },
            )
            with self.assertRaisesRegex(ValueError, "speaker notes approval is required"):
                _build_project_production_manifest(paths)

            paths = _write_project_production_fixture(Path(directory) / "duplicate-notes")
            payload = json.loads(paths["notes_manifest"].read_text(encoding="utf-8"))
            payload["notes"].append(dict(payload["notes"][0]))
            _write_json(paths["notes_manifest"], payload)
            with self.assertRaisesRegex(ValueError, "duplicate approved speaker notes record for page 2"):
                _build_project_production_manifest(paths)

    def test_project_production_run_skips_image_generation(self) -> None:
        with TemporaryDirectory() as directory:
            paths = _write_project_production_fixture(Path(directory))
            args = exporter.build_parser().parse_args(
                [
                    "run",
                    "--script",
                    str(paths["script"]),
                    "--pages",
                    "2",
                    "--output-dir",
                    str(paths["output"]),
                    "--project-production",
                    "--template-text-lock",
                    str(paths["template_lock"]),
                    "--page-image-manifest",
                    str(paths["pair_manifest"]),
                    "--speaker-notes-manifest",
                    str(paths["notes_manifest"]),
                ]
            )

            exported_pptx = Path(directory) / "approved-inputs.pptx"
            with patch.object(exporter, "command_generate") as generate, patch.object(
                exporter, "run_export", return_value=exported_pptx
            ) as export:
                result = args.func(args)

            manifest = json.loads(
                (paths["output"] / "template_image_manifest.json").read_text(encoding="utf-8")
            )
            project = (
                paths["output"] / "template_image_ppt_template_image_project"
            ).resolve()
            svg = next((project / "svg_output").glob("*.svg")).read_text(encoding="utf-8")
            copied_image_exists = (project / "images" / paths["full_image"].name).is_file()

        self.assertEqual(0, result)
        generate.assert_not_called()
        export.assert_called_once_with(project)
        self.assertTrue(copied_image_exists)
        self.assertIn("Locked title", svg)
        self.assertIn("Locked subtitle", svg)
        self.assertEqual(str(paths["full_image"].resolve()), manifest["tasks"][0]["image_path"])

    def test_rebuild_engine_required_files_exist(self) -> None:
        required = [
            "editable_overlay_rebuild.py",
            "ocr_text_locator.py",
            "script_text_overlay.py",
            "template_image_ppt_export.py",
            "svg_quality_checker.py",
            "finalize_svg.py",
            "svg_to_pptx.py",
            "svg_to_pptx/__init__.py",
            "svg_finalize/__init__.py",
            "templates/brands/中电联公共元素_轻量版/brand_rules.json",
            "templates/brands/中电联公共元素_轻量版/master_elements.svg",
        ]

        missing = [path for path in required if not (ENGINE / path).is_file()]

        self.assertEqual([], missing)

    def test_dual_image_runtime_does_not_reference_legacy_paths(self) -> None:
        runtime = ROOT / "scripts" / "dual_image_overlay"
        offenders = []
        forbidden = (
            "/Volumes/DOC/" + "ppt-" + "master",
            "vendor/" + "ppt_" + "master_dual_image",
            "vendor." + "ppt_" + "master_dual_image",
            "page_image_" + "pair_batch",
        )

        for suffix in ("*.py", "*.mjs"):
            for path in runtime.rglob(suffix):
                text = path.read_text(encoding="utf-8")
                if any(item in text for item in forbidden):
                    offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
