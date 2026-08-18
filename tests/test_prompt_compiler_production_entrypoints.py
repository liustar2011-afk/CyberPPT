"""Lock the known Stage 02 production entry points to artifact-spec-v2.

``scripts.imagegen_pipeline.prompt_compiler.DEFAULT_PROMPT_COMPILER`` stays
"content-first-v1" on purpose: dozens of existing tests exercise the legacy
compiler through that shared default (see tests/test_imagegen_creative_brief.py
and friends). Flipping it breaks that coverage without fixing anything real,
because the two actual production entry points already force
"artifact-spec-v2" explicitly:

- ``scripts/imagegen_pipeline/handoff/cli.py`` (the ``--prompt-compiler`` CLI flag)
- ``cyberppt/commands/final_script_pages.py`` (the real Stage 02 build path)

These tests exist to catch a regression in either of those two call sites,
not to change the shared multi-compiler library default.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from scripts.imagegen_pipeline.prompt_compiler import ARTIFACT_PROMPT_COMPILER

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
    def test_stage02_cli_defaults_to_artifact_spec_v2(self) -> None:
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
                self.assertEqual("ARTIFACT_PROMPT_COMPILER", default_node.id)
            else:
                self.assertEqual(ARTIFACT_PROMPT_COMPILER, ast.literal_eval(default_node))
        self.assertTrue(found, "--prompt-compiler argument not found in handoff/cli.py")

    def test_final_script_pages_build_manifest_uses_artifact_spec_v2(self) -> None:
        source = (REPO_ROOT / "cyberppt/commands/final_script_pages.py").read_text(encoding="utf-8")
        value = _call_kwarg_value(source, "build_manifest", "prompt_compiler")
        self.assertEqual(ARTIFACT_PROMPT_COMPILER, value)


if __name__ == "__main__":
    unittest.main()
