from __future__ import annotations

import unittest

from cyberppt.commands.script_runner import SCRIPT_ALIASES, script_path


class ScriptRunnerTests(unittest.TestCase):
    def test_known_aliases_resolve_to_existing_files(self) -> None:
        for alias in SCRIPT_ALIASES:
            self.assertTrue(script_path(alias).exists(), alias)

    def test_body_blueprint_prompt_alias_is_registered(self) -> None:
        self.assertEqual("body_blueprint_prompt.py", script_path("body-blueprint-prompts").name)

    def test_pair_manifest_alias_is_registered(self) -> None:
        self.assertEqual("cyberppt_pair_manifest.py", script_path("pair-manifest").name)

    def test_image_ppt_alias_is_registered(self) -> None:
        path = script_path("image-ppt")

        self.assertEqual("template_image_ppt_export.py", path.name)

    def test_unknown_alias_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            script_path("missing-command")
