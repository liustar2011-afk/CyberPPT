from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cyberppt.artifact_ledger import append_artifacts


class ArtifactLedgerTests(unittest.TestCase):
    def test_same_path_is_appended_and_links_to_previous_version(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_path = root / "artifact-ledger.json"
            artifact = root / "script-final.md"
            artifact.write_text("v1\n", encoding="utf-8")

            append_artifacts(
                ledger_path,
                [
                    {
                        "stage": "01-analysis",
                        "page": None,
                        "path": str(artifact),
                        "status": "draft",
                        "sha256": "hash-v1",
                    }
                ],
                build_id="build-001",
            )
            artifact.write_text("v2\n", encoding="utf-8")
            append_artifacts(
                ledger_path,
                [
                    {
                        "stage": "01-analysis",
                        "page": None,
                        "path": str(artifact),
                        "status": "approved",
                        "sha256": "hash-v2",
                    }
                ],
                build_id="build-002",
            )

            payload = json.loads(ledger_path.read_text(encoding="utf-8"))
            records = payload["artifacts"]

        self.assertEqual(2, len(records))
        self.assertEqual("build-001", records[0]["build_id"])
        self.assertEqual("build-002", records[1]["build_id"])
        self.assertEqual([records[0]["artifact_id"]], records[1]["supersedes"])
        self.assertEqual("hash-v2", records[1]["sha256"])

    def test_replaying_identical_artifact_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "artifact-ledger.json"
            record = {"path": "out.json", "stage": "qa", "page": "1", "status": "passed", "sha256": "abc"}
            append_artifacts(ledger_path, [record], build_id="build-001")
            append_artifacts(ledger_path, [record], build_id="build-001")
            payload = json.loads(ledger_path.read_text(encoding="utf-8"))

        self.assertEqual(1, len(payload["artifacts"]))


if __name__ == "__main__":
    unittest.main()
