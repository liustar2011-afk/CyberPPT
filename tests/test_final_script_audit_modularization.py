from __future__ import annotations

from pathlib import Path

import script_engine.analysis_audit as facade
import script_engine.analysis_audits.final_authoring as final_authoring
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


def test_final_script_runtime_routes_authoring_helpers_to_focused_module() -> None:
    for name in _AUTHORING_HELPERS:
        focused = getattr(final_authoring, name)
        assert getattr(legacy_final_script, name) is focused
        assert getattr(runtime, name) is focused
        assert getattr(facade, name) is focused
        assert legacy_final_script.audit_final_script.__globals__[name] is focused

    assert legacy_final_script._STATUS_PRESERVATION_MARKERS is final_authoring._STATUS_PRESERVATION_MARKERS
    assert legacy_final_script._STRUCTURAL_METADATA_PATTERNS is final_authoring._STRUCTURAL_METADATA_PATTERNS
    assert runtime.audit_final_script is legacy_final_script.audit_final_script
    assert facade.audit_final_script is legacy_final_script.audit_final_script


def test_final_script_public_facades_use_runtime_router() -> None:
    package_init = (ROOT / "script_engine" / "analysis_audits" / "__init__.py").read_text(encoding="utf-8")
    compatibility = (ROOT / "script_engine" / "analysis_audit.py").read_text(encoding="utf-8")
    runtime_source = (ROOT / "script_engine" / "analysis_audits" / "final_script_runtime.py").read_text(encoding="utf-8")

    assert "from .final_script_runtime import audit_final_script" in package_init
    assert "from .analysis_audits.final_script_runtime import *" in compatibility
    assert "from .final_script import audit_final_script" not in package_init
    assert "from .analysis_audits.final_script import *" not in compatibility
    assert "setattr(_legacy, _name, getattr(_authoring, _name))" in runtime_source
    assert "globals()[_name] = getattr(_legacy, _name)" in runtime_source
