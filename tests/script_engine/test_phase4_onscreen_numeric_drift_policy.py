from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract


def _case(onscreen_text: str, *, source_statement: str) -> tuple[dict, dict, dict]:
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
                "full_copy": "来源事实用于说明服务输出。",
                "onscreen": [
                    {"heading": "服务输出", "text": onscreen_text}
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
        "facts": [{"id": "F1", "statement": source_statement}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }
    return final_script, plan, foundation


def test_raw_legacy_still_blocks_number_present_onscreen_but_absent_from_full_copy() -> None:
    final_script, plan, foundation = _case(
        "来源事实包含7项服务输出。",
        source_statement="来源事实包含7项服务输出。",
    )

    issues, _ = audit_legacy_final_script(final_script, plan, foundation)

    assert any("AUTHOR_ONSCREEN_PROTECTED_FACT_DRIFTED" in issue for issue in issues)


def test_single_semantic_entry_reviews_layer_drift_when_foundation_supports_number() -> None:
    final_script, plan, foundation = _case(
        "来源事实包含7项服务输出。",
        source_statement="来源事实包含7项服务输出。",
    )

    issues, warnings, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert not any("AUTHOR_ONSCREEN_PROTECTED_FACT_DRIFTED" in issue for issue in issues)
    assert not any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue and "7" in issue
        for issue in issues
    )
    assert any(
        "LEGACY_ONSCREEN_PROTECTED_FACT_REVIEW_REQUIRED" in warning
        and "7项" in warning
        for warning in warnings
    )


def test_single_semantic_entry_still_blocks_onscreen_number_absent_from_foundation() -> None:
    final_script, plan, foundation = _case(
        "来源事实包含9项服务输出。",
        source_statement="来源事实用于说明服务输出。",
    )

    issues, _, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue and "9" in issue
        for issue in issues
    )
