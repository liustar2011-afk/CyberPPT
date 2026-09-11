from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.voice_policy import (
    collect_voice_policy_diagnostics,
)


def _foundation() -> dict:
    return {
        "facts": [{"id": "F1", "statement": "来源事实用于说明执行安排。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _plan(*, audience_scope: str = "internal") -> dict:
    return {
        "audience_scope": audience_scope,
        "authoring_mode": "faithful",
        "delivery_mode": "presenter_led",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }


def _final(core_message: str) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"authoring_mode": "faithful", "delivery_mode": "presenter_led"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "执行安排",
                "source_refs": ["F1"],
                "core_message": core_message,
                "full_copy": "来源事实用于说明执行安排。",
                "onscreen": [
                    {"heading": "执行安排", "items": ["来源事实用于说明执行安排"]}
                ],
            }
        ],
    }


def test_internal_adviser_voice_has_one_structured_formal_owner() -> None:
    final_script = _final("建议贵司推进该项工作")
    plan = _plan()

    diagnostics = collect_voice_policy_diagnostics(final_script, plan)
    assert sum(
        diagnostic.code == "INTERNAL_EXPERT_VOICE_LEAK"
        for diagnostic in diagnostics
    ) == 1

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, _foundation()
    )

    assert sum("INTERNAL_EXPERT_VOICE_LEAK" in issue for issue in issues) == 1
    assert not any(
        "internal-expert voice required" in issue
        and "INTERNAL_EXPERT_VOICE_LEAK" not in issue
        for issue in issues
    )
    assert sum(
        diagnostic["code"] == "INTERNAL_EXPERT_VOICE_LEAK"
        for diagnostic in structured
    ) == 1


def test_raw_legacy_keeps_historical_internal_voice_blocker() -> None:
    final_script = _final("建议贵司推进该项工作")
    plan = _plan()

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        _foundation(),
        compatibility_mode=False,
    )

    assert any("internal-expert voice required" in issue for issue in issues)
    assert not any("INTERNAL_EXPERT_VOICE_LEAK" in issue for issue in issues)


def test_external_audience_does_not_apply_internal_voice_policy() -> None:
    final_script = _final("建议贵司推进该项工作")
    plan = _plan(audience_scope="external")

    diagnostics = collect_voice_policy_diagnostics(final_script, plan)

    assert not any(
        diagnostic.code == "INTERNAL_EXPERT_VOICE_LEAK"
        for diagnostic in diagnostics
    )


def test_normal_internal_voice_passes_policy() -> None:
    final_script = _final("推进该项工作并明确执行安排")
    plan = _plan()

    diagnostics = collect_voice_policy_diagnostics(final_script, plan)

    assert not any(
        diagnostic.code == "INTERNAL_EXPERT_VOICE_LEAK"
        for diagnostic in diagnostics
    )
