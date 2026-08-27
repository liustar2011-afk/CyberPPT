from __future__ import annotations

import ast
from pathlib import Path

import cyberppt.argument_flow as modular
import cyberppt.argument_flow_contract as facade

ROOT = Path(__file__).resolve().parents[1]


def test_argument_flow_facade_reexports_public_api() -> None:
    for name in facade.__all__:
        assert getattr(facade, name) is getattr(modular, name)


def test_argument_flow_facade_contains_no_business_functions() -> None:
    path = ROOT / "cyberppt" / "argument_flow_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body)


def test_argument_flow_modules_have_no_cycle_back_to_facade() -> None:
    package = ROOT / "cyberppt" / "argument_flow"
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert "cyberppt.argument_flow_contract" not in imports
