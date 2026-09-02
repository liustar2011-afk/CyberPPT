"""Lock the known Stage 02 production entry points to content-first-v1.

The production paths use the content-first compiler so Stage 02 can consume the
locked final script and selected Style 09 lock without a visual-structure
prerequisite. ``artifact-spec-v2`` remains available for explicit legacy
compatibility tests and migration callers.

- ``scripts/imagegen_pipeline/handoff/cli.py`` (the ``--prompt-compiler`` CLI flag)
- ``cyberppt/stage02_production/manifest_stage.py`` (the typed Stage 02 manifest stage)

The command facade delegates to the typed production pipeline, so this test
pins the implementation that now owns the manifest compilation responsibility.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from scripts.imagegen_pipeline.prompt_compiler import DEFAULT_PROMPT_COMPILER

REPO_ROOT = Path(__file__).resolve().parent.parent


def _call_kwarg_value(source: str, func_name: str, kwarg: str) -> object:
    """Return the literal value of ``kwarg`` in the first ``func_name(...)`` call."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
        if name != func_name:
            continue
        for keyword in node.keywords:
            if keyword.arg == kwarg:
                return ast.literal_eval(keyword.value)
    raise AssertionError(f"no {func_name}(..., {kwarg}=...) call found")


class ProductionEntrypointCompilerTests(unittest.TestCase):
    def test_stage02_cli_defaults_to_content_first_without_visual_structure(self) -> None:
        source = (REPO_ROOT / "scripts/imagegen_pipeline/handoff/cli.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", None)
            if name != "add_argument":
                continue
            args = [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
            if "--prompt-compiler" not in args:
                continue
            found = True
            default_node = next(
                (kw.value for kw in node.keywords if kw.arg == "default"),
                None,
            )
            self.assertIsNotNone(default_node, "--prompt-compiler has no default=")
            if isinstance(default_node, ast.Name):
                self.assertEqual("DEFAULT_PROMPT_COMPILER", default_node.id)
            else:
                self.assertEqual(DEFAULT_PROMPT_COMPILER, ast.literal_eval(default_node))
        self.assertTrue(found, "--prompt-compiler argument not found in handoff/cli.py")

    def test_stage02_manifest_stage_uses_content_first_without_visual_structure(self) -> None:
        source = (REPO_ROOT / "cyberppt/stage02_production/manifest_stage.py").read_text(encoding="utf-8")
        value = _call_kwarg_value(source, "build_manifest", "prompt_compiler")
        self.assertEqual(DEFAULT_PROMPT_COMPILER, value)


if __name__ == "__main__":
    unittest.main()
