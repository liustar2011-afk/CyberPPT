from __future__ import annotations

import script_engine.analysis_audits.final_orchestrator as legacy_orchestrator
from script_engine.semantic_contract import audit_final_script_semantic_contract


def test_formal_semantic_audit_never_accepts_legacy_blocking_authority(
    monkeypatch,
) -> None:
    def fake_legacy_audit(*args, **kwargs):
        assert kwargs.get("compatibility_mode") is True
        return ["LEGACY_ONLY_BLOCKER: old implementation disagrees"], [
            "LEGACY_EXISTING_WARNING: review this"
        ]

    monkeypatch.setattr(
        legacy_orchestrator,
        "audit_final_script",
        fake_legacy_audit,
    )

    issues, warnings, structured = audit_final_script_semantic_contract(
        {
            "contract": "cyberppt.final-script",
            "version": "1.0",
            "deck": {"authoring_mode": "faithful", "delivery_mode": "presenter_led"},
            "slides": [],
        },
        {
            "authoring_mode": "faithful",
            "delivery_mode": "presenter_led",
            "pages": [],
        },
        {
            "facts": [],
            "concepts": [],
            "entities": [],
            "relations": [],
            "arguments": [],
            "constraints": [],
            "numbers": [],
            "source_structure": [],
        },
    )

    assert not any("LEGACY_ONLY_BLOCKER" in issue for issue in issues)
    assert any(
        warning
        == "[LEGACY_COMPATIBILITY_REVIEW_REQUIRED] LEGACY_ONLY_BLOCKER: old implementation disagrees"
        for warning in warnings
    )
    assert "LEGACY_EXISTING_WARNING: review this" in warnings
    assert structured == []
