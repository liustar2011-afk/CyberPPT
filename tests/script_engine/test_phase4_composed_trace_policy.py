from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract


def _case(full_copy: str) -> tuple[dict, dict, dict]:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"authoring_mode": "faithful"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "来源边界",
                "source_refs": ["F1"],
                "full_copy": full_copy,
                "onscreen": [{"heading": "来源边界", "text": full_copy}],
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
        "facts": [{"id": "F1", "statement": "来源事实用于说明边界。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }
    return final_script, plan, foundation


def test_raw_legacy_still_blocks_heuristic_identifier_drift() -> None:
    final_script, plan, foundation = _case(
        "来源事实用于说明边界，并采用 AlphaModel 处理。"
    )

    issues, _ = audit_legacy_final_script(final_script, plan, foundation)

    assert any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue
        and "AlphaModel" in issue
        for issue in issues
    )


def test_single_semantic_entry_routes_heuristic_identifier_drift_to_review() -> None:
    final_script, plan, foundation = _case(
        "来源事实用于说明边界，并采用 AlphaModel 处理。"
    )

    issues, warnings, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert not any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue
        and "AlphaModel" in issue
        for issue in issues
    )
    assert any(
        "COMPOSED_TRACE_IDENTIFIER_REVIEW_REQUIRED" in warning
        and "AlphaModel" in warning
        for warning in warnings
    )


def test_raw_legacy_still_blocks_unknown_number_with_composed_trace() -> None:
    final_script, plan, foundation = _case(
        "来源事实用于说明边界，并新增99项处理要求。"
    )

    issues, _ = audit_legacy_final_script(final_script, plan, foundation)

    assert any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue
        and "99" in issue
        for issue in issues
    )


def test_single_semantic_entry_owns_unknown_number_blocker() -> None:
    final_script, plan, foundation = _case(
        "来源事实用于说明边界，并新增99项处理要求。"
    )

    issues, warnings, diagnostics = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any(
        "[FINAL_NUMBER_OUTSIDE_FOUNDATION]" in issue
        and "99" in issue
        for issue in issues
    )
    assert not any("COMPOSED_TRACE_SOURCE_BOUNDARY" in issue for issue in issues)
    assert any(
        diagnostic["code"] == "FINAL_NUMBER_OUTSIDE_FOUNDATION"
        and "99" in diagnostic["reason"]
        for diagnostic in diagnostics
    )
    assert not any(
        "COMPOSED_TRACE_IDENTIFIER_REVIEW_REQUIRED" in warning
        for warning in warnings
    )
