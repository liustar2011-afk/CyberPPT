from __future__ import annotations

import ast
from pathlib import Path

import script_engine.contract_rules as implementation
import script_engine.contracts as facade


ROOT = Path(__file__).resolve().parents[1]


def test_contracts_facade_reexports_internal_implementation() -> None:
    assert facade.validate_final_script is implementation.validate_final_script
    assert facade.validate_deck_plan is implementation.validate_deck_plan
    assert facade.validate_foundation is implementation.validate_foundation
    assert facade.lint_final_script is implementation.lint_final_script
    assert facade.check_onscreen_structure is implementation.check_onscreen_structure


def test_contracts_facade_contains_no_rule_implementation() -> None:
    path = ROOT / "script_engine" / "contracts.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert functions == []
    assert classes == []
    assert path.stat().st_size < 2_000
