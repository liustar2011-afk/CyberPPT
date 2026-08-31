from __future__ import annotations

from pathlib import Path

import script_engine.analysis_audit as facade
import script_engine.analysis_audits.final_authoring as final_authoring
import script_engine.analysis_audits.final_lean as final_lean
import script_engine.analysis_audits.final_script as legacy_final_script
import script_engine.analysis_audits.final_script_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]

_AUTHORING_HELPERS = (
    "_status_strength_preserved",
    "_onscreen_module_lines",
    "_is_lead_like_evidence_item",
    "_evidence_first_item_hierarchy_issues",
    "_is_readable_proposition",
    "_onscreen_expression_warnings",
    "_looks_like_structural_metadata",
    "_author_execution_issues",
    "_authored_bare_label_detail_issues",
    "_audit_authored_content_coverage",
    "_authored_relationships_issues",
    "_slide_text",
)
_LEAN_HELPERS = (
    "_audit_lean_authored_source_consumption",
    "_onscreen_surface",
    "_audit_lean_onscreen_full_copy_alignment",
    "_audit_lean_relationship_visibility",
)
_PUBLIC_AUTHORING_HELPERS = tuple(
    name for name in _AUTHORING_HELPERS if name in legacy_final_script.__all__
)
_PUBLIC_LEAN_HELPERS = tuple(
    name for name in _LEAN_HELPERS if name in legacy_final_script.__all__
)


def test_final_script_runtime_routes_authoring_helpers_to_focused_module() -> None:
    for name in _AUTHORING_HELPERS:
        focused = getattr(final_authoring, name)
        assert getattr(legacy_final_script, name) is focused
        assert legacy_final_script.audit_final_script.__globals__[name] is focused

    for name in _PUBLIC_AUTHORING_HELPERS:
        focused = getattr(final_authoring, name)
        assert getattr(runtime, name) is focused
        assert getattr(facade, name) is focused

    assert legacy_final_script._STATUS_PRESERVATION_MARKERS is final_authoring._STATUS_PRESERVATION_MARKERS
    assert legacy_final_script._STRUCTURAL_METADATA_PATTERNS is final_authoring._STRUCTURAL_METADATA_PATTERNS
    assert "_status_strength_preserved" not in runtime.__all__
    assert runtime.audit_final_script is legacy_final_script.audit_final_script
    assert facade.audit_final_script is legacy_final_script.audit_final_script


def test_final_script_runtime_routes_lean_helpers_to_focused_module() -> None:
    for name in _LEAN_HELPERS:
        focused = getattr(final_lean, name)
        assert getattr(legacy_final_script, name) is focused
        assert legacy_final_script.audit_final_script.__globals__[name] is focused

    for name in _PUBLIC_LEAN_HELPERS:
        focused = getattr(final_lean, name)
        assert getattr(runtime, name) is focused
        assert getattr(facade, name) is focused

    assert "_onscreen_surface" not in runtime.__all__


def test_final_script_public_facades_use_runtime_router() -> None:
    package_init = (ROOT / "script_engine" / "analysis_audits" / "__init__.py").read_text(encoding="utf-8")
    compatibility = (ROOT / "script_engine" / "analysis_audit.py").read_text(encoding="utf-8")
    runtime_source = (ROOT / "script_engine" / "analysis_audits" / "final_script_runtime.py").read_text(encoding="utf-8")

    assert "from .final_script_runtime import audit_final_script" in package_init
    assert "from .analysis_audits.final_script_runtime import *" in compatibility
    assert "from .final_script import audit_final_script" not in package_init
    assert "from .analysis_audits.final_script import *" not in compatibility
    assert "for _focused in (_authoring, _lean):" in runtime_source
    assert "setattr(_legacy, _name, getattr(_focused, _name))" in runtime_source
    assert "globals()[_name] = getattr(_legacy, _name)" in runtime_source
