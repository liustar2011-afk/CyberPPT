from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path

from cyberppt.commands.script_runner import SCRIPT_ALIASES, script_path


ROOT = Path(__file__).resolve().parents[1]


class LegacyPipelineAbsenceTest(unittest.TestCase):
    def test_legacy_python_package_cannot_be_imported(self) -> None:
        self.assertIsNone(importlib.util.find_spec("scripts.dual_image_overlay"))

    def test_removed_commands_are_not_runnable(self) -> None:
        for command in ("source-capture", "template-rebuild", "image-ppt"):
            with self.subTest(command=command):
                self.assertNotIn(command, SCRIPT_ALIASES)
                with self.assertRaisesRegex(KeyError, "unknown CyberPPT script alias"):
                    script_path(command)

    def test_runtime_output_roots_are_not_tracked(self) -> None:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked = completed.stdout.splitlines()
        forbidden_roots = ("image2pptx_runs/", "tmp/", "prompts/attempts/")
        offenders = [
            path
            for path in tracked
            if path == "tmp_image_entry_scan.txt" or path.startswith(forbidden_roots)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
