from __future__ import annotations

from script_engine.semantic_contract import collect_visibility_diagnostics


def _legacy_external(value_text: str, *, visibility: str | None = "internal_only") -> tuple[dict, dict, dict]:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "full_copy": value_text,
                "onscreen": [{"heading": "结论", "text": value_text}],
            }
        ],
    }
    plan = {
        "audience_scope": "external",
        "pages": [{"id": "P01", "page_role": "content", "source_refs": ["F1"]}],
    }
    fact = {
        "id": "F1",
        "statement": "内部分析形成参考值37.5%。",
        "value": "37.5%",
    }
    if visibility is not None:
        fact["visibility"] = visibility
    foundation = {
        "facts": [fact],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    return final_script, plan, foundation


def test_external_v10_exact_internal_value_exposure_is_blocking() -> None:
    final_script, plan, foundation = _legacy_external("对外结论引用37.5%。")

    diagnostics = collect_visibility_diagnostics(final_script, plan, foundation)

    assert len(diagnostics) == 1
    finding = diagnostics[0]
    assert finding.code == "INTERNAL_PROTECTED_VALUE_EXPOSED"
    assert finding.severity == "blocking"
    assert finding.evidence_refs == ("F1",)
    assert "37.5%" in finding.message


def test_external_v10_internal_reference_without_exact_value_routes_to_review() -> None:
    final_script, plan, foundation = _legacy_external("内部分析仅用于形成综合判断。")

    diagnostics = collect_visibility_diagnostics(final_script, plan, foundation)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "INTERNAL_EVIDENCE_EXTERNAL_REVIEW_REQUIRED"
    assert diagnostics[0].severity == "review_required"


def test_visibility_contract_does_not_infer_internal_status_from_text_markers() -> None:
    final_script, plan, foundation = _legacy_external(
        "内部测算参考值为37.5%。",
        visibility=None,
    )
    foundation["facts"][0]["statement"] = "内部测算参考值为37.5%。"

    assert collect_visibility_diagnostics(final_script, plan, foundation) == []


def test_restricted_is_not_silently_redefined_as_internal_only() -> None:
    final_script, plan, foundation = _legacy_external(
        "对外结论引用37.5%。",
        visibility="restricted",
    )

    assert collect_visibility_diagnostics(final_script, plan, foundation) == []


def test_non_external_audience_is_outside_this_gate() -> None:
    final_script, plan, foundation = _legacy_external("对外结论引用37.5%。")
    plan["audience_scope"] = "internal"

    assert collect_visibility_diagnostics(final_script, plan, foundation) == []


def test_v11_uses_module_provenance_to_identify_internal_evidence() -> None:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "onscreen": [
                    {
                        "id": "M01",
                        "heading": "分析结果",
                        "text": "关键指标为37.5%",
                        "provenance": {
                            "derivation": "direct",
                            "claim_refs": ["F1"],
                            "bindings": [
                                {
                                    "target": "heading",
                                    "source_refs": ["F1"],
                                    "relation": "expresses",
                                },
                                {
                                    "target": "text",
                                    "source_refs": ["F1"],
                                    "relation": "expresses",
                                },
                            ],
                        },
                    }
                ],
            }
        ],
    }
    plan = {
        "audience_scope": "external",
        "pages": [{"id": "P01", "page_role": "content", "source_refs": ["F1"]}],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "关键指标为37.5%。",
                "number_refs": ["N1"],
                "visibility": "internal_only",
            }
        ],
        "numbers": [{"id": "N1", "value": "37.5", "unit": "%"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
    }

    diagnostics = collect_visibility_diagnostics(final_script, plan, foundation)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "INTERNAL_PROTECTED_VALUE_EXPOSED"
    assert diagnostics[0].severity == "blocking"
