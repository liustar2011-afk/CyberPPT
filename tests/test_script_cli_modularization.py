from __future__ import annotations

import ast
from pathlib import Path

import script_engine.cli as cli
import script_engine.final_quality as final_quality
import script_engine.project_scaffold as project_scaffold
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


def test_cli_routes_project_scaffolding_through_focused_module(tmp_path) -> None:
    project_dir = project_scaffold.create_project("demo-project", tmp_path)
    assert project_dir == tmp_path / "demo-project"
    assert (project_dir / "dist" / ".gitkeep").is_file()
    assert (project_dir / "sources" / ".gitkeep").is_file()
    assert (project_dir / ".cache").is_dir()
    assert (project_dir / ".gitignore").read_text(encoding="utf-8") == project_scaffold.PROJECT_GITIGNORE


def test_cli_does_not_reimplement_project_scaffolding() -> None:
    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    assignments = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }

    assert "SLUG_PATTERN" not in assignments
    assert "PROJECT_GITIGNORE" not in assignments
    assert "mkdir(" not in ast.get_source_segment(source, next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_new_project"
    ))
