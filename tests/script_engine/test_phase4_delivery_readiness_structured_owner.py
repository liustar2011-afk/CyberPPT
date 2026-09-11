from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.delivery_readiness import (
    collect_delivery_readiness_diagnostics,
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


def _plan(*, delivery_mode: str = "self_read", content_load: str = "standard") -> dict:
    return {
        "authoring_mode": "faithful",
        "delivery_mode": delivery_mode,
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "content_load": content_load,
                "source_refs": ["F1"],
            }
        ],
    }


def _final(*, delivery_mode: str = "self_read", onscreen: list[dict] | None = None) -> dict:
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
                "full_copy": "来源事实用于说明执行安排。",
                "onscreen": onscreen or [],
            }
        ],
    }


def test_missing_self_read_payload_has_one_structured_formal_owner() -> None:
    final_script = _final()
    plan = _plan()

    diagnostics = collect_delivery_readiness_diagnostics(final_script, plan)
    assert sum(
        diagnostic.code == "ONSCREEN_SELF_READ_PAYLOAD_MISSING"
        for diagnostic in diagnostics
    ) == 1

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, _foundation()
    )

    assert sum(
        "ONSCREEN_SELF_READ_PAYLOAD_MISSING" in issue for issue in issues
    ) == 1
    assert sum(
        diagnostic["code"] == "ONSCREEN_SELF_READ_PAYLOAD_MISSING"
        for diagnostic in structured
    ) == 1


def test_raw_legacy_keeps_historical_self_read_payload_blocker() -> None:
    final_script = _final()
    plan = _plan()

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        _foundation(),
        compatibility_mode=False,
    )

    assert any("ONSCREEN_SELF_READ_PAYLOAD_MISSING" in issue for issue in issues)


def test_light_self_read_page_may_omit_reader_facing_modules() -> None:
    diagnostics = collect_delivery_readiness_diagnostics(
        _final(),
        _plan(content_load="light"),
    )

    assert not any(
        diagnostic.code == "ONSCREEN_SELF_READ_PAYLOAD_MISSING"
        for diagnostic in diagnostics
    )


def test_presenter_led_page_does_not_require_self_read_payload() -> None:
    diagnostics = collect_delivery_readiness_diagnostics(
        _final(delivery_mode="presenter_led"),
        _plan(delivery_mode="presenter_led"),
    )

    assert not any(
        diagnostic.code == "ONSCREEN_SELF_READ_PAYLOAD_MISSING"
        for diagnostic in diagnostics
    )
