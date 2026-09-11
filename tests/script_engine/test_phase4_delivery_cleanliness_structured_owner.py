from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.delivery_cleanliness import (
    collect_delivery_cleanliness_diagnostics,
)


def _foundation(statement: str = "来源事实用于说明执行安排。") -> dict:
    return {
        "facts": [{"id": "F1", "statement": statement}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _plan(*, delivery_mode: str = "presenter_led", expression_mode: str = "mixed") -> dict:
    return {
        "authoring_mode": "faithful",
        "delivery_mode": delivery_mode,
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
                "onscreen_contract": {"expression_mode": expression_mode},
            }
        ],
    }


def _final(
    *,
    full_copy: str,
    delivery_mode: str = "presenter_led",
    items: list[str] | None = None,
) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"authoring_mode": "faithful", "delivery_mode": delivery_mode},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "执行安排",
                "source_refs": ["F1"],
                "full_copy": full_copy,
                "onscreen": [
                    {"heading": "执行安排", "items": items or [full_copy]}
                ],
            }
        ],
    }


def test_structural_metadata_leak_has_one_structured_formal_owner() -> None:
    foundation = _foundation("目录")
    plan = _plan()
    final_script = _final(full_copy="目录")

    diagnostics = collect_delivery_cleanliness_diagnostics(
        final_script, plan, foundation
    )
    assert sum(
        diagnostic.code == "AUTHOR_STRUCTURAL_METADATA_LEAK"
        for diagnostic in diagnostics
    ) == 1

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, foundation
    )
    assert sum("AUTHOR_STRUCTURAL_METADATA_LEAK" in issue for issue in issues) == 1
    assert sum(
        diagnostic["code"] == "AUTHOR_STRUCTURAL_METADATA_LEAK"
        for diagnostic in structured
    ) == 1


def test_raw_legacy_keeps_structural_metadata_blocker() -> None:
    foundation = _foundation("目录")
    plan = _plan()
    final_script = _final(full_copy="目录")

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=False,
    )

    assert any("AUTHOR_STRUCTURAL_METADATA_LEAK" in issue for issue in issues)


def test_raw_table_fragment_has_one_structured_formal_owner() -> None:
    foundation = _foundation()
    plan = _plan(delivery_mode="self_read", expression_mode="phrase_led")
    final_script = _final(
        full_copy="来源事实用于说明执行安排。",
        delivery_mode="self_read",
        items=["字段|取值"],
    )

    diagnostics = collect_delivery_cleanliness_diagnostics(
        final_script, plan, foundation
    )
    assert sum(
        diagnostic.code == "AUTHOR_ONSCREEN_TABLE_FRAGMENT"
        for diagnostic in diagnostics
    ) == 1

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, foundation
    )
    assert sum("AUTHOR_ONSCREEN_TABLE_FRAGMENT" in issue for issue in issues) == 1
    assert sum(
        diagnostic["code"] == "AUTHOR_ONSCREEN_TABLE_FRAGMENT"
        for diagnostic in structured
    ) == 1


def test_raw_legacy_keeps_table_fragment_blocker() -> None:
    foundation = _foundation()
    plan = _plan(delivery_mode="self_read", expression_mode="phrase_led")
    final_script = _final(
        full_copy="来源事实用于说明执行安排。",
        delivery_mode="self_read",
        items=["字段|取值"],
    )

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=False,
    )

    assert any("AUTHOR_ONSCREEN_TABLE_FRAGMENT" in issue for issue in issues)
