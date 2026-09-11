from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract


def _objective_addition_case() -> tuple[dict, dict, dict]:
    final_script = {
        "deck": {"authoring_mode": "faithful"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "新增安排",
                "source_refs": ["F1"],
                "core_message": "新增99项要求并执行《新增管理办法》",
                "full_copy": "新增99项要求并执行《新增管理办法》。",
                "onscreen": [
                    {
                        "heading": "新增安排",
                        "text": "新增99项要求并执行《新增管理办法》",
                    }
                ],
            }
        ],
    }
    plan = {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "facts": [{"id": "F1", "statement": "来源事实仅说明既有安排。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }
    return final_script, plan, foundation


def test_raw_legacy_keeps_faithful_objective_addition_codes() -> None:
    final_script, plan, foundation = _objective_addition_case()

    issues, _ = audit_legacy_final_script(final_script, plan, foundation)

    assert any("FAITHFUL_NUMBER_ADDED" in issue for issue in issues)
    assert any("FAITHFUL_FORMAL_INSTRUMENT_ADDED" in issue for issue in issues)


def test_compatibility_mode_suppresses_migrated_faithful_objective_codes() -> None:
    final_script, plan, foundation = _objective_addition_case()

    issues, warnings = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=True,
    )

    assert not any("FAITHFUL_NUMBER_ADDED" in issue for issue in issues)
    assert not any("FAITHFUL_FORMAL_INSTRUMENT_ADDED" in issue for issue in issues)
    assert not any("FAITHFUL_NUMBER_ADDED" in warning for warning in warnings)
    assert not any(
        "FAITHFUL_FORMAL_INSTRUMENT_ADDED" in warning for warning in warnings
    )


def test_single_semantic_entry_uses_structured_objective_boundary_codes() -> None:
    final_script, plan, foundation = _objective_addition_case()

    issues, _, diagnostics = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any("FINAL_NUMBER_OUTSIDE_FOUNDATION" in issue for issue in issues)
    assert any(
        "FINAL_FORMAL_INSTRUMENT_OUTSIDE_FOUNDATION" in issue
        for issue in issues
    )
    assert not any("FAITHFUL_NUMBER_ADDED" in issue for issue in issues)
    assert not any("FAITHFUL_FORMAL_INSTRUMENT_ADDED" in issue for issue in issues)
    codes = {finding["code"] for finding in diagnostics}
    assert "FINAL_NUMBER_OUTSIDE_FOUNDATION" in codes
    assert "FINAL_FORMAL_INSTRUMENT_OUTSIDE_FOUNDATION" in codes
