from __future__ import annotations

import ast
from pathlib import Path

import script_engine.cli as cli
import script_engine.final_quality as final_quality
from script_engine.contracts import load_json
from script_engine.render import render_stage02_markdown


ROOT = Path(__file__).resolve().parents[1]


def test_cli_routes_final_quality_through_focused_module() -> None:
    assert cli._final_lint_issues is final_quality.collect_final_lint_issues

    payload = load_json(ROOT / "examples" / "final-script.example.json")
    markdown = render_stage02_markdown(payload)
    assert cli._final_lint_findings(payload, markdown) == final_quality.partition_final_lint_findings(
        payload,
        markdown,
    )


def test_cli_no_longer_owns_final_quality_dependencies() -> None:
    path = ROOT / "script_engine" / "cli.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    contract_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "contracts"
        for alias in node.names
    }
    final_quality_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"_final_lint_issues"}
    }

    assert "delivery_cleanliness" not in imported_modules
    assert "quality_policy" not in imported_modules
    assert final_quality_functions == set()
    assert contract_imports.isdisjoint(
        {
            "check_full_copy_duplication",
            "check_onscreen_detail_length",
            "check_onscreen_structure",
            "check_onscreen_terminal_punctuation",
            "check_speaker_notes_length",
            "lint_final_script",
        }
    )
