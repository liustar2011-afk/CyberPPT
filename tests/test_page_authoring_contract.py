from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.prepare_stage01_input import _ensure_page_script_authoring
from cyberppt.commands.outline_audit import _source_consumption_manifest_issues


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "power-data-service-operation-cooperation-20260802"
OUTLINE = PROJECT / "workbench/stages/01-analysis/outline.json"
SOURCE_TRUTH = PROJECT / "workbench/stages/01-analysis/source-truth.json"
AUTHORING = PROJECT / "workbench/scripts/page-script-authoring.json"
BUILD_OUTLINE = PROJECT / "workbench/tmp/build_outline.py"


class PageAuthoringContractTests(unittest.TestCase):
    def test_authoring_artifact_is_bound_and_consumes_every_non_boundary_unit(self) -> None:
        outline = json.loads(OUTLINE.read_text(encoding="utf-8-sig"))
        authoring = json.loads(AUTHORING.read_text(encoding="utf-8-sig"))
        outline_hash = hashlib.sha256(OUTLINE.read_bytes()).hexdigest()
        self.assertEqual(outline_hash, authoring["outline_sha256"])

        pages = authoring["pages"]
        for page in outline["pages"]:
            if page.get("page_type") != "content":
                continue
            expected = {
                unit["unit_id"]
                for unit in page.get("content_units") or []
                if unit.get("role") != "boundary"
            }
            self.assertEqual(expected, set(pages[page["page_id"]]["consumes"]))

    def test_source_truth_is_not_page_backfilled(self) -> None:
        truth = json.loads(SOURCE_TRUTH.read_text(encoding="utf-8-sig"))
        self.assertEqual([], truth.get("pages"))
        source = BUILD_OUTLINE.read_text(encoding="utf-8-sig")
        self.assertNotIn("write(SOURCE_TRUTH_PATH", source)
        self.assertNotIn('truth["pages"]', source)

    def test_authoring_template_consumes_only_non_boundary_units(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            outline_path = project / "workbench/stages/01-analysis/outline.json"
            outline_path.parent.mkdir(parents=True)
            outline_path.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p01",
                                "page_type": "content",
                                "content_units": [
                                    {"unit_id": "CU-P01-01", "role": "primary"},
                                    {"unit_id": "CU-P01-02", "role": "boundary"},
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            artifact = _ensure_page_script_authoring(
                project,
                outline_path,
                json.loads(outline_path.read_text(encoding="utf-8"))["pages"],
            )
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(["CU-P01-01"], payload["pages"]["p01"]["consumes"])

    def test_consumption_manifest_hash_and_source_binding_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            truth_path = project / "source-truth.json"
            manifest_path = project / "outline-source-consumption.json"
            truth_path.parent.mkdir(parents=True)
            truth_path.write_text(json.dumps({"records": []}), encoding="utf-8")
            truth_hash = hashlib.sha256(truth_path.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps({"source_truth_sha256": truth_hash}),
                encoding="utf-8",
            )
            manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            outline = {
                "source_truth_mapping_mode": "consumption_manifest",
                "source_consumption_manifest": str(manifest_path),
                "source_consumption_sha256": manifest_hash,
            }
            self.assertEqual([], _source_consumption_manifest_issues(project, outline, truth_path))
            manifest_path.write_text("{}", encoding="utf-8")
            issues = _source_consumption_manifest_issues(project, outline, truth_path)
            self.assertEqual(["SOURCE_CONSUMPTION_MANIFEST_STALE"], [issue.code for issue in issues])


if __name__ == "__main__":
    unittest.main()
