from __future__ import annotations

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

from cyberppt.cli import build_parser, main
from cyberppt.commands.script_runner import SCRIPT_ALIASES


class CliTests(unittest.TestCase):
    def test_help_returns_success(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("CyberPPT product tooling", buffer.getvalue())

    def test_doctor_returns_success(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["doctor"])
        self.assertEqual(code, 0)
        self.assertIn("palette_samples: ok", buffer.getvalue())

    def test_all_script_aliases_are_registered(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        for alias in SCRIPT_ALIASES:
            self.assertIn(alias, help_text)
        self.assertIn("stage-script", help_text)
        self.assertIn("approve-script", help_text)
        self.assertIn("script-status", help_text)

    def test_script_help_is_forwarded_to_underlying_script(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "cyberppt", "validate", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Check PPTX structure", completed.stdout)
