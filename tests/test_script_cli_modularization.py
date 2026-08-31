from __future__ import annotations

import ast
from pathlib import Path

import script_engine.audit_reports as audit_reports
import script_engine.cli as cli
import script_engine.cli_parser as cli_parser
import script_engine.final_quality as final_quality
import script_engine.project_scaffold as project_scaffold
import script_engine.project_status as project_status
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


def test_cli_routes_project_status_through_focused_module() -> None:
    assert cli._project_profile_for_foundation is project_status.project_profile_for_foundation

    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    status_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_status"
    )
    status_source = ast.get_source_segment(source, status_node) or ""

    assert "build_project_status" in status_source
    assert "source_candidates" not in status_source
    assert "audit_foundation_analysis" not in status_source
    assert "audit_deck_plan" not in status_source
    assert "audit_final_script" not in status_source
    assert "render_stage02_markdown" not in status_source


def test_cli_does_not_reimplement_project_status_helpers() -> None:
    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "_mtime" not in function_names
    assert "_artifact_report" not in function_names
    assert "datetime" not in imported_modules


def test_cli_routes_parser_schema_through_focused_module() -> None:
    cli_built = cli.build_parser()
    focused = cli_parser.build_parser(cli.VALIDATORS)
    assert cli_built.prog == focused.prog == "cyberppt-script"

    cli_choices = next(
        action.choices
        for action in cli_built._actions
        if getattr(action, "dest", None) == "command"
    )
    focused_choices = next(
        action.choices
        for action in focused._actions
        if getattr(action, "dest", None) == "command"
    )
    assert set(cli_choices) == set(focused_choices)


def test_cli_does_not_reimplement_argparse_schema() -> None:
    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported_names = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    parser_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_parser"
    )
    parser_source = ast.get_source_segment(source, parser_node) or ""

    assert "argparse" not in imported_names
    assert "add_parser(" not in parser_source
    assert "add_argument(" not in parser_source
    assert "_build_parser" in parser_source


def test_cli_routes_audit_and_trace_reports_through_focused_module() -> None:
    assert cli.VALIDATORS is audit_reports.VALIDATORS

    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    wrappers = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {
            "_validate",
            "_audit_foundation",
            "_audit_plan",
            "_review_plan",
            "_audit_final",
            "_trace_composed",
            "_check_refs",
            "_build_source_index",
        }
    }

    assert "validate_artifact_report" in wrappers["_validate"]
    assert "foundation_audit_report" in wrappers["_audit_foundation"]
    assert "plan_audit_report" in wrappers["_audit_plan"]
    assert "plan_review_text" in wrappers["_review_plan"]
    assert "final_audit_report" in wrappers["_audit_final"]
    assert "composed_trace_report" in wrappers["_trace_composed"]
    assert "source_refs_report" in wrappers["_check_refs"]
    assert "build_source_index_report" in wrappers["_build_source_index"]


def test_cli_does_not_reimplement_audit_report_dependencies() -> None:
    path = ROOT / "script_engine" / "cli.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
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

    assert "analysis_audit" not in imported_modules
    assert "analysis_audits.composed_trace" not in imported_modules
    assert "plan_review" not in imported_modules
    assert "source_index" not in imported_modules
    assert contract_imports.isdisjoint(
        {
            "validate_deck_plan",
            "validate_foundation",
            "validate_source_refs_coverage",
        }
    )
