from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.content_route import (
    collect_content_route_diagnostics,
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


def _plan(signal: str) -> dict:
    return {
        "authoring_mode": "faithful",
        "delivery_mode": "presenter_led",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
                "content_route": {"meaning_signals": [signal]},
            }
        ],
    }


def _final(text: str) -> dict:
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
                "full_copy": text,
                "onscreen": [{"heading": "执行安排", "items": [text]}],
            }
        ],
    }


def test_missing_meaning_signal_has_one_structured_formal_owner() -> None:
    signal = "保留关键执行条件"
    final_script = _final("来源事实用于说明执行安排。")
    plan = _plan(signal)

    diagnostics = collect_content_route_diagnostics(final_script, plan)
    assert sum(
        diagnostic.code == "CONTENT_ROUTE_MEANING_SIGNAL_MISSING"
        for diagnostic in diagnostics
    ) == 1

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, _foundation()
    )

    assert sum(
        "CONTENT_ROUTE_MEANING_SIGNAL_MISSING" in issue for issue in issues
    ) == 1
    assert not any(
        "content_route meaning signal" in issue and "CONTENT_ROUTE_MEANING_SIGNAL_MISSING" not in issue
        for issue in issues
    )
    assert sum(
        diagnostic["code"] == "CONTENT_ROUTE_MEANING_SIGNAL_MISSING"
        for diagnostic in structured
    ) == 1


def test_raw_legacy_keeps_historical_content_route_blocker() -> None:
    signal = "保留关键执行条件"
    final_script = _final("来源事实用于说明执行安排。")
    plan = _plan(signal)

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        _foundation(),
        compatibility_mode=False,
    )

    assert any(
        f"content_route meaning signal '{signal}' is absent from final copy" in issue
        for issue in issues
    )


def test_present_meaning_signal_passes_structured_content_route_check() -> None:
    signal = "保留关键执行条件"
    final_script = _final(f"来源事实用于说明执行安排，并{signal}。")
    plan = _plan(signal)

    diagnostics = collect_content_route_diagnostics(final_script, plan)

    assert not any(
        diagnostic.code == "CONTENT_ROUTE_MEANING_SIGNAL_MISSING"
        for diagnostic in diagnostics
    )
