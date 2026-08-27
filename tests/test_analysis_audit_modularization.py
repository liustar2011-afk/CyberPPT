from __future__ import annotations

import ast
from pathlib import Path

from script_engine.analysis_audit import (
    audit_deck_plan,
    audit_final_script,
    audit_foundation_analysis,
    validate_source_index_coverage,
)

ROOT = Path(__file__).resolve().parents[1]


def test_analysis_audit_facade_has_no_business_implementations() -> None:
    tree = ast.parse((ROOT / "script_engine/analysis_audit.py").read_text(encoding="utf-8"))
    assert not [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def test_analysis_audit_public_entry_points_remain_available() -> None:
    assert callable(audit_foundation_analysis)
    assert callable(audit_deck_plan)
    assert callable(audit_final_script)
    assert callable(validate_source_index_coverage)
