from __future__ import annotations

import ast
from pathlib import Path

import script_engine.analysis_audits.common as common
import script_engine.analysis_audits.common_primitives as primitives


ROOT = Path(__file__).resolve().parents[1]


def test_analysis_common_routes_primitives_to_focused_module() -> None:
    for name in primitives.__all__:
        assert getattr(common, name) is getattr(primitives, name)


def test_analysis_common_only_owns_high_level_contract_validators() -> None:
    path = ROOT / "script_engine" / "analysis_audits" / "common.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    assert function_names == {
        "_evidence_fit_review_issues",
        "_audit_evidence_fit_reviews",
        "_onscreen_contract_definition_issues",
        "_audit_onscreen_composition_definition",
    }
    assert path.stat().st_size < 18_000
    assert "from .common_primitives import *" in source


def test_analysis_common_preserves_historical_public_surface() -> None:
    for name in (
        "foundation_items_by_id",
        "_item_text",
        "effective_visibility",
        "_page_evidence_ids",
        "requires_source_consumption",
        "_source_surface_values",
        "_page_text",
        "_audit_evidence_fit_reviews",
        "_onscreen_contract_definition_issues",
        "_audit_onscreen_composition_definition",
    ):
        assert name in common.__all__
