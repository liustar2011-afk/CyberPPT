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
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [
            {
                "id": "N1",
                "value": 2028,
                "unit": "年",
            }
        ],
    }


def _legacy_case(full_copy: str) -> tuple[dict, dict, dict]:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "兼容脚本",
            "communication_goal": "验证历史脚本保护信息",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "实施要求",
                "source_refs": ["F1"],
                "full_copy": full_copy,
                "onscreen": [{"heading": "实施要求", "text": "历史兼容内容"}],
            }
        ],
    }
    plan = {
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ]
    }
    foundation = {
        "source_consumption_policy": "required",
        "facts": [
            {
                "id": "F1",
                "statement": "相关要求自2026年7月1日起施行，由项目单位在经批准后实施。",
                "number_refs": ["N1"],
                "conditions": ["经批准后实施"],
                "entity_refs": ["E1"],
            }
        ],
        "concepts": [],
        "entities": [{"id": "E1", "name": "项目单位"}],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [
            {
                "id": "N1",
                "value": "2026年7月1日",
                "unit": "时间",
            }
        ],
    }
    return final_script, plan, foundation


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


def test_time_like_unit_is_not_appended_to_an_exact_date_literal() -> None:
    foundation = _foundation()
    foundation["facts"][0].pop("protected_literals")
    foundation["numbers"][0]["value"] = "2026年7月1日"
    foundation["numbers"][0]["unit"] = "时间"

    diagnostics = collect_protected_payload_diagnostics(
        _final("项目单位经批准后实施，自2026年7月1日起执行。"),
        foundation,
    )

    assert diagnostics == []


def test_legacy_v10_exact_date_loss_blocks_but_actor_and_condition_route_to_review() -> None:
    final_script, plan, foundation = _legacy_case("相关安排后续执行。")

    diagnostics = collect_protected_payload_diagnostics(
        final_script,
        foundation,
        plan,
    )

    by_code = {finding.code: finding for finding in diagnostics}
    assert by_code["PROTECTED_NUMBER_MISSING"].severity == "blocking"
    assert by_code["PROTECTED_NUMBER_MISSING"].evidence_refs == ("F1",)
    assert by_code["PROTECTED_NUMBER_MISSING"].target == "full_copy"
    assert by_code["PROTECTED_CONDITION_REVIEW_REQUIRED"].severity == "review_required"
    assert by_code["PROTECTED_ACTOR_REVIEW_REQUIRED"].severity == "review_required"
    assert "项目单位" in by_code["PROTECTED_ACTOR_REVIEW_REQUIRED"].message


def test_legacy_v10_typed_protected_payload_passes_when_preserved() -> None:
    final_script, plan, foundation = _legacy_case(
        "相关要求自2026年7月1日起施行，由项目单位在经批准后实施。"
    )

    diagnostics = collect_protected_payload_diagnostics(
        final_script,
        foundation,
        plan,
    )

    assert diagnostics == []
