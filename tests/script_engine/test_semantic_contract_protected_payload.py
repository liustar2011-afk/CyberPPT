from __future__ import annotations

from script_engine.semantic_contract import collect_protected_payload_diagnostics


def _final(text: str) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1", "N1"],
                "onscreen": [
                    {
                        "id": "M01-01",
                        "heading": "项目边界",
                        "text": text,
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


def _foundation() -> dict:
    return {
        "facts": [
            {
                "id": "F1",
                "statement": "示例事实",
                "protected_literals": ["GB/T 13016"],
                "number_refs": ["N1"],
                "conditions": ["经批准后实施"],
                "actors": ["项目单位"],
            }
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
        "numbers": [
            {
                "id": "N1",
                "value": 2028,
                "unit": "年",
            }
        ],
    }


def test_exact_protected_literal_and_number_are_blocking_when_missing() -> None:
    diagnostics = collect_protected_payload_diagnostics(
        _final("项目单位经批准后实施。"),
        _foundation(),
    )

    blocking_codes = {
        finding.code for finding in diagnostics if finding.severity == "blocking"
    }
    assert "PROTECTED_LITERAL_MISSING" in blocking_codes
    assert "PROTECTED_NUMBER_MISSING" in blocking_codes


def test_protected_values_pass_when_preserved_in_module_aggregate_copy() -> None:
    diagnostics = collect_protected_payload_diagnostics(
        _final("项目单位经批准后实施，按 GB/T 13016 要求推进至2028年。"),
        _foundation(),
    )

    assert diagnostics == []


def test_actor_and_condition_nonverbatim_cases_route_to_review() -> None:
    foundation = _foundation()
    foundation["facts"][0].pop("protected_literals")
    foundation["facts"][0].pop("number_refs")

    diagnostics = collect_protected_payload_diagnostics(
        _final("相关主体在获得审批之后执行。"),
        foundation,
    )

    assert {finding.code for finding in diagnostics} == {
        "PROTECTED_ACTOR_REVIEW_REQUIRED",
        "PROTECTED_CONDITION_REVIEW_REQUIRED",
    }
    assert all(finding.severity == "review_required" for finding in diagnostics)
