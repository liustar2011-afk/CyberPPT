from __future__ import annotations

from pathlib import Path

import script_engine.analysis_audit as facade
import script_engine.analysis_audits.final_authoring as final_authoring
import script_engine.analysis_audits.final_deck as final_deck
import script_engine.analysis_audits.final_lean as final_lean
import script_engine.analysis_audits.final_onscreen as final_onscreen
import script_engine.analysis_audits.final_orchestrator as final_orchestrator
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
_ONSCREEN_HELPERS = (
    "_audit_authored_onscreen_composition",
    "_semantic_payload_units",
    "_audit_self_reading_density",
    "_audit_authored_onscreen_contract",
)
_DECK_HELPERS = (
    "_source_text_for_refs",
    "_normalize_source_chapter_title",
    "_whole_deck_authoring_warnings",
)
_PUBLIC_AUTHORING_HELPERS = tuple(
    name for name in _AUTHORING_HELPERS if name in legacy_final_script.__all__
)
_PUBLIC_LEAN_HELPERS = tuple(
    name for name in _LEAN_HELPERS if name in legacy_final_script.__all__
)
_PUBLIC_ONSCREEN_HELPERS = tuple(
    name for name in _ONSCREEN_HELPERS if name in legacy_final_script.__all__
)
_PUBLIC_DECK_HELPERS = tuple(
    name for name in _DECK_HELPERS if name in legacy_final_script.__all__
)


def _assert_legacy_routes(names: tuple[str, ...], module: object) -> None:
    for name in names:
        assert getattr(legacy_final_script, name) is getattr(module, name)


def _assert_public_facades_route(names: tuple[str, ...], module: object) -> None:
    for name in names:
        focused = getattr(module, name)
        assert getattr(runtime, name) is focused
        assert getattr(facade, name) is focused


def test_final_script_runtime_routes_authoring_helpers_to_focused_module() -> None:
    _assert_legacy_routes(_AUTHORING_HELPERS, final_authoring)
    _assert_public_facades_route(_PUBLIC_AUTHORING_HELPERS, final_authoring)
    assert legacy_final_script._STATUS_PRESERVATION_MARKERS is final_authoring._STATUS_PRESERVATION_MARKERS
    assert legacy_final_script._STRUCTURAL_METADATA_PATTERNS is final_authoring._STRUCTURAL_METADATA_PATTERNS
    assert "_status_strength_preserved" not in runtime.__all__


def test_final_script_runtime_routes_lean_helpers_to_focused_module() -> None:
    _assert_legacy_routes(_LEAN_HELPERS, final_lean)
    _assert_public_facades_route(_PUBLIC_LEAN_HELPERS, final_lean)
    assert "_onscreen_surface" not in runtime.__all__


def test_final_script_runtime_routes_onscreen_helpers_to_focused_module() -> None:
    _assert_legacy_routes(_ONSCREEN_HELPERS, final_onscreen)
    _assert_public_facades_route(_PUBLIC_ONSCREEN_HELPERS, final_onscreen)


def test_final_script_runtime_routes_deck_helpers_to_focused_module() -> None:
    _assert_legacy_routes(_DECK_HELPERS, final_deck)
    _assert_public_facades_route(_PUBLIC_DECK_HELPERS, final_deck)


def test_final_script_runtime_routes_orchestrator_to_focused_module() -> None:
    focused = final_orchestrator.audit_final_script
    assert legacy_final_script.audit_final_script is focused
    assert runtime.audit_final_script is focused
    assert facade.audit_final_script is focused

    expected_globals = {
        "_slide_text": final_authoring._slide_text,
        "_audit_authored_content_coverage": final_authoring._audit_authored_content_coverage,
        "_authored_bare_label_detail_issues": final_authoring._authored_bare_label_detail_issues,
        "_author_execution_issues": final_authoring._author_execution_issues,
        "_onscreen_expression_warnings": final_authoring._onscreen_expression_warnings,
        "_audit_lean_authored_source_consumption": final_lean._audit_lean_authored_source_consumption,
        "_audit_lean_onscreen_full_copy_alignment": final_lean._audit_lean_onscreen_full_copy_alignment,
        "_audit_lean_relationship_visibility": final_lean._audit_lean_relationship_visibility,
        "_audit_authored_onscreen_composition": final_onscreen._audit_authored_onscreen_composition,
        "_audit_self_reading_density": final_onscreen._audit_self_reading_density,
        "_audit_authored_onscreen_contract": final_onscreen._audit_authored_onscreen_contract,
        "_source_text_for_refs": final_deck._source_text_for_refs,
        "_normalize_source_chapter_title": final_deck._normalize_source_chapter_title,
        "_whole_deck_authoring_warnings": final_deck._whole_deck_authoring_warnings,
    }
    for name, value in expected_globals.items():
        assert focused.__globals__[name] is value


def test_final_script_public_facades_use_runtime_router() -> None:
    package_init = (ROOT / "script_engine" / "analysis_audits" / "__init__.py").read_text(encoding="utf-8")
    compatibility = (ROOT / "script_engine" / "analysis_audit.py").read_text(encoding="utf-8")
    runtime_source = (ROOT / "script_engine" / "analysis_audits" / "final_script_runtime.py").read_text(encoding="utf-8")

    assert "from .final_script_runtime import audit_final_script" in package_init
    assert "from .analysis_audits.final_script_runtime import *" in compatibility
    assert "from .final_script import audit_final_script" not in package_init
    assert "from .analysis_audits.final_script import *" not in compatibility
    assert "for _focused in (_authoring, _lean, _onscreen, _deck):" in runtime_source
    assert "_legacy.audit_final_script = _orchestrator.audit_final_script" in runtime_source
    assert "globals()[_name] = getattr(_legacy, _name)" in runtime_source
