from __future__ import annotations

import unittest

from cyberppt.commands.script_runner import SCRIPT_ALIASES, script_path


class ScriptRunnerTests(unittest.TestCase):
    def test_known_aliases_resolve_to_existing_files(self) -> None:
        for alias in SCRIPT_ALIASES:
            self.assertTrue(script_path(alias).exists(), alias)

    def test_unknown_alias_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            script_path("missing-command")
