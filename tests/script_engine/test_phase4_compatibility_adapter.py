from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)


def _strict_source_case() -> tuple[dict, dict, dict]:
    final_script = {
        "deck": {"authoring_mode": "faithful"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": [],
                "full_copy": "来源事实。",
                "onscreen": [{"heading": "来源事实", "text": "来源事实"}],
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
        "source_consumption_policy": "required",
        "facts": [{"id": "F1", "statement": "来源事实。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }
    return final_script, plan, foundation


def _relationship_case() -> tuple[dict, dict, dict]:
    final_script = {
        "deck": {"authoring_mode": "faithful"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "full_copy": "数据输入支撑服务输出。",
                "onscreen": [{"heading": "服务关系", "text": "数据输入支撑服务输出"}],
                "relationships": [{"from": "数据输入", "relation": "支撑"}],
            }
        ],
    }
    plan = {
        "authoring_mode": "faithful",
        "pages": [{"id": "P01", "page_role": "content", "source_refs": []}],
    }
    foundation = {
        "facts": [],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }
    return final_script, plan, foundation


def test_raw_legacy_keeps_source_scope_blocker_but_compatibility_mode_suppresses_it() -> None:
    final_script, plan, foundation = _strict_source_case()

    raw_issues, _ = audit_legacy_final_script(final_script, plan, foundation)
    compatibility_issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=True,
    )

    assert any("AUTHOR_SOURCE_CONSUMPTION_MISSING" in issue for issue in raw_issues)
    assert not any(
        "AUTHOR_SOURCE_CONSUMPTION_MISSING" in issue
        for issue in compatibility_issues
    )


def test_raw_legacy_keeps_relationship_shape_blocker_but_compatibility_mode_suppresses_it() -> None:
    final_script, plan, foundation = _relationship_case()

    raw_issues, _ = audit_legacy_final_script(final_script, plan, foundation)
    compatibility_issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=True,
    )

    assert any("AUTHOR_RELATIONSHIP_NOT_MATERIALIZED" in issue for issue in raw_issues)
    assert not any(
        "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED" in issue
        for issue in compatibility_issues
    )
