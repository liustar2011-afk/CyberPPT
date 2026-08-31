from __future__ import annotations

import ast
from pathlib import Path

import script_engine.analysis_audits.composed_trace as composed_trace
import script_engine.analysis_audits.composed_trace_core as core
import script_engine.analysis_audits.composed_trace_priorities as priorities


ROOT = Path(__file__).resolve().parents[1]


def test_composed_trace_routes_core_public_surface() -> None:
    for name in core.__all__:
        assert getattr(composed_trace, name) is getattr(core, name)


def test_composed_trace_routes_priority_domain() -> None:
    assert composed_trace.critic_priorities is priorities.critic_priorities


def test_composed_trace_preserves_historical_private_helpers() -> None:
    assert composed_trace._specific_identifiers is core._specific_identifiers
    assert composed_trace._source_strings is core._source_strings
    assert composed_trace._external_check_page_ids is priorities._external_check_page_ids


def test_composed_trace_is_thin_compatibility_facade() -> None:
    path = ROOT / "script_engine" / "analysis_audits" / "composed_trace.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    implementations = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    assert implementations == []
    assert path.stat().st_size < 3_000
    assert "from .composed_trace_core import (" in source
    assert "from .composed_trace_priorities import" in source
