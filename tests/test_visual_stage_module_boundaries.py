from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "cyberppt" / "visual_stage"
FACADE = ROOT / "cyberppt" / "commands" / "visual_structure_stage.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_compiler_does_not_directly_depend_on_artifact_ledger_or_cli() -> None:
    imports = _imports(PACKAGE / "compiler.py")
    assert "cyberppt.artifact_ledger" not in imports
    assert not any(name.startswith("cyberppt.cli") for name in imports)
    assert not any(name.startswith("cyberppt.commands") for name in imports)


def test_persistence_does_not_rederive_visual_semantics() -> None:
    functions = {
        node.name
        for node in _tree(PACKAGE / "persistence.py").body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_build_executable_page" not in functions
    assert "compile_visual_spec" not in functions
    assert "_decision_execution_design" not in functions


def test_prompt_gate_does_not_import_compiler_or_audit() -> None:
    imports = _imports(PACKAGE / "prompt_gate.py")
    assert "cyberppt.visual_stage.compiler" not in imports
    assert "cyberppt.visual_stage.audit" not in imports


def test_command_module_is_compatibility_facade() -> None:
    source = FACADE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(FACADE))
    assert "ALLOWED_TOPOLOGY =" not in source
    assert "audit_visual_design_package" not in source
    assert "append_artifacts" not in source
    public = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {
        "prepare_visual_structure_stage",
        "execute_visual_structure_stage",
        "record_visual_structure_execution",
        "run_visual_structure_audit",
        "assert_visual_structure_ready",
    } <= public


def test_visual_stage_has_expected_responsibility_modules() -> None:
    assert {
        "compiler.py",
        "execution.py",
        "audit.py",
        "prompt_gate.py",
        "persistence.py",
    } <= {path.name for path in PACKAGE.glob("*.py")}
